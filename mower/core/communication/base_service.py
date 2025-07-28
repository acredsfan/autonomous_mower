"""
Base service class for all microservices.

This module provides a common foundation for all microservices with
Redis communication, health monitoring, and graceful shutdown.
"""

import asyncio
import json
import logging
import signal
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, asdict
from enum import Enum
import redis.asyncio as redis

from mower.config.settings import get_config, SystemConfig


logger = logging.getLogger(__name__)


class ServiceState(Enum):
    """Service states."""
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class ServiceMessage:
    """Standard message format for inter-service communication."""
    service: str
    timestamp: float
    message_type: str
    data: Dict[str, Any]
    correlation_id: Optional[str] = None


@dataclass
class ServiceHealth:
    """Service health information."""
    service_name: str
    state: ServiceState
    timestamp: float
    uptime: float
    memory_usage: float
    cpu_usage: float
    last_error: Optional[str] = None


class BaseService(ABC):
    """Base class for all microservices."""
    
    def __init__(self, service_name: str, config: Optional[SystemConfig] = None):
        """Initialize base service.
        
        Args:
            service_name: Unique name for this service
            config: System configuration
        """
        self.service_name = service_name
        self.config = config or get_config()
        
        # Service state
        self.state = ServiceState.STARTING
        self.start_time = time.time()
        self.last_heartbeat = 0.0
        self.last_error: Optional[str] = None
        
        # Redis connection
        self.redis_client: Optional[redis.Redis] = None
        self.redis_url = self.config.services.redis_url
        
        # Event loop and shutdown
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.shutdown_event = asyncio.Event()
        self.tasks: List[asyncio.Task] = []
        
        # Message handlers
        self.message_handlers: Dict[str, Callable] = {}
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, initiating shutdown")
        if self.loop and self.loop.is_running():
            self.loop.create_task(self.shutdown())
    
    async def initialize(self) -> bool:
        """Initialize the service."""
        try:
            logger.info(f"Initializing {self.service_name} service")
            
            # Connect to Redis
            self.redis_client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
                retry_on_timeout=True
            )
            
            # Test Redis connection
            await self.redis_client.ping()
            logger.info(f"Connected to Redis at {self.redis_url}")
            
            # Initialize service-specific components
            if not await self.service_initialize():
                logger.error("Service-specific initialization failed")
                return False
            
            self.state = ServiceState.RUNNING
            logger.info(f"{self.service_name} service initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize {self.service_name}: {e}")
            self.last_error = str(e)
            self.state = ServiceState.ERROR
            return False
    
    async def run(self) -> None:
        """Run the service."""
        try:
            self.loop = asyncio.get_running_loop()
            
            if not await self.initialize():
                return
            
            # Start background tasks
            self.tasks = [
                asyncio.create_task(self._heartbeat_loop()),
                asyncio.create_task(self._message_loop()),
                asyncio.create_task(self.service_loop())
            ]
            
            logger.info(f"{self.service_name} service running")
            
            # Wait for shutdown
            await self.shutdown_event.wait()
            
        except Exception as e:
            logger.error(f"Error running {self.service_name}: {e}")
            self.last_error = str(e)
            self.state = ServiceState.ERROR
        finally:
            await self.cleanup()
    
    async def shutdown(self) -> None:
        """Shutdown the service gracefully."""
        logger.info(f"Shutting down {self.service_name} service")
        self.state = ServiceState.STOPPING
        
        # Signal shutdown
        self.shutdown_event.set()
        
        # Cancel all tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        
        # Service-specific cleanup
        await self.service_cleanup()
        
        # Close Redis connection
        if self.redis_client:
            await self.redis_client.close()
        
        self.state = ServiceState.STOPPED
        logger.info(f"{self.service_name} service stopped")
    
    async def cleanup(self) -> None:
        """Cleanup resources."""
        if self.state != ServiceState.STOPPED:
            await self.shutdown()
    
    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeats."""
        while not self.shutdown_event.is_set():
            try:
                await self.send_heartbeat()
                await asyncio.sleep(self.config.services.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                await asyncio.sleep(1)
    
    async def _message_loop(self) -> None:
        """Listen for incoming messages."""
        if not self.redis_client:
            return
        
        stream_name = f"service:{self.service_name}:messages"
        consumer_group = f"{self.service_name}_group"
        consumer_name = f"{self.service_name}_consumer"
        
        try:
            # Create consumer group
            try:
                await self.redis_client.xgroup_create(
                    stream_name, consumer_group, id="0", mkstream=True
                )
            except redis.ResponseError:
                # Group already exists
                pass
            
            while not self.shutdown_event.is_set():
                try:
                    # Read messages
                    messages = await self.redis_client.xreadgroup(
                        consumer_group,
                        consumer_name,
                        {stream_name: ">"},
                        count=10,
                        block=1000
                    )
                    
                    for stream, msgs in messages:
                        for msg_id, fields in msgs:
                            await self._handle_message(stream, msg_id, fields)
                            
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Message loop error: {e}")
                    await asyncio.sleep(1)
                    
        except Exception as e:
            logger.error(f"Message loop setup error: {e}")
    
    async def _handle_message(self, stream: str, msg_id: str, fields: Dict[str, str]) -> None:
        """Handle incoming message."""
        try:
            # Parse message
            message_data = json.loads(fields.get("data", "{}"))
            message = ServiceMessage(**message_data)
            
            # Call handler if exists
            handler = self.message_handlers.get(message.message_type)
            if handler:
                await handler(message)
            else:
                logger.warning(f"No handler for message type: {message.message_type}")
            
            # Acknowledge message
            if self.redis_client:
                await self.redis_client.xack(stream, f"{self.service_name}_group", msg_id)
                
        except Exception as e:
            logger.error(f"Error handling message {msg_id}: {e}")
    
    async def send_message(self, target_service: str, message_type: str, 
                          data: Dict[str, Any], correlation_id: Optional[str] = None) -> None:
        """Send message to another service."""
        if not self.redis_client:
            logger.error("Cannot send message: Redis not connected")
            return
        
        message = ServiceMessage(
            service=self.service_name,
            timestamp=time.time(),
            message_type=message_type,
            data=data,
            correlation_id=correlation_id
        )
        
        stream_name = f"service:{target_service}:messages"
        
        try:
            await self.redis_client.xadd(
                stream_name,
                {"data": json.dumps(asdict(message))}
            )
        except Exception as e:
            logger.error(f"Failed to send message to {target_service}: {e}")
    
    async def send_heartbeat(self) -> None:
        """Send service heartbeat."""
        if not self.redis_client:
            return
        
        import psutil
        
        try:
            process = psutil.Process()
            health = ServiceHealth(
                service_name=self.service_name,
                state=self.state,
                timestamp=time.time(),
                uptime=time.time() - self.start_time,
                memory_usage=process.memory_info().rss / 1024 / 1024,  # MB
                cpu_usage=process.cpu_percent(),
                last_error=self.last_error
            )
            
            await self.redis_client.setex(
                f"service:{self.service_name}:health",
                30,  # 30 second TTL
                json.dumps(asdict(health))
            )
            
            self.last_heartbeat = time.time()
            
        except Exception as e:
            logger.error(f"Failed to send heartbeat: {e}")
    
    def register_message_handler(self, message_type: str, handler: Callable) -> None:
        """Register a message handler."""
        self.message_handlers[message_type] = handler
    
    async def get_service_health(self, service_name: str) -> Optional[ServiceHealth]:
        """Get health information for another service."""
        if not self.redis_client:
            return None
        
        try:
            health_data = await self.redis_client.get(f"service:{service_name}:health")
            if health_data:
                return ServiceHealth(**json.loads(health_data))
        except Exception as e:
            logger.error(f"Failed to get health for {service_name}: {e}")
        
        return None
    
    async def wait_for_service(self, service_name: str, timeout: float = 30.0) -> bool:
        """Wait for another service to be available."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            health = await self.get_service_health(service_name)
            if health and health.state == ServiceState.RUNNING:
                return True
            
            await asyncio.sleep(1)
        
        return False
    
    # Abstract methods that subclasses must implement
    @abstractmethod
    async def service_initialize(self) -> bool:
        """Initialize service-specific components."""
        pass
    
    @abstractmethod
    async def service_loop(self) -> None:
        """Main service loop."""
        pass
    
    @abstractmethod
    async def service_cleanup(self) -> None:
        """Cleanup service-specific resources."""
        pass


def run_service(service_class, service_name: str, **kwargs) -> None:
    """Run a service with proper async setup."""
    async def main():
        service = service_class(service_name, **kwargs)
        await service.run()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Service interrupted by user")
    except Exception as e:
        logger.error(f"Service error: {e}")
