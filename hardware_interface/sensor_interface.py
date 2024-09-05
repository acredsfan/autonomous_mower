import sys
import os

# Add the project root to the system path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import threading
import time
import logging
import smbus2 as smbus
import board
import busio
from constants import GRID_SIZE
from .bme280_sensor import BME280Sensor
from .vl53l0x_sensor import VL53L0XSensors
from .bno085_sensor import BNO085Sensor
from .ina3221_sensor import INA3221Sensor
from .gpio_manager import GPIOManager

class SensorInterface:
    def __init__(self):
        self.sensor_data_lock = threading.Lock()
        self.sensor_data = {}
        self.init_common_attributes()
        self.init_sensors()
        time.sleep(3)  # Ensure all sensors are fully initialized before starting the update thread
        self.start_update_thread()

    def start_update_thread(self):
        self.update_thread = threading.Thread(target=self.update_sensors)
        self.update_thread.start()

    def init_common_attributes(self):
        self.GRID_SIZE = GRID_SIZE
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.shutdown_pins = [22, 23]
        self.interrupt_pins = [6, 12]
        self.sensor_data = {}
        self.shutdown_lines, self.interrupt_lines = GPIOManager.init_gpio(self.shutdown_pins, self.interrupt_pins)

    def init_sensors(self):
        # Initialize sensors
        self.bme280 = BME280Sensor.init_bme280()
        if self.bme280 is None:
            logging.error("BME280 failed to initialize.")
        
        self.bno085 = BNO085Sensor.init_bno085(self.i2c)
        if self.bno085 is None:
            logging.error("BNO085 failed to initialize.")

        self.ina3221 = INA3221Sensor.init_ina3221(self.i2c)
        if self.ina3221 is None:
            logging.error("INA3221 failed to initialize.")
        
        self.vl53l0x = VL53L0XSensors.init_vl53l0x_sensors(self.i2c, self.shutdown_lines)
        if self.vl53l0x is None:
            logging.error("VL53L0X failed to initialize.")

    def update_sensors(self):
        while True:
            with self.sensor_data_lock:
                # Reading sensors sequentially with validation checks
                if self.bme280:
                    self.sensor_data['bme280'] = BME280Sensor.read_bme280(self.bme280)
                else:
                    logging.error("BME280 sensor not available for reading.")

                if self.bno085:
                    self.sensor_data['accel'] = BNO085Sensor.read_bno085_accel(self.bno085)
                    self.sensor_data['gyro'] = BNO085Sensor.read_bno085_gyro(self.bno085)
                    self.sensor_data['compass'] = BNO085Sensor.read_bno085_magnetometer(self.bno085)
                    self.sensor_data['quaternion'] = BNO085Sensor.read_bno085_quaternion(self.bno085)
                else:
                    logging.error("BNO085 sensor not available for reading.")

                if self.ina3221:
                    self.sensor_data['solar'] = INA3221Sensor.read_ina3221(self.ina3221, 1)
                    self.sensor_data['battery'] = INA3221Sensor.read_ina3221(self.ina3221, 3)
                    self.sensor_data['battery_charge'] = INA3221Sensor.battery_charge(self.ina3221)
                else:
                    logging.error("INA3221 sensor not available for reading.")

                if self.vl53l0x:
                    self.sensor_data['left_distance'] = VL53L0XSensors.read_vl53l0x(self.vl53l0x[0])
                    self.sensor_data['right_distance'] = VL53L0XSensors.read_vl53l0x(self.vl53l0x[1])
                else:
                    logging.error("VL53L0X sensors not available for reading.")

            time.sleep(1.0)  # Delay between sensor updates