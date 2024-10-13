import time
import json
from navigation_system.localization import Localization
from hardware_interface.sensor_interface import SensorInterface
from hardware_interface.robohat import RoboHATDriver
import logging
from constants import MIN_DISTANCE_THRESHOLD, polygon_coordinates
from shapely.geometry import Polygon, Point

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ObstacleMapper:
    def __init__(self, localization: Localization, sensors: SensorInterface, driver: RoboHATDriver):
        self.localization = localization
        self.sensors = sensors
        self.driver = driver
        self.obstacle_map = []  # Store obstacle locations as a list of coordinates

        # Create a Shapely polygon from the yard boundary
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
        """Record the current GPS position as an obstacle if it's inside the boundary."""
        position = self.localization.estimate_position()
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
            position = self.localization.estimate_position()
            if not self.is_within_yard(position):
                logger.warning("Mower is outside the yard boundary! Stopping.")
                self.driver.run(0.0, 0.0)  # Stop the mower
                break

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
    localization = Localization()
    sensors = SensorInterface()
    driver = RoboHATDriver()

    mapper = ObstacleMapper(localization, sensors, driver)
    logger.info("Starting yard exploration to build the obstacle map...")
    mapper.explore_yard(duration=600)  # Explore for 10 minutes