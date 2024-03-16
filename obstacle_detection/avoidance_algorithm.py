# Code for the obstacle avoidance algorithm
# Uses the data from the ToF sensors and the camera to calculate the best direction to move in

# IMPORTS
import threading
from obstacle_detection.tof_processing import ObstacleAvoidance as ToFAvoidance
from obstacle_detection.camera_processing import CameraProcessor
from hardware_interface.motor_controller import MotorController
import logging
import numpy as np
from constants import CAMERA_OBSTACLE_THRESHOLD, MOTOR_SPEED

# Import GRID_SIZE from path_planning.py
from navigation_system.path_planning import GRID_SIZE

# Initialize logging
logging.basicConfig(filename='main.log', level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')

class AvoidanceAlgorithm:
    def __init__(self):
        self.camera = CameraProcessor()
        self.tof_avoidance = ToFAvoidance()
        self.motor_controller = MotorController()
        self.obstacle_detected = False
        self.q_table = np.zeros((GRID_SIZE[0], GRID_SIZE[1], 4))  # Grid defined in path_planning, 4 directions
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
            # Choose an action other than the one in memory
            possible_actions = [0, 1, 2, 3]  # Assuming 4 actions: up, down, left, right
            possible_actions.remove(self.memory[current_state])
            return np.argmax(self.q_table[current_state[0], current_state[1], possible_actions])
        else:
            return np.argmax(self.q_table[current_state[0], current_state[1], :])

    def _tof_avoidance_thread(self):
        """Run the Time of Flight obstacle avoidance in a separate thread."""
        self.tof_avoidance.avoid_obstacles()

    def check_camera_obstacles(self):
        """Check for obstacles using the camera and update the obstacle_detected attribute."""
        obstacles = self.camera.process_frame()

        for obstacle in obstacles:
            _, _, w, h = obstacle['box']
            if w * h > CAMERA_OBSTACLE_THRESHOLD:
                self.obstacle_detected = True
                return

        self.obstacle_detected = False

    def run_avoidance(self):
        """Continuously run the avoidance algorithm using data from ToF sensors and the camera."""
        # Start the ToF avoidance thread
        tof_thread = threading.Thread(target=self._tof_avoidance_thread)
        tof_thread.start()

        try:
            while True:
                self.check_camera_obstacles()

                if self.tof_avoidance.obstacle_detected or self.obstacle_detected:
                    # Handle obstacle avoidance here
                    print("Obstacle detected, handling avoidance...")

        except KeyboardInterrupt:
            print("Stopping the avoidance algorithm...")

        finally:
            tof_thread.join()
            print("Avoidance algorithm stopped.")

if __name__ == "__main__":
    avoidance_algorithm = AvoidanceAlgorithm()
    avoidance_algorithm.run_avoidance()