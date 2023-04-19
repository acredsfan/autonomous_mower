# Code for processing the data from the ToF sensors
# Uses the VL53L0X library to get the distance to the nearest object

#IMPORTS
import time
from sensor_interface import read_vl53l0x_left, read_vl53l0x_right

# Constants
MIN_DISTANCE_THRESHOLD = 150  # Minimum distance to consider an obstacle in millimeters
AVOIDANCE_DELAY = 0.5  # Time to wait between avoidance checks in seconds

class ObstacleAvoidance:
    def __init__(self):
        self.obstacle_left = False
        self.obstacle_right = False

    def _update_obstacle_status(self):
        """Update the obstacle status based on the VL53L0X sensor readings."""
        left_distance = read_vl53l0x_left()
        right_distance = read_vl53l0x_right()

        self.obstacle_left = left_distance < MIN_DISTANCE_THRESHOLD
        self.obstacle_right = right_distance < MIN_DISTANCE_THRESHOLD

    def avoid_obstacles(self):
        """Continuously check for obstacles and update their status."""
        while True:
            self._update_obstacle_status()
            time.sleep(AVOIDANCE_DELAY)

if __name__ == "__main__":
    obstacle_avoidance = ObstacleAvoidance()
    obstacle_avoidance.avoid_obstacles()