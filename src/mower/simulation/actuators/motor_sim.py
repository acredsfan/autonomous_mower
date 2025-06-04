"""
Simulated motor controller.

This module provides a simulated version of the RoboHATDriver class that interacts
with the virtual world model to provide realistic motor control behavior without
requiring physical hardware.
"""

import threading
import time
from typing import Any, Dict, List, Optional, Tuple, Type, Union

from mower.simulation.hardware_sim import SimulatedActuator
from mower.simulation.world_model import Vector2D, get_world_instance
from mower.utilities.logger_config import LoggerConfigInfo

# Configure logging
logger = LoggerConfigInfo.get_logger(__name__)


class SimulatedRoboHATDriver(SimulatedActuator):
    """
    Simulated RoboHATDriver motor controller.

    This class provides a simulated version of the RoboHATDriver class that interacts
    with the virtual world model to provide realistic motor control behavior without
    requiring physical hardware.
    """

    def __init__(self, debug: bool = False):
        """
        Initialize the simulated motor controller.

        Args:
            debug: Whether to enable debug logging
        """
        super().__init__("RoboHAT Motor Controller")

        # Initialize actuator state
        self.state = {
            "left_speed": 0.0,  # -1.0 to 1.0
            "right_speed": 0.0,  # -1.0 to 1.0
            "steering": 0.0,  # -1.0 to 1.0
            "throttle": 0.0,  # -1.0 to 1.0
            "running": False,
            "debug": debug,
        }

        # Initialize actuator parameters
        self.response_time = 0.1  # 100ms response time

        # Get the virtual world instance
        self.world = get_world_instance()

    def _initialize_sim(self, *args, **kwargs) -> None:
        """Initialize the simulated motor controller."""
        # Nothing special to initialize for the simulated motor controller
        pass

    def _cleanup_sim(self) -> None:
        """Clean up the simulated motor controller."""
        # Stop the motors
        self.set_motors(0.0, 0.0)

    def _update_actuator_state(self, key: str, value: Any) -> None:
        """
        Update the state of the simulated motor controller.

        Args:
            key: The key for the value that was set
            value: The value that was set
        """
        # Update the state
        self.state[key] = value

        # If the key is left_speed or right_speed, update the robot's motor speeds
        if key in ["left_speed", "right_speed"]:
            self.world.set_robot_motor_speeds(self.state["left_speed"], self.state["right_speed"])

    # RoboHATDriver interface methods

    def trim_out_of_bound_value(self, value: float) -> float:
        """
        Trim a value to the range [-1.0, 1.0].

        Args:
            value: Value to trim

        Returns:
            float: Trimmed value
        """
        return max(-1.0, min(1.0, value))

    def set_pulse(self, steering: float, throttle: float) -> None:
        """
        Set the pulse width for the motors.

        Args:
            steering: Steering value (-1.0 to 1.0)
            throttle: Throttle value (-1.0 to 1.0)
        """
        # Trim values to the valid range
        steering = self.trim_out_of_bound_value(steering)
        throttle = self.trim_out_of_bound_value(throttle)

        # Update state
        self.set_value("steering", steering)
        self.set_value("throttle", throttle)

        # Convert steering and throttle to left and right motor speeds
        # This is a simplified version of the conversion in the real RoboHATDriver
        left_speed = throttle
        right_speed = throttle

        if steering > 0:
            # Turn right, reduce right motor speed
            right_speed = throttle * (1.0 - steering)
        elif steering < 0:
            # Turn left, reduce left motor speed
            left_speed = throttle * (1.0 + steering)

        # Set motor speeds
        self.set_motors(left_speed, right_speed)

    def is_valid_pwm_value(self, value: float) -> bool:
        """
        Check if a value is a valid PWM value.

        Args:
            value: Value to check

        Returns:
            bool: True if the value is valid, False otherwise
        """
        return -1.0 <= value <= 1.0

    def write_pwm(self, steering: float, throttle: float) -> None:
        """
        Write PWM values to the motors.

        Args:
            steering: Steering value (-1.0 to 1.0)
            throttle: Throttle value (-1.0 to 1.0)
        """
        # Check if values are valid
        if not self.is_valid_pwm_value(steering) or not self.is_valid_pwm_value(throttle):
            logger.warning(f"Invalid PWM values: steering={steering}, throttle={throttle}")
            return

        # Set pulse
        self.set_pulse(steering, throttle)

    def run(self, steering: float, throttle: float) -> None:
        """
        Run the motors with the given steering and throttle values.

        Args:
            steering: Steering value (-1.0 to 1.0)
            throttle: Throttle value (-1.0 to 1.0)
        """
        self.write_pwm(steering, throttle)

    def set_motors(self, left_speed: float, right_speed: float) -> None:
        """
        Set the speed of the left and right motors.

        Args:
            left_speed: Left motor speed (-1.0 to 1.0)
            right_speed: Right motor speed (-1.0 to 1.0)
        """
        # Trim values to the valid range
        left_speed = self.trim_out_of_bound_value(left_speed)
        right_speed = self.trim_out_of_bound_value(right_speed)

        # Update state
        self.set_value("left_speed", left_speed)
        self.set_value("right_speed", right_speed)
        self.set_value("running", left_speed != 0.0 or right_speed != 0.0)

        # Log if debug is enabled
        if self.state["debug"]:
            logger.debug(f"Set motors: left={left_speed}, right={right_speed}")

    def forward(self, speed: float = 1.0) -> None:
        """
        Move the robot forward.

        Args:
            speed: Speed to move at (0.0 to 1.0)
        """
        # Ensure speed is positive
        speed = abs(speed)

        # Set both motors to the same speed
        self.set_motors(speed, speed)

    def backward(self, speed: float = 1.0) -> None:
        """
        Move the robot backward.

        Args:
            speed: Speed to move at (0.0 to 1.0)
        """
        # Ensure speed is positive, then negate for backward motion
        speed = -abs(speed)

        # Set both motors to the same speed
        self.set_motors(speed, speed)

    def left(self, speed: float = 1.0) -> None:
        """
        Turn the robot left.

        Args:
            speed: Speed to turn at (0.0 to 1.0)
        """
        # Ensure speed is positive
        speed = abs(speed)

        # Set motors to turn left (right motor forward, left motor backward)
        self.set_motors(-speed, speed)

    def right(self, speed: float = 1.0) -> None:
        """
        Turn the robot right.

        Args:
            speed: Speed to turn at (0.0 to 1.0)
        """
        # Ensure speed is positive
        speed = abs(speed)

        # Set motors to turn right (left motor forward, right motor backward)
        self.set_motors(speed, -speed)

    def stop(self) -> None:
        """Stop the robot."""
        # Set both motors to zero speed
        self.set_motors(0.0, 0.0)

    def shutdown(self) -> None:
        """Shut down the motor controller."""
        # Stop the motors
        self.stop()

        # Clean up
        self.cleanup()
