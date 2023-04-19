# This module will be responsible for processing the data from the navigation system and obstacle detection to plan the robot's trajectory while mowing. 
# It will communicate with the motor controller module to adjust the robot's path when necessary.
# Will need to be compatible with a Raspberry Pi 4B 2GB RAM running Raspbian Bullseye OS.

#IMPORTS
import time
import numpy as np
from hardware_interface import motor_controller
from navigation_system import localization
from obstacle_detection import direction_controller, sensor_interface

# Constants
MIN_DISTANCE_TO_OBSTACLE = 30  # in centimeters
TURN_ANGLE = 45  # in degrees
SPEED = 50  # as a percentage of the maximum motor speed
WAYPOINT_REACHED_THRESHOLD = 30  # in centimeters

# FUNCTIONS
class TrajectoryController:
    def __init__(self, navigation_system, obstacle_detection):
        self.navigation_system = navigation_system
        self.obstacle_detection = obstacle_detection

    def calculate_trajectory(self):
        """
        Calculate the trajectory based on the current position, target position, and obstacle data.
        Returns a tuple (angle, distance) representing the angle to turn and the distance to move.
        """
        current_position = self.navigation_system.get_current_position()
        target_position = self.navigation_system.get_target_position()
        obstacles = self.obstacle_detection.get_obstacle_data()

        # Calculate the angle and distance to the target position
        angle_to_target, distance_to_target = self.navigation_system.calculate_angle_and_distance(
            current_position, target_position
        )

        # Check if there are any obstacles in the path
        if self.check_for_obstacles(obstacles):
            # Find a new angle to avoid the obstacle
            angle_to_target = self.find_new_angle(angle_to_target, obstacles)

        return angle_to_target, distance_to_target

    def check_for_obstacles(self, obstacles):
        """
        Check if there are any obstacles within the minimum safe distance.
        """
        for _, distance in obstacles.items():
            if distance < MIN_DISTANCE_TO_OBSTACLE:
                return True
        return False

    def find_new_angle(self, angle_to_target, obstacles):
        """
        Find a new angle to avoid the obstacles.
        """
        new_angle = angle_to_target
        while self.check_for_obstacles(obstacles):
            new_angle = (new_angle + TURN_ANGLE) % 360
            obstacles = self.obstacle_detection.get_obstacle_data()
        return new_angle

    def follow_trajectory(self, angle_to_target, distance_to_target):
        """
        Adjust the robot's speed and direction to follow the calculated trajectory.
        """
        motor_controller.set_motor_direction(angle_to_target)
        motor_controller.set_motor_speed(SPEED)
        time_to_move = distance_to_target / motor_controller.get_speed_in_cm_per_second(SPEED)
        time.sleep(time_to_move)
        motor_controller.set_motor_speed(0)

    def execute(self):
        """
        Main loop for the trajectory controller. Continuously calculates and follows the trajectory.
        """
        while not self.navigation_system.is_target_reached():
            angle_to_target, distance_to_target = self.calculate_trajectory()
            self.follow_trajectory(angle_to_target, distance_to_target)
        
    def calculate_direction_and_speed(waypoint):
        current_position = localization.get_current_position()
        angle_to_waypoint, distance_to_waypoint = localization.calculate_angle_and_distance(
            current_position, waypoint
        )

        left_obstacle, right_obstacle = direction_controller.obstacle_detected()
        if left_obstacle or right_obstacle:
            direction = direction_controller.choose_turn_direction(left_obstacle, right_obstacle)
            speed = SPEED
        else:
            direction = angle_to_waypoint
            speed = SPEED

        return direction, speed

    def is_waypoint_reached(waypoint):
        current_position = localization.get_current_position()
        _, distance_to_waypoint = localization.calculate_angle_and_distance(
            current_position, waypoint
        )
        return distance_to_waypoint <= WAYPOINT_REACHED_THRESHOLD

    # Stop the robot when the path is complete
    motor_controller.set_motor_speed(0,0)