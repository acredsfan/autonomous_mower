"""
Simulated Time-of-Flight (ToF) distance sensors.

This module provides a simulated version of the VL53L0XSensors class that interacts
with the virtual world model to provide realistic distance sensor readings without
requiring physical hardware.
"""

import math
# import time # Not used in this module
# import threading # Not used in this module
# import random # Not used in this module
# , List, Tuple, Union, Type # Unused specific types
from typing import Dict, Any, Optional

from mower.simulation.hardware_sim import SimulatedSensor
from mower.simulation.world_model import get_world_instance, Vector2D
from mower.utilities.logger_config import LoggerConfigInfo as LoggerConfig

# Configure logging
logger = LoggerConfig.get_logger(__name__)


class SimulatedVL53L0XSensors(SimulatedSensor):
    """
    Simulated VL53L0X Time-of-Flight distance sensors.

    This class provides a simulated version of the VL53L0XSensors class that interacts
    with the virtual world model to provide realistic distance sensor readings without
    requiring physical hardware.
    """

    def __init__(self, initial_statuses: Optional[Dict[str, bool]] = None):
        """
        Initialize the simulated ToF sensors.

        Args:
            initial_statuses: Optional dict to set initial working status
                              of sensors (e.g., {"left": False}).
        """
        super().__init__("VL53L0X ToF Sensors")
        self._initial_statuses = initial_statuses if initial_statuses is not None \
            else {}

        # Initialize sensor data
        self.state = {
            "left_distance": float("inf"),  # Distance in cm
            "right_distance": float("inf"),  # Distance in cm
            "sensor_status": {  # Default True, overridden by _initial_statuses
                "left": True,
                "right": True,
            },
        }

        # Initialize sensor parameters
        self.noise_level = 0.05  # 5% noise by default
        self.reading_interval = 0.05  # 20Hz update rate
        self.max_range = 200.0  # 2m maximum range
        self.min_range = 5.0  # 5cm minimum range

        # Initialize sensor positions and orientations relative to robot
        # These values should match the physical placement of sensors on the
        # robot
        self.sensor_positions = {
            "left": Vector2D(0.2, 0.15),  # 20cm forward, 15cm left of center
            "right": Vector2D(
                0.2, -0.15
            ),  # 20cm forward, 15cm right of center
        }

        self.sensor_orientations = {
            "left": math.radians(30),  # 30 degrees left of forward
            "right": math.radians(-30),  # 30 degrees right of forward
        }

        # Get the virtual world instance
        self.world = get_world_instance()

    def _initialize_sim(self, *args, **kwargs) -> None:
        """Initialize the simulated ToF sensors."""
        for sensor_name, is_working in self._initial_statuses.items():
            if sensor_name in self.state["sensor_status"]:
                self.state["sensor_status"][sensor_name] = is_working
                if not is_working:
                    # Set distance to NaN if sensor is not working initially
                    self.state[f"{sensor_name}_distance"] = float('nan')
        logger.info(
            f"Simulated ToF initialized with statuses: {
                self.state['sensor_status']}")

    def _cleanup_sim(self) -> None:
        """Clean up the simulated ToF sensors."""
        # Nothing special to clean up for the simulated ToF sensors
        pass

    def _update_sensor_data(self) -> None:
        """Update the simulated ToF sensor data from the virtual world."""
        # Get the robot state from the virtual world
        robot_state = self.world.get_robot_state()

        # Extract relevant data
        robot_position = Vector2D(*robot_state["position"])
        robot_heading = robot_state["heading"]

        # Update each sensor
        for sensor_name in ["left", "right"]:
            if not self.state["sensor_status"].get(sensor_name, False):
                self.state[f"{sensor_name}_distance"] = float(
                    'nan')  # Ensure non-working sensor reads NaN
                continue  # Skip update for non-working sensor

            # Calculate sensor position in world coordinates
            sensor_rel_pos = self.sensor_positions[sensor_name]
            sensor_rel_pos = sensor_rel_pos.rotate(robot_heading)
            sensor_position = robot_position + sensor_rel_pos

            # Calculate sensor direction in world coordinates
            sensor_orientation = (
                robot_heading + self.sensor_orientations[sensor_name]
            )
            sensor_direction = Vector2D(
                math.cos(sensor_orientation), math.sin(sensor_orientation)
            )

            # Get distance to nearest obstacle in sensor direction
            distance, obstacle = self.world.get_distance_to_nearest_obstacle(
                sensor_position, sensor_direction, self.max_range
            )

            # Convert distance to cm
            distance_cm = distance * 100.0

            # Clamp to sensor range
            distance_cm = max(
                self.min_range, min(self.max_range, distance_cm)
            )

            # Add noise to distance
            distance_cm = self.add_noise(distance_cm)

            # Update sensor data
            self.state[f"{sensor_name}_distance"] = distance_cm

    def _get_sensor_data(self) -> Dict[str, Any]:
        """Get the current simulated ToF sensor data."""
        return self.state

    # VL53L0XSensors interface methods

    def _initialize(self) -> bool:
        """Initialize the simulated ToF sensors."""
        return super()._initialize()

    def get_data(self) -> Dict[str, Any]:
        """Get all sensor data from the simulated ToF sensors."""
        return super().get_data()

    def get_distance(self, sensor_name: str) -> float:
        """
        Get the distance reading from the specified sensor.

        Args:
            sensor_name: Name of the sensor ("left" or "right")

        Returns:
            float: Distance in cm, or inf if no obstacle detected
        """
        self.get_data()  # Ensure data is up to date
        if not self.state["sensor_status"].get(sensor_name, False):
            return float('nan')  # Return NaN if sensor is not working
        return self.state.get(f"{sensor_name}_distance", float("inf"))

    def get_left_distance(self) -> float:
        """Get the distance reading from the left sensor."""
        return self.get_distance("left")

    def get_right_distance(self) -> float:
        """Get the distance reading from the right sensor."""
        return self.get_distance("right")

    def is_sensor_working(self, sensor_name: str) -> bool:
        """
        Check if the specified sensor is working.

        Args:
            sensor_name: Name of the sensor ("left" or "right")

        Returns:
            bool: True if the sensor is working, False otherwise
        """
        self.get_data()  # Ensure data is up to date
        return self.state["sensor_status"].get(sensor_name, False)

    def cleanup(self) -> bool:
        """Clean up the simulated ToF sensors."""
        return super().cleanup()
