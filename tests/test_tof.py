import time
import board
import busio
import adafruit_tca9548a
import adafruit_vl53l0x
import digitalio

# Initialize I2C bus and sensor.
i2c = busio.I2C(board.SCL, board.SDA)

# Initialize TCA9548A multiplexer
tca = adafruit_tca9548a.TCA9548A(i2c, address=0x70)

# Shutdown pins
shutdown_pins = [22, 23]

# Function to reset sensors
def reset_sensors():
    for pin_num in shutdown_pins:
        pin = digitalio.DigitalInOut(getattr(board, f"D{pin_num}"))
        pin.direction = digitalio.Direction.OUTPUT
        pin.value = False
    time.sleep(0.01)
    for pin_num in shutdown_pins:
        pin = digitalio.DigitalInOut(getattr(board, f"D{pin_num}"))
        pin.direction = digitalio.Direction.OUTPUT
        pin.value = True
    time.sleep(0.01)

# Reset sensors
reset_sensors()

# Initialize VL53L0X sensors
vl53_left = adafruit_vl53l0x.VL53L0X(tca[6])
vl53_right = adafruit_vl53l0x.VL53L0X(tca[7])

try:
    while True:
    # Read the range from the left sensor
        left_range = vl53_left.range
        print(f"Left sensor range: {left_range}mm")

        # Read the range from the right sensor
        right_range = vl53_right.range
        print(f"Right sensor range: {right_range}mm")

        time.sleep(1.0)
except KeyboardInterrupt:
    pass
finally:
    # Reset sensors
    reset_sensors()

