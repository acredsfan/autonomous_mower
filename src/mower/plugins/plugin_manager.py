"""
Plugin manager for the autonomous mower.

This module provides a plugin manager for the autonomous mower project.
The plugin manager handles plugin registration, discovery, and loading.
"""

import importlib
import inspect
import os
import pkgutil
import sys
from typing import Dict, List, Optional, Type, TypeVar, Generic, Any

from mower.plugins.plugin_base import (
    Plugin,
    SensorPlugin,
    DetectionPlugin,
    AvoidancePlugin,
)
from mower.utilities.logger_config import LoggerConfigInfo

# Initialize logger
logger = LoggerConfigInfo.get_logger(__name__)

# Type variable for plugin types
T = TypeVar("T", bound=Plugin)


class PluginManager(Generic[T]):
    """
    Plugin manager for the autonomous mower.

    This class handles plugin registration, discovery, and loading.
    It provides methods for getting plugins by type, ID, or name.
    """

    def __init__(self, plugin_base_class: Type[T]):
        """
        Initialize the plugin manager.

        Args:
            plugin_base_class: Base class for plugins managed by this manager
        """
        self.plugin_base_class = plugin_base_class
        self.plugins: Dict[str, Type[T]] = {}
        self.plugin_instances: Dict[str, T] = {}
        self.plugin_dirs: List[str] = []

        logger.info(
            f"Initialized plugin manager for {plugin_base_class.__name__}"
        )

    def register_plugin(self, plugin_class: Type[T]) -> bool:
        """
        Register a plugin class.

        Args:
            plugin_class: Plugin class to register

        Returns:
            bool: True if registration was successful, False otherwise
        """
        try:
            # Check if the plugin class is a subclass of the base class
            if not issubclass(plugin_class, self.plugin_base_class):
                logger.error(
                    f"Plugin class {plugin_class.__name__} is not a subclass of "
                    f"{self.plugin_base_class.__name__}"
                )
                return False

            # Create a temporary instance to get the plugin ID
            temp_instance = plugin_class()
            plugin_id = temp_instance.plugin_id

            # Check if a plugin with this ID is already registered
            if plugin_id in self.plugins:
                logger.warning(
                    f"Plugin with ID {plugin_id} is already registered "
                    f"({self.plugins[plugin_id].__name__})"
                )
                return False

            # Register the plugin
            self.plugins[plugin_id] = plugin_class
            logger.info(
                f"Registered plugin {plugin_class.__name__} with ID {plugin_id}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Error registering plugin {plugin_class.__name__}: {e}"
            )
            return False

    def unregister_plugin(self, plugin_id: str) -> bool:
        """
        Unregister a plugin.

        Args:
            plugin_id: ID of the plugin to unregister

        Returns:
            bool: True if unregistration was successful, False otherwise
        """
        try:
            if plugin_id not in self.plugins:
                logger.warning(
                    f"Plugin with ID {plugin_id} is not registered"
                )
                return False

            # Clean up the plugin instance if it exists
            if plugin_id in self.plugin_instances:
                try:
                    self.plugin_instances[plugin_id].cleanup()
                except Exception as e:
                    logger.error(
                        f"Error cleaning up plugin instance {plugin_id}: {e}"
                    )

                del self.plugin_instances[plugin_id]

            # Unregister the plugin
            plugin_name = self.plugins[plugin_id].__name__
            del self.plugins[plugin_id]
            logger.info(
                f"Unregistered plugin {plugin_name} with ID {plugin_id}"
            )
            return True

        except Exception as e:
            logger.error(f"Error unregistering plugin {plugin_id}: {e}")
            return False

    def get_plugin(self, plugin_id: str) -> Optional[T]:
        """
        Get a plugin instance by ID.

        Args:
            plugin_id: ID of the plugin to get

        Returns:
            Optional[T]: Plugin instance or None if not found
        """
        try:
            # Check if the plugin is registered
            if plugin_id not in self.plugins:
                logger.warning(
                    f"Plugin with ID {plugin_id} is not registered"
                )
                return None

            # Check if the plugin instance already exists
            if plugin_id in self.plugin_instances:
                return self.plugin_instances[plugin_id]

            # Create a new plugin instance
            plugin_class = self.plugins[plugin_id]
            plugin_instance = plugin_class()

            # Initialize the plugin
            if not plugin_instance.initialize():
                logger.error(
                    f"Failed to initialize plugin {plugin_class.__name__}"
                )
                return None

            # Store the plugin instance
            self.plugin_instances[plugin_id] = plugin_instance
            logger.info(
                f"Created instance of plugin {plugin_class.__name__} "
                f"with ID {plugin_id}"
            )
            return plugin_instance

        except Exception as e:
            logger.error(f"Error getting plugin {plugin_id}: {e}")
            return None

    def get_plugin_by_name(self, plugin_name: str) -> Optional[T]:
        """
        Get a plugin instance by name.

        Args:
            plugin_name: Name of the plugin to get

        Returns:
            Optional[T]: Plugin instance or None if not found
        """
        try:
            # Find the plugin ID by name
            for plugin_id, plugin_class in self.plugins.items():
                temp_instance = plugin_class()
                if temp_instance.plugin_name == plugin_name:
                    return self.get_plugin(plugin_id)

            logger.warning(f"Plugin with name {plugin_name} not found")
            return None

        except Exception as e:
            logger.error(f"Error getting plugin by name {plugin_name}: {e}")
            return None

    def get_all_plugins(self) -> List[T]:
        """
        Get all plugin instances.

        Returns:
            List[T]: List of all plugin instances
        """
        return [
            self.get_plugin(plugin_id)
            for plugin_id in self.plugins
            if self.get_plugin(plugin_id) is not None
        ]

    def add_plugin_directory(self, directory: str) -> bool:
        """
        Add a directory to search for plugins.

        Args:
            directory: Directory to search for plugins

        Returns:
            bool: True if the directory was added, False otherwise
        """
        try:
            if not os.path.isdir(directory):
                logger.error(f"Plugin directory {directory} does not exist")
                return False

            if directory in self.plugin_dirs:
                logger.warning(
                    f"Plugin directory {directory} is already registered"
                )
                return False

            self.plugin_dirs.append(directory)
            logger.info(f"Added plugin directory {directory}")
            return True

        except Exception as e:
            logger.error(f"Error adding plugin directory {directory}: {e}")
            return False

    def discover_plugins(self) -> int:
        """
        Discover plugins in the registered directories.

        Returns:
            int: Number of plugins discovered
        """
        count = 0

        try:
            # Add the plugin directories to the Python path
            for directory in self.plugin_dirs:
                if directory not in sys.path:
                    sys.path.append(directory)

            # Discover plugins in each directory
            for directory in self.plugin_dirs:
                count += self._discover_plugins_in_directory(directory)

            logger.info(f"Discovered {count} plugins")
            return count

        except Exception as e:
            logger.error(f"Error discovering plugins: {e}")
            return count

    def _discover_plugins_in_directory(self, directory: str) -> int:
        """
        Discover plugins in a directory.

        Args:
            directory: Directory to search for plugins

        Returns:
            int: Number of plugins discovered
        """
        count = 0

        try:
            # Get all Python modules in the directory
            for _, name, is_pkg in pkgutil.iter_modules([directory]):
                if is_pkg:
                    # Skip packages for now
                    continue

                try:
                    # Import the module
                    module_name = name
                    module = importlib.import_module(module_name)

                    # Find plugin classes in the module
                    for _, obj in inspect.getmembers(module, inspect.isclass):
                        if (
                            issubclass(obj, self.plugin_base_class)
                            and obj != self.plugin_base_class
                        ):
                            if self.register_plugin(obj):
                                count += 1

                except Exception as e:
                    logger.error(f"Error loading plugin module {name}: {e}")

            return count

        except Exception as e:
            logger.error(
                f"Error discovering plugins in directory {directory}: {e}"
            )
            return count

    def cleanup(self) -> None:
        """Clean up all plugin instances."""
        try:
            for plugin_id, plugin_instance in list(
                self.plugin_instances.items()
            ):
                try:
                    plugin_instance.cleanup()
                    logger.info(f"Cleaned up plugin {plugin_id}")
                except Exception as e:
                    logger.error(f"Error cleaning up plugin {plugin_id}: {e}")

                del self.plugin_instances[plugin_id]

            self.plugin_instances.clear()
            logger.info("Cleaned up all plugin instances")

        except Exception as e:
            logger.error(f"Error cleaning up plugin instances: {e}")


