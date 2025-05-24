"""
Configuration interface for the autonomous mower.

This module defines the interface for configuration management in the
autonomous mower project. It provides a standard interface for accessing
and modifying configuration values from various sources.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union


class ConfigurationInterface(ABC):
    """
    Interface for configuration implementations.

    This interface defines the contract that all configuration
    implementations must adhere to.
    """
    
    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            key: Configuration key (can be hierarchical, e.g., 'section.key')
            default: Default value if key is not found

        Returns:
            Any: Configuration value
        """
    
    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.

        Args:
            key: Configuration key (can be hierarchical, e.g., 'section.key')
            value: Configuration value
        """

    @abstractmethod
    def has(self, key: str) -> bool:
        """
        Check if a configuration key exists.

        Args:
            key: Configuration key (can be hierarchical, e.g., 'section.key')

        Returns:
            bool: True if the key exists, False otherwise
        """

    @abstractmethod
    def delete(self, key: str) -> bool:
        """
        Delete a configuration value.

        Args:
            key: Configuration key (can be hierarchical, e.g., 'section.key')

        Returns:
            bool: True if the key was deleted, False if it didn't exist
        """

    @abstractmethod
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get a configuration section.

        Args:
            section: Section name

        Returns:
            Dict[str, Any]: Configuration section
        """

    @abstractmethod
    def get_all(self) -> Dict[str, Any]:
        """
        Get all configuration values.

        Returns:
            Dict[str, Any]: All configuration values
        """

    @abstractmethod
    def load(self, source: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Load configuration from a source.

        Args:
            source: Source to load from (file path or dictionary)

        Returns:
            Dict[str, Any]: Loaded configuration
        """

    @abstractmethod
    def save(self, destination: str) -> None:
        """
        Save configuration to a destination.

        Args:
            destination: Destination to save to (file path)
        """

    @abstractmethod
    def reset(self) -> None:
        """Reset the configuration to its default state."""

    @abstractmethod
    def get_int(
        self, key: str, default: Optional[int] = None
    ) -> Optional[int]:
        """
        Get a configuration value as an integer.

        Args:
            key: Configuration key
            default: Default value if key is not found or value is not an integer

        Returns:
            Optional[int]: Configuration value as an integer, or default if not found
        """

    @abstractmethod
    def get_float(
        self, key: str, default: Optional[float] = None
    ) -> Optional[float]:
        """
        Get a configuration value as a float.

        Args:
            key: Configuration key
            default: Default value if key is not found or value is not a float

        Returns:
            Optional[float]: Configuration value as a float, or default if not found
        """

    @abstractmethod
    def get_bool(
        self, key: str, default: Optional[bool] = None
    ) -> Optional[bool]:
        """
        Get a configuration value as a boolean.

        Args:
            key: Configuration key
            default: Default value if key is not found or value is not a boolean

        Returns:
            Optional[bool]: Configuration value as a boolean, or default if not found
        """

    @abstractmethod
    def get_str(
        self, key: str, default: Optional[str] = None
    ) -> Optional[str]:
        """
        Get a configuration value as a string.

        Args:
            key: Configuration key
            default: Default value if key is not found or value is not a string

        Returns:
            Optional[str]: Configuration value as a string, or default if not found
        """

    @abstractmethod
    def get_list(
        self, key: str, default: Optional[List[Any]] = None
    ) -> Optional[List[Any]]:
        """
        Get a configuration value as a list.

        Args:
            key: Configuration key
            default: Default value if key is not found or value is not a list

        Returns:
            Optional[List[Any]]: Configuration value as a list, or default if not found
        """

    @abstractmethod
    def get_dict(
        self, key: str, default: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get a configuration value as a dictionary.

        Args:
            key: Configuration key
            default: Default value if key is not found or value is not a dictionary

        Returns:
            Optional[Dict[str, Any]]: Configuration value as a dictionary,
            or default if not found
        """
