import board
import busio
from adafruit_vl53l0x import VL53L0X

# Create I2C bus
i2c = busio.I2C(board.SCL, board.SDA)

def set_sensor_address(sensor, new_address):
    """
    Changes the I2C address of the VL53L0X sensor.
    """
    sensor.set_address(new_address)
    print(f"Sensor address set to: {hex(new_address)}")

try:
    # Step 1: Initialize the first sensor at the default address 0x29
    print("Initializing first sensor at address 0x29...")
    sensor1 = VL53L0X(i2c)
    set_sensor_address(sensor1, 0x30)  # Change to 0x30 to free up 0x29 for the next sensor

    # Step 2: Power up and initialize the second sensor at 0x29 now that the first one has moved
    print("Initializing second sensor at address 0x29...")
    sensor2 = VL53L0X(i2c)  # This should now initialize at 0x29 since 0x30 is taken
    set_sensor_address(sensor2, 0x31)  # Change to 0x31 or any other unique address

    # Both sensors should now be initialized with unique addresses
    print("Both sensors initialized successfully.")
except Exception as e:
    print(f"Error initializing sensors: {e}")

# Optional: Check if the sensors respond correctly
try:
    distance1 = sensor1.range
    print(f"Sensor 1 (0x30) Distance: {distance1} mm")

    distance2 = sensor2.range
    print(f"Sensor 2 (0x31) Distance: {distance2} mm")
except Exception as e:
    print(f"Error reading sensor distances: {e}")