# Singleton instances of plugin managers
_sensor_plugin_manager: Optional[PluginManager[SensorPlugin]] = None
_detection_plugin_manager: Optional[PluginManager[DetectionPlugin]] = None
_avoidance_plugin_manager: Optional[PluginManager[AvoidancePlugin]] = None


def get_sensor_plugin_manager() -> PluginManager[SensorPlugin]:
    """
    Get the singleton instance of the sensor plugin manager.

    Returns:
        PluginManager[SensorPlugin]: Sensor plugin manager
    """
    global _sensor_plugin_manager

    if _sensor_plugin_manager is None:
        _sensor_plugin_manager = PluginManager(SensorPlugin)

    return _sensor_plugin_manager


def get_detection_plugin_manager() -> PluginManager[DetectionPlugin]:
    """
    Get the singleton instance of the detection plugin manager.

    Returns:
        PluginManager[DetectionPlugin]: Detection plugin manager
    """
    global _detection_plugin_manager

    if _detection_plugin_manager is None:
        _detection_plugin_manager = PluginManager(DetectionPlugin)

    return _detection_plugin_manager


def get_avoidance_plugin_manager() -> PluginManager[AvoidancePlugin]:
    """
    Get the singleton instance of the avoidance plugin manager.

    Returns:
        PluginManager[AvoidancePlugin]: Avoidance plugin manager
    """
    global _avoidance_plugin_manager

    if _avoidance_plugin_manager is None:
        _avoidance_plugin_manager = PluginManager(AvoidancePlugin)

    return _avoidance_plugin_manager
