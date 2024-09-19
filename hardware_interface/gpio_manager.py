
import gpiod
from utilities import LoggerConfigInfo as LoggerConfig

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
        chip = gpiod.Chip('gpiochip0')
        shutdown_lines = [chip.get_line(pin) for pin in shutdown_pins]
        interrupt_lines = [chip.get_line(pin) for pin in interrupt_pins]

        for line in shutdown_lines:
            line.request(consumer='shutdown', type=gpiod.LINE_REQ_DIR_OUT)
            line.set_value(0)

        for line in interrupt_lines:
            line.request(
                consumer='interrupt',
                type=gpiod.LINE_REQ_EV_FALLING_EDGE)

        return shutdown_lines, interrupt_lines

    def clean():
        chip = gpiod.Chip('gpiochip0')
        for line in chip.get_all_lines():
            try:
                line.release()
            except Exception as e:
                logging.error(f"Error releasing GPIO line: {e}")
        chip.close()
        logging.info("GPIO cleanup complete.")


if __name__ == "__main__":
    GPIOManager.init_gpio([22, 23], [6, 12])
    GPIOManager.clean()
