import signal
import sys
import threading
import time

import board
import busio

from utilities import LoggerConfigDebug
from .bme280_sensor import BME280Sensor
from .bno085_sensor import BNO085Sensor
from .gpio_manager import GPIOManager
from .ina3221_sensor import (
    INA3221Sensor
)
from .vl53l0x_sensor import (
    VL53L0XSensors
)

logging = LoggerConfigDebug.get_logger(__name__)


class SensorInterface:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        # Implement thread-safe singleton pattern
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(SensorInterface, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        # Ensure that __init__ only runs once
        if self._initialized:
            return
        self._initialized = True
        self.init()

    def init(self):
        self.sensor_data_lock = threading.Lock()
        self.sensor_data = {}
        self.i2c_lock = threading.Lock()  # Lock for I2C access
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.shutdown_pins = [22, 23]
        self.interrupt_pins = [6, 12]
        self.shutdown_lines, self.interrupt_lines = GPIOManager.init_gpio(
            self.shutdown_pins, self.interrupt_pins)
        self.stop_thread = False
        self.sensors = {}
        self.init_sensors()
        self.start_update_thread()

    def init_sensors(self):
        # Initialize all sensors with consolidated error handling and retries
        self.sensors = {
            'bme280': self.initialize_sensor(
                lambda: BME280Sensor.init_bme280(self.i2c), "BME280"),
            'bno085': self.initialize_sensor_with_retry(
                self.init_bno085_sensor, "BNO085"),
            'ina3221': self.initialize_sensor_with_retry(
                lambda: INA3221Sensor.init_ina3221(self.i2c), "INA3221"),
            'vl53l0x': self.initialize_sensor_with_retry(
                lambda: VL53L0XSensors.init_vl53l0x_sensors(
                    self.i2c, self.shutdown_lines), "VL53L0X"),
        }

    def init_bno085_sensor(self):
        """Initialize and configure the BNO085 sensor."""
        from adafruit_bno08x.i2c import BNO08X_I2C
        sensor = BNO08X_I2C(self.i2c, address=0x4B)
        BNO085Sensor.enable_features(sensor)  # Enable features in the BNO085
        return sensor

    def start_update_thread(self):
        self.sensor_thread = threading.Thread(target=self.update_sensors,
                                              daemon=True)
        self.sensor_thread.start()

    def initialize_sensor(self, init_function, sensor_name):
        try:
            with self.i2c_lock:
                sensor = init_function()
            if sensor is None:
                raise Exception(f"{sensor_name} initialization returned None.")
            logging.info(f"{sensor_name} initialized successfully.")
            return sensor
        except Exception as e:
            logging.error(f"Error initializing {sensor_name}: {e}")
            return None

    def initialize_sensor_with_retry(self, init_function, sensor_name,
                                     retries=3, delay=0.5):
        for attempt in range(retries):
            time.sleep(0.1)
            sensor = self.initialize_sensor(init_function, sensor_name)
            if sensor is not None:
                return sensor
            logging.warning(f"Retrying {sensor_name}"
                            f"initialization (attempt {attempt + 1})")
            time.sleep(delay)
        logging.error(f"Failed to initialize {sensor_name}"
                      f" after {retries} attempts")
        return None

    def read_data(self, sensor, read_function, sensor_name):
        if sensor is None:
            logging.error(f"{sensor_name} is not initialized.")
            return {}
        try:
            return read_function(sensor)
        except Exception as e:
            logging.error(f"Error reading {sensor_name}: {e}")
            return {}

    def update_sensors(self):
        """Read sensor data periodically
        and update shared sensor data."""
        while not self.stop_thread:
            try:
                with self.sensor_data_lock:
                    ''' Read and Store Battery Data (INA3221 Channel 3) for:
                    battery-voltage out (shunt-voltage),
                    battery-current (current),
                    and battery-charge-level (charge_level) as a percentage.'''
                    self.sensor_data['battery_voltage'] = self.read_data(
                        self.sensors['ina3221'],
                        lambda s: INA3221Sensor.read_ina3221(s, 3)[
                            'shunt_voltage'],
                        "INA3221 Battery"
                    )
                    self.sensor_data['battery_current'] = self.read_data(
                        self.sensors['ina3221'],
                        lambda s: INA3221Sensor.read_ina3221(s, 3)['current'],
                        "INA3221 Battery"
                    )
                    self.sensor_data['battery_charge_level'] = self.read_data(
                        self.sensors['ina3221'],
                        INA3221Sensor.battery_charge,
                        "Battery Charge"
                    )

                    ''' Read and Store Solar Data (INA3221 Channel 1) for:
                    solar_voltage out (shunt_voltage) and
                    solar_current (current).'''
                    self.sensor_data['solar_voltage'] = self.read_data(
                        self.sensors['ina3221'],
                        lambda s: INA3221Sensor.read_ina3221(s, 1)[
                            'shunt_voltage'],
                        "INA3221 Solar"
                    )
                    self.sensor_data['solar_current'] = self.read_data(
                        self.sensors['ina3221'],
                        lambda s: INA3221Sensor.read_ina3221(s, 1)['current'],
                        "INA3221 Solar"
                    )

                    '''Read and store BNO085 sensor data for:
                    speed (speed),
                    heading (heading),
                    pitch (pitch),
                    and roll (roll).'''
                    self.sensor_data['speed'] = self.read_data(
                        self.sensors['bno085'],
                        BNO085Sensor.calculate_speed,
                        "BNO085 Speed"
                    )
                    self.sensor_data['heading'] = self.read_data(
                        self.sensors['bno085'],
                        BNO085Sensor.calculate_heading,
                        "BNO085 Heading"
                    )
                    self.sensor_data['pitch'] = self.read_data(
                        self.sensors['bno085'],
                        BNO085Sensor.calculate_pitch,
                        "BNO085 Pitch"
                    )
                    self.sensor_data['roll'] = self.read_data(
                        self.sensors['bno085'],
                        BNO085Sensor.calculate_roll,
                        "BNO085 Roll"
                    )

                    ''' Read and store BME280 sensor data for:
                    temperature in F (temperature_f),
                    humidity (humidity),
                    and pressure (pressure).'''
                    self.sensor_data['temperature'] = self.read_data(
                        self.sensors['bme280'],
                        lambda s: BME280Sensor.read_bme280(s)['temperature_f'],
                        "BME280"
                    )
                    self.sensor_data['humidity'] = self.read_data(
                        self.sensors['bme280'],
                        lambda s: BME280Sensor.read_bme280(s)['humidity'],
                        "BME280"
                    )
                    self.sensor_data['pressure'] = self.read_data(
                        self.sensors['bme280'],
                        lambda s: BME280Sensor.read_bme280(s)['pressure'],
                        "BME280"
                    )

                    ''' Read and store VL53L0X sensor data for:
                    left distance and right distance as a float
                    to 1 decimal place.'''

                    self.sensor_data['left_distance'] = self.read_data(
                        self.sensors['vl53l0x'],
                        lambda s: VL53L0XSensors.read_vl53l0x(s[0]),
                        "VL53L0X Left Distance"
                    )
                    self.sensor_data['right_distance'] = self.read_data(
                        self.sensors['vl53l0x'],
                        lambda s: VL53L0XSensors.read_vl53l0x(s[1]),
                        "VL53L0X Right Distance"
                    )
                time.sleep(0.5)
            except Exception as e:
                logging.error(f"Error updating sensors: {e}")
                time.sleep(1.0)  # Wait before retrying

    def shutdown(self):
        # Ensure sensors and threads are properly cleaned up
        self.stop_thread = True
        if self.sensor_thread.is_alive():
            self.sensor_thread.join()
        GPIOManager.clean()
        logging.info("SensorInterface shutdown complete.")

    @staticmethod
    def ideal_mowing_conditions():
        # Check temperature is >0, and humidity is <85% on BME for ideal mowing
        # conditions
        if SensorInterface.read_bme280()['temperature'] > 0 and \
                SensorInterface.read_bme280()['humidity'] < 85:
            return True
        else:
            return False

    # Graceful shutdown handling with signal
    @staticmethod
    def signal_handler(sig, frame):
        logging.info("Received shutdown signal. Cleaning up...")
        SensorInterface().shutdown()  # Clean up sensors and threads
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


# Singleton accessor function
sensor_interface_instance = SensorInterface()


def get_sensor_interface():
    return sensor_interface_instance


if __name__ == "__main__":
    sensor_interface = SensorInterface()
    while True:
        print(sensor_interface.sensor_data)
        time.sleep(1)
