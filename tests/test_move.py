# Code to test Motor Controller
#IMPORTS
import RPi.GPIO as GPIO
import time

#CONSTANTS
SPEED_CONTROLLER_PIN = 5
LEFT_PWMI_PIN = 13
LEFT_IN1_PIN = 19
LEFT_IN2_PIN = 26
RIGHT_PWMI_PIN = 16
RIGHT_IN3_PIN = 20
RIGHT_IN4_PIN = 21

#Variables
left_motor = None
right_motor = None
relay_controller_state = False

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

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

def init_motor_controller():
    left_motor.start(0)
    right_motor.start(0)

def relay_on():
    GPIO.output(SPEED_CONTROLLER_PIN, GPIO.HIGH)
    print("Speed controller on")

def relay_off():
    GPIO.output(SPEED_CONTROLLER_PIN, GPIO.LOW)
    print("Speed controller off")

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

def test_motor_controller():
    init_motor_controller()
    print("Testing motor controller...")
    time.sleep(5)
    relay_on()
    print("Speed controller on")
    set_motor_speed(100, 100)
    print("Speed set to 100")
    set_motor_direction("forward")
    print("Direction set to forward")
    time.sleep(5)
    set_motor_direction("backward")
    print("Direction set to backward")
    time.sleep(5)
    set_motor_direction("left")
    print("Direction set to left")
    time.sleep(5)
    set_motor_direction("right")
    print("Direction set to right")
    time.sleep(5)
    set_motor_direction("stop")
    print("Direction set to stop")
    relay_off()
    print("Speed controller off")
    GPIO.cleanup()

test_motor_controller()
