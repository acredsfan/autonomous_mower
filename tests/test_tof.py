import sys
import time
sys.path.append('/home/pi/autonomous_mower')
from hardware_interface.sensor_interface import SensorInterface

def main():
    # Initialize the sensor interface
    sensor_interface = SensorInterface()

    # Initialize sensors
    sensor_interface.init_sensors()

    while True:
        # Read the distance from the left TOF sensor
        left_distance = sensor_interface.read_vl53l0x_left()
        print('Left Distance: ', left_distance)

        # Read the distance from the right TOF sensor
        right_distance = sensor_interface.read_vl53l0x_right()
        print('Right Distance: ', right_distance)

        # Wait for a second before next reading
        time.sleep(1)

if __name__ == '__main__':
    main()