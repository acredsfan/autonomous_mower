# Python Code to Test the TOF Sensors

# Import the Libraries
import time
import VL53L0X

# Set up I2C multiplexer
import smbus
bus = smbus.SMBus(1)
MUX_ADDRESS = 0x70  # Replace with your multiplexer's I2C address if different

# Set up the sensors
# Right sensor
right_tof=VL53L0X.VL53L0X(tca9548a_num=0, tca9548a_addr=0x70)
right_tof.open()
right_tof.start_ranging(VL53L0X.VL53L0X_BETTER_ACCURACY_MODE)

# Left sensor
left_tof=VL53L0X.VL53L0X(tca9548a_num=1, tca9548a_addr=0x70)
left_tof.open()
left_tof.start_ranging(VL53L0X.VL53L0X_BETTER_ACCURACY_MODE)

# Read the sensors
while True:
    # Select the right sensor
    bus.write_byte(MUX_ADDRESS, 1 << 3)
    right_distance = right_tof.get_distance()
    # Select the left sensor
    bus.write_byte(MUX_ADDRESS, 1 << 2)
    left_distance = left_tof.get_distance()
    # Print the distances
    print(f"Right distance: {right_distance}")
    print(f"Left distance: {left_distance}")
    # Wait for a bit before getting the next packet
    time.sleep(1)
# The output should look like this:
# Right distance: 0
# Left distance: 0