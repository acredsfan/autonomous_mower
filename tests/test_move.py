# Code to test Motor Controller
#IMPORTS
import RPi.GPIO as GPIO
import time

#CONSTANTS
LEFT_PWMI_PIN = 13
LEFT_IN1_PIN = 19
LEFT_IN2_PIN = 26
RIGHT_PWMI_PIN = 16
RIGHT_IN3_PIN = 20
RIGHT_IN4_PIN = 21

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

SPEED_CONTROLLER_PIN = 5

# Set up GPIO
GPIO.setup(SPEED_CONTROLLER_PIN, GPIO.OUT)
GPIO.setup(LEFT_PWMI_PIN, GPIO.OUT)
GPIO.setup(LEFT_IN1_PIN, GPIO.OUT)
GPIO.setup(LEFT_IN2_PIN, GPIO.OUT)
GPIO.setup(RIGHT_PWMI_PIN, GPIO.OUT)
GPIO.setup(RIGHT_IN3_PIN, GPIO.OUT)
GPIO.setup(RIGHT_IN4_PIN, GPIO.OUT)

# Set up PWM
left_motor = GPIO.PWM(LEFT_PWMI_PIN, 100)
right_motor = GPIO.PWM(RIGHT_PWMI_PIN, 100)

left_motor.start(0)
right_motor.start(0)

# Test speed controller
print("Testing speed controller...")
GPIO.output(SPEED_CONTROLLER_PIN, GPIO.HIGH)
print("Speed controller on")

# Move both forward
print("Moving both forward...")
GPIO.output(LEFT_IN1_PIN, GPIO.HIGH)
GPIO.output(LEFT_IN2_PIN, GPIO.LOW)
GPIO.output(RIGHT_IN3_PIN, GPIO.HIGH)
GPIO.output(RIGHT_IN4_PIN, GPIO.LOW)
left_motor.ChangeDutyCycle(100)
right_motor.ChangeDutyCycle(100)
time.sleep(2)

# Move both backward
print("Moving both backward...")
GPIO.output(LEFT_IN1_PIN, GPIO.LOW)
GPIO.output(LEFT_IN2_PIN, GPIO.HIGH)
GPIO.output(RIGHT_IN3_PIN, GPIO.LOW)
GPIO.output(RIGHT_IN4_PIN, GPIO.HIGH)
left_motor.ChangeDutyCycle(100)
right_motor.ChangeDutyCycle(100)
time.sleep(2)

# Turn Right (Left forward, Right backward)
print("Turning right...")
GPIO.output(LEFT_IN1_PIN, GPIO.HIGH)
GPIO.output(LEFT_IN2_PIN, GPIO.LOW)
GPIO.output(RIGHT_IN3_PIN, GPIO.LOW)
GPIO.output(RIGHT_IN4_PIN, GPIO.HIGH)
left_motor.ChangeDutyCycle(100)
right_motor.ChangeDutyCycle(100)
time.sleep(2)

# Turn Left (Left backward, Right forward)
print("Turning left...")
GPIO.output(LEFT_IN1_PIN, GPIO.LOW)
GPIO.output(LEFT_IN2_PIN, GPIO.HIGH)
GPIO.output(RIGHT_IN3_PIN, GPIO.HIGH)
GPIO.output(RIGHT_IN4_PIN, GPIO.LOW)
left_motor.ChangeDutyCycle(100)
right_motor.ChangeDutyCycle(100)
time.sleep(2)

# Turn off Relay
print("Turning off speed controller...")
GPIO.output(SPEED_CONTROLLER_PIN, GPIO.LOW)
print("Speed controller off")

# Clean up GPIO
GPIO.cleanup()
