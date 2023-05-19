import sys
import time
import adafruit_vl53l0x
import busio
import board

print("Imports successful, initializing VL53L0X sensors")
vl53l0x_left = adafruit_vl53l0x.VL53L0X(i2c=busio.I2C(board.SCL, board.SDA), address=0x29)
print("Left sensor initialized successfully with address 0x29")
vl53l0x_right = adafruit_vl53l0x.VL53L0X(i2c=busio.I2C(board.SCL, board.SDA), address=0x2a)
print("Right sensor initialized successfully with address 0x2a")

print("Starting test")

try:
    while True:
        # Reading from the left sensor
        startRange() # Start a range operation for the left sensor
        while not sensor_interface.isRangeComplete(): # Wait for the range operation to complete
            time.sleep(0.01) # Sleep for 10ms
        
        if readRangeStatus() != 0: # Check if there was an error in the range operation
            print("Error reading from the left sensor")
            break

        print("tof_left: ", readRangeResult()) # Print the range result for the left sensor

        # Reading from the right sensor
        startRange() # Start a range operation for the right sensor
        while not isRangeComplete(): # Wait for the range operation to complete
            time.sleep(0.01) # Sleep for 10ms

        if readRangeStatus() != 0: # Check if there was an error in the range operation
            print("Error reading from the right sensor")
            break

        print("tof_right: ", readRangeResult()) # Print the range result for the right sensor

        time.sleep(0.1)

except KeyboardInterrupt:
    sys.exit()