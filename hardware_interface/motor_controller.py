import RPi.GPIO as GPIO
import time

# Define GPIO pins connected to the IBT-2 drivers
Prwm1, Lpwm1 = 4, 27  # Motor 1 control pins
Prwm2, Lpwm2 = 21, 20  # Motor 2 control pins
R_En1, L_En1 = 13, 13  # Motor 1 enable pins
R_En2, L_En2 = 16, 16  # Motor 2 enable pins

# Set up GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup([Prwm1, Lpwm1, Prwm2, Lpwm2, R_En1, L_En1, R_En2, L_En2], GPIO.OUT)

# Set up PWM
pwm1 = GPIO.PWM(R_En1, 2000)  # 1000 Hz
pwm2 = GPIO.PWM(R_En2, 2000)  # 1000 Hz
pwm1.start(0)  # Start with 0% duty cycle
pwm2.start(0)  # Start with 0% duty cycle

class MotorController:

    @staticmethod
    def set_motor_speed(right_speed, left_speed):
        # Set the speed of both motors
        pwm1.ChangeDutyCycle(right_speed)
        pwm2.ChangeDutyCycle(left_speed)

    @staticmethod
    def set_motor_direction(direction):
        # Set the direction of both motors
        if direction == "forward":
            GPIO.output(Prwm1, GPIO.LOW)
            GPIO.output(Lpwm1, GPIO.HIGH)
            GPIO.output(Prwm2, GPIO.HIGH)
            GPIO.output(Lpwm2, GPIO.LOW)
        elif direction == "backward":
            GPIO.output(Prwm1, GPIO.HIGH)
            GPIO.output(Lpwm1, GPIO.LOW)
            GPIO.output(Prwm2, GPIO.LOW)
            GPIO.output(Lpwm2, GPIO.HIGH)
        elif direction == "right":
            GPIO.output(Prwm1, GPIO.HIGH)
            GPIO.output(Lpwm1, GPIO.LOW)
            GPIO.output(Prwm2, GPIO.HIGH)
            GPIO.output(Lpwm2, GPIO.LOW)
        elif direction == "left":
            GPIO.output(Prwm1, GPIO.LOW)
            GPIO.output(Lpwm1, GPIO.HIGH)
            GPIO.output(Prwm2, GPIO.LOW)
            GPIO.output(Lpwm2, GPIO.HIGH)
            
    @staticmethod
    def stop_motors():
        # Stop the motors
        GPIO.output(Prwm1, GPIO.LOW)
        GPIO.output(Lpwm1, GPIO.LOW)
        GPIO.output(Prwm2, GPIO.LOW)
        GPIO.output(Lpwm2, GPIO.LOW)

    @staticmethod
    def cleanup():
        # Stop the motors
        MotorController.stop_motors()
        
        # Stop PWM
        pwm1.stop()
        pwm2.stop()
        
        GPIO.cleanup()

    @staticmethod
    def move_mower(direction, left_speed, right_speed):
        # Set the direction and speed of the motors
        MotorController.set_motor_direction(direction)
        MotorController.set_motor_speed(right_speed, left_speed)

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