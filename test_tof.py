import time
import board
import busio
import adafruit_vl53l0x
import RPi.GPIO as GPIO

# Set up I2C bus
i2c_bus = busio.I2C(board.SCL, board.SDA)

# Set the GPIO pin numbers connected to the multiplexer channel select pins
mux_address_pins = [4, 5, 6]  # GPIO pins connected to A0, A1, A2 address pins of the multiplexer

# Set up the GPIO pins
if not GPIO.getmode():
    GPIO.setmode(GPIO.BCM)
GPIO.setup(mux_address_pins, GPIO.OUT)

# Function to select the desired channel on the I2C multiplexer
def select_mux_channel(channel):
    # Convert the channel number to binary and set the address pins accordingly
    binary_channel = bin(channel)[2:].zfill(len(mux_address_pins))
    GPIO.output(mux_address_pins, list(map(int, binary_channel)))

# Reset the multiplexer to select the default channel (0)
select_mux_channel(0)

# Create a function to initialize the VL53L0X sensor
def initialize_sensor(i2c, address):
    # Reset and initialize the sensor
    sensor = adafruit_vl53l0x.VL53L0X(i2c=i2c)
    sensor.set_address(address)
    return sensor

# Initialize the right sensor (address 0x29)
select_mux_channel(0)  # Select the multiplexer channel for the right sensor
tof_right = initialize_sensor(i2c_bus, 0x29)

# Initialize the left sensor (address 0x2A)
select_mux_channel(1)  # Select the multiplexer channel for the left sensor
tof_left = initialize_sensor(i2c_bus, 0x2A)

# Start continuous mode for both sensors
tof_right.start_continuous()
tof_left.start_continuous()

# Read distance from right sensor
distance_right = tof_right.range
print("Distance right:", distance_right)

# Read distance from left sensor
distance_left = tof_left.range
print("Distance left:", distance_left)

# Stop the continuous mode for both sensors
tof_right.stop_continuous()
tof_left.stop_continuous()
