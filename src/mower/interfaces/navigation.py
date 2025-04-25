"""
Navigation interfaces for the autonomous mower.

This module defines interfaces for navigation components used in the
autonomous mower project, such as localization, path planning, and GPS.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Any, Optional
import numpy as np


class GpsInterface(ABC):
    """
    Interface for GPS implementations.

    This interface defines the contract that all GPS implementations
    must adhere to.
    """

    @abstractmethod
    def start(self) -> None:
        """Start the GPS reading thread."""
        pass

    @abstractmethod
    def run(self) -> Optional[Tuple]:
        """
        Get the current GPS position.

        Returns:
            Optional[Tuple]: GPS position data or None if not available
        """
        pass

    @abstractmethod
    def get_latest_position(self) -> Optional[Tuple]:
        """
        Get the latest GPS position.

        Returns:
            Optional[Tuple]: Latest GPS position data or None if not available
        """
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """Shutdown the GPS and release resources."""
        pass


class LocalizationInterface(ABC):
    """
    Interface for localization implementations.

    This interface defines the contract that all localization implementations
    must adhere to.
    """

    @abstractmethod
    def start(self) -> None:
        """Start the localization system."""
        pass

    @abstractmethod
    def estimate_position(self) -> Dict[str, Any]:
        """
        Estimate the current position using sensor fusion.

        Returns:
            Dict[str, Any]: Position data and status
        """
        pass

    @abstractmethod
    def update(self) -> Dict[str, Any]:
        """
        Update the position estimate with new sensor data.

        Returns:
            Dict[str, Any]: Updated position data and status
        """
        pass

    @abstractmethod
    def is_within_yard(self, lat: float, lon: float) -> bool:
        """
        Check if a position is within the yard boundary.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            bool: True if within yard, False otherwise
        """
        pass

    @abstractmethod
    def get_position_accuracy(self) -> float:
        """
        Get the current position accuracy estimate.

        Returns:
            float: Position accuracy in meters
        """
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources used by the localization system."""
        pass


class PathPlannerInterface(ABC):
    """
    Interface for path planner implementations.

    This interface defines the contract that all path planner implementations
    must adhere to.
    """

    @abstractmethod
    def start(self) -> None:
        """Start the path planner."""
        pass

    @abstractmethod
    def generate_path(self) -> List[Tuple[float, float]]:
        """
        Generate a path based on the current configuration.

        Returns:
            List[Tuple[float, float]]: List of waypoints in the path
        """
        pass

    @abstractmethod
    def update_obstacle_map(self, obstacles: List[Tuple[float, float]]) -> None:
        """
        Update the obstacle map with new obstacle positions.

        Args:
            obstacles: List of obstacle positions (lat, lon)
        """
        pass

    @abstractmethod
    def get_current_goal(self) -> Optional[Tuple[float, float]]:
        """
        Get the current goal position.

        Returns:
            Optional[Tuple[float, float]]: Current goal position or None if not available
        """
        pass

    @abstractmethod
    def get_path(self, start: Tuple[float, float], goal: Tuple[float, float]) -> List[Dict[str, float]]:
        """
        Get a path from start to goal.

        Args:
            start: Start position (lat, lon)
            goal: Goal position (lat, lon)

        Returns:
            List[Dict[str, float]]: List of waypoints in the path
        """
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources used by the path planner."""
        pass
