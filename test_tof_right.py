import time
import board
import busio
import adafruit_vl53l0x
import RPi.GPIO as GPIO

# Set up I2C bus
print("Setting up I2C bus...")
i2c = busio.I2C(board.SCL, board.SDA)

# Set the GPIO pin number connected to the sensors' XSHUT pin
left_xshut_pin = 22
right_xshut_pin = 23

# Set up the GPIO pin
print("Setting up GPIO pins...")
if not GPIO.getmode():
    GPIO.setmode(GPIO.BCM)
GPIO.setup(right_xshut_pin, GPIO.OUT)
GPIO.setup(left_xshut_pin, GPIO.OUT)

def initialize_sensor(xshut_pin, i2c, address):
    # Reset and initialize sensor
    GPIO.output(xshut_pin, GPIO.LOW)
    time.sleep(0.1)
    GPIO.output(xshut_pin, GPIO.HIGH)
    time.sleep(0.1)
    sensor = adafruit_vl53l0x.VL53L0X(i2c=i2c)
    sensor.set_address(address)
    return sensor

print("Initializing right sensor...")
tof_right = initialize_sensor(right_xshut_pin, i2c, 0x29)

print("Initializing left sensor...")
tof_left = initialize_sensor(left_xshut_pin, i2c, 0x2A)

# Start continuous mode
print("Starting continuous mode for both sensors...")
tof_right.start_continuous()
tof_left.start_continuous()

def read_tof(sensor, sensor_name):
    # Wait until data is ready for the sensor
    while not sensor.data_ready:
        print(f"{sensor_name} sensor data not ready")
        time.sleep(0.01)  # Wait for 10 ms

    # Read distance data from sensor
    tof_measurement = sensor.range
    distance = tof_measurement if tof_measurement > 0 else 65535

    # Print distance data
    print(f"Distance {sensor_name}:", distance)

    return distance

print("Reading distance from right sensor...")
distance_right = read_tof(tof_right, "right")

print("Reading distance from left sensor...")
distance_left = read_tof(tof_left, "left")

# Print the distances
print("Distance right:", distance_right)
print("Distance left:", distance_left)

# Stop the continuous mode when done
print("Stopping continuous mode for both sensors...")
tof_right.stop_continuous()
tof_left.stop_continuous()