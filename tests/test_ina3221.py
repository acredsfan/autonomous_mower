from smbus2 import SMBus, i2c_msg
import time

# Define the I2C bus
#bus = SMBus(1)

# Define the I2C address of the TCA9548A I2C multiplexer
TCA9548A_I2C_ADDR = 0x70

# Function to switch the I2C channel
def tca_select(channel):
    if channel > 7:
        return
    bus.write_byte(TCA9548A_I2C_ADDR, 1<<channel)

# Select the I2C channel
tca_select(2)

# # Create an I2C object
# i2c = busio.I2C(board.SCL, board.SDA)

# # Create an INA3221 object
# ina = INA3221(i2c)

# ina.enable_channel(1)
# #ina.enable_channel(2)
# ina.enable_channel(3)

# # Infinite loop
# while True:
#     # Print the voltage from each channel
#     sys.stdout.write("Solar Panel Voltage: {}\r".format(ina.bus_voltage(1)))
#     sys.stdout.flush()
#     sys.stdout.write("SLA Battery Voltage: {}\r".format(ina.bus_voltage(3)))
#     sys.stdout.flush()

#     # Sleep for 1 second
#     time.sleep(1)

# INA3221 constants
INA3221_ADDRESS = 0x40  # Default I2C address for INA3221
INA3221_BUSNO = 1       # I2C bus number on Raspberry Pi

# INA3221 register addresses
INA3221_REG_MANUFACTURER_ID = 0xFE
INA3221_REG_BUSVOLT_CH1 = 0x02
INA3221_REG_BUSVOLT_CH3 = 0x06
INA3221_REG_CURRENT_CH1 = 0x04
INA3221_REG_CURRENT_CH3 = 0x08

# Initialize I2C bus
bus = smbus2.SMBus(INA3221_BUSNO)

# Function to read 16-bit register
def read_register(reg):
    return bus.read_word_data(INA3221_ADDRESS, reg)

# Function to convert raw register value to voltage
def register_to_voltage(reg_val):
    return reg_val * 0.001  # 1 LSB = 1 mV

# Function to convert raw register value to current
def register_to_current(reg_val):
    return reg_val * 0.001  # 1 LSB = 1 mA

# Read voltage and current for channel 1 (solar panel)
solar_volt_raw = read_register(INA3221_REG_BUSVOLT_CH1)
solar_volt = register_to_voltage(solar_volt_raw)
solar_curr_raw = read_register(INA3221_REG_CURRENT_CH1)
solar_curr = register_to_current(solar_curr_raw)

# Read voltage and current for channel 3 (battery)
battery_volt_raw = read_register(INA3221_REG_BUSVOLT_CH3)
battery_volt = register_to_voltage(battery_volt_raw)
battery_curr_raw = read_register(INA3221_REG_CURRENT_CH3)
battery_curr = register_to_current(battery_curr_raw)

print("Solar panel output: %.2f V, %.2f A" % (solar_volt, solar_curr))
print("Battery charge level: %.2f V, %.2f A" % (battery_volt, battery_curr))