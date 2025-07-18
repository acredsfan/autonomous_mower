"""GPIO Manager module for hardware control.

This module provides a robust GPIO management interface using Adafruit Blinka
(digitalio, pwmio) libraries for precise, low-level hardware control. It ensures
maximum compatibility with Adafruit sensors and PWM components while providing
simulation capabilities for development and testing.

The module automatically detects the platform and switches between hardware mode
on Raspberry Pi and simulation mode on other platforms or when explicitly requested.

Example:
    Basic GPIO usage:
        
        gpio = GPIOManager()
        
        # Setup digital output pin
        gpio.setup_pin(22, "out")
        gpio.set_pin(22, True)
        
        # Setup PWM output pin
        gpio.setup_pin(17, "pwm", frequency=1000)
        gpio.set_pin_duty_cycle(17, 0.5)  # 50% duty cycle
        
        # Setup digital input pin with pull-up
        gpio.setup_pin(7, "in", pull_up_down=PULL_UP)
        value = gpio.get_pin(7)
        
        # Cleanup when done
        gpio.cleanup_all()

Note:
    This module replaces the previous gpiozero implementation for improved
    stability and compatibility with the Adafruit ecosystem.

Attributes:
    HARDWARE_AVAILABLE (bool): True if hardware GPIO libraries are available.
    PULL_UP: Constant for pull-up resistor configuration.
    PULL_DOWN: Constant for pull-down resistor configuration.
"""

import platform
import time
from typing import Any, Dict, Optional, Union

# Attempt to import the necessary libraries for a Raspberry Pi
if platform.system() == "Linux":
    try:
        import board
        from digitalio import DigitalInOut, Direction, Pull
        from pwmio import PWMOut
        HARDWARE_AVAILABLE = True
    except (ImportError, NotImplementedError) as e:
        # NotImplementedError can be raised by board on non-pi linux systems
        HARDWARE_AVAILABLE = False
else:
    HARDWARE_AVAILABLE = False

from mower.utilities.logger_config import LoggerConfigInfo

logger = LoggerConfigInfo.get_logger(__name__)

# Define constants for pull-up/down to match digitalio's API
if HARDWARE_AVAILABLE:
    PULL_UP = Pull.UP
    PULL_DOWN = Pull.DOWN
else: # Define fallbacks for simulation
    class _SimulatedPull:
        UP = "UP"
        DOWN = "DOWN"
    Pull = _SimulatedPull
    PULL_UP = Pull.UP
    PULL_DOWN = Pull.DOWN

