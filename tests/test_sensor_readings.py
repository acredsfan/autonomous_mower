# Test to ensure that the sensor readings are being read and reported correctly
# import SensorInterface from hardware_interface folder
import time
from hardware_interface import SensorInterface


def test_sensor_readings():
    sensor_interface = SensorInterface()
    time.sleep(5)
    sensor_data = sensor_interface.sensor_data
    assert 'bme280' in sensor_data
    assert 'accel' in sensor_data
    assert 'compass' in sensor_data
    assert 'gyro' in sensor_data
    assert 'quaternion' in sensor_data
    assert 'speed' in sensor_data
    assert 'heading' in sensor_data
    assert 'pitch' in sensor_data
    assert 'solar' in sensor_data
    assert 'battery' in sensor_data
    assert 'battery_charge' in sensor_data
    assert 'left_distance' in sensor_data
    assert 'right_distance' in sensor_data
    assert sensor_data['bme280'] is not None
    assert sensor_data['accel'] is not None
    assert sensor_data['compass'] is not None
    assert sensor_data['gyro'] is not None
    assert sensor_data['quaternion'] is not None
    assert sensor_data['speed'] is not None
    assert sensor_data['heading'] is not None
    assert sensor_data['pitch'] is not None
    assert sensor_data['solar'] is not None
    assert sensor_data['battery'] is not None
    assert sensor_data['battery_charge'] is not None
    assert sensor_data['left_distance'] is not None
    assert sensor_data['right_distance'] is not None
    print("Sensor readings are being read and reported correctly")
    print("BME280: ", sensor_data['bme280'])
    print("Accelerometer: ", sensor_data['accel'])
    print("Compass: ", sensor_data['compass'])
    print("Gyroscope: ", sensor_data['gyro'])
    print("Quaternion: ", sensor_data['quaternion'])
    print("Speed: ", sensor_data['speed'])
    print("Heading: ", sensor_data['heading'])
    print("Pitch: ", sensor_data['pitch'])
    print("Solar: ", sensor_data['solar'])
    print("Battery: ", sensor_data['battery'])
    print("Battery Charge: ", sensor_data['battery_charge'])
    print("Left Distance: ", sensor_data['left_distance'])
    print("Right Distance: ", sensor_data['right_distance'])


if __name__ == '__main__':
    test_sensor_readings()
# Compare this snippet from tests/test_sensor_readings.py:
