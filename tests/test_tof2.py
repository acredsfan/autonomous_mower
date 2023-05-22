import VL53L0X
import time

vl53l0x_right = VL53L0X.VL53L0X(tca9548a_num=0, tca9548a_addr=0x70)
#vl53l0x_left = VL53L0X.VL53L0X(tca9548a_num=1, tca9548a_addr=0x70)

vl53l0x_right.start_ranging(VL53L0X.Vl53l0xAccuracyMode.BETTER)
#vl53l0x_left.start_ranging(VL53L0X.Vl53l0xAccuracyMode.BETTER)

timing = vl53l0x_right.get_timing()
if timing < 20000:
    timing = 20000
print("Timing %d ms" % (timing/1000))

for count in range(1, 101):
    # Get distance from VL53L0X  on TCA9548A bus 0
    distance = vl53l0x_right.get_distance()
    if distance > 0:
        print("2: %d mm, %d cm, %d" % (distance, (distance/10), count))

    # Get distance from VL53L0X  on TCA9548A bus 1
    # distance = vl53l0x_left.get_distance()
    # if distance > 0:
    #     print("1: %d mm, %d cm, %d" % (distance, (distance/10), count))

    time.sleep(timing/1000000.00)

vl53l0x_right.stop_ranging()
#vl53l0x_left.stop_ranging()

vl53l0x_right.close()
#vl53l0x_left.close()