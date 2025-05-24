"""
Configuration sources for the autonomous mower.

This module defines the interface and implementations for configuration sources
in the autonomous mower project. Configuration sources provide configuration
values from various sources, such as environment variables, configuration files,
and dictionaries.
"""

import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv, set_key  # type:ignore


class ConfigurationSource(ABC):
    """
    Interface for configuration sources.

    This interface defines the contract that all configuration sources
    must adhere to.
    """
    
    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            key: Configuration key
            default: Default value if key is not found

        Returns:
            Any: Configuration value
        """
    
    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.

        Args:
            key: Configuration key
            value: Configuration value
        """

    @abstractmethod
    def has(self, key: str) -> bool:
        """
        Check if a configuration key exists.

        Args:
            key: Configuration key

        Returns:
            bool: True if the key exists, False otherwise
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """
        Delete a configuration value.

        Args:
            key: Configuration key

        Returns:
            bool: True if the key was deleted, False if it didn't exist
        """
        pass

    @abstractmethod
    def get_all(self) -> Dict[str, Any]:
        """
        Get all configuration values.

        Returns:
            Dict[str, Any]: All configuration values
        """
        pass

    @abstractmethod
    def load(self) -> Dict[str, Any]:
        """
        Load configuration from the source.

        Returns:
            Dict[str, Any]: Loaded configuration
        """
        pass

    def save(self) -> None:
        """Save configuration to the source."""


class EnvironmentConfigurationSource(ConfigurationSource):
    """
    Configuration source that uses environment variables.

    This configuration source loads configuration values from environment
    variables. It supports loading from a .env file and accessing environment
    variables directly.
    """

    def __init__(self, env_file: Optional[str] = None, prefix: str = ""):
        """
        Initialize the environment configuration source.

        Args:
            env_file: Path to a .env file to load
            prefix: Prefix for environment variables
        """
        self.env_file = env_file
        self.prefix = prefix
        self.values: Dict[str, Any] = {}

        # Load environment variables from .env file if provided
        if env_file:
            load_dotenv(dotenv_path=env_file)

        # Load environment variables
        self.load()

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            key: Configuration key
            default: Default value if key is not found

        Returns:
            Any: Configuration value
        """
        env_key = self._get_env_key(key)
        return os.environ.get(env_key, default)

    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.

        Args:
            key: Configuration key
            value: Configuration value
        """
        env_key = self._get_env_key(key)
        os.environ[env_key] = str(value)
        self.values[key] = value

    def has(self, key: str) -> bool:
        """
        Check if a configuration key exists.

        Args:
            key: Configuration key

        Returns:
            bool: True if the key exists, False otherwise
        """
        env_key = self._get_env_key(key)
        return env_key in os.environ

    def delete(self, key: str) -> bool:
        """
        Delete a configuration value.

        Args:
            key: Configuration key

        Returns:
            bool: True if the key was deleted, False if it didn't exist
        """
        env_key = self._get_env_key(key)
        if env_key in os.environ:
            del os.environ[env_key]
            if key in self.values:
                del self.values[key]
            return True
        return False

    def get_all(self) -> Dict[str, Any]:
        """
        Get all configuration values.

        Returns:
            Dict[str, Any]: All configuration values
        """
        return self.values.copy()

    def load(self) -> Dict[str, Any]:
        """
        Load configuration from environment variables.

        Returns:
            Dict[str, Any]: Loaded configuration
        """
        self.values = {}

        # Load environment variables with the specified prefix
        for key, value in os.environ.items():
            if self.prefix and not key.startswith(self.prefix):
                continue

            # Remove prefix from key
            config_key = key[len(self.prefix):] if self.prefix else key

            # Convert value to appropriate type
            if value.lower() in ["true", "yes", "y", "1"]:
                self.values[config_key] = True
            elif value.lower() in ["false", "no", "n", "0"]:
                self.values[config_key] = False
            elif value.isdigit():
                self.values[config_key] = int(value)
            elif value.replace(".", "", 1).isdigit():
                self.values[config_key] = float(value)
            else:
                self.values[config_key] = value

        return self.values

    def save(self) -> None:
        """
        Save configuration to environment variables.

        This method updates the environment variables with the current values.
        If a .env file was provided, it also updates the file.
        """
        # Update environment variables
        for key, value in self.values.items():
            env_key = self._get_env_key(key)
            os.environ[env_key] = str(value)

        # Update .env file if provided
        if self.env_file:
            for key, value in self.values.items():
                env_key = self._get_env_key(key)
                set_key(self.env_file, env_key, str(value))

    def _get_env_key(self, key: str) -> str:
        """
        Get the environment variable key for a configuration key.

        Args:
            key: Configuration key

        Returns:
            str: Environment variable key
        """
        return f"{self.prefix}{key}"


class FileConfigurationSource(ConfigurationSource):
    """
    Configuration source that uses a file.

    This configuration source loads configuration values from a file.
    It supports JSON files.
    """

    def __init__(self, file_path: str):
        """
        Initialize the file configuration source.

        Args:
            file_path: Path to the configuration file
        """
        self.file_path = file_path
        self.values: Dict[str, Any] = {}

        # Load configuration from file
        self.load()

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            key: Configuration key
            default: Default value if key is not found

        Returns:
            Any: Configuration value
        """
        # Handle hierarchical keys (e.g., "section.key")
        parts = key.split(".")
        value = self.values

        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.

        Args:
            key: Configuration key
            value: Configuration value
        """
        # Handle hierarchical keys (e.g., "section.key")
        parts = key.split(".")
        current = self.values

        # Navigate to the correct section
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        # Set the value
        current[parts[-1]] = value

    def has(self, key: str) -> bool:
        """
        Check if a configuration key exists.

        Args:
            key: Configuration key

        Returns:
            bool: True if the key exists, False otherwise
        """
        # Handle hierarchical keys (e.g., "section.key")
        parts = key.split(".")
        value = self.values

        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return False

        return True

    def delete(self, key: str) -> bool:
        """
        Delete a configuration value.

        Args:
            key: Configuration key

        Returns:
            bool: True if the key was deleted, False if it didn't exist
        """
        # Handle hierarchical keys (e.g., "section.key")
        parts = key.split(".")
        current = self.values

        # Navigate to the correct section
        for part in parts[:-1]:
            if part not in current:
                return False
            current = current[part]

        # Delete the value
        if parts[-1] in current:
            del current[parts[-1]]
            return True

        return False

    def get_all(self) -> Dict[str, Any]:
        """
        Get all configuration values.

        Returns:
            Dict[str, Any]: All configuration values
        """
        return self.values.copy()

    def load(self) -> Dict[str, Any]:
        """
        Load configuration from the file.

        Returns:
            Dict[str, Any]: Loaded configuration
        """
        self.values = {}

        # Check if file exists
        file_path = Path(self.file_path)
        if not file_path.exists():
            return self.values

        # Load configuration from file
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                self.values = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError, PermissionError) as e:
            # Log error
            print(f"Error loading configuration from {self.file_path}: {e}")

        return self.values

    def save(self) -> None:
        """Save configuration to the file."""
        # Create directory if it doesn't exist
        file_path = Path(self.file_path)
        # Save configuration to file
        file_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self.values, f, indent=4)
        except (IOError, PermissionError, TypeError) as e:
            # Log error
            print(f"Error saving configuration to {self.file_path}: {e}")


class DictConfigurationSource(ConfigurationSource):
    """
    Configuration source that uses a dictionary.

    This configuration source loads configuration values from a dictionary.
    It is useful for testing and for providing default values.
    """

    def __init__(self, values: Optional[Dict[str, Any]] = None):
        """
        Initialize the dictionary configuration source.

        Args:
            values: Initial configuration values
        """
        self.values = values or {}

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            key: Configuration key
            default: Default value if key is not found

        Returns:
            Any: Configuration value
        """
        # Handle hierarchical keys (e.g., "section.key")
        parts = key.split(".")
        value = self.values

        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.

        Args:
            key: Configuration key
            value: Configuration value
        """
        # Handle hierarchical keys (e.g., "section.key")
        parts = key.split(".")
        current = self.values

        # Navigate to the correct section
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        # Set the value
        current[parts[-1]] = value

    def has(self, key: str) -> bool:
        """
        Check if a configuration key exists.

        Args:
            key: Configuration key

        Returns:
            bool: True if the key exists, False otherwise
        """
        # Handle hierarchical keys (e.g., "section.key")
        parts = key.split(".")
        value = self.values

        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return False

        return True

    def delete(self, key: str) -> bool:
        """
        Delete a configuration value.

        Args:
            key: Configuration key

        Returns:
            bool: True if the key was deleted, False if it didn't exist
        """
        # Handle hierarchical keys (e.g., "section.key")
        parts = key.split(".")
        current = self.values

        # Navigate to the correct section
        for part in parts[:-1]:
            if part not in current:
                return False
            current = current[part]

        # Delete the value
        if parts[-1] in current:
            del current[parts[-1]]
            return True

        return False

    def get_all(self) -> Dict[str, Any]:
        """
        Get all configuration values.

        Returns:
            Dict[str, Any]: All configuration values
        """
        return self.values.copy()

    def load(self) -> Dict[str, Any]:
        """
        Load configuration from the dictionary.

        Returns:
            Dict[str, Any]: Loaded configuration
        """
        return self.values

    def save(self) -> None:
        """Save configuration to the dictionary."""
        # Nothing to do, as the dictionary is already updated
        pass
