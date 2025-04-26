"""
Base classes for simulated hardware components.

This module provides base classes and interfaces for simulated hardware components.
These classes define the common functionality and interfaces that all simulated
hardware components should implement.
"""

import time
import logging
import threading
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple, Union, Type

from mower.simulation import is_simulation_enabled

# Configure logging
logger = logging.getLogger(__name__)


class SimulatedHardwareComponent(ABC):
    """
    Base class for all simulated hardware components.

    This abstract class defines the common interface that all simulated hardware
    components should implement. It provides basic functionality for initialization,
    cleanup, and state management.
    """

    def __init__(self, component_name: str):
        """
        Initialize the simulated hardware component.

        Args:
            component_name: Name of the component for logging and identification
        """
        self.component_name = component_name
        self.initialized = False
        self.state: Dict[str, Any] = {}
        self._lock = threading.RLock()
        logger.info(f"Initialized simulated {component_name}")

    def _initialize(self, *args, **kwargs) -> bool:
        """
        Initialize the simulated hardware component.

        This method should be called by the actual hardware component's _initialize
        method when in simulation mode.

        Args:
            *args: Variable length argument list
            **kwargs: Arbitrary keyword arguments

        Returns:
            bool: True if initialization was successful, False otherwise
        """
        with self._lock:
            if self.initialized:
                logger.warning(
                    f"Simulated {self.component_name} already initialized"
                )
                return True

            try:
                self._initialize_sim(*args, **kwargs)
                self.initialized = True
                logger.info(
                    f"Simulated {self.component_name} initialized successfully"
                )
                return True
            except Exception as e:
                logger.error(
                    f"Error initializing simulated {self.component_name}: {e}"
                )
                return False

    @abstractmethod
    def _initialize_sim(self, *args, **kwargs) -> None:
        """
        Initialize the simulated hardware component (implementation specific).

        This method should be implemented by each simulated hardware component
        to perform component-specific initialization.

        Args:
            *args: Variable length argument list
            **kwargs: Arbitrary keyword arguments
        """
        pass

    def cleanup(self) -> bool:
        """
        Clean up the simulated hardware component.

        This method should be called by the actual hardware component's cleanup
        method when in simulation mode.

        Returns:
            bool: True if cleanup was successful, False otherwise
        """
        with self._lock:
            if not self.initialized:
                logger.warning(
                    f"Simulated {self.component_name} not initialized, nothing to clean up"
                )
                return True

            try:
                self._cleanup_sim()
                self.initialized = False
                logger.info(
                    f"Simulated {self.component_name} cleaned up successfully"
                )
                return True
            except Exception as e:
                logger.error(
                    f"Error cleaning up simulated {self.component_name}: {e}"
                )
                return False

    @abstractmethod
    def _cleanup_sim(self) -> None:
        """
        Clean up the simulated hardware component (implementation specific).

        This method should be implemented by each simulated hardware component
        to perform component-specific cleanup.
        """
        pass

    def get_state(self) -> Dict[str, Any]:
        """
        Get the current state of the simulated hardware component.

        Returns:
            Dict[str, Any]: Dictionary containing the current state
        """
        with self._lock:
            return self.state.copy()

    def set_state(self, state: Dict[str, Any]) -> None:
        """
        Set the state of the simulated hardware component.

        Args:
            state: Dictionary containing the new state
        """
        with self._lock:
            self.state.update(state)

    def reset_state(self) -> None:
        """Reset the state of the simulated hardware component."""
        with self._lock:
            self.state.clear()


