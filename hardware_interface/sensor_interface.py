# To set up sensors for autonomous robot sensor interface for the Raspberry Pi 4 2GB RAM with Raspbian Bullseye OS.
# Sensors included are: bme280, Neo 8-M GPS, 2x VL53L0X, MPU9250 (compass, accelerometer, gyroscope), INA3221 (current sensor), and 2 hall effect sensors.

#IMPORTS
import smbus
import time
import board
from adafruit_bme280 import basic as adafruit_bme280
import VL53L0X
import FaBo9Axis_MPU9250
from barbudor_ina3221.lite import INA3221
import RPi.GPIO as GPIO
import serial
import busio
#from gps_interface import GPSInterface

class SensorInterface:
    def __init__(self):
        self.MUX_ADDRESS = 0x70  # Replace with your multiplexer's I2C address if different
        self.bus = smbus.SMBus(1)
        # self.gps_serial = None
        self.i2c = board.I2C()  # uses board.SCL and board.SDA
        self.bme280 = adafruit_bme280.Adafruit_BME280_I2C(tca9548a_num=2, tca9548a_addr=0x70)
        self.vl53l0x_right = adafruit_vl53l0x.VL53L0X(tca9548a_num=4, tca9548a_addr=0x70)
        self.vl53l0x_left = adafruit_vl53l0x.VL53L0X(tca9548a_num=5, tca9548a_addr=0x70)
        self.mpu9250_master = FaBo9Axis_MPU9250.MPU9250(tca9548a_num=0, tca9548a_addr=0x70)
        self.mpu9250_slave = FaBo9Axis_MPU9250.MPU9250(tca9548a_num=1, tca9548a_addr=0x70)
        self.ina3221 = INA3221(tca9548a_num=3, tca9548a_addr=0x70)
        self.HALL_EFFECT_SENSOR_1 = 17  # Replace with the correct GPIO pin number for sensor 1
        self.HALL_EFFECT_SENSOR_2 = 18  # Replace with the correct GPIO pin number for sensor 2
        # change this to match the location's pressure (hPa) at sea level
        self.bme280.sea_level_pressure = 1013.25

    # FUNCTIONS
    def select_mux_channel(self, channel):
        """Select the specified channel on the TCA9548A I2C multiplexer."""
        if 0 <= channel <= 7:
            self.bus.write_byte(self.MUX_ADDRESS, 1 << channel)
        else:
            raise ValueError("Multiplexer channel must be an integer between 0 and 7.")

    def init_hall_effect_sensors(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.HALL_EFFECT_SENSOR_1, GPIO.IN)
        GPIO.setup(self.HALL_EFFECT_SENSOR_2, GPIO.IN)

    def init_sensors(self):
        """Initialize all sensors."""
        # global gps_serial  # Use the global GPS serial object

        # Initialize GPS
        # gps_serial = GPSInterface()  # Adjust the port and baud rate if needed
        # gps_serial.flush()

        # Initialize BME280
        self.bme280.begin()

        # Initialize VL53L0X sensors
        # Start ranging on TCA9548A bus 1
        self.vl53l0x_right.start_ranging(VL53L0X.Vl53l0xAccuracyMode.BETTER)
        # Start ranging on TCA9548A bus 2
        self.vl53l0x_left.start_ranging(VL53L0X.Vl53l0xAccuracyMode.BETTER)

        timing = self.vl53l0x_right.get_timing()
        if timing < 20000:
            timing = 20000
        print("Timing %d ms" % (timing / 1000))

        # Initialize MPU9250
        self.mpu9250_master.begin()
        self.mpu9250_slave.begin()

        # Initialize INA3221
        self.ina3221.begin()

        # Initialize hall effect sensors
        self.init_hall_effect_sensors()

    def read_bme280(self):
        """Read BME280 sensor data."""
        return {
            'temperature': self.bme280.temperature,
            'humidity': self.bme280.relative_humidity,
            'pressure': self.bme280.pressure
        }

    # def read_gps():
    #    """Read GPS data."""
    #    if gps_serial is None:
    #        raise Exception("GPS module not initialized")

    #    gps_data = gps_serial.read_gps_data()
    #    return gps_data

    def read_vl53l0x_left(self):
        """Read VL53L0X left sensor data."""
        return self.vl53l0x_left.get_distance()

    def read_vl53l0x_right(self):
        """Read VL53L0X right sensor data."""
        return self.vl53l0x_right.get_distance()

    def read_mpu9250_compass(self):
        """Read MPU9250 compass data."""
        return self.mpu9250_master.read_compass()

    def read_mpu9250_gyro(self):
        """Read MPU9250 gyro data."""
        return self.mpu9250_master.read_gyro()

    def read_ina3221(self):
        """Read INA3221 power monitor data."""
        return self.ina3221.read_all()

    def read_hall_effect_sensors(self):
        sensor_1_state = GPIO.input(self.HALL_EFFECT_SENSOR_1)
        sensor_2_state = GPIO.input(self.HALL_EFFECT_SENSOR_2)

        return sensor_1_state, sensor_2_state

    def ideal_mowing_conditions(self):
        # Check for high humidity
        bme280_data = self.read_bme280()
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