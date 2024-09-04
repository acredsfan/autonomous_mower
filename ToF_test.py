import board
import busio
from adafruit_vl53l0x import VL53L0X

# Create I2C bus
i2c = busio.I2C(board.SCL, board.SDA)

# List of new addresses for the sensors
# Ensure addresses are unique and do not conflict with other I2C devices
NEW_ADDRESSES = [0x31, 0x32, 0x33, 0x34]

def initialize_sensor(i2c, new_address):
    """
    Initializes a VL53L0X sensor and assigns it a new I2C address.
    
    :param i2c: I2C bus object
    :param new_address: The new I2C address to assign to the sensor
    :return: Initialized sensor object
    """
    # Initialize the sensor with the default address
    sensor = VL53L0X(i2c)
    
    # Assign new I2C address
    sensor.set_address(new_address)
    print(f"Sensor initialized at new address: {hex(new_address)}")
    return sensor

# Initialize sensors and assign new addresses
sensors = []
for address in NEW_ADDRESSES:
    try:
        # Initialize and assign new address
        sensor = initialize_sensor(i2c, address)
        sensors.append(sensor)
    except Exception as e:
        print(f"Failed to initialize sensor at address {hex(address)}: {e}")

# Now you can use the sensors array to interact with each sensor independently
for idx, sensor in enumerate(sensors):
    try:
        distance = sensor.range
        print(f"Sensor {idx} at address {hex(sensor.address)}: Distance = {distance} mm")
    except Exception as e:
        print(f"Error reading from sensor {idx}: {e}")
