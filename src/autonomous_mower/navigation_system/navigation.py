import logging
import math
import time
from math import atan2, cos, radians, sin, sqrt

import utm
from hardware_interfacerobohat import RoboHATDriver
from navigation_system.gps import GpsLatestPosition, GpsPosition

logger = logging.getLogger(__name__)

# Initialize GPS and RoboHAT components safely
try:
    gps_position_instance = GpsPosition(serial_port='/dev/ttyACM0', debug=True)
    gps_position_instance.start()  # Start GPS reading in the background
except Exception as e:
    logger.error(f"Failed to initialize GPS: {e}")
    gps_position_instance = None

gps_latest_position = GpsLatestPosition(
    gps_position_instance=gps_position_instance
    )
robohat_driver = RoboHATDriver()


class NavigationController:
    """
    Handles navigation logic separately from the motor controller.
    """

    def __init__(self, gps_latest_position, robohat_driver,
                 sensor_interface, debug=False):
        self.gps_latest_position = gps_latest_position
        self.robohat_driver = robohat_driver
        self.sensor_interface = sensor_interface
        self.debug = debug

    def navigate_to_location(self, target_location):
        """Navigates the robot to the specified target location."""
        try:
            current_position = self.get_current_gps_position()

            if not current_position:
                logger.error('No valid GPS data available.')
                return False

            while not self.has_reached_location(current_position,
                                                target_location):
                steering, throttle = self.calculate_navigation_commands(
                    current_position, target_location
                )
                self.robohat_driver.run(steering, throttle)
                time.sleep(0.1)

                current_position = self.get_current_gps_position()
                if not current_position:
                    logger.error('No valid GPS data during navigation.')
                    self.robohat_driver.run(0, 0)  # Stop the mower
                    return False

            self.robohat_driver.run(0, 0)  # Stop the mower at destination
            return True

        except Exception as e:
            logger.exception(f"Error in navigate_to_location: {e}")
            self.robohat_driver.run(0, 0)  # Stop the mower on exception
            return False

    def get_current_gps_position(self):
        """
        Attempts to fetch the latest GPS position and converts it to lat/lon.
        Returns None if data is invalid.
        """
        try:
            position = self.gps_latest_position.run()

            if not position or len(position) < 4:
                logger.warning('Incomplete GPS data received.')
                return None

            ts, easting, northing, zone_number, zone_letter = position
            lat, lon = utm.to_latlon(easting, northing,
                                     zone_number, zone_letter)
            return (lat, lon)

        except Exception as e:
            logger.error(f"Failed to parse GPS position: {e}")
            return None

    def calculate_navigation_commands(self, current_position, target_location):
        """Calculates steering and throttle commands based on the positions."""
        bearing = self.calculate_bearing(current_position, target_location)
        current_heading = self.sensor_interface.get_heading()  # Assumed method
        heading_error = (bearing - current_heading + 360) % 360
        if heading_error > 180:
            heading_error -= 360  # Normalize to [-180, 180]

        # Simple proportional controller for steering
        Kp_steering = 0.01  # Proportional gain; adjust as needed
        steering = -Kp_steering * heading_error

        # Calculate distance to target
        distance = self.calculate_distance(current_position, target_location)

        # Simple proportional controller for throttle
        Kp_throttle = 0.5  # Proportional gain; adjust as needed
        throttle = min(Kp_throttle * distance, 1.0)  # Clamp throttle

        # Clamp steering and throttle values
        steering = max(min(steering, 1.0), -1.0)
        throttle = max(min(throttle, 1.0), 0.0)

        return steering, throttle

    @staticmethod
    def calculate_bearing(current_position, target_location):
        """Calculates the bearing from current_position to target_location."""
        lat1, lon1 = map(radians, current_position)
        lat2, lon2 = map(radians, target_location)
        delta_lon = lon2 - lon1
        x = sin(delta_lon) * cos(lat2)
        y = cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(delta_lon)
        initial_bearing = atan2(x, y)
        bearing = (math.degrees(initial_bearing) + 360) % 360  # Normalize
        return bearing

    @staticmethod
    def calculate_distance(current_position, target_location):
        """Calculates the Haversine distance between two points."""
        R = 6371e3  # Earth's radius in meters
        lat1, lon1 = map(radians, current_position)
        lat2, lon2 = map(radians, target_location)
        delta_lat = lat2 - lat1
        delta_lon = lon2 - lon1
        a = (sin(delta_lat / 2) ** 2 +
             cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2)
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        distance = R * c  # Distance in meters
        return distance

    @staticmethod
    def has_reached_location(current_position,
                             target_location,
                             tolerance=0.0001):
        """Determines if the robot has reached the target location."""
        lat1, lon1 = current_position
        lat2, lon2 = target_location
        return abs(lat1 - lat2) < tolerance and abs(lon1 - lon2) < tolerance


# Example Usage
if __name__ == "__main__":
    sensor_interface = None  # Replace with actual sensor interface
    controller = NavigationController(
        gps_latest_position, robohat_driver, sensor_interface, debug=True
    )

    # Example target location (latitude, longitude)
    target = (39.123, -84.512)

    if controller.navigate_to_location(target):
        logger.info("Navigation successful.")
    else:
        logger.error("Navigation failed.")
