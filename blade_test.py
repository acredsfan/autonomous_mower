from hardware_interface.blade_controller import BladeController
import time
from hardware_interface.gpio_manager import GPIOManager
import time

# Test GPIO pins used for blade motor
shutdown_pins = [24, 25]
shutdown_lines, _ = GPIOManager.init_gpio(shutdown_pins, [])

print("Turning on pin 24")
shutdown_lines[0].set_value(1)  # Set pin 24 to HIGH
time.sleep(5)

print("Turning off pin 24")
shutdown_lines[0].set_value(0)  # Set pin 24 to LOW
time.sleep(2)

print("Turning on pin 25")
shutdown_lines[1].set_value(1)  # Set pin 25 to HIGH
time.sleep(5)

print("Turning off pin 25")
shutdown_lines[1].set_value(0)  # Set pin 25 to LOW

print("GPIO test complete")

# Initialize blade controller instance
blade_controller = BladeController()

# Turn on the blades at 50% speed
blade_controller.set_speed(50)
print("Blades running at 50% speed")
time.sleep(5)

# Stop the blades
blade_controller.stop()
print("Blades stopped")
time.sleep(2)

# Turn on the blades at 75% speed
blade_controller.set_speed(75)
print("Blades running at 75% speed")
time.sleep(5)

# Stop the blades
blade_controller.stop()
print("Blades stopped")
time.sleep(2)

# Turn on the blades at 100% speed
blade_controller.set_speed(100)
print("Blades running at 100% speed")
time.sleep(5)

# Stop the blades
blade_controller.stop()
print("Blades stopped, test complete")
