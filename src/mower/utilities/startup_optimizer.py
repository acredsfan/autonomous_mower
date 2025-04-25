"""
Startup optimization module for autonomous mower.

This module provides tools for optimizing the startup time of the application
by implementing lazy loading, parallel initialization, and prioritized loading.
"""

import time
import threading
import importlib
import functools
from typing import Dict, Any, List, Optional, Callable, Set, Tuple
from concurrent.futures import ThreadPoolExecutor

from mower.utilities.logger_config import LoggerConfig

# Initialize logger
logger = LoggerConfig.get_logger(__name__)


class LazyLoader:
    """
    Lazy loader for modules and components.

    This class provides a way to lazily load modules and components
    only when they are actually needed, reducing startup time.
    """

    def __init__(self, module_path: str, class_name: Optional[str] = None):
        """
        Initialize the lazy loader.

        Args:
            module_path: Path to the module to load
            class_name: Name of the class to instantiate (optional)
        """
        self.module_path = module_path
        self.class_name = class_name
        self.module = None
        self.instance = None
        self.loaded = False

        logger.debug(
            f"Created lazy loader for {module_path}{f'.{class_name}' if class_name else ''}")

    def __call__(self, *args, **kwargs):
        """
        Load the module and instantiate the class if needed.

        Args:
            *args: Arguments to pass to the class constructor
            **kwargs: Keyword arguments to pass to the class constructor

        Returns:
            The instantiated class
        """
        if not self.loaded:
            self._load_module()

        if self.class_name:
            if self.instance is None:
                class_ = getattr(self.module, self.class_name)
                self.instance = class_(*args, **kwargs)
            return self.instance
        else:
            return self.module

    def _load_module(self):
        """Load the module."""
        start_time = time.time()
        self.module = importlib.import_module(self.module_path)
        self.loaded = True
        load_time = time.time() - start_time
        logger.debug(
            f"Lazy loaded {self.module_path} in {load_time:.4f} seconds")


