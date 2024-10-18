
import gpiod

from autonomous_mower.utilities import LoggerConfigInfo as LoggerConfig

# Initialize logger
logging = LoggerConfig.get_logger(__name__)


class GPIOManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GPIOManager, cls).__new__(cls)
            cls.__init__(cls._instance)
        return cls._instance

    def init_gpio(shutdown_pins, interrupt_pins):
        """
        Initialize GPIO pins for shutdown and interrupt.
        :param shutdown_pins: List of GPIO pins for shutdown functionality.
        :param interrupt_pins: List of GPIO pins for interrupt functionality.
        :return: Tuple (shutdown_lines, interrupt_lines)
        """
        chip = gpiod.Chip('gpiochip0')
        shutdown_lines = [chip.get_line(pin) for pin in shutdown_pins]
        interrupt_lines = [chip.get_line(pin) for pin in interrupt_pins]

        for line in shutdown_lines:
            line.request(consumer='shutdown', type=gpiod.LINE_REQ_DIR_OUT)
            line.set_value(0)

        for line in interrupt_lines:
            line.request(consumer='interrupt',
                         type=gpiod.LINE_REQ_EV_FALLING_EDGE)

        return shutdown_lines, interrupt_lines

    @staticmethod
    def wait_for_interrupt(interrupt_lines, callback, timeout=10):
        """
        Waits for an interrupt event on the specified interrupt lines.
        :param interrupt_lines: List of GPIO lines to monitor for interrupts.
        :param callback: Callback function to invoke when an interrupt occurs.
        :param timeout: Timeout for waiting for the interrupt event (in secs).
        """
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
                    logging.info(f"Interrupt detected"
                                 f" on line {event.line.offset()}")
                    callback(event.line.offset())

    @staticmethod
    def clean():
        """Clean up GPIO lines."""
        chip = gpiod.Chip('gpiochip0')
        for line in chip.get_all_lines():
            try:
                line.release()
            except Exception as e:
                logging.error(f"Error releasing GPIO line: {e}")
        chip.close()
        logging.info("GPIO cleanup complete.")


if __name__ == "__main__":
    # Example usage
    shutdown_lines, interrupt_lines = GPIOManager.init_gpio([22, 23], [6, 12])

    # Dummy callback for interrupt handling
    def example_callback(pin):
        logging.info(f"Interrupt received on GPIO pin {pin}")

    # Wait for interrupts with the callback
    GPIOManager.wait_for_interrupt(interrupt_lines, example_callback)
    GPIOManager.clean()
