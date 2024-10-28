import json
import logging
import time
from shapely.geometry import Point, Polygon

from autonomous_mower.hardware_interface.robohat import RoboHATDriver
from autonomous_mower.hardware_interface.sensor_interface import SensorInterface
from autonomous_mower.navigation_system.localization import Localization
from autonomous_mower.navigation_system.navigation import NavigationController
from autonomous_mower.constants import (MIN_DISTANCE_THRESHOLD,
                                            polygon_coordinates)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ObstacleMapper:
    def __init__(self, localization: Localization, sensors: SensorInterface, driver: RoboHATDriver):
        self.localization = localization  # Store the instance properly
        self.sensors = sensors
        self.driver = driver
        self.obstacle_map = []  # Store obstacle locations
        self.navigation_controller = NavigationController(localization, driver, sensors)

        # Convert polygon_coordinates to a Shapely Polygon
        self.yard_boundary = self.load_yard_boundary()

    def load_yard_boundary(self):
        """Convert polygon_coordinates to a Shapely Polygon."""
        points = [(coord['lng'], coord['lat']) for coord in polygon_coordinates]
        return Polygon(points)

    def detect_obstacle(self):
        """Check if an obstacle is detected using the sensors."""
        left_distance = self.sensors.sensor_data.get('left_distance',
                                                     float('inf'))
        right_distance = self.sensors.sensor_data.get('right_distance',
                                                      float('inf'))

        return (left_distance < MIN_DISTANCE_THRESHOLD or
                right_distance < MIN_DISTANCE_THRESHOLD)

    def record_obstacle(self):
        """Record the current GPS position as an obstacle if inside the boundary."""
        position = self.localization.estimate_position()  # Call properly
        if position:
            lat, lon = position
            obstacle_point = Point(lon, lat)

            if self.yard_boundary.contains(obstacle_point):
                logger.info(f"Obstacle detected inside boundary at {lat}, {lon}")
                self.obstacle_map.append({"latitude": lat, "longitude": lon})
            else:
                logger.warning(f"Obstacle at {lat}, {lon} is outside boundary. Ignored.")

    def save_obstacle_map(self, filename="obstacle_map.json"):
        """Save the obstacle map to a JSON file."""
        with open(filename, 'w') as f:
            json.dump(self.obstacle_map, f, indent=4)
        logger.info(f"Obstacle map saved to {filename}")

    def is_within_yard(self, position):
        """Check if the current position is within the yard boundary."""
        if position:
            lat, lon = position
            return self.yard_boundary.contains(Point(lon, lat))
        return False

    def explore_yard(self, duration=300):
        """Explore the yard to map obstacles for a given duration (in seconds)."""
        start_time = time.time()

        while time.time() - start_time < duration:
            # Get the current position and ensure it's inside the yard
            position = self.localization.estimate_position()  # Fixed the call
            # Find the top right corner of the yard
            corner = self.yard_boundary.bounds
            top_right_lat = corner[3]
            top_right_lon = corner[2]
            logger.info(f"Center of the yard is at {top_right_lat}, {top_right_lon}")

            # Move Robot to the center of the yard and grid pattern
            self.navigation_controller.navigate_to_location((top_right_lat, top_right_lon))
            # Create a grid pattern to cover the yard
            # Define the grid parameters
            grid_spacing = 1.0  # Distance between grid points in meters

            # Get the bounds of the yard
            minx, miny, maxx, maxy = self.yard_boundary.bounds

            # Generate grid points within the yard boundary
            grid_points = []
            x = minx
            while x <= maxx:
                y = miny
                while y <= maxy:
                    point = Point(x, y)
                    if self.yard_boundary.contains(point):
                        grid_points.append((y, x))
                    y += grid_spacing
                x += grid_spacing

            # Navigate to each grid point
            for lat, lon in grid_points:
                self.navigation_controller.navigate_to_location((lat, lon))
                """ 
                    Check for obstacles and record them if found,
                    then move around them to get to the target location.
                """
                if self.detect_obstacle():
                    self.record_obstacle()
                    # Move around the obstacle
                    self.navigation_controller.navigate_around_obstacle()
                # Check if Robot reached the point them move to the next point
                while not self.localization.has_reached_location((lat, lon)):
                    time.sleep(0.1)
                # If the Robot is not in the yard, allow it to return to the yard
                if not self.is_within_yard(self.localization.estimate_position()):
                    self.navigation_controller.navigate_to_location((top_right_lat, top_right_lon))

            # Drive the mower forward at low speed
            self.driver.run(steering=0.0, throttle=0.2)

            # Check for obstacles and record them if found
            if self.detect_obstacle():
                self.record_obstacle()

            time.sleep(0.1)  # Adjust the loop frequency

        # Stop the mower after exploration
        self.driver.run(0.0, 0.0)
        self.save_obstacle_map()

# Usage example
if __name__ == "__main__":
    localization = Localization()  # Ensure proper instantiation
    sensors = SensorInterface()
    driver = RoboHATDriver()

    mapper = ObstacleMapper(localization, sensors, driver)
    logger.info("Starting yard exploration to build the obstacle map...")
    mapper.explore_yard(duration=600)  # Explore for 10 minutes