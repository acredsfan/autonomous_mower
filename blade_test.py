from hardware_interface.blade_controller import BladeController
import time

# Initialize blade controller instance
blade_controller = BladeController()

# Turn on the blades at 50% speed
blade_controller.set_speed(50)
time.sleep(5)

# Stop the blades
blade_controller.stop()
time.sleep(2)

# Turn on the blades at 75% speed
blade_controller.set_speed(75)
time.sleep(5)

# Stop the blades
blade_controller.stop()
time.sleep(2)

# Turn on the blades at 100% speed
blade_controller.set_speed(100)
time.sleep(5)

# Stop the blades
blade_controller.stop()
