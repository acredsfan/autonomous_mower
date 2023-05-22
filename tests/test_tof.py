import sys
import time
sys.path.append('/home/pi/autonomous_mower')
from hardware_interface.sensor_interface import SensorInterface

sensor_interface_instance = SensorInterface()
sensor_interface_instance.init_sensors()

try:
    while True:
        print("tof_left: ", sensor_interface_instance.read_vl53l0x_left())
        print("tof_right: ", sensor_interface_instance.read_vl53l0x_right())

        time.sleep(0.1)

except KeyboardInterrupt:
    sys.exit()