"""
GPIO Manager module.

This module provides a unified interface for GPIO access, with support for
both hardware GPIO and simulation mode.
It now uses RPi.GPIO for hardware access.
"""

import logging
from typing import Optional, Dict, Any

# Try to import RPi.GPIO, but don't fail if not available
try:
    import RPi.GPIO as GPIO
    RPI_GPIO_AVAILABLE = True
    GPIO.setmode(GPIO.BCM)  # Use Broadcom pin numbering
    GPIO.setwarnings(False)  # Disable warnings
except ImportError:
    RPI_GPIO_AVAILABLE = False
    logging.warning("RPi.GPIO not available. Running in simulation mode.")
except RuntimeError as e:
    # Catches errors like 'This module can only be run on a Raspberry Pi!'
    RPI_GPIO_AVAILABLE = False
    logging.warning(f"RPi.GPIO cannot be used (not a Pi?): {e}")


class GPIOManager:
    """
    GPIO Manager class using RPi.GPIO library.

    This class supports both hardware GPIO access through RPi.GPIO and
    simulation mode when hardware is not available.
    """

    def __init__(self):
        """
        Initialize the GPIO manager.
        """
        self._pins_setup: Dict[int, str] = {}
        self._simulation_mode = not RPI_GPIO_AVAILABLE

        if self._simulation_mode:
            logging.info("Running GPIO in simulation mode")
            self._simulated_values: Dict[int, int] = {}

    def setup_pin(self, pin: int, direction: str = "out",
                  initial: Optional[int] = None) -> bool:
        """
        Set up a GPIO pin for use.

        Args:
            pin: The GPIO pin number (BCM mode)
            direction: "in" for input, "out" for output
            initial: Initial value for output pins (GPIO.LOW or GPIO.HIGH)

        Returns:
            bool: True if setup successful, False otherwise
        """
        if self._simulation_mode:
            # Map GPIO.HIGH/LOW to 1/0 if necessary for simulation state
            sim_initial = initial if initial is not None else 0
            if sim_initial == GPIO.HIGH:
                sim_initial = 1
            if sim_initial == GPIO.LOW:
                sim_initial = 0
            self._simulated_values[pin] = sim_initial
            self._pins_setup[pin] = direction
            return True

        try:
            dir_const = GPIO.OUT if direction == "out" else GPIO.IN
            # Default initial for RPi.GPIO is LOW if not specified
            initial_val = initial if initial is not None else GPIO.LOW

            GPIO.setup(pin, dir_const, initial=initial_val)
            self._pins_setup[pin] = direction
            return True

        except Exception as e:
            logging.error(f"Error setting up GPIO pin {pin}: {e}")
            return False

    def cleanup_pin(self, pin: int) -> None:
        """
        Clean up a single GPIO pin (resets it).

        Args:
            pin: The GPIO pin number to clean up
        """
        if self._simulation_mode:
            self._simulated_values.pop(pin, None)
            self._pins_setup.pop(pin, None)
            return

        try:
            if pin in self._pins_setup:
                GPIO.cleanup(pin)
                self._pins_setup.pop(pin, None)
        except Exception as e:
            logging.error(f"Error cleaning up GPIO pin {pin}: {e}")

    def cleanup_all(self) -> None:
        """Clean up all GPIO pins used by this manager."""
        if self._simulation_mode:
            self._simulated_values.clear()
            self._pins_setup.clear()
            return

        try:
            # RPi.GPIO cleanup can take a channel list or clean all if no arg
            # Cleaning only the pins we set up is safer
            pins_to_clean = list(self._pins_setup.keys())
            if pins_to_clean:
                GPIO.cleanup(pins_to_clean)
            self._pins_setup.clear()
        except Exception as e:
            logging.error(f"Error cleaning up GPIO: {e}")

    def set_pin(self, pin: int, value: int) -> bool:
        """
        Set the value of a GPIO pin.

        Args:
            pin: The GPIO pin number
            value: The value to set (GPIO.LOW or GPIO.HIGH, or 0/1)

        Returns:
            bool: True if successful, False otherwise
        """
        # Ensure value is 0 or 1 for consistency
        gpio_value = GPIO.HIGH if value else GPIO.LOW
        sim_value = 1 if value else 0

        if self._simulation_mode:
            if pin in self._pins_setup and self._pins_setup[pin] == "out":
                self._simulated_values[pin] = sim_value
                return True
            else:
                # Use f-string correctly
                logging.warning(
                    f"Cannot set simulated pin {pin}, not set up as output.")
                return False

        try:
            if pin in self._pins_setup and self._pins_setup[pin] == "out":
                GPIO.output(pin, gpio_value)
                return True
            else:
                logging.warning(f"Cannot set pin {pin}, not set up as output.")
                return False
        except Exception as e:
            logging.error(f"Error setting GPIO pin {pin}: {e}")
            return False

    def get_pin(self, pin: int) -> Optional[int]:
        """
        Get the value of a GPIO pin.

        Args:
            pin: The GPIO pin number

        Returns:
            Optional[int]: The pin value (0 or 1) or None on error
        """
        if self._simulation_mode:
            if pin in self._pins_setup:
                return self._simulated_values.get(pin, 0)
            else:
                # Correct indentation and formatting
                logging.warning(f"Cannot get simulated pin {pin}, not set up.")
                return None

        try:
            if pin in self._pins_setup:
                return GPIO.input(pin)  # Returns 0 or 1
            else:
                logging.warning(f"Cannot get pin {pin}, not set up.")
                return None
        except Exception as e:
            logging.error(f"Error reading GPIO pin {pin}: {e}")
            return None

    def get_state(self) -> Dict[str, Any]:
        """
        Get the current state of all set up GPIO pins.

        Returns:
            Dict[str, Any]: Dictionary containing GPIO state information
        """
        state = {
            "simulation_mode": self._simulation_mode,
            "pins": {}
        }

        if self._simulation_mode:
            state["pins"] = self._simulated_values.copy()
        else:
            for pin in self._pins_setup.keys():
                try:
                    state["pins"][pin] = {
                        "value": self.get_pin(pin),
                        "direction": self._pins_setup.get(pin)
                    }
                except Exception as e:
                    logging.error(f"Error getting state for pin {pin}: {e}")

        return state
