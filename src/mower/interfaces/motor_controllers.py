"""
Motor controller interfaces for the autonomous mower.

This module defines interfaces for various motor controller types used in the
autonomous mower project, providing a flexible framework for adding
support for different motor controllers.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum


class MotorType(Enum):
    """Enum for different types of motors."""
    DC = "dc"
    BRUSHLESS = "brushless"
    STEPPER = "stepper"
    SERVO = "servo"


class MotorControllerInterface(ABC):
    """
    Base interface for all motor controller implementations.
    
    This interface defines the common contract that all motor controller
    implementations must adhere to.
    """
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the motor controller.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def set_speed(self, motor_id: int, speed: float) -> bool:
        """
        Set the speed of a specific motor.
        
        Args:
            motor_id: ID of the motor to control
            speed: Speed value between -1.0 (full reverse) and 1.0 (full forward)
            
        Returns:
            bool: True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def stop(self, motor_id: Optional[int] = None) -> bool:
        """
        Stop a specific motor or all motors.
        
        Args:
            motor_id: ID of the motor to stop, or None to stop all motors
            
        Returns:
            bool: True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_status(self, motor_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get the status of a specific motor or all motors.
        
        Args:
            motor_id: ID of the motor to check, or None to check all motors
            
        Returns:
            Dict[str, Any]: Motor status information
        """
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources used by the motor controller."""
        pass


class DCMotorControllerInterface(MotorControllerInterface):
    """Interface for DC motor controllers."""
    
    @abstractmethod
    def set_direction(self, motor_id: int, forward: bool) -> bool:
        """
        Set the direction of a specific motor.
        
        Args:
            motor_id: ID of the motor to control
            forward: True for forward, False for reverse
            
        Returns:
            bool: True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def set_brake(self, motor_id: int, brake: bool) -> bool:
        """
        Set the brake state of a specific motor.
        
        Args:
            motor_id: ID of the motor to control
            brake: True to enable brake, False to disable
            
        Returns:
            bool: True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_current(self, motor_id: int) -> float:
        """
        Get the current draw of a specific motor.
        
        Args:
            motor_id: ID of the motor to check
            
        Returns:
            float: Current in amperes
        """
        pass


class BrushlessMotorControllerInterface(MotorControllerInterface):
    """Interface for brushless motor controllers."""
    
    @abstractmethod
    def set_rpm(self, motor_id: int, rpm: float) -> bool:
        """
        Set the RPM of a specific motor.
        
        Args:
            motor_id: ID of the motor to control
            rpm: Target RPM
            
        Returns:
            bool: True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_rpm(self, motor_id: int) -> float:
        """
        Get the current RPM of a specific motor.
        
        Args:
            motor_id: ID of the motor to check
            
        Returns:
            float: Current RPM
        """
        pass
    
    @abstractmethod
    def calibrate_esc(self, motor_id: int) -> bool:
        """
        Calibrate the ESC for a specific motor.
        
        Args:
            motor_id: ID of the motor to calibrate
            
        Returns:
            bool: True if successful, False otherwise
        """
        pass


class StepperMotorControllerInterface(MotorControllerInterface):
    """Interface for stepper motor controllers."""
    
    @abstractmethod
    def set_position(self, motor_id: int, position: int) -> bool:
        """
        Set the position of a specific motor.
        
        Args:
            motor_id: ID of the motor to control
            position: Target position in steps
            
        Returns:
            bool: True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_position(self, motor_id: int) -> int:
        """
        Get the current position of a specific motor.
        
        Args:
            motor_id: ID of the motor to check
            
        Returns:
            int: Current position in steps
        """
        pass
    
    @abstractmethod
    def set_step_mode(self, motor_id: int, mode: str) -> bool:
        """
        Set the step mode of a specific motor.
        
        Args:
            motor_id: ID of the motor to control
            mode: Step mode (e.g., 'full', 'half', 'quarter', 'eighth', 'sixteenth')
            
        Returns:
            bool: True if successful, False otherwise
        """
        pass


class ServoControllerInterface(MotorControllerInterface):
    """Interface for servo controllers."""
    
    @abstractmethod
    def set_angle(self, motor_id: int, angle: float) -> bool:
        """
        Set the angle of a specific servo.
        
        Args:
            motor_id: ID of the servo to control
            angle: Target angle in degrees
            
        Returns:
            bool: True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_angle(self, motor_id: int) -> float:
        """
        Get the current angle of a specific servo.
        
        Args:
            motor_id: ID of the servo to check
            
        Returns:
            float: Current angle in degrees
        """
        pass
    
    @abstractmethod
    def set_pulse_width(self, motor_id: int, pulse_width: int) -> bool:
        """
        Set the pulse width of a specific servo.
        
        Args:
            motor_id: ID of the servo to control
            pulse_width: Target pulse width in microseconds
            
        Returns:
            bool: True if successful, False otherwise
        """
        pass


class MotorDriverInterface(ABC):
    """
    Interface for motor driver implementations that control multiple motors.
    
    This interface defines methods for controlling the movement of the mower
    by coordinating multiple motors.
    """
    
    @abstractmethod
    def forward(self, speed: float) -> bool:
        """
        Move forward at the specified speed.
        
        Args:
            speed: Speed value between 0.0 (stopped) and 1.0 (full speed)
            
        Returns:
            bool: True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def backward(self, speed: float) -> bool:
        """
        Move backward at the specified speed.
        
        Args:
            speed: Speed value between 0.0 (stopped) and 1.0 (full speed)
            
        Returns:
            bool: True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def left(self, speed: float) -> bool:
        """
        Turn left at the specified speed.
        
        Args:
            speed: Speed value between 0.0 (stopped) and 1.0 (full speed)
            
        Returns:
            bool: True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def right(self, speed: float) -> bool:
        """
        Turn right at the specified speed.
        
        Args:
            speed: Speed value between 0.0 (stopped) and 1.0 (full speed)
            
        Returns:
            bool: True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def stop(self) -> bool:
        """
        Stop all motors.
        
        Returns:
            bool: True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def run(self, steering: float, throttle: float) -> bool:
        """
        Run the motors with the specified steering and throttle values.
        
        Args:
            steering: Steering value between -1.0 (full left) and 1.0 (full right)
            throttle: Throttle value between -1.0 (full reverse) and 1.0 (full forward)
            
        Returns:
            bool: True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """
        Get the status of the motor driver.
        
        Returns:
            Dict[str, Any]: Motor driver status information
        """
        pass
    
    @abstractmethod
    def shutdown(self) -> None:
        """Shutdown the motor driver and release resources."""
        pass