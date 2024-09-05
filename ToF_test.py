import board
import busio
from adafruit_vl53l0x import VL53L0X
import time

# Create the I2C bus
i2c = busio.I2C(board.SCL, board.SDA)

# Initialize the first sensor at address 0x29
try:
    print("Initializing sensor at 0x29...")
    sensor1 = VL53L0X(i2c, address=0x29)
    print("Sensor 1 initialized at 0x29.")
except Exception as e:
    print(f"Failed to initialize sensor at 0x29: {e}")

# Initialize the second sensor at address 0x30
try:
    print("Initializing sensor at 0x30...")
    sensor2 = VL53L0X(i2c, address=0x30)
    print("Sensor 2 initialized at 0x30.")
except Exception as e:
    print(f"Failed to initialize sensor at 0x30: {e}")

# Test reading distance measurements from both sensors
try:
    while True:
        distance1 = sensor1.range
        print(f"Sensor 1 (0x29) Distance: {distance1} mm")
        
        distance2 = sensor2.range
        print(f"Sensor 2 (0x30) Distance: {distance2} mm")

        time.sleep(1)  # Delay between readings
except KeyboardInterrupt:
    print("Test interrupted by user.")
except Exception as e:
    print(f"Error reading sensor distances: {e}")