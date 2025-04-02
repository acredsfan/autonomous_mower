"""
GPIO Manager module.

This module provides a unified interface for GPIO access, with support for
both hardware GPIO and simulation mode.
"""

import logging
from typing import Optional, Dict, Any

# Try to import gpiod, but don't fail if not available
try:
    import gpiod  # type: ignore
    GPIOD_AVAILABLE = True
except ImportError:
    GPIOD_AVAILABLE = False
    logging.warning("gpiod not available. Running in simulation mode.")

class GPIOManager:
    """
    GPIO Manager class that provides a unified interface for GPIO access.
    
    This class supports both hardware GPIO access through gpiod and
    simulation mode when hardware is not available.
    """
    
    def __init__(self, chip_name: str = "gpiochip0"):
        """
        Initialize the GPIO manager.
        
        Args:
            chip_name: The name of the GPIO chip to use
        """
        self._chip_name = chip_name
        self._chip = None
        self._lines = {}
        self._line_configs = {}
        self._simulation_mode = not GPIOD_AVAILABLE
        
        if not self._simulation_mode:
            try:
                self._chip = gpiod.Chip(self._chip_name)
                logging.info(f"Initialized GPIO chip {self._chip_name}")
            except Exception as e:
                logging.warning(f"Failed to initialize GPIO chip: {e}")
                self._simulation_mode = True
                
        if self._simulation_mode:
            logging.info("Running GPIO in simulation mode")
            self._simulated_values = {}
            
    def setup_pin(self, pin: int, direction: str = "out", 
                  initial: Optional[int] = None) -> bool:
        """
        Set up a GPIO pin for use.
        
        Args:
            pin: The GPIO pin number
            direction: "in" for input, "out" for output
            initial: Initial value for output pins (0 or 1)
            
        Returns:
            bool: True if setup successful, False otherwise
        """
        if self._simulation_mode:
            self._simulated_values[pin] = initial if initial is not None else 0
            return True
            
        try:
            config = {
                "direction": gpiod.LINE_REQ_DIR_OUT if direction == "out" 
                            else gpiod.LINE_REQ_DIR_IN,
                "consumer": "mower"
            }
            
            if initial is not None and direction == "out":
                config["default_val"] = initial
                
            line = self._chip.get_line(pin)
            line.request(**config)
            
            self._lines[pin] = line
            self._line_configs[pin] = config
            
            return True
            
        except Exception as e:
            logging.error(f"Error setting up GPIO pin {pin}: {e}")
            return False
            
    def cleanup_pin(self, pin: int) -> None:
        """
        Clean up a GPIO pin.
        
        Args:
            pin: The GPIO pin number to clean up
        """
        if self._simulation_mode:
            self._simulated_values.pop(pin, None)
            return
            
        try:
            if pin in self._lines:
                self._lines[pin].release()
                del self._lines[pin]
                del self._line_configs[pin]
        except Exception as e:
            logging.error(f"Error cleaning up GPIO pin {pin}: {e}")
            
    def cleanup_all(self) -> None:
        """Clean up all GPIO pins."""
        if self._simulation_mode:
            self._simulated_values.clear()
            return
            
        try:
            for pin in list(self._lines.keys()):
                self.cleanup_pin(pin)
            if self._chip:
                self._chip.close()
                self._chip = None
        except Exception as e:
            logging.error(f"Error cleaning up GPIO: {e}")
            
    def set_pin(self, pin: int, value: int) -> bool:
        """
        Set the value of a GPIO pin.
        
        Args:
            pin: The GPIO pin number
            value: The value to set (0 or 1)
            
        Returns:
            bool: True if successful, False otherwise
        """
        if self._simulation_mode:
            self._simulated_values[pin] = value
            return True
            
        try:
            if pin in self._lines:
                self._lines[pin].set_value(value)
                return True
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
            return self._simulated_values.get(pin, 0)
            
        try:
            if pin in self._lines:
                return self._lines[pin].get_value()
            return None
        except Exception as e:
            logging.error(f"Error reading GPIO pin {pin}: {e}")
            return None
            
    def get_state(self) -> Dict[str, Any]:
        """
        Get the current state of all GPIO pins.
        
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
            for pin, line in self._lines.items():
                try:
                    state["pins"][pin] = {
                        "value": line.get_value(),
                        "config": self._line_configs[pin]
                    }
                except Exception as e:
                    logging.error(f"Error getting state for pin {pin}: {e}")
                    
        return state
