# FROZEN_DRIVER – do not edit (see .github/copilot-instructions.md)
import board
import busio
from adafruit_bme280 import basic as adafruit_bme280

from mower.utilities.logger_config import LoggerConfigInfo

# Initialize logger
logger = LoggerConfigInfo.get_logger(__name__)


class BME280Sensor:
    """Class to handle BME280 sensor"""

    @staticmethod
    def _initialize(i2c=None):
        """
        Initialize the BME280 sensor with the I2C bus.
        Returns the sensor object if successful, otherwise None.
        """
        try:
            # Use provided I2C bus or create default
            if i2c is None:
                i2c = busio.I2C(board.SCL, board.SDA)
            # Initialize the BME280 sensor on the specified I2C bus
            sensor = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=0x76)
            logger.info("BME280 initialized successfully.")
            return sensor
        except (OSError, ValueError, RuntimeError) as e:  # Catch potential I2C errors
            logger.error(f"Error initializing BME280: {e}")
            return None
        except Exception as e:  # Catch any other unexpected errors
            logger.error(f"Unexpected error initializing BME280: {e}")
            return None

    @staticmethod
    def read_bme280(sensor):
        """Read BME280 sensor data."""
        if sensor is None:
            logger.error("BME280 sensor is not initialized.")
            return {}

        try:
            # Fetch temperature, humidity, and pressure from the sensor
            temp_c = sensor.temperature
            humidity = sensor.humidity
            pressure = sensor.pressure
            temperature_f = temp_c * 9 / 5 + 32
            return {
                "temperature_c": round(temp_c, 1),
                "temperature_f": round(temperature_f, 1),
                "humidity": round(humidity, 1),
                "pressure": round(pressure, 1),
            }
        except (OSError, RuntimeError) as e:  # Catch potential I2C read errors
            logger.error(f"I2C Error during BME280 read: {e}")
            return {}
        except Exception as e:  # Catch any other unexpected errors
            logger.error(f"Unexpected error during BME280 read: {e}")
            return {}


if __name__ == "__main__":
    # Initialize the BME280 sensor
    bme280_sensor = BME280Sensor()
    bme280 = bme280_sensor._initialize()

    if bme280 is not None:
        # Read BME280 sensor data
        sensor_data = bme280_sensor.read_bme280(bme280)
        logger.info(f"BME280 sensor data: {sensor_data}")
    else:
        logger.error("BME280 sensor initialization failed.")
