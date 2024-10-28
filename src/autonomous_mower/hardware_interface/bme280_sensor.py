from adafruit_bme280 import basic as adafruit_bme280

from autonomous_mower.utilities.logger_config import (
    LoggerConfigDebug as LoggerConfig
)

# Initialize logger
logging = LoggerConfig.get_logger(__name__)


class BME280Sensor:
    """Class to handle BME280 sensor"""

    @staticmethod
    def init_bme280(i2c):
        """
        Initialize the BME280 sensor with the I2C bus.
        Returns the sensor object if successful, otherwise None.
        """
        try:
            # Initialize the BME280 sensor on the specified I2C bus
            sensor = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=0x76)
            logging.info("BME280 initialized successfully.")
            return sensor
        except Exception as e:
            logging.error(f"Error initializing BME280: {e}")
            return None

    @staticmethod
    def read_bme280(sensor):
        """Read BME280 sensor data."""
        if sensor is None:
            logging.error("BME280 sensor is not initialized.")
            return {}

        try:
            # Fetch temperature, humidity, and pressure from the sensor
            temperature_f = sensor.temperature * 9 / 5 + 32
            return {
                'temperature_c': round(sensor.temperature, 1),
                'temperature_f': round(temperature_f, 1),
                'humidity': round(sensor.humidity, 1),
                'pressure': round(sensor.pressure, 1)
            }
        except Exception as e:
            logging.error(f"Error during BME280 read: {e}")
            return {}


if __name__ == "__main__":
    # Initialize the BME280 sensor
    bme280_sensor = BME280Sensor()
    bme280 = bme280_sensor.init_bme280()

    if bme280 is not None:
        # Read BME280 sensor data
        sensor_data = bme280_sensor.read_bme280(bme280)
        logging.info(f"BME280 sensor data: {sensor_data}")
    else:
        logging.error("BME280 sensor initialization failed.")
