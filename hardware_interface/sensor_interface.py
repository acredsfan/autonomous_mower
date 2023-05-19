# To set up sensors for autonomous robot sensor interface for the Raspberry Pi 4 2GB RAM with Raspbian Bullseye OS.
# Sensors included are: bme280, Neo 8-M GPS, 2x VL53L0X, MPU9250 (compass, accelerometer, gyroscope), INA3221 (current sensor), and 2 hall effect sensors.

#IMPORTS
import smbus
import time
import board
from adafruit_bme280 import basic as adafruit_bme280
import adafruit_vl53l0x
import FaBo9Axis_MPU9250
from barbudor_ina3221.lite import INA3221
import RPi.GPIO as GPIO
import serial
import busio
#from gps_interface import GPSInterface

# Global variables
MUX_ADDRESS = 0x70  # Replace with your multiplexer's I2C address if different
bus = smbus.SMBus(1)
#gps_serial = None
i2c = board.I2C()   # uses board.SCL and board.SDA
bme280 = adafruit_bme280.Adafruit_BME280_I2C(tca9548a_num=2, tca9548a_addr=0x70)
vl53l0x_right = VL53L0X.VL53L0X(tca9548a_num=4, tca9548a_addr=0x70)
vl53l0x_left = VL53L0X.VL53L0X(tca9548a_num=5, tca9548a_addr=0x70)
mpu9250_master = adafruit_mpu9250.MPU9250(tca9548a_num=0, tca9548a_addr=0x70)
mpu9250_slave = adafruit_mpu9250.MPU9250(tca9548a_num=1, tca9548a_addr=0x70)
ina3221 = INA3221(tca9548a_num=3, tca9548a_addr=0x70)
HALL_EFFECT_SENSOR_1 = 17  # Replace with the correct GPIO pin number for sensor 1
HALL_EFFECT_SENSOR_2 = 18  # Replace with the correct GPIO pin number for sensor 2
# change this to match the location's pressure (hPa) at sea level
bme280.sea_level_pressure = 1013.25

class SensorInterface:

#FUNCTIONS
    def select_mux_channel(channel):
        """Select the specified channel on the TCA9548A I2C multiplexer."""
        if 0 <= channel <= 7:
            bus.write_byte(MUX_ADDRESS, 1 << channel)
        else:
            raise ValueError("Multiplexer channel must be an integer between 0 and 7.")
    
    def init_hall_effect_sensors():
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(HALL_EFFECT_SENSOR_1, GPIO.IN)
        GPIO.setup(HALL_EFFECT_SENSOR_2, GPIO.IN)

    def init_sensors():
        """Initialize all sensors."""
        #global gps_serial  # Use the global GPS serial object

        # Initialize GPS
        #gps_serial = GPSInterface()  # Adjust the port and baud rate if needed
        #gps_serial.flush()

        # Initialize BME280
        bme280.begin()

        # Initialize VL53L0X sensors
        # Start ranging on TCA9548A bus 1
        vl53l0x_right.start_ranging(VL53L0X.Vl53l0xAccuracyMode.BETTER)
        # Start ranging on TCA9548A bus 2
        vl53l0x_left.start_ranging(VL53L0X.Vl53l0xAccuracyMode.BETTER)

        timing = vl53l0x_right.get_timing()
        if timing < 20000:
            timing = 20000
        print("Timing %d ms" % (timing/1000))

        # Initialize MPU9250
        mpu9250.begin()

        # Initialize INA3221
        ina3221.begin()

        # Initialize hall effect sensors
        init_hall_effect_sensors()

    def read_bme280():
        """Read BME280 sensor data."""
        return {
            'temperature': bme280.temperature,
            'humidity': bme280.relative_humidity,
            'pressure': bme280.pressure
        }

    #def read_gps():
    #    """Read GPS data."""
    #    if gps_serial is None:
    #        raise Exception("GPS module not initialized")

    #    gps_data = gps_serial.read_gps_data()
    #    return gps_data

    def read_vl53l0x_left():
        """Read VL53L0X left sensor data."""
        return vl53l0x_left.get_distance()

    def read_vl53l0x_right():
        """Read VL53L0X right sensor data."""
        return vl53l0x_right.get_distance()

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
        bme280_data = SensorInterface.read_bme280()
        if bme280_data['humidity'] > 90:
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