"""
Weather interfaces for the autonomous mower.

This module defines interfaces for weather components used in the
autonomous mower project, such as weather services and forecasting.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional, Tuple


class WeatherServiceInterface(ABC):
    """
    Interface for weather service implementations.

    This interface defines the contract that all weather service
    implementations must adhere to.
    """

    @abstractmethod
    def get_current_conditions(self) -> Dict[str, Any]:
        """
        Get current weather conditions from API and sensors.

        Returns:
            Dict[str, Any]: Current weather conditions
        """
        pass

    @abstractmethod
    def is_mowing_weather(self) -> Tuple[bool, str]:
        """
        Check if current weather is suitable for mowing.

        Returns:
            Tuple[bool, str]: (is_suitable, reason)
        """
        pass

    @abstractmethod
    def get_forecast(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get weather forecast for specified number of hours.

        Args:
            hours: Number of hours to forecast

        Returns:
            Dict[str, Any]: Weather forecast data
        """
        pass

    @abstractmethod
    def set_location(self, latitude: float, longitude: float) -> None:
        """
        Set the location for weather forecasts.

        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
        """
        pass

    @abstractmethod
    def set_api_key(self, api_key: str) -> None:
        """
        Set the API key for weather service.

        Args:
            api_key: API key for the weather service
        """
        pass

    @abstractmethod
    def set_ideal_conditions(self, conditions: Dict[str, float]) -> None:
        """
        Set the ideal mowing conditions.

        Args:
            conditions: Dictionary of ideal conditions with thresholds
        """
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources used by the weather service."""
        pass
