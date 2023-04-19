#python code to control two 12V worm gear motors using a L298N motor driver and one 775 motor connected to a 12V 2 channel relay module.  The worm gear motors control the wheels
#and the 775 motor controls the mower blades.  Running on Raspberry Pi 4B 2GB RAM with Raspbian Bullseye OS.

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

#FUNCTIONS

#init_motor_controller
#initializes the motor controller
def init_motor_controller():
    GPIO.setup(LEFT_PWMI_PIN, GPIO.OUT)
    GPIO.setup(LEFT_IN1_PIN, GPIO.OUT)
    GPIO.setup(LEFT_IN2_PIN, GPIO.OUT)
    GPIO.setup(RIGHT_PWMI_PIN, GPIO.OUT)
    GPIO.setup(RIGHT_IN3_PIN, GPIO.OUT)
    GPIO.setup(RIGHT_IN4_PIN, GPIO.OUT)

    global left_motor
    global right_motor
    left_motor = GPIO.PWM(LEFT_PWMI_PIN, 100)
    right_motor = GPIO.PWM(RIGHT_PWMI_PIN, 100)

    left_motor.start(0)
    right_motor.start(0)


#set_motor_speed
#sets the speed of the motor
def set_motor_speed(left_speed, right_speed):
    left_motor.ChangeDutyCycle(left_speed)
    right_motor.ChangeDutyCycle(right_speed)

#set_motor_direction
#sets the direction of the motor
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
    else:
        print("Invalid direction. Please use 'forward', 'backward', 'left', or 'right'.")

#stop_motors
#stops the motors
def stop_motors():
    set_motor_speed(0)
    GPIO.output(LEFT_IN1_PIN, GPIO.LOW)
    GPIO.output(LEFT_IN2_PIN, GPIO.LOW)
    GPIO.output(RIGHT_IN3_PIN, GPIO.LOW)
    GPIO.output(RIGHT_IN4_PIN, GPIO.LOW)

def cleanup():
    left_motor.stop()
    right_motor.stop()
    GPIO.cleanup()