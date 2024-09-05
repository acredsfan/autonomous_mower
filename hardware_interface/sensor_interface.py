import sys
import os

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
        time.sleep(3)
        self.start_update_thread()

    def start_update_thread(self):
        self.update_thread = threading.Thread(target=self.update_sensors)
        self.update_thread.start()

    def init_common_attributes(self):
        self.GRID_SIZE = GRID_SIZE
        self.bus = smbus.SMBus(1)
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.shutdown_pins = [22, 23]
        self.interrupt_pins = [6, 12]
        self.sensor_data = {}
        self.shutdown_lines, self.interrupt_lines = GPIOManager.init_gpio(self.shutdown_pins, self.interrupt_pins)

    def init_sensors(self):
        self.bme280 = BME280Sensor.init_bme280(self.bus)
        self.bno085 = BNO085Sensor.init_bno085(self.i2c)
        self.ina3221 = INA3221Sensor.init_ina3221(self.i2c)
        # Initialize both VL53L0X sensors
        self.left_vl53l0x, self.right_vl53l0x = VL53L0XSensors.init_vl53l0x_sensors(self.i2c, self.shutdown_lines)

    def update_sensors(self):
        while True:
            with self.sensor_data_lock:
                self.sensor_data['temperature_f'] = BME280Sensor.read_bme280(self.bme280)['temperature_f']
                self.sensor_data['humidity'] = BME280Sensor.read_bme280(self.bme280)['humidity']
                self.sensor_data['pressure'] = BME280Sensor.read_bme280(self.bme280)['pressure']
                self.sensor_data['accel'] = BNO085Sensor.read_bno085_accel(self.bno085)['accel']
                self.sensor_data['gyro'] = BNO085Sensor.read_bno085_gyro(self.bno085)['gyro']
                self.sensor_data['magnetometer'] = BNO085Sensor.read_bno085_magnetometer(self.bno085)['magnetometer']
                self.sensor_data['quaternion'] = BNO085Sensor.read_bno085_quaternion(self.bno085)['quaternion']
                self.sensor_data['solar bus voltage'] = INA3221Sensor.read_ina3221(self.ina3221, 1)['bus_voltage']
                self.sensor_data['solar current'] = INA3221Sensor.read_ina3221(self.ina3221, 1)['current']
                self.sensor_data['solar shunt voltage'] = INA3221Sensor.read_ina3221(self.ina3221, 1)['shunt_voltage']
                self.sensor_data['battery bus voltage'] = INA3221Sensor.read_ina3221(self.ina3221, 3)['bus_voltage']
                self.sensor_data['battery current'] = INA3221Sensor.read_ina3221(self.ina3221, 3)['current']
                self.sensor_data['battery shunt voltage'] = INA3221Sensor.read_ina3221(self.ina3221, 3)['shunt_voltage']
                self.sensor_data['battery soc'] = INA3221Sensor.battery_charge(self.ina3221)['charge_level']
                self.sensor_data['left_distance'] = VL53L0XSensors.read_vl53l0x(self.left_vl53l0x)['distance']
                self.sensor_data['right_distance'] = VL53L0XSensors.read_vl53l0x(self.right_vl53l0x)['distance']
            time.sleep(1.0)
