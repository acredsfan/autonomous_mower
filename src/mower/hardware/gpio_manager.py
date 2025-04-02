import gpiod  # type: ignore
import time
import os
import importlib
from typing import List, Tuple, Callable, Any, Optional

from mower.utilities.logger_config import (
    LoggerConfigInfo as LoggerConfig
)

# Initialize logger
logging = LoggerConfig.get_logger(__name__)

# Check if we're in simulation mode
USE_SIMULATION = os.environ.get('USE_SIMULATION', 'False').lower() == 'true'

class GPIOManager:
    _instance = None
    _chip = None
    _shutdown_lines = []
    _interrupt_lines = []
    _gpio_version = 0  # 0 = unknown, 1 = gpiod v1, 2 = gpiod v2, -1 = simulation

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GPIOManager, cls).__new__(cls)
            cls.__init__(cls._instance)
        return cls._instance

    @staticmethod
    def _check_gpio_version():
        """Determine which GPIO library version to use."""
        if USE_SIMULATION:
            GPIOManager._gpio_version = -1
            logging.info("Running in simulation mode - GPIO operations will be simulated")
            return
            
        try:
            # Check if we have gpiod v1
            if hasattr(gpiod, 'Chip') and hasattr(gpiod, 'LINE_REQ_DIR_OUT'):
                GPIOManager._gpio_version = 1
                logging.info("Using gpiod v1.x API")
                return
                
            # Check if we have gpiod v2
            gpiod_spec = importlib.util.find_spec("gpiod")
            if gpiod_spec:
                GPIOManager._gpio_version = 2
                logging.info("Using gpiod v2.x API")
                return
                
            # Try to import RPi.GPIO as fallback
            import RPi.GPIO
            GPIOManager._gpio_version = 3
            logging.info("Using RPi.GPIO as fallback")
            return
        except ImportError:
            logging.warning("No GPIO library available - simulating GPIO operations")
            GPIOManager._gpio_version = -1

    @staticmethod
    def init_gpio(shutdown_pins: List[int], interrupt_pins: List[int]) -> Tuple[List[Any], List[Any]]:
        """
        Initialize GPIO pins for shutdown and interrupt.
        Args:
            shutdown_pins: List of GPIO pins for shutdown functionality.
            interrupt_pins: List of GPIO pins for interrupt functionality.
        Returns:
            Tuple of (shutdown_lines, interrupt_lines)
        """
        # Check which GPIO version to use if we haven't already
        if GPIOManager._gpio_version == 0:
            GPIOManager._check_gpio_version()
            
        # Handle different GPIO library versions
        if GPIOManager._gpio_version == 1:
            # gpiod v1.x
            return GPIOManager._init_gpiod_v1(shutdown_pins, interrupt_pins)
        elif GPIOManager._gpio_version == 2:
            # gpiod v2.x
            return GPIOManager._init_gpiod_v2(shutdown_pins, interrupt_pins)
        elif GPIOManager._gpio_version == 3:
            # RPi.GPIO fallback
            return GPIOManager._init_rpi_gpio(shutdown_pins, interrupt_pins)
        else:
            # Simulation mode or no GPIO available
            return GPIOManager._init_simulation(shutdown_pins, interrupt_pins)
    
    @staticmethod
    def _init_gpiod_v1(shutdown_pins, interrupt_pins):
        """Initialize using gpiod v1.x API."""
        try:
            chip = gpiod.Chip('/dev/gpiochip0')
            shutdown_lines = [chip.get_line(pin) for pin in shutdown_pins]
            interrupt_lines = [chip.get_line(pin) for pin in interrupt_pins]

            for line in shutdown_lines:
                line.request(consumer='shutdown',
                           type=gpiod.LINE_REQ_DIR_OUT)
                line.set_value(0)

            for line in interrupt_lines:
                line.request(consumer='interrupt',
                          type=gpiod.LINE_REQ_EV_FALLING_EDGE)
            
            # Store for cleanup
            GPIOManager._shutdown_lines = shutdown_lines
            GPIOManager._interrupt_lines = interrupt_lines
            return shutdown_lines, interrupt_lines
        except Exception as e:
            logging.error(f"gpiod v1 initialization error: {e}")
            return GPIOManager._init_simulation(shutdown_pins, interrupt_pins)
    
    @staticmethod
    def _init_gpiod_v2(shutdown_pins, interrupt_pins):
        """Initialize using gpiod v2.x API."""
        try:
            # Import enums and constants for v2
            from gpiod.line import Direction, Edge
            from gpiod.line import Bias
            
            # The correct way to open a chip in gpiod v2 - note it's a function not a class
            chip = gpiod.Chip.open('/dev/gpiochip0')
            GPIOManager._chip = chip
            
            # Set up shutdown lines (outputs)
            shutdown_lines = []
            for pin in shutdown_pins:
                try:
                    config = {
                        'consumer': 'shutdown',
                        'direction': Direction.OUTPUT,
                        'output_value': 0
                    }
                    line = chip.get_line(pin)
                    line.request(config)
                    shutdown_lines.append(line)
                except Exception as e:
                    logging.error(f"Error requesting line {pin}: {e}")
            
            # Set up interrupt lines (inputs with falling edge detection)
            interrupt_lines = []
            for pin in interrupt_pins:
                try:
                    config = {
                        'consumer': 'interrupt',
                        'edge': Edge.FALLING,
                        'bias': Bias.PULL_UP,
                    }
                    line = chip.get_line(pin)
                    line.request(config)
                    interrupt_lines.append(line)
                except Exception as e:
                    logging.error(f"Error requesting line {pin}: {e}")
            
            # Store for cleanup
            GPIOManager._shutdown_lines = shutdown_lines
            GPIOManager._interrupt_lines = interrupt_lines
            return shutdown_lines, interrupt_lines
        
        except Exception as e:
            logging.error(f"gpiod v2 initialization error: {e}")
            return GPIOManager._init_simulation(shutdown_pins, interrupt_pins)
    
    @staticmethod
    def _init_rpi_gpio(shutdown_pins, interrupt_pins):
        """Initialize using RPi.GPIO."""
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            # Set up shutdown pins as outputs
            for pin in shutdown_pins:
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, GPIO.LOW)
            
            # Set up interrupt pins as inputs with pull-up
            for pin in interrupt_pins:
                GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            
            # Create dummy line objects for consistent interface
            class DummyLine:
                def __init__(self, pin, is_output=False):
                    self.pin = pin
                    self.is_output = is_output
                
                def set_value(self, value):
                    if self.is_output:
                        GPIO.output(self.pin, value)
                
                def get_value(self):
                    return GPIO.input(self.pin)
                
                def release(self):
                    pass
                    
                def offset(self):
                    return self.pin
            
            shutdown_lines = [DummyLine(pin, True) for pin in shutdown_pins]
            interrupt_lines = [DummyLine(pin) for pin in interrupt_pins]
            
            return shutdown_lines, interrupt_lines
        
        except ImportError:
            logging.error("Failed to import RPi.GPIO")
            return GPIOManager._init_simulation(shutdown_pins, interrupt_pins)
    
    @staticmethod
    def _init_simulation(shutdown_pins, interrupt_pins):
        """Initialize in simulation mode with dummy objects."""
        logging.info("Using simulated GPIO")
        
        class SimulatedLine:
            def __init__(self, pin, is_output=False):
                self.pin = pin
                self.is_output = is_output
                self._value = 0
            
            def set_value(self, value):
                self._value = value
                logging.debug(f"Simulated GPIO pin {self.pin} set to {value}")
            
            def get_value(self):
                return self._value
                
            def release(self):
                logging.debug(f"Simulated GPIO pin {self.pin} released")
                
            def offset(self):
                return self.pin
                
            def event_wait(self, timeout=None):
                # Simulated line never has events
                return None
        
        shutdown_lines = [SimulatedLine(pin, True) for pin in shutdown_pins]
        interrupt_lines = [SimulatedLine(pin) for pin in interrupt_pins]
        
        return shutdown_lines, interrupt_lines

    @staticmethod
    def wait_for_interrupt(interrupt_lines, callback, timeout=10):
        """
        Waits for an interrupt event on the specified interrupt lines.
        Args:
            interrupt_lines: List of GPIO lines to monitor for interrupts.
            callback: Callback function to invoke when an interrupt occurs.
            timeout: Timeout for waiting for the interrupt event (in secs).
        """
        if not interrupt_lines:
            logging.warning("No interrupt lines to monitor")
            time.sleep(timeout)
            return
            
        if GPIOManager._gpio_version == -1:
            # Simulation mode - just sleep
            logging.debug("Simulated wait_for_interrupt - sleeping")
            time.sleep(timeout)
            return
            
        if GPIOManager._gpio_version == 1:
            # gpiod v1
            try:
                epoll = gpiod.epoll()
                for line in interrupt_lines:
                    epoll.add_line_event(line, gpiod.LINE_REQ_EV_FALLING_EDGE)

                while True:
                    events = epoll.poll(timeout)
                    if not events:
                        logging.debug("Waiting for interrupt timed out")
                        continue

                    for event in events:
                        if event.event_type == gpiod.LineEvent.FALLING_EDGE:
                            pin = event.line.offset()
                            logging.info(f"Interrupt on pin {pin}")
                            callback(pin)
            except Exception as e:
                logging.error(f"Error in wait_for_interrupt (v1): {e}")
                time.sleep(timeout)
                
        elif GPIOManager._gpio_version == 2:
            # gpiod v2
            try:
                from gpiod.line import Edge
                # For gpiod v2, we need to poll each line
                while True:
                    for line in interrupt_lines:
                        try:
                            if hasattr(line, 'wait_for_edge'):
                                # Newer versions
                                if line.wait_for_edge(timeout=timeout):
                                    pin = line.offset
                                    logging.info(f"Interrupt on pin {pin}")
                                    callback(pin)
                            elif hasattr(line, 'event_wait'):
                                # Older v2 versions
                                event = line.event_wait(timeout)
                                if event and event.type == Edge.FALLING:
                                    pin = line.offset
                                    logging.info(f"Interrupt on pin {pin}")
                                    callback(pin)
                        except Exception as e:
                            logging.error(f"Error polling line: {e}")
                    # Small delay to prevent CPU hogging
                    time.sleep(0.01)
            except Exception as e:
                logging.error(f"Error in wait_for_interrupt (v2): {e}")
                time.sleep(timeout)
                
        elif GPIOManager._gpio_version == 3:
            # RPi.GPIO
            try:
                import RPi.GPIO as GPIO
                # Set up event detection for each pin
                for line in interrupt_lines:
                    pin = line.pin
                    # First remove any existing detection
                    GPIO.remove_event_detect(pin)
                    # Add new falling edge detection
                    GPIO.add_event_detect(pin, GPIO.FALLING,
                                       callback=callback)
                
                # Keep the thread alive
                while True:
                    time.sleep(1)
            except Exception as e:
                logging.error(f"Error in wait_for_interrupt (RPi.GPIO): {e}")
                time.sleep(timeout)

    @staticmethod
    def clean():
        """Clean up GPIO lines and resources."""
        if GPIOManager._gpio_version == -1:
            # Simulation mode - nothing to clean up
            logging.debug("Simulated GPIO cleanup")
            return
            
        try:
            # Common cleanup for all GPIO versions
            for line in GPIOManager._shutdown_lines + GPIOManager._interrupt_lines:
                try:
                    if hasattr(line, 'release'):
                        line.release()
                except Exception as e:
                    logging.error(f"Error releasing line: {e}")
            
            # Reset instance variables
            GPIOManager._shutdown_lines = []
            GPIOManager._interrupt_lines = []
            
            # gpiod v2 chip cleanup
            if GPIOManager._gpio_version == 2 and GPIOManager._chip:
                if hasattr(GPIOManager._chip, 'close'):
                    GPIOManager._chip.close()
            
            # RPi.GPIO cleanup
            if GPIOManager._gpio_version == 3:
                import RPi.GPIO as GPIO
                GPIO.cleanup()
            
            GPIOManager._chip = None
            logging.info("GPIO cleanup complete")
            
        except Exception as e:
            logging.error(f"Error during GPIO cleanup: {e}")


if __name__ == "__main__":
    # Example usage
    shutdown_lines, interrupt_lines = GPIOManager.init_gpio([22, 23], [6, 12])

    # Dummy callback for interrupt handling
    def example_callback(pin):
        logging.info(f"Interrupt received on GPIO pin {pin}")

    # Wait for interrupts with the callback
    GPIOManager.wait_for_interrupt(interrupt_lines, example_callback)
    GPIOManager.clean()
