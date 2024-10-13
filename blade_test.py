from hardware_interface.blade_controller import BladeController

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
