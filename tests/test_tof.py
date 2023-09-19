import time
import board
import busio
import adafruit_tca9548a
import adafruit_vl53l0x

# Initialize I2C bus and sensor.
i2c = busio.I2C(board.SCL, board.SDA)

# Initialize the TCA9548A multiplexer
tca = adafruit_tca9548a.TCA9548A(i2c)

# Initialize the VL53L0X sensors
vl53_left = adafruit_vl53l0x.VL53L0X(tca[6])
vl53_right = adafruit_vl53l0x.VL53L0X(tca[7])

vl53_left.range
vl53_right.range

try:
    while True:
        # Perform ranging test
        print(f"Left sensor distance: {vl53_left.range}mm")
        print(f"Right sensor distance: {vl53_right.range}mm")
        time.sleep(1)



except KeyboardInterrupt:
    # Code will reach here when a keyboard interrupt (Ctrl+C) is detected
    print("Program stopped by the user")
    # Disable sensors or any other cleanup code
    disable_sensor(shutdown_pins[0])
    disable_sensor(shutdown_pins[1])