class SimulatedSensor(SimulatedHardwareComponent):
    """
    Base class for simulated sensors.

    This class extends SimulatedHardwareComponent with additional functionality
    specific to sensors, such as reading sensor data and simulating sensor noise.
    """

    def __init__(self, sensor_name: str):
        """
        Initialize the simulated sensor.

        Args:
            sensor_name: Name of the sensor for logging and identification
        """
        super().__init__(sensor_name)
        self.last_reading_time = 0.0
        self.reading_interval = 0.1  # seconds
        self.noise_level = 0.05  # 5% noise by default

    def get_data(self) -> Dict[str, Any]:
        """
        Get simulated sensor data.

        This method should be called by the actual sensor's get_data method
        when in simulation mode.

        Returns:
            Dict[str, Any]: Dictionary containing the simulated sensor data
        """
        with self._lock:
            current_time = time.time()
            if current_time - self.last_reading_time >= self.reading_interval:
                self._update_sensor_data()
                self.last_reading_time = current_time

            return self._get_sensor_data()

    @abstractmethod
    def _update_sensor_data(self) -> None:
        """
        Update the simulated sensor data.

        This method should be implemented by each simulated sensor to update
        the sensor data based on the current state of the virtual world.
        """
        pass

    @abstractmethod
    def _get_sensor_data(self) -> Dict[str, Any]:
        """
        Get the current simulated sensor data.

        This method should be implemented by each simulated sensor to return
        the current sensor data.

        Returns:
            Dict[str, Any]: Dictionary containing the simulated sensor data
        """
        pass

    def add_noise(
        self, value: float, noise_level: Optional[float] = None
    ) -> float:
        """
        Add random noise to a sensor value.

        Args:
            value: The sensor value to add noise to
            noise_level: The noise level as a fraction of the value (0.0-1.0)
                         If None, uses the sensor's default noise level

        Returns:
            float: The sensor value with noise added
        """
        import random

        if noise_level is None:
            noise_level = self.noise_level

        # Add random noise within the specified range
        noise = random.uniform(-noise_level, noise_level) * value
        return value + noise


class SimulatedActuator(SimulatedHardwareComponent):
    """
    Base class for simulated actuators.

    This class extends SimulatedHardwareComponent with additional functionality
    specific to actuators, such as setting actuator values and simulating actuator
    response time.
    """

    def __init__(self, actuator_name: str):
        """
        Initialize the simulated actuator.

        Args:
            actuator_name: Name of the actuator for logging and identification
        """
        super().__init__(actuator_name)
        self.response_time = 0.1  # seconds
        self.last_command_time = 0.0
        self.target_state: Dict[str, Any] = {}

    def set_value(self, key: str, value: Any) -> bool:
        """
        Set a value for the simulated actuator.

        This method should be called by the actual actuator's set_value method
        when in simulation mode.

        Args:
            key: The key for the value to set
            value: The value to set

        Returns:
            bool: True if the value was set successfully, False otherwise
        """
        with self._lock:
            try:
                self.target_state[key] = value
                self.last_command_time = time.time()
                self._update_actuator_state(key, value)
                return True
            except Exception as e:
                logger.error(
                    f"Error setting value for simulated {self.component_name}: {e}"
                )
                return False

    @abstractmethod
    def _update_actuator_state(self, key: str, value: Any) -> None:
        """
        Update the state of the simulated actuator.

        This method should be implemented by each simulated actuator to update
        the actuator state based on the new value.

        Args:
            key: The key for the value that was set
            value: The value that was set
        """
        pass

    def update(self) -> None:
        """
        Update the simulated actuator state based on elapsed time.

        This method should be called periodically to update the actuator state
        based on the elapsed time since the last command.
        """
        with self._lock:
            current_time = time.time()
            elapsed_time = current_time - self.last_command_time

            if elapsed_time >= self.response_time:
                # Actuator has reached target state
                self.state.update(self.target_state)
            else:
                # Actuator is still moving toward target state
                progress = elapsed_time / self.response_time
                self._interpolate_state(progress)

    def _interpolate_state(self, progress: float) -> None:
        """
        Interpolate between current state and target state.

        Args:
            progress: Progress from 0.0 (current state) to 1.0 (target state)
        """
        # Default implementation for numeric values
        for key, target_value in self.target_state.items():
            if (
                key in self.state
                and isinstance(self.state[key], (int, float))
                and isinstance(target_value, (int, float))
            ):
                current_value = self.state[key]
                self.state[key] = (
                    current_value + (target_value - current_value) * progress
                )
