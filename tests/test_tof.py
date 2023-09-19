import time
import board
import adafruit_vl53l0x as VL53L0X
import adafruit_tca9548a

# Create I2C bus as normal
i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller

# Create the TCA9548A object and give it the I2C bus
tca = adafruit_tca9548a.TCA9548A(i2c)

# For each sensor, create it using the TCA9548A channel instead of the I2C object
tof_right = VL53L0X.VL53L0X(tca[6])
tof_left = VL53L0X.VL53L0X(tca[7])

# After initial setup, can just use sensors as normal.
try:
    while True:
        print(tof_right.range, tof_left.range)
        time.sleep(0.1)
except KeyboardInterrupt:
    print("Done!")