class GPIOManager:
    """GPIO Manager class using digitalio and pwmio libraries for precise control.
    
    This class provides a unified interface for GPIO operations including digital I/O
    and PWM control. It automatically handles platform detection and provides simulation
    capabilities for development environments.
    
    Attributes:
        _devices (Dict[int, Any]): Dictionary mapping pin numbers to device objects.
        _simulation_mode (bool): True if running in simulation mode.
        
    Args:
        simulate (bool, optional): Force simulation mode. Defaults to False.
        
    Example:
        >>> gpio = GPIOManager()
        >>> gpio.setup_pin(22, "out")
        >>> gpio.set_pin(22, True)
        >>> gpio.cleanup_all()
    """

    def __init__(self, simulate: bool = False) -> None:
        """Initialize the GPIO manager."""
        self._devices: Dict[int, Any] = {}
        self._simulation_mode: bool = simulate or not HARDWARE_AVAILABLE

        if self._simulation_mode:
            logger.info("GPIOManager running in SIMULATION mode.")
        else:
            logger.info("GPIOManager running with HARDWARE access via Adafruit Blinka (digitalio/pwmio).")

    def _get_pin_obj(self, pin: int) -> Optional[Any]:
        """Safely retrieve a device object by its pin number."""
        if pin not in self._devices:
            logger.warning(f"Pin {pin} has not been set up.")
            return None
        return self._devices[pin]

    def setup_pin(self, pin: int, direction: str, pull_up_down: Optional[str] = None, frequency: int = 1000) -> None:
        """Set up a GPIO pin for use.
        
        Configures a GPIO pin for digital input, digital output, or PWM output.
        In simulation mode, creates a mock device for testing purposes.
        
        Args:
            pin: GPIO pin number to configure.
            direction: Pin direction - 'out' for output, 'in' for input, 'pwm' for PWM.
            pull_up_down: Pull resistor configuration for input pins - PULL_UP or PULL_DOWN.
            frequency: PWM frequency in Hz for PWM pins. Defaults to 1000.
            
        Raises:
            Exception: If pin setup fails or invalid direction is specified.
            
        Example:
            >>> gpio.setup_pin(22, "out")  # Digital output
            >>> gpio.setup_pin(7, "in", pull_up_down=PULL_UP)  # Input with pull-up
            >>> gpio.setup_pin(17, "pwm", frequency=2000)  # PWM at 2kHz
        """
        if pin in self._devices:
            self.cleanup_pin(pin)

        if self._simulation_mode:
            self._devices[pin] = {"direction": direction, "value": False, "duty_cycle": 0}
            logger.info(f"SIMULATED: Pin {pin} setup as {direction}.")
            return

        try:
            # Use board.D{pin_number} to get the correct pin object
            pin_object = getattr(board, f"D{pin}")

            if direction.lower() == "out":
                device = DigitalInOut(pin_object)
                device.direction = Direction.OUTPUT
            elif direction.lower() == "in":
                device = DigitalInOut(pin_object)
                device.direction = Direction.INPUT
                if pull_up_down == PULL_UP:
                    device.pull = Pull.UP
                elif pull_up_down == PULL_DOWN:
                    device.pull = Pull.DOWN
            elif direction.lower() == "pwm":
                # pwmio handles PWM output
                device = PWMOut(pin_object, frequency=frequency, duty_cycle=0)
            else:
                logger.error(f"Invalid direction '{direction}' for pin {pin}.")
                return

            self._devices[pin] = device
            logger.info(f"Pin {pin} successfully configured as '{direction}'.")

        except Exception as e:
            logger.error(f"Failed to setup pin {pin} as '{direction}': {e}")

    def set_pin(self, pin: int, value: bool) -> None:
        """Set the value of a digital output pin.
        
        Sets the digital output state of a previously configured output pin.
        
        Args:
            pin: GPIO pin number to set.
            value: Digital value to set - True for high, False for low.
            
        Note:
            Pin must be configured as 'out' before calling this method.
            
        Example:
            >>> gpio.setup_pin(22, "out")
            >>> gpio.set_pin(22, True)   # Set pin high
            >>> gpio.set_pin(22, False)  # Set pin low
        """
        device = self._get_pin_obj(pin)
        if not device: return

        if self._simulation_mode:
            device["value"] = value
            return

        # Ensure it's a DigitalInOut object before setting value
        if isinstance(device, DigitalInOut):
            try:
                device.value = value
            except Exception as e:
                logger.error(f"Failed to set pin {pin} to {value}: {e}")
        else:
            logger.warning(f"Cannot set digital value on pin {pin}; it's not a digital output.")

    def set_pin_duty_cycle(self, pin: int, duty_cycle: float) -> None:
        """Set the duty cycle of a PWM pin.
        
        Controls the PWM duty cycle for a previously configured PWM pin.
        The duty cycle value is automatically clamped to the valid range.
        
        Args:
            pin: GPIO pin number configured for PWM.
            duty_cycle: Duty cycle as a float from 0.0 (0%) to 1.0 (100%).
            
        Note:
            Pin must be configured as 'pwm' before calling this method.
            Values outside 0.0-1.0 range are automatically clamped.
            
        Example:
            >>> gpio.setup_pin(17, "pwm")
            >>> gpio.set_pin_duty_cycle(17, 0.5)   # 50% duty cycle
            >>> gpio.set_pin_duty_cycle(17, 0.75)  # 75% duty cycle
        """
        device = self._get_pin_obj(pin)
        if not device: return

        # Clamp value between 0.0 and 1.0
        duty_cycle = max(0.0, min(1.0, duty_cycle))
        # `pwmio` uses a 16-bit value (0-65535) for duty cycle
        duty_cycle_16_bit = int(duty_cycle * 65535)

        if self._simulation_mode:
            device["duty_cycle"] = duty_cycle_16_bit
            return
        
        # Ensure it's a PWMOut object
        if isinstance(device, PWMOut):
            try:
                device.duty_cycle = duty_cycle_16_bit
            except Exception as e:
                logger.error(f"Failed to set duty cycle for pin {pin}: {e}")
        else:
            logger.warning(f"Cannot set duty cycle on pin {pin}; it's not a PWM output.")

    def get_pin(self, pin: int) -> Optional[bool]:
        """Get the value of a digital input pin.
        
        Reads the current digital state of a previously configured input pin.
        
        Args:
            pin: GPIO pin number to read.
            
        Returns:
            Digital state of the pin - True for high, False for low, 
            None if pin is not configured or read fails.
            
        Note:
            Pin must be configured as 'in' before calling this method.
            
        Example:
            >>> gpio.setup_pin(7, "in", pull_up_down=PULL_UP)
            >>> state = gpio.get_pin(7)
            >>> if state is True:
            ...     print("Button pressed")
        """
        device = self._get_pin_obj(pin)
        if not device: return None

        if self._simulation_mode:
            return bool(device.get("value", False))

        if isinstance(device, DigitalInOut):
            try:
                return bool(device.value)
            except Exception as e:
                logger.error(f"Failed to get value from pin {pin}: {e}")
                return None
        else:
             logger.warning(f"Cannot get digital value from pin {pin}; it's not a digital I/O pin.")
             return None

    def cleanup_pin(self, pin: int) -> None:
        """Clean up a single GPIO pin."""
        device = self._devices.pop(pin, None)
        if device and not self._simulation_mode:
            try:
                device.deinit()
                logger.info(f"Cleaned up pin {pin}.")
            except Exception as e:
                logger.error(f"Error cleaning up pin {pin}: {e}")

    def cleanup_all(self) -> None:
        """Clean up all registered GPIO pins."""
        for pin in list(self._devices.keys()):
            self.cleanup_pin(pin)
        logger.info("All managed GPIO pins have been cleaned up.")

# Standalone test for debugging
if __name__ == "__main__":
    logger.info("--- GPIO Manager Test ---")
    manager = GPIOManager()

    # Test a digital output pin
    OUT_PIN = 22
    manager.setup_pin(OUT_PIN, "out")
    manager.set_pin(OUT_PIN, True)
    time.sleep(0.5)
    manager.set_pin(OUT_PIN, False)

    # Test a PWM output pin
    PWM_PIN = 17
    manager.setup_pin(PWM_PIN, "pwm", frequency=1000)
    manager.set_pin_duty_cycle(PWM_PIN, 0.5) # 50% duty cycle
    time.sleep(0.5)
    manager.set_pin_duty_cycle(PWM_PIN, 0.0) # Off

    # Test a digital input pin
    IN_PIN = 7
    manager.setup_pin(IN_PIN, "in", pull_up_down=PULL_UP)
    print(f"Value of input pin {IN_PIN}: {manager.get_pin(IN_PIN)}")
    time.sleep(0.5)

    manager.cleanup_all()
    logger.info("--- Test Complete ---")