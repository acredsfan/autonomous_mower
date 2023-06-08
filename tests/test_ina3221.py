# from smbus2 import SMBus, i2c_msg
# from barbudor_ina3221.lite import INA3221
# import time
# import busio
# import board
# import sys

# # Define the I2C bus
# bus = SMBus(1)

# # Define the I2C address of the TCA9548A I2C multiplexer
# TCA9548A_I2C_ADDR = 0x70

# # Function to switch the I2C channel
# def tca_select(channel):
#     if channel > 7:
#         return
#     bus.write_byte(TCA9548A_I2C_ADDR, 1<<channel)

# # Select the I2C channel
# tca_select(2)

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

import smbus

# Setup constants
DEVICE_BUS = 1  # the bus the devices are connected to
DEVICE_ADDR = 0x70  # the address of your TCA9548A
CHANNEL = 2  # the channel your INA3221 is on

# Create a bus object
bus = smbus.SMBus(DEVICE_BUS)

# Function to switch the multiplexer to the desired channel
def tca_select(channel):
    if 0 <= channel <= 7:
        bus.write_byte_data(DEVICE_ADDR, 0, 1 << channel)
    else:
        raise ValueError('Multiplexer channel out of range (0-7)')

# Switch to the INA3221 channel
tca_select(CHANNEL)

import time

# INA3221 I2C address
INA_ADDR = 0x40

# INA3221 Registers
INA3221_REG_MANUFACTURER_ID = 0xFE
INA3221_REG_BUSVOLT_1 = 0x02  # Channel 1 Bus Voltage
INA3221_REG_SHUNTVOLT_1 = 0x01  # Channel 1 Shunt Voltage
INA3221_REG_BUSVOLT_3 = 0x08  # Channel 3 Bus Voltage
INA3221_REG_SHUNTVOLT_3 = 0x07  # Channel 3 Shunt Voltage

# Constants for voltage-based SoC estimation
BATTERY_FULL_VOLTAGE = 12.7 * 1e3  # mV
BATTERY_EMPTY_VOLTAGE = 11.9 * 1e3  # mV

# Function to read a 16-bit register
def read_register(register):
    data = bus.read_i2c_block_data(INA_ADDR, register, 2)
    return (data[0] << 8) + data[1]

# Function to convert shunt voltage to current (assuming 0.1 ohm shunt resistor)
def shunt_to_current(shunt_v):
    return shunt_v / 0.1

def estimate_soc(voltage):
    if voltage >= BATTERY_FULL_VOLTAGE:
        return 100.0
    elif voltage <= BATTERY_EMPTY_VOLTAGE:
        return 0.0
    else:
        return ((voltage - BATTERY_EMPTY_VOLTAGE) /
                (BATTERY_FULL_VOLTAGE - BATTERY_EMPTY_VOLTAGE)) * 100.0

# Read the manufacturer id (should be 0x5449)
print("Manufacturer ID: ", hex(read_register(INA3221_REG_MANUFACTURER_ID)))

while True:
    # Read bus voltage (mV)
    bus_volt_1 = read_register(INA3221_REG_BUSVOLT_1)
    bus_volt_3 = read_register(INA3221_REG_BUSVOLT_3)

    # Read shunt voltage (uV), convert to current (mA)
    shunt_volt_1 = read_register(INA3221_REG_SHUNTVOLT_1) * 40
    current_1 = shunt_to_current(shunt_volt_1 / 1e6)

    shunt_volt_3 = read_register(INA3221_REG_SHUNTVOLT_3) * 40
    current_3 = shunt_to_current(shunt_volt_3 / 1e6)

    soc = estimate_soc(bus_volt_3)

    print("Solar Panel: Voltage = {} mV, Current = {} mA".format(bus_volt_1, current_1))
    print("Battery: Voltage = {} mV, Current = {} mA".format(bus_volt_3, current_3))
    print("Battery SoC: {:.1f}%".format(soc))

    time.sleep(1)