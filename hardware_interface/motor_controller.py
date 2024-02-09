import RPi.GPIO as GPIO
import time
import numpy as np
import logging

# Initialize logging
logging.basicConfig(filename='main.log', level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')

class MotorController:
    def __init__(self):
        # Define GPIO pins connected to the IBT-2 drivers
        self.Prwm1, self.Lpwm1 = 4, 27  # Motor 1 control pins
        self.Prwm2, self.Lpwm2 = 21, 20  # Motor 2 control pins
        self.R_En1, self.L_En1 = 13, 13  # Motor 1 enable pins
        self.R_En2, self.L_En2 = 16, 16  # Motor 2 enable pins

        # Set up GPIO
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup([self.Prwm1, self.Lpwm1, self.Prwm2, self.Lpwm2, self.R_En1, self.L_En1, self.R_En2, self.L_En2], GPIO.OUT)

        # Set up PWM
        self.pwm1 = GPIO.PWM(self.R_En1, 2000)  # 2000 Hz
        self.pwm2 = GPIO.PWM(self.R_En2, 2000)  # 2000 Hz
        self.pwm1.start(0)  # Start with 0% duty cycle
        self.pwm2.start(0)  # Start with 0% duty cycle

    def set_motor_speed(self, right_speed, left_speed):
        # Set the speed of both motors
        self.pwm1.ChangeDutyCycle(right_speed)
        self.pwm2.ChangeDutyCycle(left_speed)

    def set_motor_direction(self, direction):
        # Set the direction of both motors
        if direction == "forward":
            GPIO.output(self.Prwm1, GPIO.LOW)
            GPIO.output(self.Lpwm1, GPIO.HIGH)
            GPIO.output(self.Prwm2, GPIO.HIGH)
            GPIO.output(self.Lpwm2, GPIO.LOW)
        elif direction == "backward":
            GPIO.output(self.Prwm1, GPIO.HIGH)
            GPIO.output(self.Lpwm1, GPIO.LOW)
            GPIO.output(self.Prwm2, GPIO.LOW)
            GPIO.output(self.Lpwm2, GPIO.HIGH)
        elif direction == "right":
            GPIO.output(self.Prwm1, GPIO.HIGH)
            GPIO.output(self.Lpwm1, GPIO.LOW)
            GPIO.output(self.Prwm2, GPIO.HIGH)
            GPIO.output(self.Lpwm2, GPIO.LOW)
        elif direction == "left":
            GPIO.output(self.Prwm1, GPIO.LOW)
            GPIO.output(self.Lpwm1, GPIO.HIGH)
            GPIO.output(self.Prwm2, GPIO.LOW)
            GPIO.output(self.Lpwm2, GPIO.HIGH)

    def stop_motors(self):
        # Stop the motors
        GPIO.output(self.Prwm1, GPIO.LOW)
        GPIO.output(self.Lpwm1, GPIO.LOW)
        GPIO.output(self.Prwm2, GPIO.LOW)
        GPIO.output(self.Lpwm2, GPIO.LOW)

    def cleanup(self):
        # Stop the motors
        self.stop_motors()
        
        # Stop PWM
        self.pwm1.stop()
        self.pwm2.stop()
        
        GPIO.cleanup()

    def move_mower(self, direction, left_speed, right_speed):
        try:
            # Set the direction and speed of the motors
            self.set_motor_direction(direction)
            self.set_motor_speed(right_speed, left_speed)
            return True
        except Exception as e:
            logging.error(f"Failed to move mower due to: {e}")
            return False

    @staticmethod
    def set_motor_direction_degrees(direction_degrees):
        # Normalize the direction to the range [-180, 180]
        direction_degrees = ((direction_degrees + 180) % 360) - 180

        # Calculate the motor speeds based on the direction
        if direction_degrees < -90:
            # Turn left
            right_speed = 100
            left_speed = 100 + (direction_degrees + 90) * 2
        elif direction_degrees < 0:
            # Turn slightly left
            right_speed = 100
            left_speed = 100 + direction_degrees * 2
        elif direction_degrees < 90:
            # Turn slightly right
            left_speed = 100
            right_speed = 100 - direction_degrees * 2
        else:
            # Turn right
            left_speed = 100
            right_speed = 100 - (direction_degrees - 90) * 2

        # Set the motor speeds
        MotorController.set_motor_speed(right_speed, left_speed)

    def reward_function(self, deviation_from_path):
        # Reward function based on how well the mower is following the path
        return -abs(deviation_from_path)
    
    def q_learning(self, current_state, deviation_from_path, learning_rate=0.1, discount_factor=0.9):
        reward = self.reward_function(deviation_from_path)
        old_value = self.q_table[current_state][self.last_action]
        next_max = np.max(self.q_table[current_state])
        new_value = (1 - learning_rate) * old_value + learning_rate * (reward + discount_factor * next_max)
        self.q_table[current_state][self.last_action] = new_value

    def set_motor_speed_and_direction(self, current_state):
        # Choose an action based on Q-table
        action = np.argmax(self.q_table[current_state])
        self.last_action = action

        if action == 0:
            self.move_mower("forward", 100, 100)
        elif action == 1:
            self.move_mower("backward", 100, 100)
        elif action == 2:
            self.move_mower("left", 100, 100)
        elif action == 3:
            self.move_mower("right", 100, 100)

# Test the motors
# try:
#     print("Testing the motors")
#     MotorController.move_mower("forward", 100, 100)  # Move forward at 50% speed
#     print("Moving Forward")
#     time.sleep(5)  # Run the motors for 5 seconds
#     MotorController.stop_motors()  # Stop the motors
#     time.sleep(1)  # Wait for 1 second
#     MotorController.move_mower("backward", 100, 100)  # Move backward at 50% speed
#     print("Moving Backward")
#     time.sleep(5)  # Run the motors for 5 seconds
#     MotorController.stop_motors()  # Stop the motors
#     time.sleep(1)  # Wait for 1 second
#     MotorController.move_mower("left", 100, 100)  # Turn left at 50% speed
#     print("Turning Left")
#     time.sleep(5)  # Run the motors for 5 seconds
#     MotorController.stop_motors()  # Stop the motors
#     time.sleep(1)  # Wait for 1 second
#     MotorController.move_mower("right", 100, 100)  # Turn right at 50% speed
#     print("Turning Right")
#     time.sleep(5)  # Run the motors for 5 seconds
#     MotorController.stop_motors()  # Stop the motors
#     MotorController.cleanup()

# except KeyboardInterrupt:
#     MotorController.cleanup()