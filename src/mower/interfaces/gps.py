"""
GPS and positioning interfaces for the autonomous mower.

This module defines interfaces for GPS and positioning systems used in the
autonomous mower project, providing a flexible framework for adding
support for different GPS modules and positioning systems.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
from datetime import datetime


class GPSFixType(Enum):
    """Enum for different GPS fix types."""
    NO_FIX = 0
    GPS_FIX = 1
    DGPS_FIX = 2
    PPS_FIX = 3
    RTK_FIX = 4
    FLOAT_RTK = 5
    DEAD_RECKONING = 6
    MANUAL = 7
    SIMULATION = 8


class GPSModuleInterface(ABC):
    """
    Interface for GPS module implementations.
    
    This interface defines the contract that all GPS module
    implementations must adhere to.
    """
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the GPS module.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_position(self) -> Tuple[float, float]:
        """
        Get the current GPS position.
        
        Returns:
            Tuple[float, float]: Latitude and longitude
        """
        pass
    
    @abstractmethod
    def get_altitude(self) -> float:
        """
        Get the current altitude.
        
        Returns:
            float: Altitude in meters
        """
        pass
    
    @abstractmethod
    def get_speed(self) -> float:
        """
        Get the current ground speed.
        
        Returns:
            float: Speed in meters per second
        """
        pass
    
    @abstractmethod
    def get_heading(self) -> float:
        """
        Get the current heading.
        
        Returns:
            float: Heading in degrees (0-359)
        """
        pass
    
    @abstractmethod
    def get_fix_type(self) -> GPSFixType:
        """
        Get the current GPS fix type.
        
        Returns:
            GPSFixType: Current fix type
        """
        pass
    
    @abstractmethod
    def get_satellites(self) -> int:
        """
        Get the number of satellites in view.
        
        Returns:
            int: Number of satellites
        """
        pass
    
    @abstractmethod
    def get_hdop(self) -> float:
        """
        Get the horizontal dilution of precision.
        
        Returns:
            float: HDOP value
        """
        pass
    
    @abstractmethod
    def get_timestamp(self) -> datetime:
        """
        Get the timestamp of the last GPS fix.
        
        Returns:
            datetime: Timestamp
        """
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the GPS module.
        
        Returns:
            Dict[str, Any]: GPS status information
        """
        pass
    
    @abstractmethod
    def set_update_rate(self, rate: int) -> bool:
        """
        Set the update rate of the GPS module.
        
        Args:
            rate: Update rate in Hz
            
        Returns:
            bool: True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources used by the GPS module."""
        pass


class RTKGPSModuleInterface(GPSModuleInterface):
    """
    Interface for RTK-enabled GPS module implementations.
    
    This interface extends the GPSModuleInterface with methods
    specific to RTK-enabled GPS modules.
    """
    
    @abstractmethod
    def get_rtk_status(self) -> Dict[str, Any]:
        """
        Get the current RTK status.
        
        Returns:
            Dict[str, Any]: RTK status information
        """
        pass
    
    @abstractmethod
    def set_rtk_base_position(self, latitude: float, longitude: float, altitude: float) -> bool:
        """
        Set the position of the RTK base station.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            altitude: Altitude in meters
            
        Returns:
            bool: True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def connect_to_ntrip(self, host: str, port: int, mountpoint: str, username: str, password: str) -> bool:
        """
        Connect to an NTRIP server for RTK corrections.
        
        Args:
            host: NTRIP server hostname
            port: NTRIP server port
            mountpoint: NTRIP mountpoint
            username: NTRIP username
            password: NTRIP password
            
        Returns:
            bool: True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def disconnect_from_ntrip(self) -> bool:
        """
        Disconnect from the NTRIP server.
        
        Returns:
            bool: True if successful, False otherwise
        """
        pass


class PositioningSystemInterface(ABC):
    """
    Interface for positioning system implementations.
    
    This interface defines methods for managing multiple positioning
    sources and providing a unified positioning solution.
    """
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the positioning system.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def register_positioning_source(self, source_id: str, source: Any) -> bool:
        """
        Register a positioning source with the system.
        
        Args:
            source_id: ID of the positioning source
            source: Positioning source instance
            
        Returns:
            bool: True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def unregister_positioning_source(self, source_id: str) -> bool:
        """
        Unregister a positioning source from the system.
        
        Args:
            source_id: ID of the positioning source
            
        Returns:
            bool: True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_position(self) -> Tuple[float, float]:
        """
        Get the current position from the best available source.
        
        Returns:
            Tuple[float, float]: Latitude and longitude
        """
        pass
    
    @abstractmethod
    def get_position_accuracy(self) -> float:
        """
        Get the accuracy of the current position estimate.
        
        Returns:
            float: Position accuracy in meters
        """
        pass
    
    @abstractmethod
    def get_altitude(self) -> float:
        """
        Get the current altitude from the best available source.
        
        Returns:
            float: Altitude in meters
        """
        pass
    
    @abstractmethod
    def get_heading(self) -> float:
        """
        Get the current heading from the best available source.
        
        Returns:
            float: Heading in degrees (0-359)
        """
        pass
    
    @abstractmethod
    def get_speed(self) -> float:
        """
        Get the current speed from the best available source.
        
        Returns:
            float: Speed in meters per second
        """
        pass
    
    @abstractmethod
    def get_positioning_sources(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all registered positioning sources.
        
        Returns:
            Dict[str, Dict[str, Any]]: Information about each positioning source
        """
        pass
    
    @abstractmethod
    def set_primary_source(self, source_id: str) -> bool:
        """
        Set the primary positioning source.
        
        Args:
            source_id: ID of the positioning source to set as primary
            
        Returns:
            bool: True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_primary_source(self) -> str:
        """
        Get the ID of the current primary positioning source.
        
        Returns:
            str: ID of the primary positioning source
        """
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources used by the positioning system."""
        pass