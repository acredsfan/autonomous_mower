#Test to ensure that the sensor readings are being read and reported correctly
from hardware_interface import SensorInterface
import time

def test_sensor_readings():
    sensor_interface = SensorInterface()
    time.sleep(5)
    sensor_data = sensor_interface.sensor_data
    assert 'bme280' in sensor_data
    assert 'accel' in sensor_data
    assert 'solar' in sensor_data
    assert 'battery' in sensor_data
    assert 'left_distance' in sensor_data
    assert 'right_distance' in sensor_data
    assert sensor_data['bme280'] is not None
    assert sensor_data['accel'] is not None
    assert sensor_data['solar'] is not None
    assert sensor_data['battery'] is not None
    assert sensor_data['left_distance'] is not None
    assert sensor_data['right_distance'] is not None
    print("Sensor readings are being read and reported correctly")
    print("BME280: ", sensor_data['bme280'])
    print("Accelerometer: ", sensor_data['accel'])
    print("Solar: ", sensor_data['solar'])
    print("Battery: ", sensor_data['battery'])
    print("Left Distance: ", sensor_data['left_distance'])
    print("Right Distance: ", sensor_data['right_distance'])

if __name__ == '__main__':
    test_sensor_readings()
# Compare this snippet from tests/test_sensor_readings.py: