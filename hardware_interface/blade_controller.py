import RPi.GPIO as GPIO
import time
import logging

# Initialize logging
logging.basicConfig(filename='main.log', level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')

# Set the GPIO mode
GPIO.setmode(GPIO.BCM)

# Set the motor control pins
IN1 = 24
IN2 = 25

# Set the motor control pins as output
GPIO.setup(IN1, GPIO.OUT)
GPIO.setup(IN2, GPIO.OUT)

# Set the frequency for PWM (adjust as needed)
freq = 1000

# Setup PWM
pwm1 = GPIO.PWM(IN1, freq)
pwm2 = GPIO.PWM(IN2, freq)

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
        GPIO.cleanup()
        BladeController.blades_on = False  # Blades are off

# # Try changing the speed
# set_speed(50)  # 50% speed forward
# time.sleep(2)  # run for 2 seconds
# set_speed(75)
# time.sleep(2)
# set_speed(100)
# time.sleep(2)
# set_speed(75)
# time.sleep(2)
# set_speed(50)
# time.sleep(2) 
# set_speed(10)
# time.sleep(2)
# set_speed(0)  # stop
# set_speed(-50)  # 50% speed reverse
# time.sleep(2)  # run for 2 seconds
# set_speed(-10)
# time.sleep(2)
# set_speed(0)  # stop

# # Cleanup
# GPIO.cleanup()