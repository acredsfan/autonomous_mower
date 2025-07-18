"""
Integration tests for AsyncResourceManager.

Tests the async resource management functionality including:
- Resource initialization and cleanup
- Resource pooling
- Health monitoring
- Recovery mechanisms
"""

import asyncio
import pytest
import pytest_asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

from mower.utilities.async_resource_manager import (
    AsyncResourceManager,
    ResourceState,
    ResourceHealth,
    ResourcePool
)


class MockResource:
    """Mock resource for testing"""
    
    def __init__(self, name: str, should_fail: bool = False):
        self.name = name
        self.should_fail = should_fail
        self.initialized = True
        self.cleaned_up = False
        self.health_check_count = 0
    
    async def cleanup(self):
        """Mock cleanup method"""
        if self.should_fail:
            raise RuntimeError(f"Cleanup failed for {self.name}")
        self.cleaned_up = True
    
    def health_check(self):
        """Mock health check method"""
        self.health_check_count += 1
        return not self.should_fail


class TestAsyncResourceManager:
    """Test cases for AsyncResourceManager"""
    
    @pytest_asyncio.fixture
    async def resource_manager(self):
        """Create and initialize a resource manager for testing"""
        manager = AsyncResourceManager()
        await manager.initialize()
        try:
            yield manager
        finally:
            await manager.cleanup()
    
    @pytest.mark.asyncio
    async def test_initialization_and_cleanup(self):
        """Test basic initialization and cleanup"""
        manager = AsyncResourceManager()
        assert not manager._initialized
        
        await manager.initialize()
        assert manager._initialized
        assert manager._health_monitor_task is not None
        assert manager._pool_cleanup_task is not None
        
        await manager.cleanup()
        assert not manager._initialized
        assert len(manager._resources) == 0
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager functionality"""
        async with AsyncResourceManager() as manager:
            assert manager._initialized
            assert len(manager._resources) == 0
        # Manager should be cleaned up automatically
    
    @pytest.mark.asyncio
    async def test_resource_registration_and_retrieval(self, resource_manager):
        """Test registering and retrieving resources"""
        
        async def create_mock_resource():
            return MockResource("test_resource")
        
        # Register resource
        await resource_manager.register_resource(
            "test_resource",
            create_mock_resource
        )
        
        # Retrieve resource
        resource = await resource_manager.get_resource("test_resource")
        assert resource is not None
        assert resource.name == "test_resource"
        assert resource.initialized
        
        # Check health tracking
        health = await resource_manager.get_resource_health("test_resource")
        assert health is not None
        assert health.state == ResourceState.OPERATIONAL
    
    @pytest.mark.asyncio
    async def test_resource_initialization_failure(self, resource_manager):
        """Test handling of resource initialization failures"""
        
        async def failing_factory():
            raise RuntimeError("Initialization failed")
        
        with pytest.raises(RuntimeError, match="Initialization failed"):
            await resource_manager.register_resource(
                "failing_resource",
                failing_factory
            )
        
        # Resource should not be registered
        resource = await resource_manager.get_resource("failing_resource")
        assert resource is None
        
        # Health should show failed state
        health = await resource_manager.get_resource_health("failing_resource")
        assert health is not None
        assert health.state == ResourceState.FAILED
        assert health.error_count == 1
    
    @pytest.mark.asyncio
    async def test_resource_cleanup_callbacks(self, resource_manager):
        """Test resource cleanup callbacks"""
        cleanup_called = False
        
        async def create_mock_resource():
            return MockResource("test_resource")
        
        async def cleanup_callback(resource):
            nonlocal cleanup_called
            cleanup_called = True
            assert resource.name == "test_resource"
        
        # Register resource with cleanup callback
        await resource_manager.register_resource(
            "test_resource",
            create_mock_resource,
            cleanup_func=cleanup_callback
        )
        
        # Cleanup should call the callback
        await resource_manager.cleanup()
        assert cleanup_called
    
    @pytest.mark.asyncio
    async def test_health_monitoring(self, resource_manager):
        """Test resource health monitoring"""
        
        async def create_mock_resource():
            return MockResource("test_resource")
        
        def health_check(resource):
            return resource.health_check()
        
        # Register resource with health check
        await resource_manager.register_resource(
            "test_resource",
            create_mock_resource,
            health_check_func=health_check
        )
        
        resource = await resource_manager.get_resource("test_resource")
        
        # Manually trigger health check
        await resource_manager._check_resource_health("test_resource", resource)
        
        health = await resource_manager.get_resource_health("test_resource")
        assert health.last_check is not None
        assert resource.health_check_count == 1
    
    @pytest.mark.asyncio
    async def test_resource_recovery(self, resource_manager):
        """Test resource recovery mechanisms"""
        recovery_called = False
        
        async def create_mock_resource():
            return MockResource("test_resource", should_fail=True)
        
        def health_check(resource):
            return resource.health_check()
        
        async def recovery_strategy(resource):
            nonlocal recovery_called
            recovery_called = True
            resource.should_fail = False  # Fix the resource
            return True
        
        # Register resource with health check and recovery
        await resource_manager.register_resource(
            "test_resource",
            create_mock_resource,
            health_check_func=health_check,
            recovery_func=recovery_strategy
        )
        
        resource = await resource_manager.get_resource("test_resource")
        health = await resource_manager.get_resource_health("test_resource")
        
        # Simulate multiple health check failures to trigger recovery
        for _ in range(3):
            await resource_manager._check_resource_health("test_resource", resource)
        
        # Recovery should have been attempted
        assert recovery_called
        assert health.recovery_attempts == 1
    
    @pytest.mark.asyncio
    async def test_resource_pool_creation(self, resource_manager):
        """Test resource pool creation and management"""
        
        async def create_mock_connection():
            return MockResource(f"connection_{time.time()}")
        
        # Create resource pool
        pool = await resource_manager.create_resource_pool(
            "connections",
            create_mock_connection,
            max_size=5,
            min_size=2
        )
        
        assert pool.name == "connections"
        assert pool.max_size == 5
        assert pool.min_size == 2
        assert len(pool.resources) == 2  # Pre-populated with min_size
    
    @pytest.mark.asyncio
    async def test_resource_pool_acquire_release(self, resource_manager):
        """Test acquiring and releasing resources from pool"""
        
        async def create_mock_connection():
            return MockResource(f"connection_{time.time()}")
        
        # Create resource pool
        pool = await resource_manager.create_resource_pool(
            "connections",
            create_mock_connection,
            max_size=3,
            min_size=1
        )
        
        # Acquire resource
        resource1 = await pool.acquire(create_mock_connection)
        assert resource1 is not None
        assert resource1 in pool.in_use
        assert len(pool.in_use) == 1
        
        # Acquire another resource
        resource2 = await pool.acquire(create_mock_connection)
        assert resource2 is not None
        assert resource2 != resource1
        assert len(pool.in_use) == 2
        
        # Release resources
        await pool.release(resource1)
        assert resource1 not in pool.in_use
        assert len(pool.in_use) == 1
        
        await pool.release(resource2)
        assert len(pool.in_use) == 0
    
    @pytest.mark.asyncio
    async def test_resource_pool_context_manager(self, resource_manager):
        """Test resource pool context manager"""
        
        async def create_mock_connection():
            return MockResource(f"connection_{time.time()}")
        
        # Create resource pool
        await resource_manager.create_resource_pool(
            "connections",
            create_mock_connection,
            max_size=3,
            min_size=1
        )
        
        # Use context manager
        async with resource_manager.acquire_from_pool("connections", create_mock_connection) as resource:
            assert resource is not None
            pool = resource_manager._resource_pools["connections"]
            assert resource in pool.in_use
        
        # Resource should be released after context
        assert resource not in pool.in_use
    
    @pytest.mark.asyncio
    async def test_resource_pool_exhaustion(self, resource_manager):
        """Test resource pool exhaustion handling"""
        
        async def create_mock_connection():
            return MockResource(f"connection_{time.time()}")
        
        # Create small resource pool
        pool = await resource_manager.create_resource_pool(
            "connections",
            create_mock_connection,
            max_size=2,
            min_size=1
        )
        
        # Acquire all resources
        resource1 = await pool.acquire(create_mock_connection)
        resource2 = await pool.acquire(create_mock_connection)
        
        # Pool should be exhausted
        with pytest.raises(RuntimeError, match="Resource pool connections exhausted"):
            await pool.acquire(create_mock_connection)
    
    @pytest.mark.asyncio
    async def test_resource_pool_idle_cleanup(self, resource_manager):
        """Test cleanup of idle resources in pool"""
        
        async def create_mock_connection():
            return MockResource(f"connection_{time.time()}")
        
        # Create resource pool with short idle timeout
        pool = await resource_manager.create_resource_pool(
            "connections",
            create_mock_connection,
            max_size=5,
            min_size=1,
            idle_timeout=0.1  # 100ms
        )
        
        # Add extra resources
        resource1 = await pool.acquire(create_mock_connection)
        resource2 = await pool.acquire(create_mock_connection)
        await pool.release(resource1)
        await pool.release(resource2)
        
        initial_count = len(pool.resources)
        assert initial_count > 1
        
        # Wait for idle timeout
        await asyncio.sleep(0.2)
        
        # Trigger cleanup
        await pool.cleanup_idle()
        
        # Should keep minimum resources
        assert len(pool.resources) >= pool.min_size
        assert len(pool.resources) <= initial_count
    
    @pytest.mark.asyncio
    async def test_status_reporting(self, resource_manager):
        """Test status reporting functionality"""
        
        async def create_mock_resource():
            return MockResource("test_resource")
        
        async def create_mock_connection():
            return MockResource(f"connection_{time.time()}")
        
        # Register resource and create pool
        await resource_manager.register_resource("test_resource", create_mock_resource)
        await resource_manager.create_resource_pool("connections", create_mock_connection, max_size=3, min_size=1)
        
        # Get status
        status = resource_manager.get_status()
        
        assert status["initialized"] is True
        assert status["resource_count"] == 1
        assert status["pool_count"] == 1
        assert "test_resource" in status["resources"]
        assert "connections" in status["pools"]
        
        # Check resource status details
        resource_status = status["resources"]["test_resource"]
        assert resource_status["state"] == ResourceState.OPERATIONAL.value
        assert resource_status["error_count"] == 0
        
        # Check pool status details
        pool_status = status["pools"]["connections"]
        assert pool_status["total_resources"] >= 1
        assert pool_status["in_use"] == 0
        assert pool_status["available"] >= 1


class TestResourcePool:
    """Test cases for ResourcePool class"""
    
    @pytest.mark.asyncio
    async def test_pool_initialization(self):
        """Test resource pool initialization"""
        pool = ResourcePool(
            name="test_pool",
            max_size=10,
            min_size=2,
            idle_timeout=300.0
        )
        
        assert pool.name == "test_pool"
        assert pool.max_size == 10
        assert pool.min_size == 2
        assert pool.idle_timeout == 300.0
        assert len(pool.resources) == 0
        assert len(pool.in_use) == 0
    
    @pytest.mark.asyncio
    async def test_pool_resource_lifecycle(self):
        """Test complete resource lifecycle in pool"""
        
        async def create_resource():
            return MockResource(f"resource_{time.time()}")
        
        pool = ResourcePool("test_pool", max_size=3, min_size=1)
        
        # Acquire first resource (should create new)
        resource1 = await pool.acquire(create_resource)
        assert resource1 is not None
        assert len(pool.resources) == 1
        assert len(pool.in_use) == 1
        
        # Release and re-acquire (should reuse)
        await pool.release(resource1)
        assert len(pool.in_use) == 0
        
        resource2 = await pool.acquire()
        assert resource2 is resource1  # Should be the same resource
        assert len(pool.in_use) == 1
        
        # Clean up
        await pool.release(resource2)
        await pool.cleanup_all()
        assert len(pool.resources) == 0


if __name__ == "__main__":
    pytest.main([__file__])