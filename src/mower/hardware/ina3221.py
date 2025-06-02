"""
INA3221 current and voltage sensor interface.

This module provides a wrapper around the INA3221 sensor hardware,
allowing for power monitoring across three channels simultaneously.
The INA3221 can measure voltage, current, and power on three separate channels.
"""

import board
import busio
import adafruit_ina3221
from mower.utilities.logger_config import LoggerConfigInfo

# Initialize logger
logger = LoggerConfigInfo.get_logger(__name__)


class INA3221Sensor:
    """
    Interface for the INA3221 current and voltage sensor.

    This class provides methods to initialize the INA3221 sensor and read
    voltage, current and power measurements from its three channels.
    """

    @staticmethod
    def init_ina3221():
        """Initialize the INA3221 sensor"""
        try:
            i2c = busio.I2C(board.SCL, board.SDA)

            # Initialize INA3221 sensor with Adafruit library
            sensor = adafruit_ina3221.INA3221(i2c)
            logger.info("INA3221 initialized successfully.")
            return sensor
        except (OSError, ValueError, RuntimeError) as e:  # Catch potential I2C errors
            logger.error("Error initializing INA3221: %s", e)
            return None
        # Replace generic Exception with specific ones
        except (ImportError, AttributeError) as e:
            logger.error("Unexpected error initializing INA3221: %s", e)
            return None

    @staticmethod
    def read_ina3221(sensor, channel):
        """Read data from the INA3221 sensor for a specific channel."""
        if sensor is None:
            logger.error("INA3221 sensor is not initialized.")
            return {}
        try:
            if channel in [1, 2, 3]:
                # Convert channel number to zero-based index for Adafruit
                # library
                channel_index = channel - 1

                # Read voltage and current using Adafruit library API
                bus_voltage = sensor[channel_index].bus_voltage
                shunt_voltage = sensor[channel_index].shunt_voltage
                current = sensor[channel_index].current

                return {
                    "bus_voltage": round(bus_voltage, 2),
                    "shunt_voltage": round(shunt_voltage, 2),
                    "current": round(current, 2),
                }
            else:
                # Log the error instead of raising ValueError immediately
                logger.error(
                    "Invalid channel for INA3221: %s. Must be 1, 2, or 3.",
                    channel)
                return {}  # Return empty dict for invalid channel
        except (OSError, RuntimeError) as e:  # Catch potential I2C read errors
            logger.error(
                "I2C Error reading INA3221 channel %s: %s",
                channel,
                e)
            return {}
        # Replace generic Exception with specific ones
        except (ValueError, AttributeError) as e:
            logger.error(
                "Unexpected error reading INA3221 channel %s: %s",
                channel,
                e)
            return {}


if __name__ == "__main__":
    # Example usage
    sensor = INA3221Sensor.init_ina3221()
    if sensor:
        for channel in [1, 2, 3]:
            data = INA3221Sensor.read_ina3221(sensor, channel)
            print("Channel " + str(channel) + ":", data)
