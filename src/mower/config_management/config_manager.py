import json

"""
Configuration manager for the autonomous mower.

This module provides a centralized configuration manager for the autonomous mower
project. It implements the ConfigurationInterface and provides methods for
accessing and modifying configuration values from various sources.
"""

import os
import threading
from typing import Any, Dict, List, Optional, Union

from mower.config_management.config_interface import ConfigurationInterface
from mower.config_management.config_source import (
    ConfigurationSource,
    DictConfigurationSource,
    EnvironmentConfigurationSource,
    FileConfigurationSource,
)


class ConfigurationManager(ConfigurationInterface):
    """
    Configuration manager for the autonomous mower.

    This class implements the ConfigurationInterface and provides methods for
    accessing and modifying configuration values from various sources. It
    supports hierarchical configuration keys, type conversion, and multiple
    configuration sources.
    """

    def __init__(self):
        """Initialize the configuration manager."""
        self._sources: List[ConfigurationSource] = []
        self._defaults: Dict[str, Any] = {}
        self._lock = threading.RLock()

        # Add default configuration sources
        self._add_default_sources()

    def _add_default_sources(self):
        """Add default configuration sources."""
        # Add environment variables source
        env_file = ".env"
        if os.path.exists(env_file):
            self.add_source(EnvironmentConfigurationSource(env_file))
        else:
            self.add_source(EnvironmentConfigurationSource())

        # Add default values source
        self.add_source(DictConfigurationSource(self._defaults))

    def add_source(self, source: ConfigurationSource, priority: int = -1) -> None:
        """
        Add a configuration source.

        Args:
            source: Configuration source to add
            priority: Priority of the source (higher priority sources are checked first)
                     If -1, the source is added at the end of the list
        """
        with self._lock:
            if priority < 0 or priority >= len(self._sources):
                self._sources.append(source)
            else:
                self._sources.insert(priority, source)

    def remove_source(self, source: ConfigurationSource) -> bool:
        """
        Remove a configuration source.

        Args:
            source: Configuration source to remove

        Returns:
            bool: True if the source was removed, False if it wasn't found
        """
        with self._lock:
            if source in self._sources:
                self._sources.remove(source)
                return True
            return False

    def get_sources(self) -> List[ConfigurationSource]:
        """
        Get all configuration sources.

        Returns:
            List[ConfigurationSource]: All configuration sources
        """
        with self._lock:
            return list(self._sources)

    def set_defaults(self, defaults: Dict[str, Any]) -> None:
        """
        Set default configuration values.

        Args:
            defaults: Default configuration values
        """
        with self._lock:
            self._defaults = defaults.copy()

            # Update the defaults source
            for source in self._sources:
                if isinstance(source, DictConfigurationSource):
                    source.values = self._defaults.copy()
                    break
            else:
                # If no defaults source exists, add one
                self.add_source(DictConfigurationSource(self._defaults))

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            key: Configuration key (can be hierarchical, e.g., 'section.key')
            default: Default value if key is not found

        Returns:
            Any: Configuration value
        """
        with self._lock:
            # Check each source in order
            for source in self._sources:
                if source.has(key):
                    return source.get(key)

            # If not found in any source, return the default
            return default

    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.

        Args:
            key: Configuration key (can be hierarchical, e.g., 'section.key')
            value: Configuration value
        """
        with self._lock:
            # Set the value in the first source
            if self._sources:
                self._sources[0].set(key, value)

    def has(self, key: str) -> bool:
        """
        Check if a configuration key exists.

        Args:
            key: Configuration key (can be hierarchical, e.g., 'section.key')

        Returns:
            bool: True if the key exists, False otherwise
        """
        with self._lock:
            # Check each source in order
            for source in self._sources:
                if source.has(key):
                    return True

            return False

    def delete(self, key: str) -> bool:
        """
        Delete a configuration value.

        Args:
            key: Configuration key (can be hierarchical, e.g., 'section.key')

        Returns:
            bool: True if the key was deleted, False if it didn't exist
        """
        with self._lock:
            # Delete the key from all sources
            deleted = False
            for source in self._sources:
                if source.delete(key):
                    deleted = True

            return deleted

    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get a configuration section.

        Args:
            section: Section name

        Returns:
            Dict[str, Any]: Configuration section
        """
        with self._lock:
            result = {}

            # Get the section from all sources
            for source in self._sources:
                # Get all values from the source
                values = source.get_all()

                # Extract the section
                section_values = {}
                for key, value in values.items():
                    if key.startswith(f"{section}."):
                        # Remove the section prefix
                        section_key = key[len(section) + 1 :]
                        section_values[section_key] = value
                    elif isinstance(value, dict) and section in value:
                        # Handle nested dictionaries
                        section_values.update(value[section])

                # Update the result with the section values
                result.update(section_values)

            return result

    def get_all(self) -> Dict[str, Any]:
        """
        Get all configuration values.

        Returns:
            Dict[str, Any]: All configuration values
        """
        with self._lock:
            result = {}

            # Get all values from all sources
            for source in self._sources:
                result.update(source.get_all())

            return result

    def load(self, source: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Load configuration from a source.

        Args:
            source: Source to load from (file path or dictionary)

        Returns:
            Dict[str, Any]: Loaded configuration
        """
        with self._lock:
            if isinstance(source, str):
                # Load from file
                file_source = FileConfigurationSource(source)
                self.add_source(file_source, 0)  # Add with highest priority
                return file_source.get_all()
            elif isinstance(source, dict):
                # Load from dictionary
                dict_source = DictConfigurationSource(source)
                self.add_source(dict_source, 0)  # Add with highest priority
                return dict_source.get_all()
            else:
                raise ValueError(f"Unsupported source type: {type(source)}")

    def save(self, destination: str) -> None:
        """
        Save configuration to a destination.

        Args:
            destination: Destination to save to (file path)
        """
        with self._lock:
            # Create a file source with all configuration values
            file_source = FileConfigurationSource(destination)

            # Get all values from all sources
            values = self.get_all()

            # Set all values in the file source
            for key, value in values.items():
                file_source.set(key, value)

            # Save the file source
            file_source.save()

    def reset(self) -> None:
        """Reset the configuration to its default state."""
        with self._lock:
            # Remove all sources except the defaults
            self._sources = [
                source
                for source in self._sources
                if isinstance(source, DictConfigurationSource) and source.values == self._defaults
            ]

            # Add default sources
            self._add_default_sources()

    def get_int(self, key: str, default: Optional[int] = None) -> Optional[int]:
        """
        Get a configuration value as an integer.

        Args:
            key: Configuration key
            default: Default value if key is not found or value is not an integer

        Returns:
            Optional[int]: Configuration value as an integer, or default if not found
        """
        value = self.get(key, default)

        if value is None:
            return default

        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    def get_float(self, key: str, default: Optional[float] = None) -> Optional[float]:
        """
        Get a configuration value as a float.

        Args:
            key: Configuration key
            default: Default value if key is not found or value is not a float

        Returns:
            Optional[float]: Configuration value as a float, or default if not found
        """
        value = self.get(key, default)

        if value is None:
            return default

        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    def get_bool(self, key: str, default: Optional[bool] = None) -> Optional[bool]:
        """
        Get a configuration value as a boolean.

        Args:
            key: Configuration key
            default: Default value if key is not found or value is not a boolean

        Returns:
            Optional[bool]: Configuration value as a boolean, or default if not found
        """
        value = self.get(key, default)

        if value is None:
            return default

        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            value = value.lower()
            if value in ["true", "yes", "y", "1"]:
                return True
            if value in ["false", "no", "n", "0"]:
                return False

        return default

    def get_str(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get a configuration value as a string.

        Args:
            key: Configuration key
            default: Default value if key is not found or value is not a string

        Returns:
            Optional[str]: Configuration value as a string, or default if not found
        """
        value = self.get(key, default)

        if value is None:
            return default

        try:
            return str(value)
        except (ValueError, TypeError):
            return default

    def get_list(self, key: str, default: Optional[List[Any]] = None) -> Optional[List[Any]]:
        """
        Get a configuration value as a list.

        Args:
            key: Configuration key
            default: Default value if key is not found or value is not a list

        Returns:
            Optional[List[Any]]: Configuration value as a list, or default if not found
        """
        value = self.get(key, default)

        if value is None:
            return default

        if isinstance(value, list):
            return value

        if isinstance(value, str):
            try:
                # Try to parse as JSON

                return json.loads(value)
            except json.JSONDecodeError:
                # Try to split by comma
                return [item.strip() for item in value.split(",")]

        return default

    def get_dict(self, key: str, default: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Get a configuration value as a dictionary.

        Args:
            key: Configuration key
            default: Default value if key is not found or value is not a dictionary

        Returns:
            Optional[Dict[str, Any]]: Configuration value as a dictionary,
            or default if not found
        """
        value = self.get(key, default)

        if value is None:
            return default

        if isinstance(value, dict):
            return value

        if isinstance(value, str):
            try:
                # Try to parse as JSON

                return json.loads(value)
            except json.JSONDecodeError:
                pass

        return default


# Singleton instance of ConfigurationManager
_config_manager: Optional[ConfigurationManager] = None
_config_manager_lock = threading.RLock()


def get_config_manager() -> ConfigurationManager:
    """
    Get the singleton instance of ConfigurationManager.

    Returns:
        ConfigurationManager: The singleton instance
    """
    with _config_manager_lock:
        # Use of 'global' is required for singleton pattern in this context.
        global _config_manager
        if _config_manager is None:
            _config_manager = ConfigurationManager()

    return _config_manager


# Initialize the configuration manager with default values
def initialize_config_manager(
    defaults: Optional[Dict[str, Any]] = None,
    config_file: Optional[str] = None,
    env_file: Optional[str] = None,
) -> ConfigurationManager:
    """
    Initialize the configuration manager with default values.

    Args:
        defaults: Default configuration values
        config_file: Path to a configuration file to load
        env_file: Path to a .env file to load

    Returns:
        ConfigurationManager: The initialized configuration manager
    """
    config_manager = get_config_manager()

    # Set defaults if provided
    if defaults:
        config_manager.set_defaults(defaults)

    # Load configuration from file if provided
    if config_file and os.path.exists(config_file):
        config_manager.load(config_file)

    # Add environment variables source if provided
    if env_file and os.path.exists(env_file):
        config_manager.add_source(EnvironmentConfigurationSource(env_file), 0)

    return config_manager


# Get a configuration value (convenience function)
def get_config(key: str, default: Any = None) -> Any:
    """
    Get a configuration value.

    Args:
        key: Configuration key
        default: Default value if key is not found

    Returns:
        Any: Configuration value
    """
    return get_config_manager().get(key, default)


# Set a configuration value (convenience function)
def set_config(key: str, value: Any) -> None:
    """
    Set a configuration value.

    Args:
        key: Configuration key
        value: Configuration value
    """
    get_config_manager().set(key, value)
