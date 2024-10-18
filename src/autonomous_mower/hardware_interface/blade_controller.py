import threading
import time

from .gpio_manager import GPIOManager
from autonomous_mower.utilities.logger_config import LoggerConfigConfigDebug as LoggerConfig

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
        self.lock = threading.Lock()  # Ensure thread-safe updates

    def start(self, duty_cycle=0):
        """Start the PWM signal with an initial duty cycle."""
        self.duty_cycle = duty_cycle
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()
            logging.info(f"Started PWM with duty cycle {duty_cycle}%")

    def _run(self):
        """Send PWM signals by toggling the GPIO line."""
        period = 1.0 / self.frequency
        while self.running:
            with self.lock:
                on_time = period * (self.duty_cycle / 100.0)
                off_time = period - on_time

            if on_time > 0:
                self.line.set_value(1)
                time.sleep(on_time)
            if off_time > 0:
                self.line.set_value(0)
                time.sleep(off_time)

    def change_duty_cycle(self, duty_cycle):
        """Thread-safe change to the PWM duty cycle."""
        with self.lock:
            self.duty_cycle = duty_cycle
            logging.info(f"Changed duty cycle to {duty_cycle}%")

    def stop(self):
        """Stop the PWM signal."""
        self.running = False
        if self.thread is not None:
            self.thread.join()
        self.line.set_value(0)  # Ensure the motor is off
        logging.info("Stopped PWM")


# Initialize PWM objects for both motor control lines
pwm1 = PWM(shutdown_lines[0])
pwm2 = PWM(shutdown_lines[1])


class BladeController:
    blades_on = False

    @staticmethod
    def set_speed(speed):
        """Set the blade speed via PWM."""
        if speed > 0:
            pwm1.start(speed)  # Start PWM1 with the given speed
            pwm2.stop()  # Ensure PWM2 is off
            BladeController.blades_on = True
            logging.info(f"Blades turned on at speed: {speed}%")
        else:
            BladeController.stop()

    @staticmethod
    def stop():
        """Stop the blades."""
        pwm1.stop()
        pwm2.stop()
        BladeController.blades_on = False
        logging.info("Blades turned off")


# Initialize blade controller instance
blade_controller = BladeController()
