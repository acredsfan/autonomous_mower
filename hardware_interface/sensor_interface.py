# To set up sensors for autonomous robot sensor interface for the Raspberry Pi 4 2GB RAM with Raspbian Bullseye OS.
# Sensors included are: bme280, Neo 8-M GPS, 2x VL53L0X, MPU9250 (compass, accelerometer, gyroscope), INA3221 (current sensor), and 2 hall effect sensors.

#IMPORTS
import smbus
import time
from gps import GPS
from BME280 import BME280
from VL53L0X import VL53L0X
from MPU9250 import MPU9250
from INA3221 import INA3221
import RPi.GPIO as GPIO
import serial
from gps_interface import GPSInterface

# Global variables
bus = smbus.SMBus(1)
gps_serial = None
bme280 = BME280(bus)
vl53l0x_left = VL53L0X(0x2a)
vl53l0x_right = VL53L0X(0x29)
mpu9250 = MPU9250(bus)
ina3221 = INA3221(bus)
HALL_EFFECT_SENSOR_1 = 17  # Replace with the correct GPIO pin number for sensor 1
HALL_EFFECT_SENSOR_2 = 18  # Replace with the correct GPIO pin number for sensor 2

#FUNCTIONS
def init_hall_effect_sensors():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(HALL_EFFECT_SENSOR_1, GPIO.IN)
    GPIO.setup(HALL_EFFECT_SENSOR_2, GPIO.IN)

def init_sensors():
    """Initialize all sensors."""
    global gps_serial  # Use the global GPS serial object

    # Initialize GPS
    gps_serial = GPSInterface()  # Adjust the port and baud rate if needed
    gps_serial.flush()

    # Initialize BME280
    bme280.begin()

    # Initialize VL53L0X sensors
    vl53l0x_left.begin()
    vl53l0x_right.begin()

    # Initialize MPU9250
    mpu9250.begin()

    # Initialize INA3221
    ina3221.begin()

    # Initialize hall effect sensors
    init_hall_effect_sensors()

def read_bme280():
    """Read BME280 sensor data."""
    return bme280.read_all()

def read_gps():
    """Read GPS data."""
    if gps_serial is None:
        raise Exception("GPS module not initialized")

    gps_data = gps_serial.read_gps_data()
    return gps_data

def read_vl53l0x_left():
    """Read VL53L0X left sensor data."""
    return vl53l0x_left.read_distance()

def read_vl53l0x_right():
    """Read VL53L0X right sensor data."""
    return vl53l0x_right.read_distance()

def read_mpu9250_compass():
    """Read MPU9250 compass data."""
    return mpu9250.read_compass()

def read_mpu9250_gyro():
    """Read MPU9250 gyro data."""
    return mpu9250.read_gyro()

def read_ina3221():
    """Read INA3221 power monitor data."""
    return ina3221.read_all()

def read_hall_effect_sensors():
    sensor_1_state = GPIO.input(HALL_EFFECT_SENSOR_1)
    sensor_2_state = GPIO.input(HALL_EFFECT_SENSOR_2)

    return sensor_1_state, sensor_2_state

def ideal_mowing_conditions():
    # Check for high humidity
    bme280_data = read_bme280()
    if bme280_data["humidity"] > 90:
        return False

    # Check for high temperature
    if bme280_data['temperature'] > 30:
        return False

    # Check for low temperature
    if bme280_data['temperature'] < 1:
        return False

    # Check for low pressure
    if bme280_data['pressure'] < 1000:
        return False

    # Return True if all conditions are met
    return True