class StartupOptimizer:
    """
    Startup optimizer for the autonomous mower system.

    This class provides methods for optimizing the startup time of the application
    by implementing lazy loading, parallel initialization, and prioritized loading.
    """

    def __init__(self):
        """Initialize the startup optimizer."""
        self.lazy_loaders = {}
        self.initialization_times = {}
        self.initialized_components = set()
        self.component_dependencies = {}
        self.initialization_order = []

        # Default thread pool size
        self.thread_pool_size = 4

        logger.info("Startup optimizer initialized")

    def register_lazy_loader(self, name: str, module_path: str, class_name: Optional[str] = None) -> LazyLoader:
        """
        Register a lazy loader for a module or component.

        Args:
            name: Name to use for the lazy loader
            module_path: Path to the module to load
            class_name: Name of the class to instantiate (optional)

        Returns:
            The lazy loader
        """
        loader = LazyLoader(module_path, class_name)
        self.lazy_loaders[name] = loader
        logger.debug(f"Registered lazy loader for {name}")
        return loader

    def register_component_dependency(self, component: str, depends_on: List[str]):
        """
        Register dependencies between components.

        Args:
            component: Name of the component
            depends_on: List of components that this component depends on
        """
        self.component_dependencies[component] = depends_on
        logger.debug(f"Registered dependencies for {component}: {depends_on}")

    def optimize_initialization_order(self) -> List[str]:
        """
        Optimize the initialization order of components based on dependencies.

        Returns:
            List of component names in optimized initialization order
        """
        # Build dependency graph
        graph = self.component_dependencies.copy()

        # Add components with no dependencies
        for component in self.lazy_loaders:
            if component not in graph:
                graph[component] = []

        # Topological sort
        visited = set()
        temp_visited = set()
        order = []

        def visit(node):
            if node in temp_visited:
                # Cyclic dependency detected
                logger.warning(f"Cyclic dependency detected involving {node}")
                return
            if node in visited:
                return

            temp_visited.add(node)

            for dependency in graph.get(node, []):
                visit(dependency)

            temp_visited.remove(node)
            visited.add(node)
            order.append(node)

        for component in graph:
            if component not in visited:
                visit(component)

        # Reverse to get correct order
        order.reverse()

        self.initialization_order = order
        logger.info(f"Optimized initialization order: {order}")
        return order

    def initialize_components(self, components: Optional[List[str]] = None, parallel: bool = True) -> Dict[str, Any]:
        """
        Initialize components in optimized order.

        Args:
            components: List of components to initialize (if None, initialize all)
            parallel: Whether to initialize components in parallel

        Returns:
            Dictionary of initialized components
        """
        if not self.initialization_order:
            self.optimize_initialization_order()

        if components is None:
            components = self.initialization_order
        else:
            # Filter out components that are not registered
            components = [c for c in components if c in self.lazy_loaders]

        initialized = {}

        if parallel:
            # Initialize components in parallel
            with ThreadPoolExecutor(max_workers=self.thread_pool_size) as executor:
                # Submit initialization tasks
                future_to_component = {
                    executor.submit(self._initialize_component, component): component
                    for component in components
                }

                # Collect results
                for future in future_to_component:
                    component = future_to_component[future]
                    try:
                        instance = future.result()
                        initialized[component] = instance
                    except Exception as e:
                        logger.error(f"Error initializing {component}: {e}")
        else:
            # Initialize components sequentially
            for component in components:
                try:
                    instance = self._initialize_component(component)
                    initialized[component] = instance
                except Exception as e:
                    logger.error(f"Error initializing {component}: {e}")

        return initialized

    def _initialize_component(self, component: str) -> Any:
        """
        Initialize a component.

        Args:
            component: Name of the component to initialize

        Returns:
            The initialized component
        """
        if component in self.initialized_components:
            logger.debug(f"Component {component} already initialized")
            return self.lazy_loaders[component]()

        # Check if dependencies are initialized
        for dependency in self.component_dependencies.get(component, []):
            if dependency not in self.initialized_components:
                logger.debug(
                    f"Initializing dependency {dependency} for {component}")
                self._initialize_component(dependency)

        # Initialize the component
        start_time = time.time()
        instance = self.lazy_loaders[component]()
        initialization_time = time.time() - start_time

        self.initialization_times[component] = initialization_time
        self.initialized_components.add(component)

        logger.info(
            f"Initialized {component} in {initialization_time:.4f} seconds")
        return instance

    def get_initialization_times(self) -> Dict[str, float]:
        """
        Get initialization times for components.

        Returns:
            Dictionary of component names to initialization times
        """
        return self.initialization_times

    def print_initialization_times(self):
        """Print initialization times for components."""
        if not self.initialization_times:
            logger.info("No components have been initialized yet")
            return

        logger.info("Component Initialization Times:")
        total_time = 0
        for component, time_taken in sorted(
            self.initialization_times.items(),
            key=lambda x: x[1],
            reverse=True
        ):
            logger.info(f"  {component}: {time_taken:.4f} seconds")
            total_time += time_taken

        logger.info(f"Total initialization time: {total_time:.4f} seconds")

# Decorator for lazy loading


def lazy_load(module_path: str, class_name: Optional[str] = None):
    """
    Decorator for lazy loading a module or class.

    Args:
        module_path: Path to the module to load
        class_name: Name of the class to instantiate (optional)

    Returns:
        Decorator function
    """
    def decorator(func):
        loader = LazyLoader(module_path, class_name)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(loader(), *args, **kwargs)

        return wrapper

    return decorator


# Singleton instance
_startup_optimizer = None


def get_startup_optimizer() -> StartupOptimizer:
    """
    Get or create the singleton startup optimizer instance.

    Returns:
        The startup optimizer instance
    """
    global _startup_optimizer

    if _startup_optimizer is None:
        _startup_optimizer = StartupOptimizer()

    return _startup_optimizer


def optimize_startup():
    """
    Optimize the startup process for the autonomous mower.

    This function registers lazy loaders for all major components
    and optimizes their initialization order.
    """
    logger.info("Optimizing startup process")

    # Get optimizer
    optimizer = get_startup_optimizer()

    # Register lazy loaders for major components
    optimizer.register_lazy_loader(
        "config_manager",
        "mower.config_management.config_manager",
        "ConfigManager"
    )

    optimizer.register_lazy_loader(
        "resource_optimizer",
        "mower.utilities.resource_optimizer",
        "ResourceOptimizer"
    )

    optimizer.register_lazy_loader(
        "path_planner",
        "mower.navigation.path_planner",
        "PathPlanner"
    )

    optimizer.register_lazy_loader(
        "obstacle_detector",
        "mower.obstacle_detection.obstacle_detector",
        "ObstacleDetector"
    )

    optimizer.register_lazy_loader(
        "navigation_controller",
        "mower.navigation.navigation",
        "NavigationController"
    )

    optimizer.register_lazy_loader(
        "web_ui",
        "mower.ui.web_ui.server",
        "WebServer"
    )

    # Register component dependencies
    optimizer.register_component_dependency(
        "navigation_controller",
        ["path_planner", "obstacle_detector"]
    )

    optimizer.register_component_dependency(
        "web_ui",
        ["navigation_controller", "config_manager"]
    )

    # Optimize initialization order
    optimizer.optimize_initialization_order()

    logger.info("Startup optimization complete")

    return optimizer


def initialize_critical_components():
    """
    Initialize only the critical components needed for basic operation.

    Returns:
        Dictionary of initialized components
    """
    optimizer = get_startup_optimizer()

    # Define critical components
    critical_components = [
        "config_manager",
        "resource_optimizer",
        "path_planner",
        "obstacle_detector"
    ]

    # Initialize critical components
    return optimizer.initialize_components(critical_components, parallel=True)


def initialize_all_components():
    """
    Initialize all components.

    Returns:
        Dictionary of initialized components
    """
    optimizer = get_startup_optimizer()
    return optimizer.initialize_components(parallel=True)


def measure_startup_time(func: Callable):
    """
    Measure the execution time of a function.

    Args:
        func: Function to measure

    Returns:
        Tuple of (result, execution_time)
    """
    start_time = time.time()
    result = func()
    execution_time = time.time() - start_time

    logger.info(
        f"Function {func.__name__} executed in {execution_time:.4f} seconds")

    return result, execution_time


def compare_startup_times():
    """
    Compare startup times with and without optimization.

    Returns:
        Dictionary with comparison results
    """
    logger.info("Comparing startup times")

    # Measure unoptimized startup time
    def unoptimized_startup():
        from mower.config_management.config_manager import ConfigManager
        from mower.navigation.path_planner import PathPlanner, PatternConfig, PatternType
        from mower.obstacle_detection.obstacle_detector import ObstacleDetector
        from mower.navigation.navigation import NavigationController

        config_manager = ConfigManager()

        config = PatternConfig(
            pattern_type=PatternType.PARALLEL,
            spacing=0.5,
            angle=0.0,
            overlap=0.1,
            start_point=(0.0, 0.0),
            boundary_points=[(0, 0), (10, 0), (10, 10), (0, 10)]
        )
        path_planner = PathPlanner(config)

        obstacle_detector = ObstacleDetector()

        navigation_controller = NavigationController(
            path_planner=path_planner,
            obstacle_detector=obstacle_detector
        )

        return {
            "config_manager": config_manager,
            "path_planner": path_planner,
            "obstacle_detector": obstacle_detector,
            "navigation_controller": navigation_controller
        }

    # Measure optimized startup time
    def optimized_startup():
        optimize_startup()
        return initialize_all_components()

    # Run measurements
    _, unoptimized_time = measure_startup_time(unoptimized_startup)
    _, optimized_time = measure_startup_time(optimized_startup)

    # Calculate improvement
    improvement = (unoptimized_time - optimized_time) / unoptimized_time * 100

    results = {
        "unoptimized_time": unoptimized_time,
        "optimized_time": optimized_time,
        "improvement_percent": improvement
    }

    logger.info(f"Startup time comparison:")
    logger.info(f"  Unoptimized: {unoptimized_time:.4f} seconds")
    logger.info(f"  Optimized: {optimized_time:.4f} seconds")
    logger.info(f"  Improvement: {improvement:.2f}%")

    return results


if __name__ == "__main__":
    # Run startup optimization and comparison
    optimize_startup()
    compare_startup_times()
