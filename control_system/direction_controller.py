# direction_controller.py
# Python code to control the direction of an autonomous robot based on sensor input
# Running on Raspberry Pi 4B 2GB RAM with Raspbian Bullseye OS

import time
import motor_controller
import sensor_interface

# Set the distance threshold for obstacle avoidance (in millimeters)
DISTANCE_THRESHOLD = 300

# Set time intervals for various actions
CHECK_INTERVAL = 0.5
TURN_INTERVAL = 1

# Check if an obstacle is detected on the left or right side of the robot
def obstacle_detected():
    left_distance = sensor_interface.read_vl53l0x_left()
    right_distance = sensor_interface.read_vl53l0x_right()

    return left_distance < DISTANCE_THRESHOLD, right_distance < DISTANCE_THRESHOLD

# Determine the direction to turn based on obstacle detection
def choose_turn_direction(left_obstacle, right_obstacle):
    if left_obstacle and right_obstacle:
        return "backward"
    elif left_obstacle:
        return "right"
    elif right_obstacle:
        return "left"
    else:
        return "forward"

# Main function to control the robot direction based on sensor input
def control_direction():
    sensor_interface.init_sensors()
    motor_controller.init_motor_controller()

    while True:
        left_obstacle, right_obstacle = obstacle_detected()

        if left_obstacle or right_obstacle:
            direction = choose_turn_direction(left_obstacle, right_obstacle)
            motor_controller.set_motor_direction(direction)
            motor_controller.set_motor_speed(50, 50)
            time.sleep(TURN_INTERVAL)
        else:
            motor_controller.set_motor_direction("forward")
            motor_controller.set_motor_speed(50, 50)
            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    try:
        control_direction()
    except KeyboardInterrupt:
        motor_controller.stop_motors()
        motor_controller.cleanup()
        sensor_interface.cleanup()