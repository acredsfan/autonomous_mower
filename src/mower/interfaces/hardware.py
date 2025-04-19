"""
Hardware interfaces for the autonomous mower.

This module defines interfaces for hardware components used in the
autonomous mower project, such as blade controllers, motor drivers,
and sensors.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BladeControllerInterface(ABC):
    """
    Interface for blade controller implementations.
    
    This interface defines the contract that all blade controller
    implementations must adhere to.
    """
    
    @abstractmethod
    def enable(self) -> bool:
        """
        Enable the blade motor.
        
        Returns:
            bool: True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def disable(self) -> bool:
        """
        Disable the blade motor.
        
        Returns:
            bool: True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def set_speed(self, speed: float) -> bool:
        """
        Set the blade motor speed.
        
        Args:
            speed: Speed value between 0.0 (stopped) and 1.0 (full speed).
            
        Returns:
            bool: True if successful, False otherwise.
        """
        pass
    
    @abstractmethod
    def is_enabled(self) -> bool:
        """
        Check if the blade motor is enabled.
        
        Returns:
            bool: True if enabled, False otherwise
        """
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources used by the blade controller."""
        pass
    
    @abstractmethod
    def get_state(self) -> Dict[str, Any]:
        """
        Get the current state of the blade controller.
        
        Returns:
            Dict[str, Any]: Dictionary containing state information
        """
        pass


class MotorDriverInterface(ABC):
    """
    Interface for motor driver implementations.
    
    This interface defines the contract that all motor driver
    implementations must adhere to.
    """
    
    @abstractmethod
    def forward(self, speed: float) -> None:
        """
        Move forward at the specified speed.
        
        Args:
            speed: Speed value between 0.0 (stopped) and 1.0 (full speed).
        """
        pass
    
    @abstractmethod
    def backward(self, speed: float) -> None:
        """
        Move backward at the specified speed.
        
        Args:
            speed: Speed value between 0.0 (stopped) and 1.0 (full speed).
        """
        pass
    
    @abstractmethod
    def left(self, speed: float) -> None:
        """
        Turn left at the specified speed.
        
        Args:
            speed: Speed value between 0.0 (stopped) and 1.0 (full speed).
        """
        pass
    
    @abstractmethod
    def right(self, speed: float) -> None:
        """
        Turn right at the specified speed.
        
        Args:
            speed: Speed value between 0.0 (stopped) and 1.0 (full speed).
        """
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """Stop all motors."""
        pass
    
    @abstractmethod
    def run(self, steering: float, throttle: float) -> None:
        """
        Run the motors with the specified steering and throttle values.
        
        Args:
            steering: Steering value between -1.0 (full left) and 1.0 (full right).
            throttle: Throttle value between -1.0 (full reverse) and 1.0 (full forward).
        """
        pass
    
    @abstractmethod
    def shutdown(self) -> None:
        """Shutdown the motor driver and release resources."""
        pass