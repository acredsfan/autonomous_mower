#Script to test Worm Motors

#IMPORTS
import worm_motors
import time

#CONSTANTS
SPEED = 100

#VARIABLES
worm_motors = None

# Set up worm motors
worm_motors = worm_motors.WormMotors()

# Test worm motors
print("Testing worm motors...")
worm_motors.move_mower(forward, SPEED)
print("moving forward")
time.sleep(2)
worm_motors.move_mower(backward, SPEED)
print("moving backward")
time.sleep(2)
worm_motors.move_mower(left, SPEED)
print("moving left")
time.sleep(2)
worm_motors.move_mower(right, SPEED)
print("moving right")
time.sleep(2)
worm_motors.stop_motors()
print("Worm motors off")

# Clean up worm motors
worm_motors.cleanup()
