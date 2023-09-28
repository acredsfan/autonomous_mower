# speed_controller.py
# Python code to control the speed of two 12V worm gear motors using a L298N motor driver
# Running on Raspberry Pi 4B 2GB RAM with Raspbian Bullseye OS

import time
from hardware_interface import MotorController
import logging
from constants import MIN_SPEED, MAX_SPEED, ACCELERATION_RATE, DECELERATION_RATE, TIME_INTERVAL
# Initialize logging
logging.basicConfig(filename='main.log', level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')

class SpeedController:
    # Function to accelerate the motors to the target speed
    def accelerate_to_target_speed(target_left_speed, target_right_speed):
        current_left_speed, current_right_speed = MIN_SPEED, MIN_SPEED
        MotorController.set_motor_speed(current_left_speed, current_right_speed)

        while current_left_speed < target_left_speed or current_right_speed < target_right_speed:
            if current_left_speed < target_left_speed:
                current_left_speed = min(current_left_speed + ACCELERATION_RATE, target_left_speed)

            if current_right_speed < target_right_speed:
                current_right_speed = min(current_right_speed + ACCELERATION_RATE, target_right_speed)

            MotorController.set_motor_speed(current_left_speed, current_right_speed)
            time.sleep(TIME_INTERVAL)

    # Function to decelerate the motors to the target speed
    def decelerate_to_target_speed(target_left_speed, target_right_speed):
        current_left_speed, current_right_speed = MotorController.get_motor_speed()

        while current_left_speed > target_left_speed or current_right_speed > target_right_speed:
            if current_left_speed > target_left_speed:
                current_left_speed = max(current_left_speed - DECELERATION_RATE, target_left_speed)

            if current_right_speed > target_right_speed:
                current_right_speed = max(current_right_speed - DECELERATION_RATE, target_right_speed)

            MotorController.set_motor_speed(current_left_speed, current_right_speed)
            time.sleep(TIME_INTERVAL)

    # Function to set the speed of the motors with smooth acceleration and deceleration
    def set_motor_speed(left_speed, right_speed):
        MotorController.set_motor_speed(left_speed, right_speed)
        MotorController.set_motor_speed(left_speed + ACCELERATION_RATE, right_speed + ACCELERATION_RATE)
        MotorController.set_motor_speed(left_speed + 2 * ACCELERATION_RATE, right_speed + 2 * ACCELERATION_RATE)
        MotorController.set_motor_speed(left_speed + 3 * ACCELERATION_RATE, right_speed + 3 * ACCELERATION_RATE)
        MotorController.set_motor_speed(left_speed + 4 * ACCELERATION_RATE, right_speed + 4 * ACCELERATION_RATE)
        MotorController.set_motor_speed(left_speed + 5 * ACCELERATION_RATE, right_speed + 5 * ACCELERATION_RATE)
        MotorController.set_motor_speed(left_speed + 6 * ACCELERATION_RATE, right_speed + 6 * ACCELERATION_RATE)
        MotorController.set_motor_speed(left_speed + 7 * ACCELERATION_RATE, right_speed + 7 * ACCELERATION_RATE)
        MotorController.set_motor_speed(left_speed + 8 * ACCELERATION_RATE, right_speed + 8 * ACCELERATION_RATE)
        MotorController.set_motor_speed(left_speed + 9 * ACCELERATION_RATE, right_speed + 9 * ACCELERATION_RATE)