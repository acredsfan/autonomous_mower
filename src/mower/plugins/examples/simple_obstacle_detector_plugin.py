"""
Example obstacle detector plugin for the autonomous mower.

This module demonstrates how to create a detection plugin for the autonomous mower.
It provides a simple obstacle detector that detects obstacles based on distance sensor data.
"""

import time
from typing import Dict, Any, List

from mower.plugins.plugin_base import DetectionPlugin
from mower.utilities.logger_config import LoggerConfigInfo

# Initialize logger
logger = LoggerConfigInfo.get_logger(__name__)


class SimpleObstacleDetectorPlugin(DetectionPlugin):
    """
    Example obstacle detector plugin.
    
    This plugin provides a simple obstacle detector that detects obstacles
    based on distance sensor data.
    """
    
    def __init__(self):
        """Initialize the obstacle detector plugin."""
        self._initialized = False
        self._distance_threshold = 30.0  # Distance threshold in cm
        
        logger.info("SimpleObstacleDetectorPlugin created")
    
    @property
    def plugin_id(self) -> str:
        """
        Get the unique identifier for this plugin.
        
        Returns:
            str: Unique identifier for this plugin
        """
        return "simple_obstacle_detector"
    
    @property
    def plugin_name(self) -> str:
        """
        Get the human-readable name for this plugin.
        
        Returns:
            str: Human-readable name for this plugin
        """
        return "Simple Obstacle Detector"
    
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
        return "Simple obstacle detector that detects obstacles based on distance sensor data"
    
    @property
    def detection_type(self) -> str:
        """
        Get the type of detection this plugin performs.
        
        Returns:
            str: Type of detection
        """
        return "obstacle"
    
    @property
    def required_data_keys(self) -> List[str]:
        """
        Get the keys required in the data dictionary for detection.
        
        Returns:
            List[str]: List of required keys
        """
        return ["left_distance", "right_distance", "front_distance"]
    
    def initialize(self) -> bool:
        """
        Initialize the plugin.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            # Simulate detector initialization
            logger.info("Initializing simple obstacle detector plugin")
            time.sleep(0.1)  # Simulate initialization delay
            
            self._initialized = True
            
            logger.info("Simple obstacle detector plugin initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing simple obstacle detector plugin: {e}")
            return False
    
    def detect(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Detect obstacles in the provided data.
        
        Args:
            data: Data to analyze
            
        Returns:
            List[Dict[str, Any]]: List of detected obstacles
        """
        try:
            # Check if all required keys are present
            for key in self.required_data_keys:
                if key not in data:
                    logger.warning(f"Missing required key: {key}")
                    return []
            
            # Get distance values
            left_distance = data.get("left_distance", float("inf"))
            right_distance = data.get("right_distance", float("inf"))
            front_distance = data.get("front_distance", float("inf"))
            
            # Detect obstacles
            obstacles = []
            
            if left_distance < self._distance_threshold:
                obstacles.append({
                    "type": "obstacle",
                    "position": "left",
                    "distance": left_distance,
                    "confidence": 0.8,
                    "timestamp": time.time()
                })
            
            if right_distance < self._distance_threshold:
                obstacles.append({
                    "type": "obstacle",
                    "position": "right",
                    "distance": right_distance,
                    "confidence": 0.8,
                    "timestamp": time.time()
                })
            
            if front_distance < self._distance_threshold:
                obstacles.append({
                    "type": "obstacle",
                    "position": "front",
                    "distance": front_distance,
                    "confidence": 0.9,
                    "timestamp": time.time()
                })
            
            return obstacles
            
        except Exception as e:
            logger.error(f"Error detecting obstacles: {e}")
            return []
    
    def cleanup(self) -> None:
        """Clean up resources used by the plugin."""
        try:
            # Simulate cleanup
            logger.info("Cleaning up simple obstacle detector plugin")
            time.sleep(0.1)  # Simulate cleanup delay
            
            self._initialized = False
            
            logger.info("Simple obstacle detector plugin cleaned up successfully")
            
        except Exception as e:
            logger.error(f"Error cleaning up simple obstacle detector plugin: {e}")


# Example usage
if __name__ == "__main__":
    # Create and initialize the plugin
    plugin = SimpleObstacleDetectorPlugin()
    plugin.initialize()
    
    # Test with sample data
    sample_data = {
        "left_distance": 20.0,
        "right_distance": 50.0,
        "front_distance": 15.0
    }
    
    # Detect obstacles
    obstacles = plugin.detect(sample_data)
    
    # Print detected obstacles
    print(f"Detected {len(obstacles)} obstacles:")
    for obstacle in obstacles:
        print(f"  Position: {obstacle['position']}, Distance: {obstacle['distance']} cm")
    
    # Clean up the plugin
    plugin.cleanup()