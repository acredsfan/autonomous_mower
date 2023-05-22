import sys
sys.path.append('/home/pi/autonomous_mower')
from hardware_interface import sensor_interface

try:
    while True:
        print("tof_left: ", sensor_interface.read_vl53l0x_left())
        print("tof_right: ", sensor_interface.read_VL53l0X_right())

        time.sleep(0.1)

except KeyboardInterrupt:
    sys.exit()