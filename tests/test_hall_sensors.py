import time
sys.path.append('/home/pi/autonomous_mower')
from hardware_interface.sensor_interface import SensorInterface

def test_hall_sensors():
    # Initialize SensorInterface
    si = SensorInterface()
    
    # Initialize the hall effect sensors
    si.init_hall_effect_sensors()
    
    while True:
        # Read the hall effect sensors
        sensor_1_state, sensor_2_state = si.read_hall_effect_sensors()
        
        # Print the states of the hall effect sensors
        print("Hall Effect Sensor 1 State: ", sensor_1_state)
        print("Hall Effect Sensor 2 State: ", sensor_2_state)
        
        # Wait for a bit before reading the sensors again
        time.sleep(1)

if __name__ == "__main__":
    test_hall_sensors()