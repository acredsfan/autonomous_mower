import threading
import logging
import board
import busio
from .bme280_sensor import BME280Sensor
from .bno085_sensor import BNO085Sensor
from .ina3221_sensor import INA3221Sensor
from .vl53l0x_sensor import VL53L0XSensors
from .gpio_manager import GPIOManager
import time

class SensorInterface:
    def __init__(self):
        self.sensor_data_lock = threading.Lock()
        self.sensor_data = {}
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.shutdown_pins = [22, 23]
        self.interrupt_pins = [6, 12]
        self.shutdown_lines, self.interrupt_lines = GPIOManager.init_gpio(self.shutdown_pins, self.interrupt_pins)
        self.init_sensors()
        self.start_update_thread()

    def init_sensors(self):
        """Initialize all sensors with consolidated error handling."""
        self.sensors = {
            'bme280': self.initialize_sensor(BME280Sensor.init_bme280, "BME280"),
            'bno085': self.initialize_sensor(lambda: BNO085Sensor.init_bno085(self.i2c), "BNO085"),
            'ina3221': self.initialize_sensor(lambda: INA3221Sensor.init_ina3221(self.i2c), "INA3221"),
            'vl53l0x': self.initialize_sensor(lambda: VL53L0XSensors.init_vl53l0x_sensors(self.i2c, self.shutdown_lines), "VL53L0X"),
        }

    def initialize_sensor(self, init_function, sensor_name):
        """Utility function to initialize a sensor and log errors if any."""
        try:
            sensor = init_function()
            if sensor is None:
                raise Exception(f"{sensor_name} initialization returned None.")
            logging.info(f"{sensor_name} initialized successfully.")
            return sensor
        except Exception as e:
            logging.error(f"Error initializing {sensor_name}: {e}")
            return None

    def start_update_thread(self):
        """Start the thread that periodically updates sensor readings."""
        self.sensor_thread = threading.Thread(target=self.update_sensors, daemon=True)
        self.sensor_thread.start()

    def update_sensors(self):
        """Read sensor data periodically and update shared sensor data."""
        while True:
            with self.sensor_data_lock:
                self.sensor_data['bme280'] = self.read_sensor_data(self.sensors['bme280'], BME280Sensor.read_bme280, "BME280")
                self.sensor_data['accel'] = self.read_sensor_data(self.sensors['bno085'], BNO085Sensor.read_bno085_accel, "BNO085 Accelerometer")
                self.sensor_data['gyro'] = self.read_sensor_data(self.sensors['bno085'], BNO085Sensor.read_bno085_gyro, "BNO085 Gyroscope")
                self.sensor_data['compass'] = self.read_sensor_data(self.sensors['bno085'], BNO085Sensor.read_bno085_magnetometer, "BNO085 Magnetometer")
                self.sensor_data['quaternion'] = self.read_sensor_data(self.sensors['bno085'], BNO085Sensor.read_bno085_quaternion, "BNO085 Quaternion")
                self.sensor_data['solar'] = self.read_sensor_data(self.sensors['ina3221'], lambda s: INA3221Sensor.read_ina3221(s, 1), "INA3221 Solar")
                self.sensor_data['battery'] = self.read_sensor_data(self.sensors['ina3221'], lambda s: INA3221Sensor.read_ina3221(s, 3), "INA3221 Battery")
                self.sensor_data['battery_charge'] = self.read_sensor_data(self.sensors['ina3221'], INA3221Sensor.battery_charge, "Battery Charge")
                self.sensor_data['left_distance'] = self.read_sensor_data(self.sensors['vl53l0x'], lambda s: VL53L0XSensors.read_vl53l0x(s[0]), "VL53L0X Left Distance")
                self.sensor_data['right_distance'] = self.read_sensor_data(self.sensors['vl53l0x'], lambda s: VL53L0XSensors.read_vl53l0x(s[1]), "VL53L0X Right Distance")
            time.sleep(1.0)  # Adjust the update interval as needed

    def read_sensor_data(self, sensor, read_function, sensor_name):
        """Utility function to read sensor data and handle errors."""
        if sensor is None:
            logging.error(f"{sensor_name} is not initialized.")
            return {}
        try:
            return read_function(sensor)
        except Exception as e:
            logging.error(f"Error reading {sensor_name}: {e}")
            return {}
        
    
    @staticmethod
    def ideal_mowing_conditions():
        #Check temperature is >0, and humidity is <85% on BME for ideal mowing conditions
        if SensorInterface.read_bme280()['temperature'] > 0 and SensorInterface.read_bme280()['humidity'] < 85:
            return True
        else:
            return False