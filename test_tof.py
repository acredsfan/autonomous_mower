print("Starting ToF sensor thread")

import time
print("time imported")
import board
print("board imported")
import busio
print("busio imported")
import adafruit_vl53l0x
print("adafruit_vl53l0x imported")
import RPi.GPIO as GPIO
print("RPi.GPIO imported")

print("Setting up I2C bus")
# Set up I2C bus
i2c = busio.I2C(board.SCL, board.SDA)

# Set the GPIO pin numbers connected to the XSHUT pins of the left and right sensors
print("Setting up GPIO pins")
left_xshut_pin = 22  # GPIO pin connected to the left sensor's XSHUT pin
right_xshut_pin = 23  # GPIO pin connected to the right sensor's XSHUT pin

print("Setting up GPIO pins")

# Set up the GPIO pins
if not GPIO.getmode():
    GPIO.setmode(GPIO.BCM)
GPIO.setup(left_xshut_pin, GPIO.OUT)
GPIO.setup(right_xshut_pin, GPIO.OUT)

print("Resetting Left Sensor")
# Reset the left sensor
GPIO.output(left_xshut_pin, GPIO.LOW)
GPIO.output(right_xshut_pin, GPIO.HIGH)
time.sleep(0.1)

print("Initializing left sensor")
# Initialize the left sensor
tof_left = adafruit_vl53l0x.VL53L0X(i2c=i2c)
tof_left.set_address(0x29)  # Set the I2C address of the left sensor

print("Resetting right sensor and initializing")
# Reset and initialize the right sensor
GPIO.output(left_xshut_pin, GPIO.HIGH)
GPIO.output(right_xshut_pin, GPIO.LOW)
time.sleep(0.1)
tof_right = adafruit_vl53l0x.VL53L0X(i2c=i2c)
tof_right.set_address(0x2A)  # Set the I2C address of the right sensor

print("Enabling both sensors")
# Enable both sensors
GPIO.output(right_xshut_pin, GPIO.HIGH)
time.sleep(0.1)

print("ToF sensors set up")
print("Starting continuous mode for both sensors")
tof_left.start_continuous()
tof_right.start_continuous()

print("Reading ToF sensors")
def read_tof():
    # Wait until data is ready for the left sensor
    while not tof_left.data_ready:
        time.sleep(0.01)  # Wait for 10 ms

    # Read distance data from left sensor
    tof_left_measurement = tof_left.range
    distance_left = tof_left_measurement if tof_left_measurement > 0 else 65535

    # Wait until data is ready for the right sensor
    while not tof_right.data_ready:
        time.sleep(0.01)  # Wait for 10 ms

    # Read distance data from right sensor
    tof_right_measurement = tof_right.range
    distance_right = tof_right_measurement if tof_right_measurement > 0 else 65535

    # Print distance data
    print("Distance left:", distance_left)
    print("Distance right:", distance_right)

    return distance_left, distance_right

distances = read_tof()  # Call the function without any arguments
print("Distance left:", distances[0])  # Print the left distance
print("Distance right:", distances[1])  # Print the right distance

# Stop the continuous mode when done
tof_left.stop_continuous()
tof_right.stop_continuous()