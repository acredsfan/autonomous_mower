"""
Asynchronous Resource Manager for the autonomous mower.

This module provides an enhanced resource management system with:
- Asynchronous initialization and cleanup
- Resource pooling for I2C connections and serial ports
- Connection lifecycle management with automatic cleanup
- Health monitoring and automatic recovery mechanisms
"""

import asyncio
import logging
import threading
import time
import weakref
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Callable, Union
from pathlib import Path

from mower.utilities.logger_config import LoggerConfigInfo

logger = LoggerConfigInfo.get_logger(__name__)


class ResourceState(Enum):
    """Resource operational states"""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    FAILED = "failed"
    CLEANUP = "cleanup"


@dataclass
class ResourceHealth:
    """Resource health tracking information"""
    state: ResourceState = ResourceState.UNINITIALIZED
    last_check: Optional[datetime] = None
    error_count: int = 0
    consecutive_errors: int = 0
    last_error: Optional[str] = None
    uptime_start: Optional[datetime] = None
    recovery_attempts: int = 0
    max_recovery_attempts: int = 3
    
    def is_healthy(self) -> bool:
        """Check if resource is in a healthy state"""
        return self.state in (ResourceState.OPERATIONAL, ResourceState.DEGRADED)
    
    def get_uptime(self) -> Optional[timedelta]:
        """Get resource uptime"""
        if self.uptime_start:
            return datetime.now() - self.uptime_start
        return None


@dataclass
class ResourcePool:
    """Resource pool for managing shared connections"""
    name: str
    max_size: int = 10
    min_size: int = 1
    idle_timeout: float = 300.0  # 5 minutes
    resources: List[Any] = field(default_factory=list)
    in_use: Set[Any] = field(default_factory=set)
    created_at: Dict[Any, datetime] = field(default_factory=dict)
    last_used: Dict[Any, datetime] = field(default_factory=dict)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    
    async def acquire(self, factory_func: Callable = None) -> Any:
        """Acquire a resource from the pool"""
        async with self.lock:
            # Try to get an available resource
            available = [r for r in self.resources if r not in self.in_use]
            
            if available:
                resource = available[0]
                self.in_use.add(resource)
                self.last_used[resource] = datetime.now()
                return resource
            
            # Create new resource if pool not at max capacity
            if len(self.resources) < self.max_size and factory_func:
                try:
                    resource = await factory_func()
                    self.resources.append(resource)
                    self.in_use.add(resource)
                    self.created_at[resource] = datetime.now()
                    self.last_used[resource] = datetime.now()
                    return resource
                except Exception as e:
                    logger.error(f"Failed to create resource for pool {self.name}: {e}")
                    raise
            
            # Wait for a resource to become available
            raise RuntimeError(f"Resource pool {self.name} exhausted")
    
    async def release(self, resource: Any):
        """Release a resource back to the pool"""
        async with self.lock:
            if resource in self.in_use:
                self.in_use.remove(resource)
                self.last_used[resource] = datetime.now()
    
    async def cleanup_idle(self):
        """Clean up idle resources"""
        async with self.lock:
            now = datetime.now()
            to_remove = []
            
            for resource in self.resources:
                if resource not in self.in_use:
                    last_used = self.last_used.get(resource, self.created_at.get(resource, now))
                    if (now - last_used).total_seconds() > self.idle_timeout:
                        to_remove.append(resource)
            
            for resource in to_remove:
                if len(self.resources) > self.min_size:
                    await self._cleanup_resource(resource)
                    self.resources.remove(resource)
                    self.created_at.pop(resource, None)
                    self.last_used.pop(resource, None)
    
    async def _cleanup_resource(self, resource: Any):
        """Clean up a single resource"""
        try:
            if hasattr(resource, 'close'):
                if asyncio.iscoroutinefunction(resource.close):
                    await resource.close()
                else:
                    resource.close()
            elif hasattr(resource, 'cleanup'):
                if asyncio.iscoroutinefunction(resource.cleanup):
                    await resource.cleanup()
                else:
                    resource.cleanup()
        except Exception as e:
            logger.warning(f"Error cleaning up resource: {e}")
    
    async def cleanup_all(self):
        """Clean up all resources in the pool"""
        async with self.lock:
            for resource in self.resources.copy():
                await self._cleanup_resource(resource)
            self.resources.clear()
            self.in_use.clear()
            self.created_at.clear()
            self.last_used.clear()


