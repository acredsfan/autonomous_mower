"""
Simulated IMU sensor.

This module provides a simulated version of the BNO085Sensor class that interacts
with the virtual world model to provide realistic IMU sensor readings without
requiring physical hardware.
"""

import math

# import time # Unused
# import threading # Unused
# import random # Unused
# from enum import Enum # Unused
# Removed unused: Optional, List, Union, Type
from typing import Any, Callable, Dict, Tuple

# from mower.hardware.imu import IMUStatus # Unused
from mower.simulation.hardware_sim import SimulatedSensor
from mower.simulation.world_model import get_world_instance  # Removed unused: Vector2D
from mower.utilities.logger_config import LoggerConfigInfo

# Configure logging
logger = LoggerConfigInfo.get_logger(__name__)


class SimulatedBNO085Sensor(SimulatedSensor):
    """
    Simulated BNO085 IMU sensor.

    This class provides a simulated version of the BNO085Sensor class that interacts
    with the virtual world model to provide realistic IMU sensor readings without
    requiring physical hardware.
    """

    def __init__(self, initial_status: bool = True):
        """
        Initialize the simulated IMU sensor.

        Args:
            initial_status: Set the initial working status of the sensor.
                            Defaults to True (working).
        """
        super().__init__("BNO085 IMU")
        self._initial_status = initial_status

        # Initialize sensor data
        self.state = {
            "working": True,  # Default to True, overridden by _initial_status
            "acceleration": (float("nan"), float("nan"), float("nan")),
            "gyro": (float("nan"), float("nan"), float("nan")),
            "magnetometer": (float("nan"), float("nan"), float("nan")),
            "quaternion": (float("nan"), float("nan"), float("nan"), float("nan")),
            "euler_angles": (float("nan"), float("nan"), float("nan")),
            "heading": float("nan"),
            "speed": float("nan"),
            "calibration_status": {  # Assume calibration fails if sensor not working
                "system": 3,
                "gyro": 3,
                "accel": 3,
                "mag": 3,
            },
            "safety_status": {
                "tilt_warning": False,
                "tilt_error": False,
                "vibration_warning": False,
                "vibration_error": False,
                "impact_detected": False,
            },
        }

        # Initialize sensor parameters
        self.noise_level = 0.02  # 2% noise by default
        self.reading_interval = 0.01  # 100Hz update rate

        # Initialize safety thresholds
        self.tilt_warning_threshold = math.radians(20)  # 20 degrees
        self.tilt_error_threshold = math.radians(30)  # 30 degrees
        self.vibration_warning_threshold = 2.0  # m/s^2
        self.vibration_error_threshold = 5.0  # m/s^2
        self.impact_threshold = 10.0  # m/s^2

        # Initialize safety callback
        self.safety_callback = None

        # Get the virtual world instance
        self.world = get_world_instance()

    def _initialize_sim(self, *args, **kwargs) -> None:
        """Initialize the simulated IMU sensor."""
        self.state["working"] = self._initial_status
        if not self.state["working"]:
            # Set calibration status to 0 if not working
            self.state["calibration_status"] = {"system": 0, "gyro": 0, "accel": 0, "mag": 0}
            logger.warning("Simulated BNO085 initialized in a FAILED state.")
        else:
            # Set calibration status to 3 (fully calibrated) if working
            self.state["calibration_status"] = {"system": 3, "gyro": 3, "accel": 3, "mag": 3}
            logger.info("Simulated BNO085 initialized successfully.")

    def _cleanup_sim(self) -> None:
        """Clean up the simulated IMU sensor."""
        # Nothing special to clean up for the simulated IMU
        pass

    def _update_sensor_data(self) -> None:
        """Update the simulated IMU sensor data from the virtual world."""
        if not self.state["working"]:
            # If not working, don't update sensor readings, keep them as
            # NaN/default error state
            return

        # Get the robot state from the virtual world
        robot_state = self.world.get_robot_state()

        # Extract relevant data
        # position = robot_state["position"] # Unused variable
        heading = robot_state["heading"]
        velocity = robot_state["velocity"]
        angular_velocity = robot_state["angular_velocity"]

        # Calculate acceleration based on velocity changes
        # In a real system, this would be more complex
        # For simulation, we'll use a simple approximation
        prev_velocity = self.state.get("prev_velocity", (0.0, 0.0))
        dt = self.reading_interval

        # Calculate acceleration in world coordinates
        accel_x = (velocity[0] - prev_velocity[0]) / dt
        accel_y = (velocity[1] - prev_velocity[1]) / dt

        # Store current velocity for next update
        self.state["prev_velocity"] = velocity

        # Calculate acceleration in robot coordinates
        # Rotate acceleration vector by negative heading
        cos_heading = math.cos(-heading)
        sin_heading = math.sin(-heading)
        accel_robot_x = accel_x * cos_heading - accel_y * sin_heading
        accel_robot_y = accel_x * sin_heading + accel_y * cos_heading

        # Add gravity (9.81 m/s^2 in z direction)
        accel_robot_z = 9.81

        # Add noise to acceleration
        accel_robot_x = self.add_noise(accel_robot_x)
        accel_robot_y = self.add_noise(accel_robot_y)
        accel_robot_z = self.add_noise(accel_robot_z)

        # Update acceleration
        self.state["acceleration"] = (
            accel_robot_x,
            accel_robot_y,
            accel_robot_z,
        )

        # Update gyro (angular velocity)
        # In a real system, this would be in the robot's coordinate system
        # For simulation, we'll use a simple approximation
        gyro_x = 0.0  # Roll rate
        gyro_y = 0.0  # Pitch rate
        gyro_z = angular_velocity  # Yaw rate

        # Add noise to gyro
        gyro_x = self.add_noise(gyro_x)
        gyro_y = self.add_noise(gyro_y)
        gyro_z = self.add_noise(gyro_z)

        # Update gyro
        self.state["gyro"] = (gyro_x, gyro_y, gyro_z)

        # Update magnetometer
        # In a real system, this would be based on the Earth's magnetic field
        # For simulation, we'll use a simple approximation based on heading
        mag_strength = 50.0  # uT (typical strength of Earth's magnetic field)
        mag_x = mag_strength * math.cos(heading)
        mag_y = mag_strength * math.sin(heading)
        mag_z = 0.0

        # Add noise to magnetometer
        mag_x = self.add_noise(mag_x)
        mag_y = self.add_noise(mag_y)
        mag_z = self.add_noise(mag_z)

        # Update magnetometer
        self.state["magnetometer"] = (mag_x, mag_y, mag_z)

        # Update quaternion
        # In a real system, this would be calculated from sensor fusion
        # For simulation, we'll use a simple approximation based on heading
        # This is a simplified quaternion for rotation around z-axis only
        qw = math.cos(heading / 2)
        qx = 0.0
        qy = 0.0
        qz = math.sin(heading / 2)

        # Update quaternion
        self.state["quaternion"] = (qw, qx, qy, qz)

        # Update euler angles
        # In a real system, these would be calculated from the quaternion
        # For simulation, we'll use a simple approximation
        roll = 0.0  # Assume flat ground for now
        pitch = 0.0  # Assume flat ground for now
        yaw = heading

        # Update euler angles
        self.state["euler_angles"] = (roll, pitch, yaw)

        # Update heading
        self.state["heading"] = heading

        # Update speed
        speed = math.sqrt(velocity[0] ** 2 + velocity[1] ** 2)
        self.state["speed"] = speed

        # Check safety conditions
        self._check_safety_conditions()

    def _get_sensor_data(self) -> Dict[str, Any]:
        """Get the current simulated IMU sensor data."""
        return self.state

    def _check_safety_conditions(self) -> None:
        """Check safety conditions based on sensor data."""
        # Get relevant data
        roll, pitch, _ = self.state["euler_angles"]
        accel_x, accel_y, accel_z = self.state["acceleration"]

        # Calculate tilt angle (combined roll and pitch)
        tilt_angle = math.sqrt(roll**2 + pitch**2)

        # Calculate vibration level (magnitude of acceleration)
        vibration_level = math.sqrt(accel_x**2 + accel_y**2 + accel_z**2) - 9.81

        # Check tilt warning
        tilt_warning = tilt_angle > self.tilt_warning_threshold

        # Check tilt error
        tilt_error = tilt_angle > self.tilt_error_threshold

        # Check vibration warning
        vibration_warning = vibration_level > self.vibration_warning_threshold

        # Check vibration error
        vibration_error = vibration_level > self.vibration_error_threshold

        # Check impact
        impact_detected = vibration_level > self.impact_threshold

        # Update safety status
        self.state["safety_status"] = {
            "tilt_warning": tilt_warning,
            "tilt_error": tilt_error,
            "vibration_warning": vibration_warning,
            "vibration_error": vibration_error,
            "impact_detected": impact_detected,
        }

        # Call safety callback if registered
        if self.safety_callback is not None:
            self.safety_callback(self.state["safety_status"])

    # BNO085Sensor interface methods

    def _initialize(self) -> bool:
        """Initialize the simulated IMU sensor."""
        # In simulation, initialization success depends on the initial_status
        # flag
        return self.state["working"]

    def read_bno085_accel(self) -> Tuple[float, float, float]:
        """Read acceleration data from the simulated IMU sensor."""
        self.get_data()
        return self.state["acceleration"] if self.state["working"] else (float("nan"), float("nan"), float("nan"))

    def read_bno085_gyro(self) -> Tuple[float, float, float]:
        """Read gyroscope data from the simulated IMU sensor."""
        self.get_data()
        return self.state["gyro"] if self.state["working"] else (float("nan"), float("nan"), float("nan"))

    def read_bno085_magnetometer(self) -> Tuple[float, float, float]:
        """Read magnetometer data from the simulated IMU sensor."""
        self.get_data()
        return self.state["magnetometer"] if self.state["working"] else (float("nan"), float("nan"), float("nan"))

    def calculate_quaternion(self) -> Tuple[float, float, float, float]:
        """Calculate quaternion from the simulated IMU sensor data."""
        self.get_data()
        return (
            self.state["quaternion"]
            if self.state["working"]
            else (float("nan"), float("nan"), float("nan"), float("nan"))
        )

    def calculate_heading(self) -> float:
        """Calculate heading from the simulated IMU sensor data."""
        self.get_data()
        return self.state["heading"] if self.state["working"] else float("nan")

    def calculate_pitch(self) -> float:
        """Calculate pitch from the simulated IMU sensor data."""
        self.get_data()
        return self.state["euler_angles"][1] if self.state["working"] else float("nan")

    def calculate_roll(self) -> float:
        """Calculate roll from the simulated IMU sensor data."""
        self.get_data()
        return self.state["euler_angles"][0] if self.state["working"] else float("nan")

    def calculate_speed(self) -> float:
        """Calculate speed from the simulated IMU sensor data."""
        self.get_data()
        return self.state["speed"] if self.state["working"] else float("nan")

    def get_orientation(self) -> Tuple[float, float, float]:
        """Get orientation data from the simulated IMU sensor."""
        self.get_data()
        return self.state["euler_angles"] if self.state["working"] else (float("nan"), float("nan"), float("nan"))

    def get_quaternion(self) -> Tuple[float, float, float, float]:
        """Get quaternion data from the simulated IMU sensor."""
        self.get_data()
        return (
            self.state["quaternion"]
            if self.state["working"]
            else (float("nan"), float("nan"), float("nan"), float("nan"))
        )

    def get_acceleration(self) -> Tuple[float, float, float]:
        """Get acceleration data from the simulated IMU sensor."""
        self.get_data()
        return self.state["acceleration"] if self.state["working"] else (float("nan"), float("nan"), float("nan"))

    def get_gyro(self) -> Tuple[float, float, float]:
        """Get gyroscope data from the simulated IMU sensor."""
        self.get_data()
        return self.state["gyro"] if self.state["working"] else (float("nan"), float("nan"), float("nan"))

    def get_heading(self) -> float:
        """Get heading data from the simulated IMU sensor."""
        self.get_data()
        return self.state["heading"] if self.state["working"] else float("nan")

    def get_calibration_status(self) -> Dict[str, int]:
        """Get calibration status from the simulated IMU sensor."""
        self.get_data()
        # Calibration status is set during init based on working status
        return self.state["calibration_status"]

    def check_safety_conditions(self) -> Dict[str, bool]:
        """Check safety conditions based on simulated IMU sensor data."""
        self.get_data()
        # Safety status check depends on valid sensor data, which won't be
        # updated if not working
        return self.state["safety_status"]

    def get_safety_status(self) -> Dict[str, bool]:
        """Get safety status from the simulated IMU sensor."""
        self.get_data()
        return self.state["safety_status"]

    def register_safety_callback(self, callback: Callable[[Dict[str, bool]], None]) -> None:
        """Register a callback for safety status changes."""
        self.safety_callback = callback

    def cleanup(self) -> bool:
        """Clean up the simulated IMU sensor."""
        return super().cleanup()

    def get_data(self) -> Dict[str, Any]:
        """Get all sensor data from the simulated IMU sensor."""
        return super().get_data()
