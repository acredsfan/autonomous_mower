import board
import busio
from barbudor_ina3221.lite import INA3221
from mower.utilities.logger_config import LoggerConfigInfo as LoggerConfig

# Initialize logger
logger = LoggerConfig.get_logger(__name__)


class INA3221Sensor:
    @staticmethod
    def init_ina3221():
        """Initialize the INA3221 sensor"""
        try:
            i2c = busio.I2C(board.SCL, board.SDA)

            # Initialize INA3221 sensor
            sensor = INA3221(i2c)
            logger.info("INA3221 initialized successfully.")
            return sensor
        except (OSError, ValueError, RuntimeError) as e:  # Catch potential I2C errors
            logger.error(f"Error initializing INA3221: {e}")
            return None
        except Exception as e:  # Catch any other unexpected errors
            logger.error(f"Unexpected error initializing INA3221: {e}")
            return None

    @staticmethod
    def read_ina3221(sensor, channel):
        """Read data from the INA3221 sensor for a specific channel."""
        if sensor is None:
            logger.error("INA3221 sensor is not initialized.")
            return {}
        try:
            if channel in [1, 2, 3]:
                bus_voltage = sensor.bus_voltage(channel)
                shunt_voltage = sensor.shunt_voltage(channel)
                current = sensor.current(channel)
                return {
                    "bus_voltage": round(bus_voltage, 2),
                    "shunt_voltage": round(shunt_voltage, 2),
                    "current": round(current, 2),
                }
            else:
                # Log the error instead of raising ValueError immediately
                logger.error(
                    f"Invalid channel for INA3221: {channel}. Must be 1, 2, or 3."
                )
                return {}  # Return empty dict for invalid channel
        except (OSError, RuntimeError) as e:  # Catch potential I2C read errors
            logger.error(f"I2C Error reading INA3221 channel {channel}: {e}")
            return {}
        except Exception as e:  # Catch any other unexpected errors
            logger.error(f"Unexpected error reading INA3221 channel {channel}: {e}")
            return {}


if __name__ == "__main__":
    # Example usage
    sensor = INA3221Sensor.init_ina3221()
    if sensor:
        for channel in [1, 2, 3]:
            data = INA3221Sensor.read_ina3221(sensor, channel)
            print(f"Channel {channel}: {data}")
