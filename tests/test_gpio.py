import gpiod

try:
    chip = gpiod.Chip('gpiochip0')
    print("Successfully accessed gpiochip0")
#    chip = gpiod.Chip('gpiochip1')
#    print("Successfully accessed gpiochip1")
except Exception as e:
    print(f"Error accessing gpiochip1: {e}")
