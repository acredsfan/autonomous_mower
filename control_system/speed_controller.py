# speed_controller.py
# Python code to control the speed of two 12V worm gear motors using a L298N motor driver
# Running on Raspberry Pi 4B 2GB RAM with Raspbian Bullseye OS

import time
import motor_controller

# Set default speed limits
MIN_SPEED = 0
MAX_SPEED = 100

# Set acceleration and deceleration rates
ACCELERATION_RATE = 2  # Increase in motor speed per loop iteration
DECELERATION_RATE = 3  # Decrease in motor speed per loop iteration

# Time interval between loop iterations
TIME_INTERVAL = 0.1

class SpeedController:
    # Function to accelerate the motors to the target speed
    def accelerate_to_target_speed(target_left_speed, target_right_speed):
        current_left_speed, current_right_speed = MIN_SPEED, MIN_SPEED
        motor_controller.set_motor_speed(current_left_speed, current_right_speed)

        while current_left_speed < target_left_speed or current_right_speed < target_right_speed:
            if current_left_speed < target_left_speed:
                current_left_speed = min(current_left_speed + ACCELERATION_RATE, target_left_speed)

            if current_right_speed < target_right_speed:
                current_right_speed = min(current_right_speed + ACCELERATION_RATE, target_right_speed)

            motor_controller.set_motor_speed(current_left_speed, current_right_speed)
            time.sleep(TIME_INTERVAL)

    # Function to decelerate the motors to the target speed
    def decelerate_to_target_speed(target_left_speed, target_right_speed):
        current_left_speed, current_right_speed = motor_controller.get_motor_speed()

        while current_left_speed > target_left_speed or current_right_speed > target_right_speed:
            if current_left_speed > target_left_speed:
                current_left_speed = max(current_left_speed - DECELERATION_RATE, target_left_speed)

            if current_right_speed > target_right_speed:
                current_right_speed = max(current_right_speed - DECELERATION_RATE, target_right_speed)

            motor_controller.set_motor_speed(current_left_speed, current_right_speed)
            time.sleep(TIME_INTERVAL)

    # Function to set the speed of the motors with smooth acceleration and deceleration