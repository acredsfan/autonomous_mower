# Code to test Motor Controller
#IMPORTS
import RPi.GPIO as GPIO
import time

#Setup and define speed controller
#CONSTANTS
SPEED_CONTROLLER_PIN = 5
MOWER_BLADES_PIN = 6

#VARIABLES
relay_controller_state = False
mower_blades_state = False

# Set up GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(SPEED_CONTROLLER_PIN, GPIO.OUT)
GPIO.setup(MOWER_BLADES_PIN, GPIO.OUT)

def relay_controller_on():
    global relay_controller_state
    GPIO.output(SPEED_CONTROLLER_PIN, GPIO.HIGH)
    relay_controller_state = True
    print("Speed controller on")

def relay_controller_off():
    global relay_controller_state
    GPIO.output(SPEED_CONTROLLER_PIN, GPIO.LOW)
    relay_controller_state = False
    print("Speed controller off")

#setup and define motor controller
#CONSTANTS
LEFT_PWMI_PIN = 13
LEFT_IN1_PIN = 19
LEFT_IN2_PIN = 26
RIGHT_PWMI_PIN = 16
RIGHT_IN3_PIN = 20
RIGHT_IN4_PIN = 21

#Variables
left_motor = None
right_motor = None

# Set up GPIO
GPIO.setup(LEFT_PWMI_PIN, GPIO.OUT)
GPIO.setup(LEFT_IN1_PIN, GPIO.OUT)
GPIO.setup(LEFT_IN2_PIN, GPIO.OUT)
GPIO.setup(RIGHT_PWMI_PIN, GPIO.OUT)
GPIO.setup(RIGHT_IN3_PIN, GPIO.OUT)
GPIO.setup(RIGHT_IN4_PIN, GPIO.OUT)

# Set up PWM
left_motor = GPIO.PWM(LEFT_PWMI_PIN, 100)
right_motor = GPIO.PWM(RIGHT_PWMI_PIN, 100)

def init_motor_controller():
    left_motor.start(0)
    right_motor.start(0)

def set_motor_speed(left_speed, right_speed):
    left_motor.ChangeDutyCycle(left_speed)
    right_motor.ChangeDutyCycle(right_speed)

def set_motor_direction(direction):
    if direction == "forward":
        GPIO.output(LEFT_IN1_PIN, GPIO.HIGH)
        GPIO.output(LEFT_IN2_PIN, GPIO.LOW)
        GPIO.output(RIGHT_IN3_PIN, GPIO.HIGH)
        GPIO.output(RIGHT_IN4_PIN, GPIO.LOW)
    elif direction == "backward":
        GPIO.output(LEFT_IN1_PIN, GPIO.LOW)
        GPIO.output(LEFT_IN2_PIN, GPIO.HIGH)
        GPIO.output(RIGHT_IN3_PIN, GPIO.LOW)
        GPIO.output(RIGHT_IN4_PIN, GPIO.HIGH)
    elif direction == "left":
        GPIO.output(LEFT_IN1_PIN, GPIO.LOW)
        GPIO.output(LEFT_IN2_PIN, GPIO.HIGH)
        GPIO.output(RIGHT_IN3_PIN, GPIO.HIGH)
        GPIO.output(RIGHT_IN4_PIN, GPIO.LOW)
    elif direction == "right":
        GPIO.output(LEFT_IN1_PIN, GPIO.HIGH)
        GPIO.output(LEFT_IN2_PIN, GPIO.LOW)
        GPIO.output(RIGHT_IN3_PIN, GPIO.LOW)
        GPIO.output(RIGHT_IN4_PIN, GPIO.HIGH)
    elif direction == "stop":
        GPIO.output(LEFT_IN1_PIN, GPIO.LOW)
        GPIO.output(LEFT_IN2_PIN, GPIO.LOW)
        GPIO.output(RIGHT_IN3_PIN, GPIO.LOW)
        GPIO.output(RIGHT_IN4_PIN, GPIO.LOW)
    else:
        print("Invalid direction")

# Test speed controller (relay controller must be on to run motor controller)
print("Testing speed controller...")
relay_controller_on()
print("Speed controller on")
set_motor_speed(100, 100)
set_motor_direction("forward")
time.sleep(5)
set_motor_speed(0, 0)
set_motor_direction("stop")
relay_controller_off()
print("Speed controller off")


