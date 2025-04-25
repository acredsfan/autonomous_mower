"""
Example temperature sensor plugin for the autonomous mower.

This module demonstrates how to create a sensor plugin for the autonomous mower.
It provides a simulated temperature sensor that generates random temperature values.
"""

import random
import time
from typing import Dict, Any

from mower.plugins.plugin_base import SensorPlugin
from mower.utilities.logger_config import LoggerConfigInfo

# Initialize logger
logger = LoggerConfigInfo.get_logger(__name__)


class TemperatureSensorPlugin(SensorPlugin):
    """
    Example temperature sensor plugin.

    This plugin provides a simulated temperature sensor that generates
    random temperature values.
    """

    def __init__(self):
        """Initialize the temperature sensor plugin."""
        self._initialized = False
        self._last_reading = 20.0  # Initial temperature in Celsius
        self._last_update = 0.0
        self._update_interval = 1.0  # Update interval in seconds

        logger.info("TemperatureSensorPlugin created")

    @property
    def plugin_id(self) -> str:
        """
        Get the unique identifier for this plugin.

        Returns:
            str: Unique identifier for this plugin
        """
        return "temperature_sensor"

    @property
    def plugin_name(self) -> str:
        """
        Get the human-readable name for this plugin.

        Returns:
            str: Human-readable name for this plugin
        """
        return "Temperature Sensor"

    @property
    def plugin_version(self) -> str:
        """
        Get the version of this plugin.

        Returns:
            str: Version of this plugin
        """
        return "1.0.0"

    @property
    def plugin_description(self) -> str:
        """
        Get the description of this plugin.

        Returns:
            str: Description of this plugin
        """
        return "Simulated temperature sensor that generates random temperature values"

    @property
    def sensor_type(self) -> str:
        """
        Get the type of this sensor.

        Returns:
            str: Type of this sensor
        """
        return "temperature"

    def initialize(self) -> bool:
        """
        Initialize the plugin.

        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            # Simulate sensor initialization
            logger.info("Initializing temperature sensor plugin")
            time.sleep(0.1)  # Simulate initialization delay

            self._initialized = True
            self._last_update = time.time()

            logger.info("Temperature sensor plugin initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Error initializing temperature sensor plugin: {e}")
            return False

    def get_data(self) -> Dict[str, Any]:
        """
        Get data from the sensor.

        Returns:
            Dict[str, Any]: Sensor data
        """
        try:
            # Check if it's time to update the reading
            current_time = time.time()
            if current_time - self._last_update >= self._update_interval:
                # Generate a new random temperature value
                # Simulate temperature changes by adding a small random offset
                # to the previous reading
                self._last_reading += random.uniform(-0.5, 0.5)
                self._last_update = current_time

            # Return the sensor data
            return {
                "temperature_c": round(self._last_reading, 1),
                "temperature_f": round(self._last_reading * 9 / 5 + 32, 1),
                "timestamp": time.time()
            }

        except Exception as e:
            logger.error(f"Error getting temperature sensor data: {e}")
            return {}

    def get_status(self) -> Dict[str, Any]:
        """
        Get the status of the sensor.

        Returns:
            Dict[str, Any]: Sensor status
        """
        return {
            "initialized": self._initialized,
            "last_update": self._last_update,
            "update_interval": self._update_interval
        }

    def cleanup(self) -> None:
        """Clean up resources used by the plugin."""
        try:
            # Simulate cleanup
            logger.info("Cleaning up temperature sensor plugin")
            time.sleep(0.1)  # Simulate cleanup delay

            self._initialized = False

            logger.info("Temperature sensor plugin cleaned up successfully")

        except Exception as e:
            logger.error(f"Error cleaning up temperature sensor plugin: {e}")


# Example usage
if __name__ == "__main__":
    # Create and initialize the plugin
    plugin = TemperatureSensorPlugin()
    plugin.initialize()

    # Get data from the plugin
    for _ in range(5):
        data = plugin.get_data()
        print(
            f"Temperature: {data.get('temperature_c')}°C / {data.get('temperature_f')}°F")
        time.sleep(1)

    # Clean up the plugin
    plugin.cleanup()
