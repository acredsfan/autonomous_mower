"""
Blade controller module.

This module provides control over the mower's blade motor.
"""

from mower.hardware.gpio_manager import GPIOManager
from mower.utilities.logger_config import LoggerConfigInfo

logging = LoggerConfigInfo.get_logger(__name__)

# GPIO pins for blade control
BLADE_ENABLE_PIN = 22  # This pin will be used for PWM speed control
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
        self._enabled = False  # Represents if the blade *should* be active
        self._direction = 0

        # Set up GPIO pins
        # BLADE_ENABLE_PIN is a PWM pin for speed control, initialized to 0%
        # duty cycle.
        self._gpio.setup_pin(
            BLADE_ENABLE_PIN,
            "pwm",
            initial_value=0.0,
            frequency=1000,
            active_high=True)
        self._gpio.setup_pin(BLADE_DIRECTION_PIN, "out", initial_value=False)

        logging.info("Blade controller initialized")

    def enable(self) -> bool:
        """
        Signal that the blade motor can be active.
        Actual motor movement is controlled by set_speed.
        Returns:
            bool: True if successful, False otherwise
        """
        # This method now primarily manages the logical state _enabled.
        # Physical enabling (PWM > 0) is handled by set_speed.
        if not self._enabled:
            self._enabled = True
            logging.info(
                "Blade motor logically enabled. Use set_speed to start rotation.")
        return True

    def disable(self) -> bool:
        """
        Signal that the blade motor should be inactive and stop it.
        Sets PWM duty cycle to 0%.
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Always set speed to 0 to ensure motor stops.
            self.set_speed(0.0)
            if self._enabled:
                self._enabled = False
                logging.info(
                    "Blade motor logically disabled and speed set to 0%.")
            return True
        except (IOError, ValueError, RuntimeError) as e:
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
                self._gpio.set_pin(BLADE_DIRECTION_PIN, bool(direction))
                self._direction = direction
                logging.info(f"Blade motor direction set to {direction}")
            return True
        except (IOError, ValueError, RuntimeError) as e:
            logging.error(f"Error setting blade motor direction: {e}")
            return False

    def set_speed(self, speed: float) -> bool:
        """
        Set the speed of the blade motor using PWM.
        Only applies speed if the blade is logically enabled.

        Args:
            speed (float): Speed value between 0.0 (stopped) and 1.0 (full speed).

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            if not 0.0 <= speed <= 1.0:
                logging.error(
                    "Invalid speed value: %s. Must be between 0.0 and 1.0.", speed)
                return False

            if not self._enabled and speed > 0.0:
                logging.warning(
                    "Blade motor is not enabled. Call enable() first to set speed > 0.")
                # Optionally, we could auto-enable here, but explicit control is safer.
                # self.enable()
                # However, we will allow setting speed to 0 even if not
                # enabled.
                if speed > 0.0:
                    return False  # Do not set speed if not enabled and speed > 0

            # If speed is 0, we always allow it, effectively stopping the motor.
            # If speed > 0, it will only be applied if self._enabled is True.
            if self._enabled or speed == 0.0:
                self._gpio.set_pin_duty_cycle(BLADE_ENABLE_PIN, speed)
                logging.info("Blade motor speed set to %.1f%%", speed * 100)
                if speed == 0.0 and self._enabled:
                    logging.info(
                        "Blade motor speed set to 0%, but still logically enabled.")
                elif speed == 0.0 and not self._enabled:
                    logging.info(
                        "Blade motor speed set to 0% and is logically disabled.")
            return True
        except (IOError, ValueError, RuntimeError) as e:
            logging.error(f"Error setting blade motor speed: {e}")
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
        except (IOError, ValueError, RuntimeError) as e:
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
            "direction_pin": BLADE_DIRECTION_PIN,
        }

    def stop_blade(self) -> None:
        """Stop the blade motor."""
        if self._enabled:
            logging.info("Stopping blade motor")
            self.set_speed(0)  # Set speed to 0 to stop the motor
            self.disable()  # Disable the motor enable pin
            logging.info("Blade motor stopped")
        else:
            logging.info("Blade motor is already stopped")
