from .gpio_manager import GPIOManager
import threading
import time
from utilities import LoggerConfigDebug as LoggerConfig

# Initialize logging
logging = LoggerConfig.get_logger(__name__)

# Initialize GPIO lines
shutdown_pins = [24, 25]  # GPIO lines for IN1 and IN2
shutdown_lines, _ = GPIOManager.init_gpio(shutdown_pins, [])


class PWM:
    def __init__(self, line, frequency=1000):
        """Initialize PWM on a GPIO line with a given frequency."""
        self.line = line
        self.frequency = frequency
        self.duty_cycle = 0
        self.running = False
        self.thread = None

    def start(self, duty_cycle=0):
        """Start the PWM signal with an initial duty cycle."""
        self.duty_cycle = duty_cycle
        self.running = True
        self.thread = threading.Thread(target=self._run)
        self.thread.start()

    def _run(self):
        """Send PWM signals by toggling the GPIO line."""
        period = 1.0 / self.frequency
        while self.running:
            on_time = period * (self.duty_cycle / 100.0)
            off_time = period - on_time

            # Toggle GPIO line
            self.line.set_value(1)
            time.sleep(on_time)
            self.line.set_value(0)
            time.sleep(off_time)

    def change_duty_cycle(self, duty_cycle):
        """Change the PWM duty cycle."""
        logging.info(f"Changing duty cycle to {duty_cycle}%")
        self.duty_cycle = duty_cycle

    def stop(self):
        """Stop the PWM signal."""
        self.running = False
        if self.thread is not None:
            self.thread.join()
        self.line.set_value(0)  # Ensure the motor is off


# Initialize PWM objects for both motor control lines
pwm1 = PWM(shutdown_lines[0])
pwm2 = PWM(shutdown_lines[1])


class BladeController:
    blades_on = False

    @staticmethod
    def set_speed(speed):
        """Set the blade speed via PWM."""
        if speed > 0:
            pwm1.change_duty_cycle(speed)
            pwm2.change_duty_cycle(0)
            BladeController.blades_on = True
            logging.info(f"Blades turned on at speed: {speed}")
        else:
            pwm1.change_duty_cycle(0)
            pwm2.change_duty_cycle(0)
            BladeController.blades_on = False
            logging.info("Blades turned off")

    @staticmethod
    def stop():
        """Stop the blades."""
        pwm1.stop()
        pwm2.stop()
        BladeController.blades_on = False


# Initialize blade controller instance
blade_controller = BladeController()
