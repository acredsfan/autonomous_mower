import sys
import os

# Add the project root to the system path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import time
from hardware_interface import SensorInterface
import logging
from constants import MIN_DISTANCE_THRESHOLD, AVOIDANCE_DELAY

# Initialize logging
logging.basicConfig(filename='main.log', level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')

class ObstacleAvoidance:
    def __init__(self, camera=None):
        self.camera = camera
        self.obstacle_left = False
        self.obstacle_right = False

    def _update_obstacle_status(self):
        """Update the obstacle status based on the VL53L0X sensor readings."""
        left_distance = SensorInterface.read_vl53l0x_left()
        right_distance = SensorInterface.read_vl53l0x_right()

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