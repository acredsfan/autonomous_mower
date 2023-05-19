import time
import board
import busio
import adafruit_vl53l0x
import RPi.GPIO as GPIO

# Set up I2C bus
i2c = busio.I2C(board.SCL, board.SDA)

# Set the GPIO pin numbers connected to the XSHUT pins of the left and right sensors
left_xshut_pin = 22  # GPIO pin connected to the left sensor's XSHUT pin
right_xshut_pin = 23  # GPIO pin connected to the right sensor's XSHUT pin

# Set up the GPIO pins
if not GPIO.getmode():
    GPIO.setmode(GPIO.BCM)
GPIO.setup(left_xshut_pin, GPIO.OUT)
GPIO.setup(right_xshut_pin, GPIO.OUT)

def initialize_sensor(xshut_pin, i2c, address):
    print(f"Resetting and initializing sensor with address {hex(address)}...")
    # Reset and initialize the sensor
    GPIO.output(xshut_pin, GPIO.LOW)
    time.sleep(0.1)
    GPIO.output(xshut_pin, GPIO.HIGH)
    time.sleep(0.1)
    sensor = adafruit_vl53l0x.VL53L0X(i2c=i2c)
    sensor.set_address(address)
    print(f"Sensor with address {hex(address)} initialized successfully.")
    return sensor

# Initialize the right sensor (address 0x29)
tof_right = initialize_sensor(right_xshut_pin, i2c, 0x30)

# Initialize the left sensor (address 0x2A)
tof_left = initialize_sensor(left_xshut_pin, i2c, 0x31)

# Start continuous mode for both sensors
print("Starting continuous mode for both sensors...")
tof_right.start_continuous()
tof_left.start_continuous()

# Read distance from right sensor
print("Reading distance from right sensor...")
distance_right = tof_right.range
print("Distance right:", distance_right)

# Read distance from left sensor
print("Reading distance from left sensor...")
distance_left = tof_left.range
print("Distance left:", distance_left)

# Stop the continuous mode for both sensors
print("Stopping continuous mode for both sensors...")
tof_right.stop_continuous()
tof_left.stop_continuous()