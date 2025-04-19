"""
Base classes for plugins in the autonomous mower.

This module defines the base classes for plugins in the autonomous mower project.
All plugins must inherit from one of these base classes to be recognized by the
plugin system.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Type


class Plugin(ABC):
    """
    Base class for all plugins.
    
    All plugins must inherit from this class to be recognized by the plugin system.
    """
    
    @property
    @abstractmethod
    def plugin_id(self) -> str:
        """
        Get the unique identifier for this plugin.
        
        Returns:
            str: Unique identifier for this plugin
        """
        pass
    
    @property
    @abstractmethod
    def plugin_name(self) -> str:
        """
        Get the human-readable name for this plugin.
        
        Returns:
            str: Human-readable name for this plugin
        """
        pass
    
    @property
    @abstractmethod
    def plugin_version(self) -> str:
        """
        Get the version of this plugin.
        
        Returns:
            str: Version of this plugin
        """
        pass
    
    @property
    @abstractmethod
    def plugin_description(self) -> str:
        """
        Get the description of this plugin.
        
        Returns:
            str: Description of this plugin
        """
        pass
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the plugin.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources used by the plugin."""
        pass


class SensorPlugin(Plugin):
    """
    Base class for sensor plugins.
    
    Sensor plugins provide data from physical or virtual sensors.
    """
    
    @abstractmethod
    def get_data(self) -> Dict[str, Any]:
        """
        Get data from the sensor.
        
        Returns:
            Dict[str, Any]: Sensor data
        """
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """
        Get the status of the sensor.
        
        Returns:
            Dict[str, Any]: Sensor status
        """
        pass
    
    @property
    @abstractmethod
    def sensor_type(self) -> str:
        """
        Get the type of this sensor.
        
        Returns:
            str: Type of this sensor (e.g., 'temperature', 'humidity', 'distance')
        """
        pass


class DetectionPlugin(Plugin):
    """
    Base class for detection algorithm plugins.
    
    Detection plugins provide algorithms for detecting obstacles, objects, or other
    features in the environment.
    """
    
    @abstractmethod
    def detect(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Detect objects or features in the provided data.
        
        Args:
            data: Data to analyze
            
        Returns:
            List[Dict[str, Any]]: List of detected objects or features
        """
        pass
    
    @property
    @abstractmethod
    def detection_type(self) -> str:
        """
        Get the type of detection this plugin performs.
        
        Returns:
            str: Type of detection (e.g., 'obstacle', 'object', 'boundary')
        """
        pass
    
    @property
    @abstractmethod
    def required_data_keys(self) -> List[str]:
        """
        Get the keys required in the data dictionary for detection.
        
        Returns:
            List[str]: List of required keys
        """
        pass


class AvoidancePlugin(Plugin):
    """
    Base class for avoidance algorithm plugins.
    
    Avoidance plugins provide algorithms for avoiding obstacles or other
    features in the environment.
    """
    
    @abstractmethod
    def avoid(self, obstacles: List[Dict[str, Any]], current_path: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate a new path to avoid the detected obstacles.
        
        Args:
            obstacles: List of detected obstacles
            current_path: Current planned path
            
        Returns:
            List[Dict[str, Any]]: New path that avoids the obstacles
        """
        pass
    
    @property
    @abstractmethod
    def avoidance_type(self) -> str:
        """
        Get the type of avoidance this plugin performs.
        
        Returns:
            str: Type of avoidance (e.g., 'obstacle', 'boundary')
        """
        pass