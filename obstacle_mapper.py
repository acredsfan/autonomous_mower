import time
import json
from navigation_system.localization import Localization
from hardware_interface.sensor_interface import SensorInterface
from hardware_interface.robohat import RoboHATDriver
import logging
from constants import MIN_DISTANCE_THRESHOLD

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ObstacleMapper:
    def __init__(self, localization: Localization,
                 sensors: SensorInterface, driver: RoboHATDriver):
        self.localization = localization
        self.sensors = sensors
        self.driver = driver
        # Store obstacle locations as a list of coordinates
        self.obstacle_map = []

    def detect_obstacle(self):
        """Check if an obstacle is detected using the sensors."""
        left_distance = self.sensors.sensor_data.get('left_distance',
                                                     float('inf'))
        right_distance = self.sensors.sensor_data.get('right_distance',
                                                      float('inf'))

        return (left_distance < MIN_DISTANCE_THRESHOLD or
                right_distance < MIN_DISTANCE_THRESHOLD)

    def record_obstacle(self):
        """Record the current GPS position as an obstacle."""
        position = self.localization.estimate_position()
        if position:
            lat, lon = position
            logger.info(f"Obstacle detected at {lat}, {lon}")
            self.obstacle_map.append({"latitude": lat, "longitude": lon})

    def save_obstacle_map(self, filename="obstacle_map.json"):
        """Save the obstacle map to a JSON file."""
        with open(filename, 'w') as f:
            json.dump(self.obstacle_map, f, indent=4)
        logger.info(f"Obstacle map saved to {filename}")

    def explore_yard(self, duration=300):
        """Explore the yard to map obstacles
           for a given duration (in seconds)."""
        start_time = time.time()
        while time.time() - start_time < duration:
            # Drive the mower forward at low speed
            self.driver.run(steering=0.0, throttle=0.2)

            # Check for obstacles and record them if found
            if self.detect_obstacle():
                self.record_obstacle()

            time.sleep(0.1)  # Adjust the loop frequency as needed

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
    # Explore for 20 minutes
    mapper.explore_yard(duration=600)
