import gpiod  # type: ignore
import time

from mower.utilities.logger_config import (
    LoggerConfigInfo as LoggerConfig
)

# Initialize logger
logging = LoggerConfig.get_logger(__name__)


class GPIOManager:
    _instance = None
    _chip = None
    _shutdown_lines = []
    _interrupt_lines = []

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GPIOManager, cls).__new__(cls)
            cls.__init__(cls._instance)
        return cls._instance

    @staticmethod
    def init_gpio(shutdown_pins, interrupt_pins):
        """
        Initialize GPIO pins for shutdown and interrupt.
        :param shutdown_pins: List of GPIO pins for shutdown functionality.
        :param interrupt_pins: List of GPIO pins for interrupt functionality.
        :return: Tuple (shutdown_lines, interrupt_lines)
        """
        try:
            # Check gpiod version to use appropriate API
            if hasattr(gpiod, 'Chip'):
                # Old API (gpiod 1.x)
                chip = gpiod.Chip('/dev/gpiochip0')
                shutdown_lines = [chip.get_line(pin) for pin in shutdown_pins]
                interrupt_lines = [chip.get_line(pin) for pin in interrupt_pins]

                for line in shutdown_lines:
                    line.request(consumer='shutdown', type=gpiod.LINE_REQ_DIR_OUT)
                    line.set_value(0)

                for line in interrupt_lines:
                    line.request(consumer='interrupt',
                                type=gpiod.LINE_REQ_EV_FALLING_EDGE)
            else:
                # New API (gpiod 2.x)
                logging.info("Using gpiod 2.x API")
                chip = gpiod.chip('/dev/gpiochip0')
                
                # Configure output lines for shutdown pins
                shutdown_config = gpiod.line_request()
                shutdown_config.consumer = "shutdown"
                shutdown_config.request_type = gpiod.line_request.DIRECTION_OUTPUT
                
                # Configure input lines for interrupt pins with falling edge detection
                interrupt_config = gpiod.line_request()
                interrupt_config.consumer = "interrupt"
                interrupt_config.request_type = gpiod.line_request.EVENT_FALLING_EDGE
                
                # Get lines and request them
                shutdown_lines = []
                for pin in shutdown_pins:
                    line = chip.get_line(pin)
                    line.request(shutdown_config)
                    line.set_value(0)
                    shutdown_lines.append(line)
                
                interrupt_lines = []
                for pin in interrupt_pins:
                    line = chip.get_line(pin)
                    line.request(interrupt_config)
                    interrupt_lines.append(line)
                
                # Store chip reference for cleanup
                GPIOManager._chip = chip
            
            # Store lines for cleanup
            GPIOManager._shutdown_lines = shutdown_lines
            GPIOManager._interrupt_lines = interrupt_lines
            
            return shutdown_lines, interrupt_lines
        
        except Exception as e:
            logging.error(f"GPIO initialization error: {e}")
            # Fallback to RPi.GPIO if gpiod fails
            try:
                import RPi.GPIO as GPIO
                logging.info("Falling back to RPi.GPIO")
                GPIO.setmode(GPIO.BCM)
                
                # Set up shutdown pins as outputs
                for pin in shutdown_pins:
                    GPIO.setup(pin, GPIO.OUT)
                    GPIO.output(pin, GPIO.LOW)
                
                # Set up interrupt pins as inputs with pull-up
                for pin in interrupt_pins:
                    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                
                # Return dummy objects with compatible interface
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
                
                shutdown_lines = [DummyLine(pin, True) for pin in shutdown_pins]
                interrupt_lines = [DummyLine(pin) for pin in interrupt_pins]
                
                return shutdown_lines, interrupt_lines
            
            except ImportError:
                logging.error("Failed to fall back to RPi.GPIO. GPIO functionality will be unavailable.")
                return [], []

    @staticmethod
    def wait_for_interrupt(interrupt_lines, callback, timeout=10):
        """
        Waits for an interrupt event on the specified interrupt lines.
        :param interrupt_lines: List of GPIO lines to monitor for interrupts.
        :param callback: Callback function to invoke when an interrupt occurs.
        :param timeout: Timeout for waiting for the interrupt event (in secs).
        """
        try:
            if hasattr(gpiod, 'Chip'):
                # Old API (gpiod 1.x)
                epoll = gpiod.epoll()  # Initialize epoll to monitor multiple lines
                for line in interrupt_lines:
                    epoll.add_line_event(line, gpiod.LINE_REQ_EV_FALLING_EDGE)

                while True:
                    events = epoll.poll(timeout)  # Poll for interrupt events
                    if not events:
                        logging.info("Waiting for interrupt timed out.")
                        continue

                    for event in events:
                        if event.event_type == gpiod.LineEvent.FALLING_EDGE:
                            logging.info(f"Interrupt detected on line {event.line.offset()}")
                            callback(event.line.offset())
            else:
                # New API (gpiod 2.x)
                while True:
                    for line in interrupt_lines:
                        event = line.event_wait(timeout)
                        if event:
                            if event.event_type == gpiod.line_event.FALLING_EDGE:
                                pin = line.offset()
                                logging.info(f"Interrupt detected on line {pin}")
                                callback(pin)
                    time.sleep(0.01)  # Small delay to prevent CPU hogging
        
        except Exception as e:
            logging.error(f"Error in wait_for_interrupt: {e}")
            # Try fallback to RPi.GPIO
            try:
                import RPi.GPIO as GPIO
                
                # Set up callbacks for the interrupt pins
                for line in interrupt_lines:
                    GPIO.add_event_detect(line.pin, GPIO.FALLING, 
                                         callback=lambda pin: callback(pin))
                
                # Keep the thread alive
                while True:
                    time.sleep(1)
            
            except ImportError:
                logging.error("Failed to fall back to RPi.GPIO for interrupt handling.")

    @staticmethod
    def clean():
        """Clean up GPIO lines."""
        try:
            # Release all lines we've kept track of
            for line in GPIOManager._shutdown_lines + GPIOManager._interrupt_lines:
                try:
                    line.release()
                except Exception as e:
                    logging.error(f"Error releasing GPIO line: {e}")
            
            # Close the chip if we're using the new API
            if GPIOManager._chip and hasattr(GPIOManager._chip, 'close'):
                GPIOManager._chip.close()
            
            # Reset our stored references
            GPIOManager._shutdown_lines = []
            GPIOManager._interrupt_lines = []
            GPIOManager._chip = None
            
            logging.info("GPIO cleanup complete.")
        
        except Exception as e:
            logging.error(f"Error during GPIO cleanup: {e}")
            # Try fallback cleanup with RPi.GPIO
            try:
                import RPi.GPIO as GPIO
                GPIO.cleanup()
                logging.info("RPi.GPIO cleanup complete.")
            except ImportError:
                pass


if __name__ == "__main__":
    # Example usage
    shutdown_lines, interrupt_lines = GPIOManager.init_gpio([22, 23], [6, 12])

    # Dummy callback for interrupt handling
    def example_callback(pin):
        logging.info(f"Interrupt received on GPIO pin {pin}")

    # Wait for interrupts with the callback
    GPIOManager.wait_for_interrupt(interrupt_lines, example_callback)
    GPIOManager.clean()
