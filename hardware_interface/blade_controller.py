from .gpio_manager import GPIOManager
import threading
import time
import logging
import sys
import os
from utils import LoggerConfig

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# Initialize logging
LoggerConfig.configure_logging()
logging = logging.getLogger(__name__)

# Initialize GPIO lines using gpio_manager
shutdown_pins = [24, 25]  # GPIO lines for IN1 and IN2
interrupt_pins = []  # No interrupt lines needed here
shutdown_lines, _ = GPIOManager.init_gpio(shutdown_pins, interrupt_pins)


class PWM:
    def __init__(self, line, frequency):
        self.line = line
        self.frequency = frequency
        self.duty_cycle = 0
        self.running = False
        self.thread = None

    def start(self, duty_cycle):
        self.duty_cycle = duty_cycle
        self.running = True
        self.thread = threading.Thread(target=self._run)
        self.thread.start()

    def _run(self):
        period = 1.0 / self.frequency
        while self.running:
            on_time = period * (self.duty_cycle / 100.0)
            off_time = period - on_time
            if self.duty_cycle > 0:
                self.line.set_value(1)
                time.sleep(on_time)
            if self.duty_cycle < 100:
                self.line.set_value(0)
                time.sleep(off_time)

    def ChangeDutyCycle(self, duty_cycle):
        self.duty_cycle = duty_cycle

    def stop(self):
        self.running = False
        if self.thread is not None:
            self.thread.join()
        self.line.set_value(0)


# Set the frequency for PWM (adjust as needed)
freq = 1000

# Setup PWM
pwm1 = PWM(shutdown_lines[0], freq)
pwm2 = PWM(shutdown_lines[1], freq)

# Start PWM with 0% duty cycle (off)
pwm1.start(0)
pwm2.start(0)


class BladeController:
    blades_on = False  # Class attribute to track blade state

    @staticmethod
    def set_speed(speed):
        if speed > 0:
            pwm1.ChangeDutyCycle(speed)
            pwm2.ChangeDutyCycle(0)
            BladeController.blades_on = True
        elif speed < 0:
            pwm1.ChangeDutyCycle(0)
            pwm2.ChangeDutyCycle(-speed)
            BladeController.blades_on = True
        else:
            pwm1.ChangeDutyCycle(0)
            pwm2.ChangeDutyCycle(0)
            BladeController.blades_on = False

    @staticmethod
    def stop():
        pwm1.stop()
        pwm2.stop()
        BladeController.blades_on = False
