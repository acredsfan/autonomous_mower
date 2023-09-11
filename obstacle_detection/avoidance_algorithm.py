# Code for the obstacle avoidance algorithm
# Uses the data from the ToF sensors and the camera to calculate the best direction to move in

# IMPORTS
import threading
from obstacle_detection import tof_processing
from obstacle_detection import camera_processing
from hardware_interface import MotorController
import json
import time
import logging
import numpy as np

# Import GRID_SIZE from path_planning.py
from navigation_system.path_planning import GRID_SIZE

# Initialize logging
logging.basicConfig(filename='avoidance.log', level=logging.DEBUG)

with open("config.json") as f:
    config = json.load(f)

# Constants
CAMERA_OBSTACLE_THRESHOLD = config['CAMERA_OBSTACLE_THRESHOLD'] # Minimum area to consider an obstacle from the camera
MOTOR_SPEED = 70

class AvoidanceAlgorithm:
    def __init__(self):
        self.tof_avoidance = tof_processing()
        self.camera_processor = camera_processing()
        self.obstacle_detected = False
        self.q_table = np.zeros((GRID_SIZE, GRID_SIZE, 4)) # Grid defined in path_planning, 4 directions
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
        obstacles = self.camera_processor.process_frame()

        for _, _, w, h in obstacles:
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
            MotorController.set_motor_speed(MOTOR_SPEED, MOTOR_SPEED)
            MotorController.set_motor_direction("forward")

            while True:
                self.check_camera_obstacles()

                if self.tof_avoidance.obstacle_left or self.tof_avoidance.obstacle_right or self.obstacle_detected:
                    # Handle obstacle avoidance here
                    MotorController.stop_motors
                    MotorController.set_motor_direction("backward")
                    MotorController.set_motor_speed(MOTOR_SPEED, MOTOR_SPEED)
                    time.sleep(1)

                    MotorController.set_motor_direction("left" if self.tof_avoidance.obstacle_left else "right")
                    time.sleep(0.5)

                    MotorController.set_motor_direction("forward")
                    MotorController.set_motor_speed(MOTOR_SPEED, MOTOR_SPEED)

                else:
                    # No obstacles detected
                    # Continue the normal operation of the robot
                    print("No obstacles detected.")

        except KeyboardInterrupt:
            print("Stopping the avoidance algorithm...")

        finally:
            MotorController.stop_motors()
            self.camera_processor.close()
            tof_thread.join()
            self.cleanup()

if __name__ == "__main__":
    avoidance_algorithm = AvoidanceAlgorithm()
    avoidance_algorithm.run_avoidance()
