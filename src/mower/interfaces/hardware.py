"""
Hardware interfaces for the autonomous mower.

This module defines interfaces for hardware components used in the
autonomous mower project, such as blade controllers, motor drivers,
and sensors.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime


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


class SensorInterface(ABC):
    """
    Interface for sensor interface implementations.

    This interface defines the contract that all sensor interface
    implementations must adhere to.
    """

    @abstractmethod
    def start(self) -> None:
        """Start the sensor interface."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop the sensor interface."""
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """Shutdown the sensor interface."""
        pass

    @abstractmethod
    def get_sensor_data(self) -> Dict[str, Any]:
        """
        Get the current sensor readings.

        Returns:
            Dict[str, Any]: Dictionary containing sensor readings
        """
        pass

    @abstractmethod
    def get_sensor_status(self) -> Dict[str, Any]:
        """
        Get the status of all sensors.

        Returns:
            Dict[str, Any]: Dictionary containing sensor status information
        """
        pass

    @abstractmethod
    def is_safe_to_operate(self) -> bool:
        """
        Check if it's safe to operate based on sensor readings.

        Returns:
            bool: True if safe to operate, False otherwise
        """
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources used by the sensor interface."""
        pass


class CameraInterface(ABC):
    """
    Interface for camera implementations.

    This interface defines the contract that all camera
    implementations must adhere to.
    """

    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the camera.

        Returns:
            bool: True if initialization was successful, False otherwise
        """
        pass

    @abstractmethod
    def capture_image(self) -> Any:
        """
        Capture an image from the camera.

        Returns:
            Any: The captured image
        """
        pass

    @abstractmethod
    def start_preview(self) -> None:
        """Start the camera preview."""
        pass

    @abstractmethod
    def stop_preview(self) -> None:
        """Stop the camera preview."""
        pass

    @abstractmethod
    def set_resolution(self, width: int, height: int) -> None:
        """
        Set the camera resolution.

        Args:
            width: Image width in pixels
            height: Image height in pixels
        """
        pass

    @abstractmethod
    def get_resolution(self) -> tuple:
        """
        Get the current camera resolution.

        Returns:
            tuple: (width, height) in pixels
        """
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources used by the camera."""
        pass


class GPIOInterface(ABC):
    """
    Interface for GPIO manager implementations.

    This interface defines the contract that all GPIO manager
    implementations must adhere to.
    """

    @abstractmethod
    def setup_pin(
        self, pin: int, mode: str, initial: Optional[int] = None
    ) -> None:
        """
        Set up a GPIO pin.

        Args:
            pin: Pin number
            mode: Pin mode ('in' or 'out')
            initial: Initial value for output pins
        """
        pass

    @abstractmethod
    def set_pin(self, pin: int, value: int) -> None:
        """
        Set the value of a GPIO pin.

        Args:
            pin: Pin number
            value: Pin value (0 or 1)
        """
        pass

    @abstractmethod
    def get_pin(self, pin: int) -> int:
        """
        Get the value of a GPIO pin.

        Args:
            pin: Pin number

        Returns:
            int: Pin value (0 or 1)
        """
        pass

    @abstractmethod
    def cleanup_pin(self, pin: int) -> None:
        """
        Clean up a GPIO pin.

        Args:
            pin: Pin number
        """
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up all GPIO resources."""
        pass
