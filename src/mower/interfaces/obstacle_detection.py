"""
Obstacle detection interfaces for the autonomous mower.

This module defines interfaces for obstacle detection components used in the
autonomous mower project, such as avoidance algorithms and obstacle detectors.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Any, Optional, Union


class AvoidanceAlgorithmInterface(ABC):
    """
    Interface for obstacle avoidance algorithm implementations.

    This interface defines the contract that all obstacle avoidance algorithm
    implementations must adhere to.
    """

    @abstractmethod
    def start(self) -> None:
        """Start the avoidance algorithm background monitoring."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop the avoidance algorithm background monitoring."""
        pass

    @abstractmethod
    def check_obstacles(self) -> bool:
        """
        Check for obstacles in the current path.

        Returns:
            bool: True if obstacles detected, False otherwise
        """
        pass

    @abstractmethod
    def avoid_obstacle(self) -> bool:
        """
        Modify path to avoid detected obstacles.

        Returns:
            bool: True if successful, False otherwise
        """
        pass

    @abstractmethod
    def check_camera_obstacles_and_dropoffs(self) -> Tuple[bool, bool]:
        """
        Check for obstacles and drop-offs using camera.

        Returns:
            Tuple[bool, bool]: (has_obstacle, has_dropoff)
        """
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources used by the avoidance algorithm."""
        pass


class ObstacleDetectorInterface(ABC):
    """
    Interface for obstacle detector implementations.

    This interface defines the contract that all obstacle detector
    implementations must adhere to.
    """

    @abstractmethod
    def detect_obstacles(self) -> List[Dict[str, Any]]:
        """
        Detect obstacles in the current environment.

        Returns:
            List[Dict[str, Any]]: List of detected obstacles with their properties
        """
        pass

    @abstractmethod
    def detect_drop(self) -> bool:
        """
        Detect drop-offs in the current environment.

        Returns:
            bool: True if drop-off detected, False otherwise
        """
        pass

    @abstractmethod
    def get_latest_frame(self) -> Optional[Any]:
        """
        Get the latest camera frame.

        Returns:
            Optional[Any]: Latest camera frame or None if not available
        """
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources used by the obstacle detector."""
        pass


class ObstacleMapperInterface(ABC):
    """
    Interface for obstacle mapper implementations.

    This interface defines the contract that all obstacle mapper
    implementations must adhere to.
    """

    @abstractmethod
    def detect_obstacle(self) -> bool:
        """
        Check if an obstacle is detected using the sensors.

        Returns:
            bool: True if obstacle detected, False otherwise
        """
        pass

    @abstractmethod
    def record_obstacle(self) -> None:
        """
        Record the current GPS position as an obstacle if inside the boundary.
        """
        pass

    @abstractmethod
    def save_obstacle_map(self, filename: str = "obstacle_map.json") -> None:
        """
        Save the obstacle map to a JSON file.

        Args:
            filename: Name of the file to save the obstacle map to
        """
        pass

    @abstractmethod
    def load_obstacle_map(
        self, filename: str = "obstacle_map.json"
    ) -> List[Dict[str, float]]:
        """
        Load the obstacle map from a JSON file.

        Args:
            filename: Name of the file to load the obstacle map from

        Returns:
            List[Dict[str, float]]: List of obstacle positions
        """
        pass

    @abstractmethod
    def is_within_yard(self, position: Tuple[float, float]) -> bool:
        """
        Check if the current position is within the yard boundary.

        Args:
            position: Position to check (latitude, longitude)

        Returns:
            bool: True if position is within yard, False otherwise
        """
        pass

    @abstractmethod
    def explore_yard(self, duration: int = 300) -> None:
        """
        Explore the yard to map obstacles for a given duration.

        Args:
            duration: Duration of exploration in seconds
        """
        pass

    @abstractmethod
    def get_obstacle_map(self) -> List[Dict[str, float]]:
        """
        Get the current obstacle map.

        Returns:
            List[Dict[str, float]]: List of obstacle positions
        """
        pass

    @abstractmethod
    def clear_obstacle_map(self) -> None:
        """Clear the obstacle map."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources used by the obstacle mapper."""
        pass
