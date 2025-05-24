"""
GPIO Manager module.

This module provides a unified interface for GPIO access, with support for
both hardware GPIO and simulation mode.
It now uses RPi.GPIO for hardware access.
"""

import logging
from typing import Optional, Dict, Any
from mower.config_management.config_manager import get_config

# Try to import RPi.GPIO, but don't fail if not available
try:
    from RPi import GPIO  # type: ignore[import]

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

    PIN_CONFIG = {
        "BLADE_ENABLE": 17,
        "BLADE_DIRECTION": 27,
        "EMERGENCY_STOP": 7,
        "MOTOR_LEFT": 22,
        "MOTOR_RIGHT": 23,
    }

    def __init__(self):
        """
        Initialize the GPIO manager.
        """
        self._pins_setup: Dict[int, str] = {}
        self._simulation_mode = not RPI_GPIO_AVAILABLE

        if self._simulation_mode:
            logging.info("Running GPIO in simulation mode")
            self._simulated_values: Dict[int, int] = {}

    def setup_pin(
        self,
        pin: int,
        direction: str = "out",
        initial: Optional[int] = None,
        pull_up_down: Optional[int] = None,
    ) -> bool:
        """
        Set up a GPIO pin for use.

        Args:
            pin: The GPIO pin number (BCM mode)
            direction: "in" for input, "out" for output
            initial: Initial value for output pins (GPIO.LOW or GPIO.HIGH)
            pull_up_down: Pull up/down resistor mode for input pins
                         (GPIO.PUD_UP, GPIO.PUD_DOWN, or None)

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

            # Handle different setup scenarios
            if direction == "in" and pull_up_down is not None:
                # Input pin with pull-up/down
                GPIO.setup(pin, dir_const, pull_up_down=pull_up_down)
            elif direction == "out":
                # Output pin with initial value
                initial_val = initial if initial is not None else GPIO.LOW
                GPIO.setup(pin, dir_const, initial=initial_val)
            else:
                # Default input pin setup
                GPIO.setup(pin, dir_const)

            self._pins_setup[pin] = direction
            return True

        except (IOError, ValueError, RuntimeError) as e:
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
        except (IOError, ValueError, RuntimeError) as e:
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
        except (IOError, ValueError, RuntimeError) as e:
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

            # No else after return - removed unnecessary else
            logging.warning(
                "Cannot set simulated pin %s, not set up as output.", pin
            )
            return False

        try:
            if pin in self._pins_setup and self._pins_setup[pin] == "out":
                GPIO.output(pin, gpio_value)
                return True

            # No else after return - removed unnecessary else
            logging.warning("Cannot set pin %s, not set up as output.", pin)
            return False
        except (IOError, ValueError, RuntimeError) as e:
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

            # No else after return - removed unnecessary else
            logging.warning("Cannot get simulated pin %s, not set up.", pin)
            return None

        try:
            if pin in self._pins_setup:
                return GPIO.input(pin)  # Returns 0 or 1

            # No else after return - removed unnecessary else
            logging.warning("Cannot get pin %s, not set up.", pin)
            return None
        except (IOError, ValueError, RuntimeError) as e:
            logging.error("Error reading GPIO pin %s: %s", pin, e)
            return None

    def get_state(self) -> Dict[str, Any]:
        """
        Get the current state of all set up GPIO pins.

        Returns:
            Dict[str, Any]: Dictionary containing GPIO state information
        """
        state = {"simulation_mode": self._simulation_mode, "pins": {}}
        if self._simulation_mode:
            state["pins"] = self._simulated_values.copy()
        else:
            for pin in self._pins_setup:  # Iterate directly over keys
                try:
                    state["pins"][pin] = {
                        "value": self.get_pin(pin),
                        "direction": self._pins_setup.get(pin),
                    }
                except (IOError, ValueError, RuntimeError) as e:
                    logging.error("Error getting state for pin %s: %s", pin, e)

        return state

    def initialize_pins(self):
        """Initialize all GPIO pins based on predefined configuration."""
        # Check if emergency stop button is physically installed
        use_physical_estop = get_config(
            "safety.use_physical_emergency_stop", True)

        for name, pin in self.PIN_CONFIG.items():
            try:
                if name == "EMERGENCY_STOP":
                    if use_physical_estop:
                        # Use pull-up for NC button (HIGH when not pressed,
                        # LOW when pressed or disconnected - fail-safe)
                        if not self._simulation_mode:
                            self.setup_pin(
                                pin, direction="in", pull_up_down=GPIO.PUD_UP
                            )
                        else:
                            self.setup_pin(pin, direction="in")
                        logging.info(
                            f"Initialized GPIO pin {pin} for {name} with pull-up")
                    else:
                        # If no physical button, simulate a non-pressed state
                        self.setup_pin(pin, direction="in")
                        if self._simulation_mode:
                            # In simulation, set to HIGH (not pressed) by
                            # default
                            self._simulated_values[pin] = 1
                        logging.info(
                            f"Initialized virtual emergency stop on pin {pin}")
                else:
                    self.setup_pin(pin, direction="out", initial=0)
                    logging.info(f"Initialized GPIO pin {pin} for {name}")
            except (IOError, ValueError, RuntimeError) as e:
                logging.error(
                    f"Error initializing GPIO pin {pin} for {name}: {e}")

    def setup_pwm(
        self,
        pin: int,
        frequency: int = 1000,
        duty_cycle: int = 50,
    ) -> Optional[Any]:
        """
        Set up PWM on a GPIO pin.

        Args:
            pin: The GPIO pin number
            frequency: Frequency of the PWM signal (default is 1000 Hz)
            duty_cycle: Duty cycle percentage (0-100, default is 50%)

        Returns:
            Optional[Any]: PWM object if successful, None otherwise
        """
        if self._simulation_mode:
            logging.warning("PWM setup not available in simulation mode.")
            return None

        try:
            pwm = GPIO.PWM(pin, frequency)
            pwm.start(duty_cycle)
            return pwm
        except (IOError, ValueError, RuntimeError) as e:
            logging.error(f"Error setting up PWM on pin {pin}: {e}")
            return None
