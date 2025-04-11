"""
Blade controller module.

This module provides control over the mower's blade motor.
"""


from mower.hardware.gpio_manager import GPIOManager
from mower.utilities.logger_config import LoggerConfigInfo as LoggerConfig

logging = LoggerConfig.get_logger(__name__)

# GPIO pins for blade control
BLADE_IN1_PIN = 22
BLADE_IN2_PIN = 23


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

        # Set up GPIO pins
        self._gpio.setup_pin(BLADE_IN1_PIN, "out", 0)
        self._gpio.setup_pin(BLADE_IN2_PIN, "out", 0)

        logging.info("Blade controller initialized")

    def enable(self) -> bool:
        """
        Enable the blade motor.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self._enabled:
                self._gpio.set_pin(BLADE_IN1_PIN, 1)
                self._gpio.set_pin(BLADE_IN2_PIN, 0)
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
                self._gpio.set_pin(BLADE_IN1_PIN, 0)
                self._gpio.set_pin(BLADE_IN2_PIN, 0)
                self._enabled = False
                logging.info("Blade motor disabled")
            return True
        except Exception as e:
            logging.error(f"Error disabling blade motor: {e}")
            return False

    def set_speed(self, speed: float) -> bool:
        """
        Set the blade motor speed.

        Args:
            speed: Speed value between 0.0 (stopped) and 1.0 (full speed).

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            if not (0.0 <= speed <= 1.0):
                logging.error(f"Invalid speed value: {speed}")
                return False

            # Map speed to duty cycle percentage (0 to 100)
            duty_cycle = speed * 100
            self._gpio.set_pwm(BLADE_IN1_PIN, duty_cycle)
            logging.info(f"Blade motor speed set to {speed}")
            return True
        except Exception as e:
            logging.error(f"Error setting blade motor speed: {e}")
            return False

    def is_enabled(self) -> bool:
        """
        Check if the blade motor is enabled.

        Returns:
            bool: True if enabled, False otherwise
        """
        return self._enabled

    def cleanup(self) -> None:
        """Clean up GPIO resources."""
        try:
            self.disable()
            self._gpio.cleanup_pin(BLADE_IN1_PIN)
            self._gpio.cleanup_pin(BLADE_IN2_PIN)
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
            "in1_pin": BLADE_IN1_PIN,
            "in2_pin": BLADE_IN2_PIN
        }


if __name__ == "__main__":
    import time

    logging.info("Starting BladeController test...")

    blade_controller = BladeController()

    try:
        logging.info("Enabling blade motor...")
        blade_controller.enable()
        time.sleep(2)

        logging.info("Setting blade motor speed to 50%...")
        blade_controller.set_speed(0.5)
        time.sleep(2)

        logging.info("Disabling blade motor...")
        blade_controller.disable()

    except Exception as e:
        logging.error(f"Error during BladeController test: {e}")

    finally:
        logging.info("Cleaning up BladeController...")
        blade_controller.cleanup()

    logging.info("BladeController test completed.")
