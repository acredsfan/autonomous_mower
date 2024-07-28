import gpiod
import time
import logging
import threading

# Initialize logging
logging.basicConfig(filename='/home/pi/autonomous_mower/main.log', level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')

# Print available GPIO chips
logging.debug("Available GPIO chips: %s", os.listdir('/dev/'))

# Define the GPIO chip and lines
chip = gpiod.Chip('gpiochip0')
IN1 = chip.get_line(24)
IN2 = chip.get_line(25)

# Configure the lines as outputs
IN1.request(consumer='blade_controller', type=gpiod.LINE_REQ_DIR_OUT)
IN2.request(consumer='blade_controller', type=gpiod.LINE_REQ_DIR_OUT)

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
pwm1 = PWM(IN1, freq)
pwm2 = PWM(IN2, freq)

# Start PWM with 0% duty cycle (off)
pwm1.start(0)
pwm2.start(0)

class BladeController:
    blades_on = False  # Class attribute to track blade state

    # Function to set the motor speed
    @staticmethod
    def set_speed(speed):
        if speed > 0:
            # Forward
            pwm1.ChangeDutyCycle(speed)
            pwm2.ChangeDutyCycle(0)
            BladeController.blades_on = True  # Blades are on
        elif speed < 0:
            # Reverse
            pwm1.ChangeDutyCycle(0)
            pwm2.ChangeDutyCycle(-speed)
            BladeController.blades_on = True  # Blades are on
        else:
            # Stop
            pwm1.ChangeDutyCycle(0)
            pwm2.ChangeDutyCycle(0)
            BladeController.blades_on = False  # Blades are off

    @staticmethod
    def stop():
        pwm1.stop()
        pwm2.stop()
        BladeController.blades_on = False  # Blades are off

# # Try changing the speed
# BladeController.set_speed(50)  # 50% speed forward
# time.sleep(2)  # run for 2 seconds
# BladeController.set_speed(75)
# time.sleep(2)
# BladeController.set_speed(100)
# time.sleep(2)
# BladeController.set_speed(75)
# time.sleep(2)
# BladeController.set_speed(50)
# time.sleep(2)
# BladeController.set_speed(10)
# time.sleep(2)
# BladeController.set_speed(0)  # stop
# BladeController.set_speed(-50)  # 50% speed reverse
# time.sleep(2)  # run for 2 seconds
# BladeController.set_speed(-10)
# time.sleep(2)
# BladeController.set_speed(0)  # stop

# # Cleanup
# BladeController.stop()
