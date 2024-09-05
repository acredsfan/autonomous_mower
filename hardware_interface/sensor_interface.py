import threading
import time
import logging
import smbus2 as smbus
import board
import busio
from constants import GRID_SIZE
from bme280_sensor import init_bme280, read_bme280
from vl53l0x_sensor import init_vl53l0x, reset_sensor, read_vl53l0x
from bno085_sensor import init_bno085, read_bno085_accel
from ina3221_sensor import init_ina3221, read_ina3221
from gpio_manager import init_gpio

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
        self.shutdown_lines, self.interrupt_lines = init_gpio(self.shutdown_pins, self.interrupt_pins)

    def init_sensors(self):
        self.bme280 = init_bme280(self.i2c)
        self.bno085 = init_bno085(self.i2c)
        self.ina3221 = init_ina3221(self.i2c)
        self.init_vl53l0x_sensors()

    def init_vl53l0x_sensors(self):
        self.vl53l0x_left = init_vl53l0x(self.i2c, 0x30)
        self.vl53l0x_right = init_vl53l0x(self.i2c, 0x31)

    def update_sensors(self):
        while True:
            with self.sensor_data_lock:
                self.sensor_data['bme280'] = read_bme280(self.bme280)
                self.sensor_data['accel'] = read_bno085_accel(self.bno085)
                self.sensor_data['solar'] = read_ina3221(self.ina3221, 1)
                self.sensor_data['battery'] = read_ina3221(self.ina3221, 3)
            time.sleep(1.0)
