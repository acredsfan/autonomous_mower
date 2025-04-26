"""
Utility interfaces for the autonomous mower.

This module defines interfaces for utility components used in the
autonomous mower project, such as mapping functions and other helpers.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union


class UtilitiesInterface(ABC):
    """
    Interface for utilities implementations.

    This interface defines the contract that all utilities
    implementations must adhere to.
    """

    @staticmethod
    @abstractmethod
    def map_range(
        x: float, X_min: float, X_max: float, Y_min: float, Y_max: float
    ) -> int:
        """
        Linear mapping between two ranges of values, returning an integer.

        Args:
            x: Value to map
            X_min: Minimum value of the first range
            X_max: Maximum value of the first range
            Y_min: Minimum value of the second range
            Y_max: Maximum value of the second range

        Returns:
            int: Mapped value as an integer
        """
        pass

    @staticmethod
    @abstractmethod
    def map_range_float(
        x: float, X_min: float, X_max: float, Y_min: float, Y_max: float
    ) -> float:
        """
        Linear mapping between two ranges of values, returning a float.

        Args:
            x: Value to map
            X_min: Minimum value of the first range
            X_max: Maximum value of the first range
            Y_min: Minimum value of the second range
            Y_max: Maximum value of the second range

        Returns:
            float: Mapped value as a float, rounded to 2 decimal places
        """
        pass


class LoggerInterface(ABC):
    """
    Interface for logger implementations.

    This interface defines the contract that all logger
    implementations must adhere to.
    """

    @abstractmethod
    def debug(self, message: str) -> None:
        """
        Log a debug message.

        Args:
            message: Message to log
        """
        pass

    @abstractmethod
    def info(self, message: str) -> None:
        """
        Log an info message.

        Args:
            message: Message to log
        """
        pass

    @abstractmethod
    def warning(self, message: str) -> None:
        """
        Log a warning message.

        Args:
            message: Message to log
        """
        pass

    @abstractmethod
    def error(self, message: str) -> None:
        """
        Log an error message.

        Args:
            message: Message to log
        """
        pass

    @abstractmethod
    def critical(self, message: str) -> None:
        """
        Log a critical message.

        Args:
            message: Message to log
        """
        pass

    @abstractmethod
    def exception(self, message: str) -> None:
        """
        Log an exception message.

        Args:
            message: Message to log
        """
        pass


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
            key: Configuration key
            default: Default value if key is not found

        Returns:
            Any: Configuration value
        """
        pass

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.

        Args:
            key: Configuration key
            value: Configuration value
        """
        pass

    @abstractmethod
    def load(self, filename: str) -> Dict[str, Any]:
        """
        Load configuration from a file.

        Args:
            filename: Name of the file to load

        Returns:
            Dict[str, Any]: Loaded configuration
        """
        pass

    @abstractmethod
    def save(self, filename: str) -> None:
        """
        Save configuration to a file.

        Args:
            filename: Name of the file to save to
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
