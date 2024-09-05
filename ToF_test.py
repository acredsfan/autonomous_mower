import board
import busio
import digitalio
from adafruit_vl53l0x import VL53L0X
import time

# Create I2C bus
i2c = busio.I2C(board.SCL, board.SDA)

# Define GPIO pins connected to the XSHUT pins of each VL53L0X sensor
XSHUT_1 = digitalio.DigitalInOut(board.D22)  # Adjust GPIO pin as needed
XSHUT_2 = digitalio.DigitalInOut(board.D23)  # Adjust GPIO pin as needed

# Configure the XSHUT pins as outputs
XSHUT_1.direction = digitalio.Direction.OUTPUT
XSHUT_2.direction = digitalio.Direction.OUTPUT

def reset_sensor(xshut_pin):
    """
    Resets a VL53L0X sensor by toggling its XSHUT pin.
    
    :param xshut_pin: DigitalInOut object connected to the sensor's XSHUT pin
    """
    xshut_pin.value = False  # Pull XSHUT low to turn off the sensor
    time.sleep(0.1)  # Ensure the sensor is fully powered down
    xshut_pin.value = True   # Pull XSHUT high to power the sensor back up
    time.sleep(0.1)  # Wait for the sensor to initialize

def initialize_sensor(xshut_pin, new_address):
    """
    Initializes a VL53L0X sensor connected to the specified XSHUT pin and sets a new I2C address.
    
    :param xshut_pin: DigitalInOut object connected to the sensor's XSHUT pin
    :param new_address: The new I2C address to assign to the sensor
    :return: Initialized sensor object with the new address
    """
    reset_sensor(xshut_pin)  # Reset the sensor to ensure it starts at 0x29
    sensor = VL53L0X(i2c)    # Initialize the sensor at the default address 0x29
    sensor.set_address(new_address)  # Set a new address
    print(f"Sensor initialized at new address: {hex(new_address)}")
    return sensor

# Step 1: Reset both sensors
XSHUT_1.value = False
XSHUT_2.value = False
time.sleep(0.1)  # Ensure sensors are powered down

# Step 2: Initialize and set addresses
sensor1 = initialize_sensor(XSHUT_1, 0x30)  # First sensor to 0x30
sensor2 = initialize_sensor(XSHUT_2, 0x31)  # Second sensor to 0x31

# Optional: Verify sensors by reading their distances
try:
    distance1 = sensor1.range
    print(f"Sensor 1 (0x30) Distance: {distance1} mm")

    distance2 = sensor2.range
    print(f"Sensor 2 (0x31) Distance: {distance2} mm")
except Exception as e:
    print(f"Error reading sensor distances: {e}")