class AsyncResourceManager:
    """
    Enhanced asynchronous resource manager with pooling and health monitoring.
    """
    
    def __init__(self):
        self.logger = LoggerConfigInfo.get_logger(__name__)
        self._resources: Dict[str, Any] = {}
        self._resource_health: Dict[str, ResourceHealth] = {}
        self._resource_pools: Dict[str, ResourcePool] = {}
        self._initialization_order: List[str] = []
        self._cleanup_callbacks: Dict[str, List[Callable]] = {}
        self._health_check_callbacks: Dict[str, Callable] = {}
        self._recovery_strategies: Dict[str, Callable] = {}
        
        self._lock = asyncio.Lock()
        self._initialized = False
        self._health_monitor_task: Optional[asyncio.Task] = None
        self._pool_cleanup_task: Optional[asyncio.Task] = None
        
        # Configuration
        self._health_check_interval = 30.0  # seconds
        self._pool_cleanup_interval = 60.0  # seconds
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.cleanup()
    
    async def initialize(self):
        """Initialize the resource manager"""
        if self._initialized:
            self.logger.warning("AsyncResourceManager already initialized")
            return
        
        self.logger.info("Initializing AsyncResourceManager...")
        
        try:
            # Start background tasks
            self._health_monitor_task = asyncio.create_task(self._health_monitor_loop())
            self._pool_cleanup_task = asyncio.create_task(self._pool_cleanup_loop())
            
            self._initialized = True
            self.logger.info("AsyncResourceManager initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize AsyncResourceManager: {e}")
            await self.cleanup()
            raise
    
    async def cleanup(self):
        """Clean up all resources and stop background tasks"""
        if not self._initialized:
            return
        
        self.logger.info("Cleaning up AsyncResourceManager...")
        
        # Stop background tasks
        if self._health_monitor_task:
            self._health_monitor_task.cancel()
            try:
                await self._health_monitor_task
            except asyncio.CancelledError:
                pass
        
        if self._pool_cleanup_task:
            self._pool_cleanup_task.cancel()
            try:
                await self._pool_cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Clean up resources in reverse order
        async with self._lock:
            for resource_name in reversed(self._initialization_order):
                await self._cleanup_resource(resource_name)
            
            # Clean up all resource pools
            for pool in self._resource_pools.values():
                await pool.cleanup_all()
            
            self._resources.clear()
            self._resource_health.clear()
            self._resource_pools.clear()
            self._initialization_order.clear()
            self._cleanup_callbacks.clear()
            self._health_check_callbacks.clear()
            self._recovery_strategies.clear()
        
        self._initialized = False
        self.logger.info("AsyncResourceManager cleanup complete")
    
    async def register_resource(
        self,
        name: str,
        factory_func: Callable,
        cleanup_func: Optional[Callable] = None,
        health_check_func: Optional[Callable] = None,
        recovery_func: Optional[Callable] = None,
        max_recovery_attempts: int = 3
    ):
        """Register a resource with the manager"""
        async with self._lock:
            if name in self._resources:
                self.logger.warning(f"Resource {name} already registered")
                return
            
            # Initialize resource health tracking
            self._resource_health[name] = ResourceHealth(
                max_recovery_attempts=max_recovery_attempts
            )
            
            # Register callbacks
            if cleanup_func:
                self._cleanup_callbacks.setdefault(name, []).append(cleanup_func)
            if health_check_func:
                self._health_check_callbacks[name] = health_check_func
            if recovery_func:
                self._recovery_strategies[name] = recovery_func
            
            # Initialize the resource
            await self._initialize_resource(name, factory_func)
    
    async def _initialize_resource(self, name: str, factory_func: Callable):
        """Initialize a single resource"""
        health = self._resource_health[name]
        health.state = ResourceState.INITIALIZING
        
        try:
            self.logger.info(f"Initializing resource: {name}")
            
            # Call factory function
            if asyncio.iscoroutinefunction(factory_func):
                resource = await factory_func()
            else:
                # Run in executor for blocking calls
                loop = asyncio.get_running_loop()
                resource = await loop.run_in_executor(None, factory_func)
            
            if resource is not None:
                self._resources[name] = resource
                self._initialization_order.append(name)
                health.state = ResourceState.OPERATIONAL
                health.uptime_start = datetime.now()
                health.consecutive_errors = 0
                self.logger.info(f"Resource {name} initialized successfully")
            else:
                raise RuntimeError(f"Factory function returned None for {name}")
                
        except Exception as e:
            health.state = ResourceState.FAILED
            health.last_error = str(e)
            health.error_count += 1
            health.consecutive_errors += 1
            self.logger.error(f"Failed to initialize resource {name}: {e}")
            raise
    
    async def get_resource(self, name: str) -> Optional[Any]:
        """Get a resource by name"""
        async with self._lock:
            resource = self._resources.get(name)
            if resource is None:
                self.logger.warning(f"Resource {name} not found")
            return resource
    
    async def get_resource_health(self, name: str) -> Optional[ResourceHealth]:
        """Get health information for a resource"""
        return self._resource_health.get(name)
    
    async def create_resource_pool(
        self,
        name: str,
        factory_func: Callable,
        max_size: int = 10,
        min_size: int = 1,
        idle_timeout: float = 300.0
    ) -> ResourcePool:
        """Create a resource pool"""
        async with self._lock:
            if name in self._resource_pools:
                return self._resource_pools[name]
            
            pool = ResourcePool(
                name=name,
                max_size=max_size,
                min_size=min_size,
                idle_timeout=idle_timeout
            )
            
            # Pre-populate with minimum resources
            for _ in range(min_size):
                try:
                    if asyncio.iscoroutinefunction(factory_func):
                        resource = await factory_func()
                    else:
                        loop = asyncio.get_running_loop()
                        resource = await loop.run_in_executor(None, factory_func)
                    
                    pool.resources.append(resource)
                    pool.created_at[resource] = datetime.now()
                    pool.last_used[resource] = datetime.now()
                except Exception as e:
                    self.logger.error(f"Failed to pre-populate pool {name}: {e}")
            
            self._resource_pools[name] = pool
            self.logger.info(f"Created resource pool {name} with {len(pool.resources)} resources")
            return pool
    
    @asynccontextmanager
    async def acquire_from_pool(self, pool_name: str, factory_func: Callable = None):
        """Context manager for acquiring resources from a pool"""
        pool = self._resource_pools.get(pool_name)
        if not pool:
            raise ValueError(f"Resource pool {pool_name} not found")
        
        resource = await pool.acquire(factory_func)
        try:
            yield resource
        finally:
            await pool.release(resource)
    
    async def _cleanup_resource(self, name: str):
        """Clean up a single resource"""
        resource = self._resources.get(name)
        if not resource:
            return
        
        health = self._resource_health.get(name)
        if health:
            health.state = ResourceState.CLEANUP
        
        try:
            # Call registered cleanup callbacks
            callbacks = self._cleanup_callbacks.get(name, [])
            for callback in callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(resource)
                    else:
                        callback(resource)
                except Exception as e:
                    self.logger.warning(f"Error in cleanup callback for {name}: {e}")
            
            # Try standard cleanup methods
            if hasattr(resource, 'cleanup'):
                if asyncio.iscoroutinefunction(resource.cleanup):
                    await resource.cleanup()
                else:
                    resource.cleanup()
            elif hasattr(resource, 'close'):
                if asyncio.iscoroutinefunction(resource.close):
                    await resource.close()
                else:
                    resource.close()
            
            self.logger.info(f"Resource {name} cleaned up successfully")
            
        except Exception as e:
            self.logger.error(f"Error cleaning up resource {name}: {e}")
        finally:
            self._resources.pop(name, None)
            if name in self._initialization_order:
                self._initialization_order.remove(name)
    
    async def _health_monitor_loop(self):
        """Background task for monitoring resource health"""
        while True:
            try:
                await asyncio.sleep(self._health_check_interval)
                await self._check_all_health()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in health monitor loop: {e}")
    
    async def _check_all_health(self):
        """Check health of all resources"""
        async with self._lock:
            for name, resource in self._resources.items():
                await self._check_resource_health(name, resource)
    
    async def _check_resource_health(self, name: str, resource: Any):
        """Check health of a single resource"""
        health = self._resource_health.get(name)
        if not health:
            return
        
        health.last_check = datetime.now()
        
        try:
            # Use registered health check callback if available
            health_check = self._health_check_callbacks.get(name)
            if health_check:
                if asyncio.iscoroutinefunction(health_check):
                    is_healthy = await health_check(resource)
                else:
                    is_healthy = health_check(resource)
                
                if is_healthy:
                    if health.state == ResourceState.DEGRADED:
                        health.state = ResourceState.OPERATIONAL
                        self.logger.info(f"Resource {name} recovered to operational state")
                    health.consecutive_errors = 0
                else:
                    health.consecutive_errors += 1
                    if health.state == ResourceState.OPERATIONAL:
                        health.state = ResourceState.DEGRADED
                        self.logger.warning(f"Resource {name} degraded")
            
            # Attempt recovery if needed
            if health.consecutive_errors >= 3 and health.state != ResourceState.FAILED:
                await self._attempt_recovery(name, resource)
                
        except Exception as e:
            health.error_count += 1
            health.consecutive_errors += 1
            health.last_error = str(e)
            self.logger.error(f"Health check failed for resource {name}: {e}")
    
    async def _attempt_recovery(self, name: str, resource: Any):
        """Attempt to recover a failed resource"""
        health = self._resource_health.get(name)
        if not health or health.recovery_attempts >= health.max_recovery_attempts:
            health.state = ResourceState.FAILED
            self.logger.error(f"Resource {name} marked as failed after {health.recovery_attempts} recovery attempts")
            return
        
        recovery_func = self._recovery_strategies.get(name)
        if not recovery_func:
            return
        
        health.recovery_attempts += 1
        self.logger.info(f"Attempting recovery for resource {name} (attempt {health.recovery_attempts})")
        
        try:
            if asyncio.iscoroutinefunction(recovery_func):
                success = await recovery_func(resource)
            else:
                success = recovery_func(resource)
            
            if success:
                health.state = ResourceState.OPERATIONAL
                health.consecutive_errors = 0
                self.logger.info(f"Resource {name} recovered successfully")
            else:
                self.logger.warning(f"Recovery attempt failed for resource {name}")
                
        except Exception as e:
            self.logger.error(f"Recovery attempt failed for resource {name}: {e}")
    
    async def _pool_cleanup_loop(self):
        """Background task for cleaning up idle resources in pools"""
        while True:
            try:
                await asyncio.sleep(self._pool_cleanup_interval)
                for pool in self._resource_pools.values():
                    await pool.cleanup_idle()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in pool cleanup loop: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get overall status of the resource manager"""
        return {
            "initialized": self._initialized,
            "resource_count": len(self._resources),
            "pool_count": len(self._resource_pools),
            "resources": {
                name: {
                    "state": health.state.value,
                    "error_count": health.error_count,
                    "consecutive_errors": health.consecutive_errors,
                    "uptime": str(health.get_uptime()) if health.get_uptime() else None,
                    "last_error": health.last_error
                }
                for name, health in self._resource_health.items()
            },
            "pools": {
                name: {
                    "total_resources": len(pool.resources),
                    "in_use": len(pool.in_use),
                    "available": len(pool.resources) - len(pool.in_use)
                }
                for name, pool in self._resource_pools.items()
            }
        }