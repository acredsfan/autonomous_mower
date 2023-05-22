from smbus2 import SMBus, i2c_msg
import busio
import board
from adafruit_bme280 import basic as adafruit_bme280

# Define the I2C bus
bus = SMBus(1)

# Define the I2C address of the TCA9548A I2C multiplexer
TCA9548A_I2C_ADDR = 0x70

# Function to switch the I2C channel
def tca_select(channel):
    if channel > 7:
        return
    bus.write_byte(TCA9548A_I2C_ADDR, 1<<channel)

# Select the I2C channel
tca_select(3)

# Now create BME280 object as usual
i2c = busio.I2C(board.SCL, board.SDA)
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)

# Now you can interact with your BME280 as usual
print("\nTemperature: %0.1f C" % bme280.temperature)
print("Humidity: %0.1f %%" % bme280.humidity)
print("Pressure: %0.1f hPa" % bme280.pressure)