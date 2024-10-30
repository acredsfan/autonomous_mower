# avoidance_algorithm.py

import threading
import time

from mower.utilities.logger_config import (
    LoggerConfigDebug as LoggerConfig
)
from mower.constants import (AVOIDANCE_DELAY,
                             CAMERA_OBSTACLE_THRESHOLD,
                             MIN_DISTANCE_THRESHOLD)

# Initialize logger
logging = LoggerConfig.get_logger(__name__)


class ObstacleAvoidance:
    def __init__(self, sensor_interface):
        self.sensor_interface = sensor_interface
        self.obstacle_left = False
        self.obstacle_right = False
        self.stop_thread = False

    def _update_obstacle_status(self):
        """Update the obstacle status based on the VL53L0X sensor readings."""
        while not self.stop_thread:
            left_distance = self.sensor_interface._read_vl53l0x(
                'left_distance', float('inf'))
            right_distance = self.sensor_interface._read_vl53l0x(
                'right_distance', float('inf'))

            self.obstacle_left = left_distance < MIN_DISTANCE_THRESHOLD
            self.obstacle_right = right_distance < MIN_DISTANCE_THRESHOLD
            time.sleep(AVOIDANCE_DELAY)

    def start(self):
        """Start the obstacle avoidance thread."""
        self.thread = threading.Thread(target=self._update_obstacle_status,
                                       daemon=True)
        self.thread.start()

    def stop(self):
        """Stop the obstacle avoidance thread."""
        self.stop_thread = True
        self.thread.join()


class AvoidanceAlgorithm:
    def __init__(self, path_planner, motor_controller, sensor_interface):
        self.camera_obstacle_flag = None
        self.path_planner = path_planner
        self.motor_controller = motor_controller
        self.sensor_interface = sensor_interface

        self.obstacle_avoidance = ObstacleAvoidance(sensor_interface)
        self.obstacle_detected = False
        self.dropoff_detected = False

    def check_camera_obstacles_and_dropoffs(self):
        """Check for obstacles and drop-offs using the camera and
        update the obstacle_detected attribute."""
        obstacles = self.camera.classify_obstacle()
        dropoff_detected = self.camera.detect_dropoff()

        if dropoff_detected:
            self.dropoff_detected = True
            logging.info("Drop-off detected! Avoiding this area.")
            return

        for obstacle in obstacles or []:
            _, _, w, h = obstacle['box']
            if w * h > CAMERA_OBSTACLE_THRESHOLD:
                self.obstacle_detected = True
                logging.info("Obstacle detected! Avoiding this area.")
                return

        self.obstacle_detected = False
        self.dropoff_detected = False

    def handle_avoidance(self):
        """Handle the obstacle and drop-off avoidance logic."""
        logging.info("Handling avoidance...")
        self.motor_controller.stop()  # Stop the mower

        # Get current position
        current_position = self.motor_controller.gps_latest_position.run()

        # Get the obstacle position (assuming it's at the current position)
        obstacle_position = (current_position[1], current_position[2])

        # Update obstacles in path planner
        self.path_planner.update_obstacle_map([obstacle_position])

        # Re-plan the path to avoid the obstacle
        goal = self.path_planner.goal  # Assuming goal is set
        if goal is None:
            logging.error("Goal not set in path planner.")
            return

        start_grid = self.path_planner.coord_to_grid(*obstacle_position)
        goal_grid = goal  # Goal is already in grid coordinates

        # Plan a new path
        new_path = self.path_planner.get_path(start_grid, goal_grid)

        # Follow the new path
        for coord in new_path:
            self.motor_controller.navigate_to_location((coord['lat'],
                                                        coord['lng']))
            time.sleep(0.1)  # Adjust as needed

    def run_avoidance(self):
        """Continuously run the avoidance algorithm
        using data from sensors and the camera."""
        self.obstacle_avoidance.start()

        try:
            while True:
                self.check_camera_obstacles_and_dropoffs()

                if (self.obstacle_avoidance.obstacle_left or
                        self.obstacle_avoidance.obstacle_right or
                        self.obstacle_detected or
                        self.dropoff_detected):
                    self.handle_avoidance()
                else:
                    # Continue normal operation
                    time.sleep(0.1)
        except KeyboardInterrupt:
            logging.info("Stopping the avoidance algorithm...")
        finally:
            self.obstacle_avoidance.stop()
            logging.info("Avoidance algorithm stopped.")
