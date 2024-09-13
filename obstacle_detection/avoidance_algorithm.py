import threading
import numpy as np
from constants import CAMERA_OBSTACLE_THRESHOLD, MOTOR_SPEED, MIN_DISTANCE_THRESHOLD, AVOIDANCE_DELAY
import time
from constants import MIN_DISTANCE_THRESHOLD, AVOIDANCE_DELAY
from navigation_system import path_planning  # Import GRID_SIZE from path_planning.py
from hardware_interface import SensorInterface

from utils import LoggerConfig

# Initialize logger
logging = LoggerConfig.get_logger(__name__)

class ObstacleAvoidance:
    def __init__(self, camera=None):
        self.camera = camera
        self.obstacle_left = False
        self.obstacle_right = False
        self.sensor_interface = SensorInterface()

    def _update_obstacle_status(self):
        from hardware_interface import SensorInterface
        """Update the obstacle status based on the VL53L0X sensor readings."""
        left_distance = self.sensor_interface.sensor_data.get('left_distance', float('inf'))
        right_distance = self.sensor_interface.sensor_data.get('right_distance', float('inf'))

        self.obstacle_left = left_distance < MIN_DISTANCE_THRESHOLD
        self.obstacle_right = right_distance < MIN_DISTANCE_THRESHOLD

    def avoid_obstacles(self):
        """Continuously check for obstacles and update their status."""
        while True:
            self._update_obstacle_status()
            time.sleep(AVOIDANCE_DELAY)

class AvoidanceAlgorithm:
    def __init__(self, cfg):
        from hardware_interface import CameraProcessor
        from hardware_interface import RoboHATController

        self.camera = CameraProcessor()
        self.tof_avoidance = ObstacleAvoidance()
        self.motor_controller = RoboHATController(cfg)
        self.obstacle_detected = False
        self.dropoff_detected = False
        self.q_table = np.zeros((path_planning.GRID_SIZE[0], path_planning.GRID_SIZE[1], 4))  # 4 directions
        self.last_action = None
        self.memory = {}

    def reward_function(self, obstacle_data, new_state):
        if obstacle_data[new_state[0], new_state[1]] == 1:
            return -100  # Penalty for hitting an obstacle
        else:
            return 1  # Reward for free space

    def q_learning(self, current_state, obstacle_data, learning_rate=0.1, discount_factor=0.9):
        if self.last_action is not None:
            reward = self.reward_function(obstacle_data, current_state)
            old_value = self.q_table[current_state[0], current_state[1], self.last_action]
            next_max = np.max(self.q_table[current_state[0], current_state[1], :])
            new_value = (1 - learning_rate) * old_value + learning_rate * (reward + discount_factor * next_max)
            self.q_table[current_state[0], current_state[1], self.last_action] = new_value

        # Check if the action led to a negative outcome
        if self.reward_function(obstacle_data, current_state) < 0:
            self.memory[current_state] = self.last_action

    def get_next_action(self, current_state):
        # Check memory to avoid actions that led to negative outcomes
        if current_state in self.memory:
            possible_actions = [0, 1, 2, 3]  # Assuming 4 actions: up, down, left, right
            possible_actions.remove(self.memory[current_state])
            return np.argmax(self.q_table[current_state[0], current_state[1], possible_actions])
        else:
            return np.argmax(self.q_table[current_state[0], current_state[1], :])

    def _tof_avoidance_thread(self):
        """Run the Time of Flight obstacle avoidance in a separate thread."""
        self.tof_avoidance.avoid_obstacles()

    def check_camera_obstacles_and_dropoffs(self):
        """Check for obstacles and drop-offs using the camera and update the obstacle_detected attribute."""
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
        
        # Re-plan the path to avoid the obstacle
        start = self.get_current_state()
        goal = self.path_planning.goal  # Assuming you have set the goal
        new_path = self.path_planning.plan_path(start, goal, self.obstacles)
        
        # Follow the new path
        for cell in new_path:
            coord = self.path_planning.grid_to_coord(cell)
            self.motor_controller.navigate_to_location((coord['lat'], coord['lng']))

    def get_current_state(self):
        """Get the current state based on the robot's position."""
        current_position = self.motor_controller.gps_latest_position.run()
        grid_cell = self.path_planning.coord_to_grid(current_position[0], current_position[1])
        return grid_cell

    def run_avoidance(self):
        """Continuously run the avoidance algorithm using data from ToF sensors and the camera."""
        tof_thread = threading.Thread(target=self._tof_avoidance_thread)
        tof_thread.start()

        try:
            while True:
                self.check_camera_obstacles_and_dropoffs()

                if self.tof_avoidance.obstacle_left or self.tof_avoidance.obstacle_right or self.obstacle_detected or self.dropoff_detected:
                    self.handle_avoidance()

        except KeyboardInterrupt:
            logging.info("Stopping the avoidance algorithm...")

        finally:
            tof_thread.join()
            logging.info("Avoidance algorithm stopped.")

if __name__ == "__main__":
    # Configuration placeholder (replace with actual configuration)
    class Config:
        MM1_SERIAL_PORT = '/dev/ttyUSB0'
        MM1_MAX_FORWARD = 2000
        MM1_MAX_REVERSE = 1000
        MM1_STOPPED_PWM = 1500
        MM1_STEERING_MID = 1500
        AUTO_RECORD_ON_THROTTLE = True
        JOYSTICK_DEADZONE = 0.1

    cfg = Config()
    avoidance_algorithm = AvoidanceAlgorithm(cfg)
    avoidance_algorithm.run_avoidance()