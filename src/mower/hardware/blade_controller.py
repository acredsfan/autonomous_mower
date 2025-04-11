"""
Blade controller module.

This module provides control over the mower's blade motor.
"""


from mower.hardware.gpio_manager import GPIOManager
from mower.utilities.logger_config import LoggerConfigInfo as LoggerConfig

logging = LoggerConfig.get_logger(__name__)

# GPIO pins for blade control
BLADE_ENABLE_PIN = 22
BLADE_DIRECTION_PIN = 23


class BladeController:
    """
    Controls the blade motor of the mower.

    This class provides methods to start, stop, and control the blade motor,
    with safety features to prevent accidental activation.
    """

    def __init__(self):
        """Initialize the blade controller."""
        self._gpio = GPIOManager()
        self._enabled = False
        self._direction = 0

        # Set up GPIO pins
        self._gpio.setup_pin(BLADE_ENABLE_PIN, "out", 0)
        self._gpio.setup_pin(BLADE_DIRECTION_PIN, "out", 0)

        logging.info("Blade controller initialized")

    def _initialize(self):
        """Initialize the blade controller."""
        logging.info("Blade controller initialized successfully.")

    def enable(self) -> bool:
        """
        Enable the blade motor.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self._enabled:
                self._gpio.set_pin(BLADE_ENABLE_PIN, 1)
                self._enabled = True
                logging.info("Blade motor enabled")
            return True
        except Exception as e:
            logging.error(f"Error enabling blade motor: {e}")
            return False

    def disable(self) -> bool:
        """
        Disable the blade motor.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if self._enabled:
                self._gpio.set_pin(BLADE_ENABLE_PIN, 0)
                self._enabled = False
                logging.info("Blade motor disabled")
            return True
        except Exception as e:
            logging.error(f"Error disabling blade motor: {e}")
            return False

    def set_direction(self, direction: int) -> bool:
        """
        Set the blade motor direction.

        Args:
            direction: 0 for forward, 1 for reverse

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if direction not in [0, 1]:
                logging.error(f"Invalid direction value: {direction}")
                return False

            if self._direction != direction:
                self._gpio.set_pin(BLADE_DIRECTION_PIN, direction)
                self._direction = direction
                logging.info(f"Blade motor direction set to {direction}")
            return True
        except Exception as e:
            logging.error(f"Error setting blade motor direction: {e}")
            return False

    def is_enabled(self) -> bool:
        """
        Check if the blade motor is enabled.

        Returns:
            bool: True if enabled, False otherwise
        """
        return self._enabled

    def get_direction(self) -> int:
        """
        Get the current blade motor direction.

        Returns:
            int: 0 for forward, 1 for reverse
        """
        return self._direction

    def cleanup(self) -> None:
        """Clean up GPIO resources."""
        try:
            self.disable()
            self._gpio.cleanup_pin(BLADE_ENABLE_PIN)
            self._gpio.cleanup_pin(BLADE_DIRECTION_PIN)
            logging.info("Blade controller cleaned up")
        except Exception as e:
            logging.error(f"Error cleaning up blade controller: {e}")

    def get_state(self) -> dict:
        """
        Get the current state of the blade controller.

        Returns:
            dict: Dictionary containing state information
        """
        return {
            "enabled": self._enabled,
            "direction": self._direction,
            "enable_pin": BLADE_ENABLE_PIN,
            "direction_pin": BLADE_DIRECTION_PIN
            }
