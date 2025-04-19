"""
Power management interfaces for the autonomous mower.

This module defines interfaces for power management components used in the
autonomous mower project, providing a flexible framework for battery
optimization and power monitoring.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum


class PowerMode(Enum):
    """Enum for different power modes."""
    NORMAL = "normal"
    ECO = "eco"
    PERFORMANCE = "performance"
    LOW_BATTERY = "low_battery"
    CHARGING = "charging"


class PowerManagerInterface(ABC):
    """
    Interface for power manager implementations.
    
    This interface defines the contract that all power manager
    implementations must adhere to.
    """
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the power manager.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def set_power_mode(self, mode: PowerMode) -> bool:
        """
        Set the power mode.
        
        Args:
            mode: Power mode to set
            
        Returns:
            bool: True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_power_mode(self) -> PowerMode:
        """
        Get the current power mode.
        
        Returns:
            PowerMode: Current power mode
        """
        pass
    
    @abstractmethod
    def get_battery_level(self) -> float:
        """
        Get the current battery level.
        
        Returns:
            float: Battery level as a percentage (0-100)
        """
        pass
    
    @abstractmethod
    def get_battery_voltage(self) -> float:
        """
        Get the current battery voltage.
        
        Returns:
            float: Battery voltage in volts
        """
        pass
    
    @abstractmethod
    def get_power_consumption(self) -> float:
        """
        Get the current power consumption.
        
        Returns:
            float: Power consumption in watts
        """
        pass
    
    @abstractmethod
    def is_charging(self) -> bool:
        """
        Check if the battery is currently charging.
        
        Returns:
            bool: True if charging, False otherwise
        """
        pass
    
    @abstractmethod
    def get_estimated_runtime(self) -> int:
        """
        Get the estimated remaining runtime.
        
        Returns:
            int: Estimated runtime in minutes
        """
        pass
    
    @abstractmethod
    def enable_component(self, component_id: str) -> bool:
        """
        Enable a specific component.
        
        Args:
            component_id: ID of the component to enable
            
        Returns:
            bool: True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def disable_component(self, component_id: str) -> bool:
        """
        Disable a specific component.
        
        Args:
            component_id: ID of the component to disable
            
        Returns:
            bool: True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_component_power_state(self, component_id: str) -> bool:
        """
        Get the power state of a specific component.
        
        Args:
            component_id: ID of the component to check
            
        Returns:
            bool: True if enabled, False if disabled
        """
        pass
    
    @abstractmethod
    def register_low_battery_callback(self, callback: callable) -> None:
        """
        Register a callback for low battery events.
        
        Args:
            callback: Function to call when battery level is low
        """
        pass
    
    @abstractmethod
    def set_low_battery_threshold(self, threshold: float) -> None:
        """
        Set the low battery threshold.
        
        Args:
            threshold: Battery level threshold as a percentage (0-100)
        """
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources used by the power manager."""
        pass


class ChargingStationInterface(ABC):
    """
    Interface for charging station implementations.
    
    This interface defines the contract that all charging station
    implementations must adhere to.
    """
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the charging station interface.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def is_docked(self) -> bool:
        """
        Check if the mower is currently docked at the charging station.
        
        Returns:
            bool: True if docked, False otherwise
        """
        pass
    
    @abstractmethod
    def is_charging(self) -> bool:
        """
        Check if the mower is currently charging.
        
        Returns:
            bool: True if charging, False otherwise
        """
        pass
    
    @abstractmethod
    def get_charging_status(self) -> Dict[str, Any]:
        """
        Get the current charging status.
        
        Returns:
            Dict[str, Any]: Charging status information
        """
        pass
    
    @abstractmethod
    def get_charging_station_location(self) -> Tuple[float, float]:
        """
        Get the location of the charging station.
        
        Returns:
            Tuple[float, float]: Latitude and longitude of the charging station
        """
        pass
    
    @abstractmethod
    def set_charging_station_location(self, latitude: float, longitude: float) -> bool:
        """
        Set the location of the charging station.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            
        Returns:
            bool: True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def start_docking_procedure(self) -> bool:
        """
        Start the docking procedure.
        
        Returns:
            bool: True if docking procedure started successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def abort_docking_procedure(self) -> bool:
        """
        Abort the docking procedure.
        
        Returns:
            bool: True if docking procedure aborted successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def undock(self) -> bool:
        """
        Undock from the charging station.
        
        Returns:
            bool: True if undocked successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources used by the charging station interface."""
        pass


class WirelessChargingStationInterface(ChargingStationInterface):
    """
    Interface for wireless charging station implementations.
    
    This interface extends the ChargingStationInterface with methods
    specific to wireless charging.
    """
    
    @abstractmethod
    def get_charging_efficiency(self) -> float:
        """
        Get the current charging efficiency.
        
        Returns:
            float: Charging efficiency as a percentage (0-100)
        """
        pass
    
    @abstractmethod
    def get_alignment_status(self) -> Dict[str, Any]:
        """
        Get the current alignment status with the charging pad.
        
        Returns:
            Dict[str, Any]: Alignment status information
        """
        pass
    
    @abstractmethod
    def optimize_alignment(self) -> bool:
        """
        Optimize the alignment with the charging pad.
        
        Returns:
            bool: True if alignment optimization was successful, False otherwise
        """
        pass