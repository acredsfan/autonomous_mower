from smbus2 import SMBus, i2c_msg
from barbudor_ina3221.lite import INA3221
import time
import busio
import board

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
tca_select(2)

# Create an I2C object
i2c = busio.I2C(board.SCL, board.SDA)

# Create an INA3221 object
ina = INA3221(i2c)

ina.enable_channel(1)
#ina.enable_channel(2)
ina.enable_channel(3)

# Infinite loop
while True:
    # Print the voltage from each channel
    print("Solar Panel Voltage: ", ina.bus_voltage(1))
    print("SLA Battery Voltage: ", ina.bus_voltage(3))

    # Sleep for 0.1 seconds
    time.sleep(0.1)
