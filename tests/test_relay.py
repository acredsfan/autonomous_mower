# Code to test 12v relay

#IMPORTS
import RPi.GPIO as GPIO
import time

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

# Test speed controller
print("Testing speed controller...")
GPIO.output(SPEED_CONTROLLER_PIN, GPIO.HIGH)
print("Speed controller on")
time.sleep(5)
GPIO.output(SPEED_CONTROLLER_PIN, GPIO.LOW)
print("Speed controller off")

# Test mower blades
print("Testing mower blades...")
GPIO.output(MOWER_BLADES_PIN, GPIO.LOW)
print("Mower blades on")
time.sleep(5)
GPIO.output(MOWER_BLADES_PIN, GPIO.LOW)
print("Mower blades off")

# Clean up GPIO
GPIO.cleanup()