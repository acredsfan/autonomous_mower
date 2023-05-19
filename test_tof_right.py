import time
import board
import busio
import adafruit_vl53l0x
import RPi.GPIO as GPIO

# Set up I2C bus
i2c = busio.I2C(board.SCL, board.SDA)

# Set the GPIO pin number connected to the right sensor's XSHUT pin
left_xshut_pin = 22
right_xshut_pin = 23

# Set up the GPIO pin
if not GPIO.getmode():
    GPIO.setmode(GPIO.BCM)
GPIO.setup(right_xshut_pin, GPIO.OUT)
GPIO.setup(left_xshut_pin, GPIO.OUT)

# Reset and initialize the right sensor
GPIO.output(right_xshut_pin, GPIO.LOW)
time.sleep(0.1)
tof_right = adafruit_vl53l0x.VL53L0X(i2c=i2c)
tof_right.set_address(0x29)  # Set the I2C address of the right sensor

# Reset and initialize the left sensor
GPIO.output(right_xshut_pin, GPIO.LOW)
time.sleep(0.1)
tof_left = adafruit_vl53l0x.VL53L0X(i2c=i2c)
tof_left.set_address(0x2a)  # Set the I2C address of the right sensor

# Enable the right sensor
GPIO.output(right_xshut_pin, GPIO.HIGH)
time.sleep(0.1)

# Enable the left sensor
GPIO.output(left_xshut_pin, GPIO.HIGH)
time.sleep(0.1)

# Start continuous mode
tof_right.start_continuous()
tof_left.start_continuous()

def read_right_tof():
    # Wait until data is ready for the right sensor
    while not tof_right.data_ready:
        print("Right sensor data not ready")
        time.sleep(0.01)  # Wait for 10 ms

    # Read distance data from right sensor
    tof_right_measurement = tof_right.range
    distance_right = tof_right_measurement if tof_right_measurement > 0 else 65535

    # Print distance data
    print("Distance right:", distance_right)

    return distance_right

def read_left_tof():
    #Wait until data is ready for the left sensor
    while not tof_left.data_ready:
        print("Left sensor data not ready")
        time.sleep(0.01)  # Wait for 10 ms

    # Read distance data from left sensor
    tof_left_measurement = tof_left.range
    distance_left = tof_left_measurement if tof_left_measurement > 0 else 65535

    # Print distance data
    print("Distance left:", distance_left)

    return distance_left

distance = read_right_tof()  # Call the function without any arguments
print("Distance right:", distance)  # Print the right distance
distance = read_left_tof()  # Call the function without any arguments
print("Distance left:", distance)  # Print the left distance

# Stop the continuous mode when done
tof_right.stop_continuous()
tof_left.stop_continuous()
