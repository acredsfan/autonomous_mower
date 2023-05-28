#Script to test Worm Motors

#IMPORTS
import worm_motors
import relay_controller
import time

#CONSTANTS
SPEED = 100

# Turn on relay controller
#relay_controller.RelayController.init()
#relay_controller.RelayController.set_speed_controller("on")

# Test worm motors
print("Testing worm motors...")
worm_motors.MotorController.move_mower("forward", SPEED)
print("moving forward")
time.sleep(2)
worm_motors.MotorController.move_mower("backward", SPEED)
print("moving backward")
time.sleep(2)
worm_motors.MotorController.move_mower("left", SPEED)
print("moving left")
time.sleep(2)
worm_motors.MotorController.move_mower("right", SPEED)
print("moving right")
time.sleep(2)
worm_motors.MotorController.stop_motors()
print("Worm motors off")

# Clean up worm motors
worm_motors.MotorController.cleanup()

# Turn off relay controller
#relay_controller.RelayController.set_speed_controller("off")
#relay_controller.RelayController.clean_up()