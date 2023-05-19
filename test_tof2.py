import time
import VL53L0X

# Create a VL53L0X object for device on TCA9548A bus 4
vl53l0x_right = VL53L0X.VL53L0X(tca9548a_num=4, tca9548a_addr=0x70)
# Create a VL53L0X object for device on TCA9548A bus 5
vl53l0x_left = VL53L0X.VL53L0X(tca9548a_num=5, tca9548a_addr=0x70)
vl53l0x_right.open()
vl53l0x_left.open()

# Start ranging on TCA9548A bus 1
vl53l0x_right.start_ranging(VL53L0X.Vl53l0xAccuracyMode.BETTER)
# Start ranging on TCA9548A bus 2
vl53l0x_left.start_ranging(VL53L0X.Vl53l0xAccuracyMode.BETTER)

timing = vl53l0x_right.get_timing()
if timing < 20000:
    timing = 20000
print("Timing %d ms" % (timing/1000))

for count in range(1, 101):
    # Get distance from VL53L0X  on TCA9548A bus 1
    distance_right_mm = vl53l0x_right.get_distance()
    # convert distance to inches and print
    if distance_right_mm > 0:
        distance_right_inch = distance_right_mm * 0.0393701
        print("Right ToF Distance = %.1f inches" % distance_right_inch)

    # Get distance from VL53L0X  on TCA9548A bus 2
    distance_left_mm = vl53l0x_left.get_distance()
    # convert distance to inches and print
    if distance_left_mm > 0:
        distance_left_inch = distance_left_mm * 0.0393701
        print("Left ToF Distance = %.1f inches" % distance_left_inch)

    time.sleep(timing/1000000.00)

vl53l0x_right.stop_ranging()
vl53l0x_left.stop_ranging()

vl53l0x_right.close()
vl53l0x_left.close()
