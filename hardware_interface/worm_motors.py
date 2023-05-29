import RPi.GPIO as GPIO
import time

# Set up GPIO mode
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Define GPIO pins connected to the L298N
IN1, IN2 = 19, 26
IN3, IN4 = 20, 21
ENA, ENB = 13, 16

# Set up GPIO pins as output
for pin in [IN1, IN2, IN3, IN4, ENA, ENB]:
    GPIO.setup(pin, GPIO.OUT)

# Set up PWM channels
pwmA = GPIO.PWM(ENA, 1000)  # Initialize PWM for motor A (100Hz frequency)
pwmB = GPIO.PWM(ENB, 1000)  # Initialize PWM for motor B (100Hz frequency)

# Start PWM with 0% duty cycle (off)
pwmA.start(0)
pwmB.start(0)

class MotorController:

    @staticmethod
    def set_motor_speed(left_speed, right_speed):
        # Set the speed of both motors
        pwmA.ChangeDutyCycle(left_speed)
        pwmB.ChangeDutyCycle(right_speed)

    @staticmethod
    def set_motor_direction(direction):
        # Set the direction of both motors
        if direction == "forward":
            GPIO.output(IN1, GPIO.LOW)
            GPIO.output(IN2, GPIO.HIGH)
            GPIO.output(IN3, GPIO.LOW)
            GPIO.output(IN4, GPIO.HIGH)
        elif direction == "backward":
            GPIO.output(IN1, GPIO.HIGH)
            GPIO.output(IN2, GPIO.LOW)
            GPIO.output(IN3, GPIO.HIGH)
            GPIO.output(IN4, GPIO.LOW)
        elif direction == "left":
            GPIO.output(IN1, GPIO.HIGH)
            GPIO.output(IN2, GPIO.LOW)
            GPIO.output(IN3, GPIO.LOW)
            GPIO.output(IN4, GPIO.HIGH)
        elif direction == "right":
            GPIO.output(IN1, GPIO.LOW)
            GPIO.output(IN2, GPIO.HIGH)
            GPIO.output(IN3, GPIO.HIGH)
            GPIO.output(IN4, GPIO.LOW)

    @staticmethod
    def stop_motors():
        # Stop the motors
        GPIO.output(IN1, GPIO.LOW)
        GPIO.output(IN2, GPIO.LOW)
        GPIO.output(IN3, GPIO.LOW)
        GPIO.output(IN4, GPIO.LOW)

    @staticmethod
    def cleanup():
        # Stop the motors
        MotorController.stop_motors()
        
        # Stop PWM
        pwmA.stop()
        pwmB.stop()
        
        GPIO.cleanup()

    @staticmethod
    def move_mower(direction, speed):
        # Set the direction and speed of the motors
        MotorController.set_motor_direction(direction)
        MotorController.set_motor_speed(speed)

# Test the motors
try:
    #GPIO.cleanup()
    #GPIO.setmode(GPIO.BCM)
    MotorController.move_mower("forward", 100)  # Move forward at 50% speed
    time.sleep(5)  # Run the motors for 5 seconds
    MotorController.cleanup()

except KeyboardInterrupt:
    MotorController.cleanup()
