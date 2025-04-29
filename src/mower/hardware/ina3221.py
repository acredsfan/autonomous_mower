import board
import busio
from barbudor_ina3221 import INA3221
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
        except Exception as e:
            logger.error(f"Error initializing INA3221: {e}")
            return None

    @staticmethod
    def read_ina3221(sensor, channel):
        """Read data from the INA3221 sensor for a specific channel."""
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
                raise ValueError("Invalid channel. Must be 1, 2, or 3.")
        except Exception as e:
            logger.error(f"Error reading INA3221 data: {e}")
            return {}


if __name__ == "__main__":
    # Example usage
    sensor = INA3221Sensor.init_ina3221()
    if sensor:
        for channel in [1, 2, 3]:
            data = INA3221Sensor.read_ina3221(sensor, channel)
            print(f"Channel {channel}: {data}")
