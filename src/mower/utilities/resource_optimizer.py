"""
Resource optimization module for autonomous mower.

This module provides tools for optimizing resource usage (memory, CPU, power)
in resource-constrained environments like the Raspberry Pi.
"""

import gc
import os
import psutil
import time
import threading
import functools
from typing import Dict, Any, List, Optional, Callable, Set

from mower.utilities.logger_config import LoggerConfig

# Initialize logger
logger = LoggerConfig.get_logger(__name__)


class ResourceOptimizer:
    """
    Resource optimizer for the autonomous mower system.

    This class provides methods for optimizing resource usage by:
    1. Monitoring and limiting memory usage
    2. Implementing memory pools for frequently allocated objects
    3. Providing garbage collection optimization
    4. Implementing CPU usage throttling
    5. Optimizing power consumption
    """

    def __init__(
        self,
        memory_limit_percent: float = 80.0,
        enable_monitoring: bool = True,
    ):
        """
        Initialize the resource optimizer.

        Args:
            memory_limit_percent: Maximum memory usage as percentage of total
            enable_monitoring: Whether to enable resource monitoring
        """
        self.memory_limit_percent = memory_limit_percent
        self.enable_monitoring = enable_monitoring
        self.monitoring_interval = 5  # seconds
        self.monitoring_thread = None
        self.stop_monitoring = threading.Event()

        # Memory pools for frequently allocated objects
        self.numpy_array_pool = {}
        self.object_pools = {}

        # Resource usage statistics
        self.stats = {
            "memory_usage": [],
            "cpu_usage": [],
            "gc_collections": 0,
            "pool_hits": 0,
            "pool_misses": 0,
        }

        # Set of optimized components
        self.optimized_components = set()

        # Start monitoring if enabled
        if self.enable_monitoring:
            self.start_monitoring()

        logger.info(
            f"Resource optimizer initialized with memory limit: {memory_limit_percent}%"
        )

    def start_monitoring(self):
        """Start resource usage monitoring."""
        if (
            self.monitoring_thread is not None
            and self.monitoring_thread.is_alive()
        ):
            logger.warning("Monitoring thread is already running")
            return

        self.stop_monitoring.clear()
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop, daemon=True
        )
        self.monitoring_thread.start()
        logger.info("Resource monitoring started")

    def stop_monitoring(self):
        """Stop resource usage monitoring."""
        if (
            self.monitoring_thread is None
            or not self.monitoring_thread.is_alive()
        ):
            logger.warning("Monitoring thread is not running")
            return

        self.stop_monitoring.set()
        self.monitoring_thread.join(timeout=2)
        logger.info("Resource monitoring stopped")

    def _monitoring_loop(self):
        """Main monitoring loop."""
        while not self.stop_monitoring.is_set():
            try:
                # Get current resource usage
                memory_percent = psutil.virtual_memory().percent
                cpu_percent = psutil.cpu_percent(interval=0.1)

                # Store statistics
                self.stats["memory_usage"].append(memory_percent)
                self.stats["cpu_usage"].append(cpu_percent)

                # Keep only the last 100 measurements
                if len(self.stats["memory_usage"]) > 100:
                    self.stats["memory_usage"] = self.stats["memory_usage"][
                        -100:
                    ]
                    self.stats["cpu_usage"] = self.stats["cpu_usage"][-100:]

                # Check if memory usage is above limit
                if memory_percent > self.memory_limit_percent:
                    logger.warning(
                        (
                            f"Memory usage ({memory_percent}%) exceeds"
                            f" limit ({self.memory_limit_percent}%)"
                        )
                    )
                    self._reduce_memory_usage()

                # Sleep for the monitoring interval
                time.sleep(self.monitoring_interval)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.monitoring_interval)

    def _reduce_memory_usage(self):
        """Reduce memory usage when it exceeds the limit."""
        logger.info("Reducing memory usage")

        # Force garbage collection
        collected = gc.collect()
        self.stats["gc_collections"] += 1
        logger.info(f"Garbage collection freed {collected} objects")

        # Clear object pools
        self._clear_object_pools()

        # Check if memory usage is still above limit
        memory_percent = psutil.virtual_memory().percent
        if memory_percent > self.memory_limit_percent:
            logger.warning(
                f"Memory usage still high ({memory_percent}%) after reduction attempts"
            )

    def _clear_object_pools(self):
        """Clear object pools to free memory."""
        pool_sizes = {
            "numpy_array_pool": len(self.numpy_array_pool),
            "object_pools": sum(
                len(pool) for pool in self.object_pools.values()
            ),
        }

        self.numpy_array_pool.clear()
        for pool in self.object_pools.values():
            pool.clear()

        logger.info(f"Cleared object pools: {pool_sizes}")

    def optimize_memory_usage(self, component_name: str, component: Any):
        """
        Optimize memory usage for a component.

        Args:
            component_name: Name of the component to optimize
            component: The component to optimize
        """
        if component_name in self.optimized_components:
            logger.debug(f"Component {component_name} already optimized")
            return

        logger.info(f"Optimizing memory usage for {component_name}")

        # Apply memory optimizations based on component type
        if hasattr(component, "clear_caches"):
            # Wrap the clear_caches method to be called during memory reduction
            original_clear_caches = component.clear_caches

            @functools.wraps(original_clear_caches)
            def memory_aware_clear_caches():
                memory_percent = psutil.virtual_memory().percent
                if (
                    memory_percent > self.memory_limit_percent * 0.9
                ):  # 90% of limit
                    logger.info(
                        (
                            f"Memory usage high ({memory_percent}%),"
                            f" clearing caches for {component_name}"
                        )
                    )
                    original_clear_caches()
                return original_clear_caches()

            component.clear_caches = memory_aware_clear_caches
            logger.info(f"Applied cache optimization to {component_name}")

        # Add component to optimized set
        self.optimized_components.add(component_name)

    def get_numpy_array(self, shape, dtype):
        """
        Get a numpy array from the pool or create a new one.

        Args:
            shape: Shape of the array
            dtype: Data type of the array

        Returns:
            A numpy array of the specified shape and type
        """
        import numpy as np

        # Create a key for the pool
        key = (shape, dtype)

        # Check if an array of this shape and type is in the pool
        if key in self.numpy_array_pool and self.numpy_array_pool[key]:
            self.stats["pool_hits"] += 1
            return self.numpy_array_pool[key].pop()

        # Create a new array
        self.stats["pool_misses"] += 1
        return np.zeros(shape, dtype=dtype)

    def return_numpy_array(self, array):
        """
        Return a numpy array to the pool.

        Args:
            array: The numpy array to return to the pool
        """
        # Create a key for the pool
        key = (array.shape, array.dtype)

        # Initialize the pool for this key if it doesn't exist
        if key not in self.numpy_array_pool:
            self.numpy_array_pool[key] = []

        # Zero out the array to prevent memory leaks
        array.fill(0)

        # Add the array to the pool
        self.numpy_array_pool[key].append(array)

    def register_object_pool(
        self, pool_name: str, factory_func: Callable, max_size: int = 10
    ):
        """
        Register an object pool.

        Args:
            pool_name: Name of the pool
            factory_func: Function to create new objects
            max_size: Maximum size of the pool
        """
        if pool_name in self.object_pools:
            logger.warning(f"Object pool {pool_name} already exists")
            return

        self.object_pools[pool_name] = {
            "objects": [],
            "factory": factory_func,
            "max_size": max_size,
        }

        logger.info(
            f"Registered object pool {pool_name} with max size {max_size}"
        )

    def get_object(self, pool_name: str):
        """
        Get an object from a pool.

        Args:
            pool_name: Name of the pool

        Returns:
            An object from the pool
        """
        if pool_name not in self.object_pools:
            logger.warning(f"Object pool {pool_name} does not exist")
            return None

        pool = self.object_pools[pool_name]

        # Get an object from the pool or create a new one
        if pool["objects"]:
            self.stats["pool_hits"] += 1
            return pool["objects"].pop()
        else:
            self.stats["pool_misses"] += 1
            return pool["factory"]()

    def return_object(self, pool_name: str, obj):
        """
        Return an object to a pool.

        Args:
            pool_name: Name of the pool
            obj: The object to return
        """
        if pool_name not in self.object_pools:
            logger.warning(f"Object pool {pool_name} does not exist")
            return

        pool = self.object_pools[pool_name]

        # Reset the object if it has a reset method
        if hasattr(obj, "reset"):
            obj.reset()

        # Add the object to the pool if it's not full
        if len(pool["objects"]) < pool["max_size"]:
            pool["objects"].append(obj)

    def optimize_garbage_collection(self):
        """Optimize garbage collection settings."""
        # Get current thresholds
        old_thresholds = gc.get_threshold()

        # Set more aggressive thresholds for resource-constrained environments
        # The default is (700, 10, 10) which means:
        # - Collection of generation 0 when 700 new objects have been allocated
        # - Collection of generation 1 when 10 collections of generation 0 have occurred
        # - Collection of generation 2 when 10 collections of generation 1 have occurred
        new_thresholds = (500, 5, 5)  # More frequent collections
        gc.set_threshold(*new_thresholds)

        logger.info(
            (
                f"Optimized garbage collection thresholds: "
                f"{old_thresholds} -> {new_thresholds}"
            )
        )

    def get_resource_usage(self) -> Dict[str, Any]:
        """
        Get current resource usage statistics.

        Returns:
            Dictionary with resource usage statistics
        """
        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=0.1)

        return {
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "percent": memory.percent,
            },
            "cpu": {"percent": cpu},
            "stats": self.stats,
        }

    def print_resource_usage(self):
        """Print current resource usage statistics."""
        usage = self.get_resource_usage()

        logger.info("Resource Usage:")
        logger.info(
            (
                f"  Memory: {usage['memory']['percent']}% used ({usage"
                f"['memory']['used'] / 1024 / 1024:.1f} MB)"
            )
        )
        logger.info(f"  CPU: {usage['cpu']['percent']}% used")
        logger.info(
            (
                f"  Pool hits/misses: {usage['stats']['pool_hits']}/"
                f"{usage['stats']['pool_misses']}"
            )
        )
        logger.info(f"  GC collections: {usage['stats']['gc_collections']}")

    def cleanup(self):
        """Clean up resources used by the optimizer."""
        if self.enable_monitoring:
            self.stop_monitoring()

        self._clear_object_pools()

        logger.info("Resource optimizer cleaned up")


