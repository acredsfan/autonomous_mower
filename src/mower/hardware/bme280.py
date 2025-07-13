# FROZEN_DRIVER – do not edit (see .github/copilot-instructions.md)
import board
import busio
import time
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
        """Read BME280 sensor data with enhanced error handling and retry logic."""
        if sensor is None:
            logger.error("BME280 sensor is not initialized.")
            return {}

        max_retries = 2
        retry_delay = 0.1
        
        for attempt in range(max_retries):
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
            except OSError as e:
                if e.errno == 121:  # Remote I/O error
                    if attempt < max_retries - 1:
                        logger.debug(f"BME280 I/O error (errno 121), retrying in {retry_delay}s... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(retry_delay)
                        continue
                    else:
                        logger.warning(f"BME280 I/O error after {max_retries} attempts, marking sensor as optional: {e}")
                        # Mark sensor as optional - return empty dict but don't crash
                        return {}
                else:
                    logger.error(f"BME280 OSError (errno {e.errno}): {e}")
                    return {}
            except (RuntimeError, ValueError) as e:  # Catch potential I2C read errors
                logger.error(f"BME280 read error: {e}")
                return {}
            except Exception as e:  # Catch any other unexpected errors
                logger.error(f"Unexpected BME280 read error: {e}")
                return {}
        
        # Should never reach here, but just in case
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
