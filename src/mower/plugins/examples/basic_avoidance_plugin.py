"""
Example avoidance plugin for the autonomous mower.

This module demonstrates how to create an avoidance plugin for the autonomous mower.
It provides a basic avoidance algorithm that generates a new path to avoid obstacles.
"""

import time
import math
import random
from typing import Dict, Any, List

from mower.plugins.plugin_base import AvoidancePlugin
from mower.utilities.logger_config import LoggerConfigInfo

# Initialize logger
logger = LoggerConfigInfo.get_logger(__name__)


class BasicAvoidancePlugin(AvoidancePlugin):
    """
    Example avoidance plugin.

    This plugin provides a basic avoidance algorithm that generates
    a new path to avoid obstacles.
    """

    def __init__(self):
        """Initialize the avoidance plugin."""
        self._initialized = False
        self._safety_margin = 0.5  # Safety margin in meters

        logger.info("BasicAvoidancePlugin created")

    @property
    def plugin_id(self) -> str:
        """
        Get the unique identifier for this plugin.

        Returns:
            str: Unique identifier for this plugin
        """
        return "basic_avoidance"

    @property
    def plugin_name(self) -> str:
        """
        Get the human-readable name for this plugin.

        Returns:
            str: Human-readable name for this plugin
        """
        return "Basic Avoidance"

    @property
    def plugin_version(self) -> str:
        """
        Get the version of this plugin.

        Returns:
            str: Version of this plugin
        """
        return "1.0.0"

    @property
    def plugin_description(self) -> str:
        """
        Get the description of this plugin.

        Returns:
            str: Description of this plugin
        """
        return "Basic avoidance algorithm that generates a new path to avoid obstacles"

    @property
    def avoidance_type(self) -> str:
        """
        Get the type of avoidance this plugin performs.

        Returns:
            str: Type of avoidance
        """
        return "obstacle"

    def initialize(self) -> bool:
        """
        Initialize the plugin.

        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            # Simulate avoidance algorithm initialization
            logger.info("Initializing basic avoidance plugin")
            time.sleep(0.1)  # Simulate initialization delay

            self._initialized = True

            logger.info("Basic avoidance plugin initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Error initializing basic avoidance plugin: {e}")
            return False

    def avoid(
        self,
        obstacles: List[Dict[str, Any]],
        current_path: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Generate a new path to avoid the detected obstacles.

        Args:
            obstacles: List of detected obstacles
            current_path: Current planned path

        Returns:
            List[Dict[str, Any]]: New path that avoids the obstacles
        """
        try:
            if not obstacles:
                # No obstacles, return the current path
                return current_path

            if not current_path:
                # No current path, return an empty path
                return []

            # Create a new path that avoids the obstacles
            new_path = []

            # Add the first point of the current path
            new_path.append(current_path[0])

            # Process each point in the current path
            for i in range(1, len(current_path)):
                current_point = current_path[i]

                # Check if the current point is near any obstacle
                is_near_obstacle = False
                for obstacle in obstacles:
                    obstacle_position = obstacle.get("position", "")

                    # Skip obstacles without position information
                    if not obstacle_position:
                        continue

                    # Check if the current point is near the obstacle
                    if self._is_point_near_obstacle(current_point, obstacle):
                        is_near_obstacle = True
                        break

                if is_near_obstacle:
                    # Generate a detour around the obstacle
                    detour_points = self._generate_detour(
                        current_point, obstacles
                    )
                    new_path.extend(detour_points)
                else:
                    # Add the current point to the new path
                    new_path.append(current_point)

            return new_path

        except Exception as e:
            logger.error(f"Error generating avoidance path: {e}")
            return current_path

    def _is_point_near_obstacle(
        self, point: Dict[str, Any], obstacle: Dict[str, Any]
    ) -> bool:
        """
        Check if a point is near an obstacle.

        Args:
            point: Point to check
            obstacle: Obstacle to check against

        Returns:
            bool: True if the point is near the obstacle, False otherwise
        """
        # This is a simplified implementation
        # In a real implementation, you would use the actual coordinates

        # Get the position of the obstacle
        obstacle_position = obstacle.get("position", "")

        # Get the coordinates of the point
        point_lat = point.get("lat", 0.0)
        point_lng = point.get("lng", 0.0)

        # Check if the point is near the obstacle based on the position
        if obstacle_position == "left":
            # Check if the point is to the left
            return point_lng < 0.0
        elif obstacle_position == "right":
            # Check if the point is to the right
            return point_lng > 0.0
        elif obstacle_position == "front":
            # Check if the point is in front
            return point_lat > 0.0

        return False

    def _generate_detour(
        self, point: Dict[str, Any], obstacles: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate a detour around obstacles.

        Args:
            point: Point to detour around
            obstacles: List of obstacles

        Returns:
            List[Dict[str, Any]]: List of points forming the detour
        """
        # This is a simplified implementation
        # In a real implementation, you would generate a proper detour path

        # Get the coordinates of the point
        point_lat = point.get("lat", 0.0)
        point_lng = point.get("lng", 0.0)

        # Determine the direction of the detour
        detour_direction = "right"  # Default direction

        # Check if there are obstacles on the right
        for obstacle in obstacles:
            if obstacle.get("position", "") == "right":
                detour_direction = "left"
                break

        # Generate detour points
        detour_points = []

        if detour_direction == "right":
            # Generate a detour to the right
            detour_points.append(
                {"lat": point_lat, "lng": point_lng + self._safety_margin}
            )
            detour_points.append(
                {
                    "lat": point_lat + self._safety_margin,
                    "lng": point_lng + self._safety_margin,
                }
            )
            detour_points.append(
                {"lat": point_lat + self._safety_margin, "lng": point_lng}
            )
        else:
            # Generate a detour to the left
            detour_points.append(
                {"lat": point_lat, "lng": point_lng - self._safety_margin}
            )
            detour_points.append(
                {
                    "lat": point_lat + self._safety_margin,
                    "lng": point_lng - self._safety_margin,
                }
            )
            detour_points.append(
                {"lat": point_lat + self._safety_margin, "lng": point_lng}
            )

        return detour_points

    def cleanup(self) -> None:
        """Clean up resources used by the plugin."""
        try:
            # Simulate cleanup
            logger.info("Cleaning up basic avoidance plugin")
            time.sleep(0.1)  # Simulate cleanup delay

            self._initialized = False

            logger.info("Basic avoidance plugin cleaned up successfully")

        except Exception as e:
            logger.error(f"Error cleaning up basic avoidance plugin: {e}")


# Example usage
if __name__ == "__main__":
    # Create and initialize the plugin
    plugin = BasicAvoidancePlugin()
    plugin.initialize()

    # Test with sample data
    obstacles = [
        {
            "type": "obstacle",
            "position": "front",
            "distance": 15.0,
            "confidence": 0.9,
            "timestamp": time.time(),
        }
    ]

    current_path = [
        {"lat": 0.0, "lng": 0.0},
        {"lat": 1.0, "lng": 0.0},
        {"lat": 2.0, "lng": 0.0},
        {"lat": 3.0, "lng": 0.0},
    ]

    # Generate avoidance path
    new_path = plugin.avoid(obstacles, current_path)

    # Print the new path
    print("Original path:")
    for point in current_path:
        print(f"  ({point['lat']}, {point['lng']})")

    print("\nNew path:")
    for point in new_path:
        print(f"  ({point['lat']}, {point['lng']})")

    # Clean up the plugin
    plugin.cleanup()