# Singleton instance
_resource_optimizer = None


def get_resource_optimizer(
    memory_limit_percent: float = 80.0, enable_monitoring: bool = True
) -> ResourceOptimizer:
    """
    Get or create the singleton resource optimizer instance.

    Args:
        memory_limit_percent: Maximum memory usage as percentage of total
        enable_monitoring: Whether to enable resource monitoring

    Returns:
        The resource optimizer instance
    """
    global _resource_optimizer

    if _resource_optimizer is None:
        _resource_optimizer = ResourceOptimizer(
            memory_limit_percent, enable_monitoring
        )

    return _resource_optimizer


def optimize_component(component_name: str, component: Any):
    """
    Optimize resource usage for a component.

    Args:
        component_name: Name of the component to optimize
        component: The component to optimize
    """
    optimizer = get_resource_optimizer()
    optimizer.optimize_memory_usage(component_name, component)


def reduce_memory_usage():
    """Force memory usage reduction."""
    optimizer = get_resource_optimizer()
    optimizer._reduce_memory_usage()


def get_memory_usage() -> float:
    """
    Get current memory usage as a percentage.

    Returns:
        Memory usage percentage
    """
    return psutil.virtual_memory().percent


def get_cpu_usage() -> float:
    """
    Get current CPU usage as a percentage.

    Returns:
        CPU usage percentage
    """
    return psutil.cpu_percent(interval=0.1)


