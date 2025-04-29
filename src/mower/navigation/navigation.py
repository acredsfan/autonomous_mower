import math
import time
from math import atan2, cos, radians, sin, sqrt
from typing import Optional, Tuple, Dict

import utm  # Ensure `utm` is installed in your environment
from dataclasses import dataclass

from mower.hardware.robohat import RoboHATDriver
from mower.navigation.gps import GpsLatestPosition, GpsPosition
from mower.utilities.logger_config import LoggerConfigInfo as LoggerConfig

logger = LoggerConfig.get_logger(__name__)


@dataclass
class NavigationStatus:
    """Store navigation status information."""

    is_moving: bool
    target_reached: bool
    current_position: Optional[Tuple[float, float]]
    target_position: Optional[Tuple[float, float]]
    distance_to_target: float
    heading_error: float
    last_error: Optional[str]


class NavigationController:
    """Handles navigation logic separately from the motor controller."""

    def __init__(
        self,
        gps_latest_position: GpsLatestPosition,
        robohat_driver: RoboHATDriver,
        sensor_interface,
        debug: bool = False,
    ):
        """
        Initialize the navigation controller.

        Args:
            gps_latest_position: GPS position handler
            robohat_driver: Motor controller interface
            sensor_interface: Sensor interface
            debug: Enable debug logging
        """
        self.gps_latest_position = gps_latest_position
        self.robohat_driver = robohat_driver
        self.sensor_interface = sensor_interface
        self.debug = debug

        # Navigation parameters
        self.control_params = {
            "steering_kp": 0.01,  # Proportional gain for steering
            "throttle_kp": 0.5,  # Proportional gain for throttle
            "max_throttle": 1.0,  # Maximum throttle value
            "min_throttle": 0.1,  # Minimum throttle value
            "position_tolerance": 0.0001,  # GPS position tolerance
            "max_steering": 1.0,  # Maximum steering value
            "safety_timeout": 30.0,  # Maximum time without position update
        }

        self.status = NavigationStatus(
            is_moving=False,
            target_reached=False,
            current_position=None,
            target_position=None,
            distance_to_target=0.0,
            heading_error=0.0,
            last_error=None,
        )

        self.last_position_update = time.time()

    def navigate_to_location(
        self, target_location: Tuple[float, float]
    ) -> bool:
        """
        Navigate the robot to the specified target location.

        Args:
            target_location: Tuple of (latitude, longitude)

        Returns:
            bool: True if navigation was successful
        """
        try:
            self.status.target_position = target_location
            self.status.is_moving = True
            self.status.target_reached = False

            while not self.status.target_reached:
                if not self._execute_navigation_step():
                    return False

                if self._check_safety_timeout():
                    self._handle_safety_stop("Position update timeout")
                    return False

                time.sleep(0.1)

            self._handle_successful_arrival()
            return True

        except Exception as e:
            self._handle_navigation_error(str(e))
            return False

    def _execute_navigation_step(self) -> bool:
        """
        Execute a single step of the navigation process.

        Returns:
            bool: True if the step was successful
        """
        current_position = self.get_current_gps_position()

        if not current_position:
            self._handle_safety_stop("No valid GPS data")
            return False

        self.status.current_position = current_position
        self.last_position_update = time.time()

        if self.has_reached_location(
            current_position, self.status.target_position
        ):
            self.status.target_reached = True
            return True

        steering, throttle = self.calculate_navigation_commands(
            current_position, self.status.target_position
        )

        self.robohat_driver.run(steering, throttle)
        return True

    def get_current_gps_position(self) -> Optional[Tuple[float, float]]:
        """
        Get the latest GPS position.

        Returns:
            Optional[Tuple[float, float]]: Latitude and longitude if available
        """
        try:
            position = self.gps_latest_position.run()

            if not position or len(position) < 4:
                logger.warning("Incomplete GPS data received.")
                return None

            ts, easting, northing, zone_number, zone_letter = position
            lat, lon = utm.to_latlon(
                easting, northing, zone_number, zone_letter
            )
            return (lat, lon)

        except Exception as e:
            logger.error(f"Failed to parse GPS position: {e}")
            return None

    def calculate_navigation_commands(
        self,
        current_position: Tuple[float, float],
        target_location: Tuple[float, float],
    ) -> Tuple[float, float]:
        """
        Calculate steering and throttle commands.

        Args:
            current_position: Current (latitude, longitude)
            target_location: Target (latitude, longitude)

        Returns:
            Tuple[float, float]: Steering and throttle commands
        """
        bearing = self.calculate_bearing(current_position, target_location)
        current_heading = self.sensor_interface.get_sensor_data("heading")

        heading_error = (bearing - current_heading + 360) % 360
        if heading_error > 180:
            heading_error -= 360  # Normalize to [-180, 180]

        self.status.heading_error = heading_error

        # Calculate steering using proportional control
        steering = -self.control_params["steering_kp"] * heading_error

        # Calculate distance and throttle
        distance = self.calculate_distance(current_position, target_location)
        self.status.distance_to_target = distance

        throttle = min(
            self.control_params["throttle_kp"] * distance,
            self.control_params["max_throttle"],
        )

        # Apply safety limits
        steering = self._clamp_value(
            steering,
            -self.control_params["max_steering"],
            self.control_params["max_steering"],
        )

        throttle = self._clamp_value(
            throttle,
            self.control_params["min_throttle"],
            self.control_params["max_throttle"],
        )

        return steering, throttle

    @staticmethod
    def calculate_bearing(
        current_position: Tuple[float, float],
        target_location: Tuple[float, float],
    ) -> float:
        """
        Calculate bearing between two points.

        Args:
            current_position: Starting (latitude, longitude)
            target_location: Target (latitude, longitude)

        Returns:
            float: Bearing in degrees
        """
        lat1, lon1 = map(radians, current_position)
        lat2, lon2 = map(radians, target_location)

        delta_lon = lon2 - lon1

        x = sin(delta_lon) * cos(lat2)
        y = cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(delta_lon)

        initial_bearing = atan2(x, y)
        bearing = (math.degrees(initial_bearing) + 360) % 360

        return bearing

    @staticmethod
    def calculate_distance(
        current_position: Tuple[float, float],
        target_location: Tuple[float, float],
    ) -> float:
        """
        Calculate Haversine distance between two points.

        Args:
            current_position: Starting (latitude, longitude)
            target_location: Target (latitude, longitude)

        Returns:
            float: Distance in meters
        """
        R = 6371e3  # Earth's radius in meters
        lat1, lon1 = map(radians, current_position)
        lat2, lon2 = map(radians, target_location)

        delta_lat = lat2 - lat1
        delta_lon = lon2 - lon1

        a = (
            sin(delta_lat / 2) ** 2
            + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
        )
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        return R * c

    def has_reached_location(
        self,
        current_position: Tuple[float, float],
        target_location: Tuple[float, float],
        tolerance: Optional[float] = None,
    ) -> bool:
        """
        Check if target location has been reached.

        Args:
            current_position: Current (latitude, longitude)
            target_location: Target (latitude, longitude)
            tolerance: Position tolerance (optional)

        Returns:
            bool: True if target has been reached
        """
        if tolerance is None:
            tolerance = self.control_params["position_tolerance"]

        lat1, lon1 = current_position
        lat2, lon2 = target_location

        return abs(lat1 - lat2) < tolerance and abs(lon1 - lon2) < tolerance

    def _check_safety_timeout(self) -> bool:
        """
        Check if position updates have timed out.

        Returns:
            bool: True if safety timeout has occurred
        """
        time_since_update = time.time() - self.last_position_update
        return time_since_update > self.control_params["safety_timeout"]

    def _handle_safety_stop(self, reason: str):
        """
        Handle safety stop condition.

        Args:
            reason: Reason for safety stop
        """
        self.robohat_driver.run(0, 0)
        self.status.is_moving = False
        self.status.last_error = f"Safety stop: {reason}"
        logger.warning(f"Safety stop triggered: {reason}")

    def _handle_successful_arrival(self):
        """Handle successful arrival at target."""
        self.robohat_driver.run(0, 0)
        self.status.is_moving = False
        self.status.target_reached = True
        logger.info("Successfully reached target location")

    def _handle_navigation_error(self, error: str):
        """
        Handle navigation error.

        Args:
            error: Error message
        """
        self.robohat_driver.run(0, 0)
        self.status.is_moving = False
        self.status.last_error = f"Navigation error: {error}"
        logger.error(f"Navigation error: {error}")

    @staticmethod
    def _clamp_value(value: float, min_val: float, max_val: float) -> float:
        """
        Clamp a value between minimum and maximum.

        Args:
            value: Value to clamp
            min_val: Minimum allowed value
            max_val: Maximum allowed value

        Returns:
            float: Clamped value
        """
        return max(min(value, max_val), min_val)

    def get_status(self) -> Dict:
        """
        Get current navigation status.

        Returns:
            Dict: Current navigation status
        """
        return {
            "is_moving": self.status.is_moving,
            "target_reached": self.status.target_reached,
            "current_position": self.status.current_position,
            "target_position": self.status.target_position,
            "distance_to_target": self.status.distance_to_target,
            "heading_error": self.status.heading_error,
            "last_error": self.status.last_error,
        }

    def stop(self):
        """Stop the navigation process."""
        self.robohat_driver.run(0, 0)  # Stop the motors
        self.status.is_moving = False
        logger.info("Navigation process stopped.")


def initialize_navigation():
    """Initialize navigation system components."""
    try:
        gps_position_instance = GpsPosition(
            serial_port="/dev/ttyACM0", debug=True
        )
        gps_position_instance.start()

        gps_latest_position = GpsLatestPosition(
            gps_position_instance=gps_position_instance
        )
        robohat_driver = RoboHATDriver()

        return gps_latest_position, robohat_driver

    except Exception as e:
        logger.error(f"Failed to initialize navigation system: {e}")
        return None, None


if __name__ == "__main__":
    gps_latest_position, robohat_driver = initialize_navigation()

    if gps_latest_position and robohat_driver:
        sensor_interface = None  # Replace with actual sensor interface
        controller = NavigationController(
            gps_latest_position, robohat_driver, sensor_interface, debug=True
        )

        # Example target location (latitude, longitude)
        target = (39.123, -84.512)

        if controller.navigate_to_location(target):
            logger.info("Navigation successful")
        else:
            logger.error("Navigation failed")
    else:
        logger.error("Failed to initialize navigation components")
