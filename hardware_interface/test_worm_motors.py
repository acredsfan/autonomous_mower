#Script to test Worm Motors

#IMPORTS
import worm_motors
import relay_controller
import time

#CONSTANTS
SPEED = 100

#VARIABLES
worm_motors = None

# Turn on relay controller
#relay_controller.init_relay_controller()
relay_controller.set_speed_controller(on)

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

# Turn off relay controller
relay_controller.set_speed_controller(off)
relay_controller.clean_up()