def optimize_all_components():
    """Optimize resource usage for all major components."""
    logger.info("Optimizing resource usage for all major components")

    # Get optimizer
    optimizer = get_resource_optimizer()

    # Optimize garbage collection
    optimizer.optimize_garbage_collection()

    # Optimize path planning
    try:
        from mower.navigation.path_planning_optimizer import (
            optimize_path_planner,
        )
        from mower.navigation.path_planner import (
            PathPlanner,
            PatternConfig,
            PatternType,
        )

        # Create a test path planner to optimize
        config = PatternConfig(
            pattern_type=PatternType.PARALLEL,
            spacing=0.5,
            angle=0.0,
            overlap=0.1,
            start_point=(0.0, 0.0),
            boundary_points=[(0, 0), (10, 0), (10, 10), (0, 10)],
        )
        planner = PathPlanner(config)

        # Optimize the path planner
        optimize_path_planner(planner)
        optimize_component("path_planner", planner)

        logger.info("Optimized path planning component")
    except Exception as e:
        logger.error(f"Failed to optimize path planning component: {e}")

    # Optimize obstacle detection
    try:
        from mower.obstacle_detection.image_processing_optimizer import (
            optimize_obstacle_detector,
        )
        from mower.obstacle_detection.obstacle_detector import (
            get_obstacle_detector,
        )

        # Get the obstacle detector
        detector = get_obstacle_detector()

        # Optimize the obstacle detector
        optimize_obstacle_detector(detector)
        optimize_component("obstacle_detector", detector)

        logger.info("Optimized obstacle detection component")
    except Exception as e:
        logger.error(f"Failed to optimize obstacle detection component: {e}")

    # Register common object pools
    try:
        import numpy as np

        # Register a pool for small numpy arrays used in path planning
        optimizer.register_object_pool(
            "small_arrays",
            lambda: np.zeros((10, 2), dtype=np.float32),
            max_size=20,
        )

        # Register a pool for medium numpy arrays used in image processing
        optimizer.register_object_pool(
            "medium_arrays",
            lambda: np.zeros((100, 100), dtype=np.uint8),
            max_size=10,
        )

        logger.info("Registered common object pools")
    except Exception as e:
        logger.error(f"Failed to register object pools: {e}")

    logger.info("Resource optimization complete")

    return optimizer


if __name__ == "__main__":
    # Run optimization and print resource usage
    optimizer = optimize_all_components()
    optimizer.print_resource_usage()
