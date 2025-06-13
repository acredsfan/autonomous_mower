# FROZEN_DRIVER – do not edit
"""
Blade controller module.

This module provides control over the mower's blade motor using an IBT-4 driver.
The IBT-4 is a dual H-bridge motor driver that controls the blade motor through
two input pins (IN1 and IN2).

@hardware_interface IBT-4 motor driver
@gpio_pin_usage 24 (BCM) - IBT-4 IN1 input (forward PWM control)
@gpio_pin_usage 25 (BCM) - IBT-4 IN2 input (reverse PWM control)
"""

from mower.hardware.gpio_manager import GPIOManager
from mower.utilities.logger_config import LoggerConfigInfo

logging = LoggerConfigInfo.get_logger(__name__)

# GPIO pins for blade control via IBT-4 driver
# IN1 connected to GPIO 24 (physical pin 18) - Forward PWM control
# IN2 connected to GPIO 25 (physical pin 22) - Reverse PWM control
BLADE_IN1_PIN = 24  # Forward PWM signal to IBT-4 IN1
BLADE_IN2_PIN = 25  # Reverse PWM signal to IBT-4 IN2


class BladeController:
    """
    Controls the blade motor of the mower using an IBT-4 motor driver.

    This class provides methods to start, stop, and control the blade motor,
    with safety features to prevent accidental activation. The IBT-4 driver
    uses two input pins (IN1 and IN2) for directional PWM control.

    Control Logic:
    - Forward: IN1 = PWM, IN2 = LOW
    - Reverse: IN1 = LOW, IN2 = PWM  
    - Stop: IN1 = LOW, IN2 = LOW
    """

    def __init__(self):
        """Initialize the blade controller with IBT-4 driver."""
        self._gpio = GPIOManager()
        self._enabled = False  # Represents if the blade is logically enabled
        self._current_speed = 0.0  # Current speed (0.0 to 1.0)
        self._direction = 0  # 0 = forward, 1 = reverse

        # Set up GPIO pins for IBT-4 driver
        # Both pins are PWM capable for speed control in both directions
        self._gpio.setup_pin(BLADE_IN1_PIN, "pwm", initial_value=0.0, frequency=1000, active_high=True)
        self._gpio.setup_pin(BLADE_IN2_PIN, "pwm", initial_value=0.0, frequency=1000, active_high=True)

        logging.info("Blade controller initialized with IBT-4 driver (IN1: GPIO%d, IN2: GPIO%d)", 
                    BLADE_IN1_PIN, BLADE_IN2_PIN)

    def enable(self) -> bool:
        """
        Enable the blade motor controller.
        
        This allows the blade to be started with set_speed().
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self._enabled:
                self._enabled = True
                logging.info("Blade motor controller enabled")
            return True
        except Exception as e:
            logging.error(f"Error enabling blade motor controller: {e}")
            return False

    def disable(self) -> bool:
        """
        Disable the blade motor controller and stop the blade.
        
        This immediately stops the blade and prevents further operation
        until enable() is called again.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Stop the blade immediately
            self._stop_blade_motor()
            self._enabled = False
            self._current_speed = 0.0
            logging.info("Blade motor controller disabled and blade stopped")
            return True
        except Exception as e:
            logging.error(f"Error disabling blade motor controller: {e}")
            return False

    def _stop_blade_motor(self) -> None:
        """Internal method to stop the blade motor by setting both IN pins to LOW."""
        self._gpio.set_pin_duty_cycle(BLADE_IN1_PIN, 0.0)
        self._gpio.set_pin_duty_cycle(BLADE_IN2_PIN, 0.0)
        self._current_speed = 0.0

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
                self._direction = direction
                # Apply the new direction with current speed
                self._apply_speed_and_direction()
                logging.info(f"Blade motor direction set to {direction}")
            return True
        except (IOError, ValueError, RuntimeError) as e:
            logging.error(f"Error setting blade motor direction: {e}")
            return False

    def _apply_speed_and_direction(self) -> None:
        """Apply the current speed and direction to the IBT-4 driver pins."""
        if not self._enabled or self._current_speed == 0.0:
            # Stop the motor
            self._gpio.set_pin_duty_cycle(BLADE_IN1_PIN, 0.0)
            self._gpio.set_pin_duty_cycle(BLADE_IN2_PIN, 0.0)
        elif self._direction == 0:
            # Forward: IN1 = PWM, IN2 = LOW
            self._gpio.set_pin_duty_cycle(BLADE_IN1_PIN, self._current_speed)
            self._gpio.set_pin_duty_cycle(BLADE_IN2_PIN, 0.0)
        else:
            # Reverse: IN1 = LOW, IN2 = PWM
            self._gpio.set_pin_duty_cycle(BLADE_IN1_PIN, 0.0)
            self._gpio.set_pin_duty_cycle(BLADE_IN2_PIN, self._current_speed)

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
                logging.error("Invalid speed value: %s. Must be between 0.0 and 1.0.", speed)
                return False

            if not self._enabled and speed > 0.0:
                logging.warning("Blade motor is not enabled. Call enable() first to set speed > 0.")
                return False

            # Update current speed and apply to hardware
            self._current_speed = speed
            self._apply_speed_and_direction()
            
            logging.info("Blade motor speed set to %.1f%%", speed * 100)
            if speed == 0.0 and self._enabled:
                logging.info("Blade motor speed set to 0%, but still logically enabled.")
            elif speed == 0.0 and not self._enabled:
                logging.info("Blade motor speed set to 0% and is logically disabled.")
            
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

    def get_speed(self) -> float:
        """
        Get the current blade motor speed.

        Returns:
            float: Current speed (0.0 to 1.0)
        """
        return self._current_speed

    def is_running(self) -> bool:
        """
        Check if the blade motor is currently running.

        Returns:
            bool: True if running (speed > 0 and enabled), False otherwise
        """
        return self._enabled and self._current_speed > 0.0

    def start_blade(self, speed: float = 0.8) -> bool:
        """
        Start the blade motor at the specified speed.
        
        This is a convenience method that enables the controller and sets speed.

        Args:
            speed: Speed value between 0.0 and 1.0 (default: 0.8)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.enable():
                return False
            return self.set_speed(speed)
        except Exception as e:
            logging.error(f"Error starting blade motor: {e}")
            return False

    def start(self, speed: float = 0.8) -> bool:
        """
        Start the blade motor at the specified speed.
        
        This is an alias for start_blade() for compatibility.

        Args:
            speed: Speed value between 0.0 and 1.0 (default: 0.8)

        Returns:
            bool: True if successful, False otherwise
        """
        return self.start_blade(speed)

    def stop(self) -> bool:
        """
        Stop the blade motor.
        
        This is an alias for stop_blade() for compatibility.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.stop_blade()
            return True
        except Exception as e:
            logging.error(f"Error stopping blade motor: {e}")
            return False

    def cleanup(self) -> None:
        """Clean up GPIO resources."""
        try:
            self.disable()
            self._gpio.cleanup_pin(BLADE_IN1_PIN)
            self._gpio.cleanup_pin(BLADE_IN2_PIN)
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
            "speed": self._current_speed,
            "direction": self._direction,
            "in1_pin": BLADE_IN1_PIN,
            "in2_pin": BLADE_IN2_PIN,
        }

    def stop_blade(self) -> None:
        """Stop the blade motor."""
        if self._enabled:
            logging.info("Stopping blade motor")
            self.set_speed(0.0)  # Set speed to 0 to stop the motor
            self.disable()  # Disable the motor controller
            logging.info("Blade motor stopped")
        else:
            logging.info("Blade motor is already stopped")


if __name__ == "__main__":
    # Simple test to demonstrate functionality
    blade_controller = BladeController()
    blade_controller.enable()
    blade_controller.set_direction(0)  # Set forward direction
    blade_controller.set_speed(1.0)  # Set speed to 50%
    
    logging.info("Blade controller state: %s", blade_controller.get_state())
    
    # Simulate some operation
    import time
    time.sleep(2)
    
    blade_controller.set_speed(0)  # Stop the blade
    blade_controller.disable()  # Disable the blade controller
    blade_controller.cleanup()  # Clean up resources
