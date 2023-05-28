import RPi.GPIO as GPIO
import time

# Set up the GPIO Pins
GPIO.setmode(GPIO.BCM)
GPIO.setup(19, GPIO.OUT)
GPIO.setup(26, GPIO.OUT)
GPIO.setup(20, GPIO.OUT)
GPIO.setup(21, GPIO.OUT)
GPIO.setup(13, GPIO.OUT)
GPIO.setup(16, GPIO.OUT)

# Set up the PWM channels
pwm_A = GPIO.PWM(13, 5000)
pwm_B = GPIO.PWM(16, 5000)

def set_speed(speed_A, speed_B):
    try:
        # Set the duty cycle for each PWM channel
        pwm_A.start(speed_A)
        pwm_B.start(speed_B)
    except Exception as e:
        print("An error occurred while setting the speed: ", str(e))

def set_direction(direction_A, direction_B):
    try:
        # Set the motor direction for Motor A
        if direction_A == 'FORWARD':
            GPIO.output(19, GPIO.HIGH)
            GPIO.output(26, GPIO.LOW)
        else:
            GPIO.output(19, GPIO.LOW)
            GPIO.output(26, GPIO.HIGH)

        # Set the motor direction for Motor B
        if direction_B == 'FORWARD':
            GPIO.output(20, GPIO.HIGH)
            GPIO.output(21, GPIO.LOW)
        else:
            GPIO.output(20, GPIO.LOW)
            GPIO.output(21, GPIO.HIGH)
    except Exception as e:
        print("An error occurred while setting the direction: ", str(e))

def cleanup():
    # Stop the motors
    pwm_A.stop()
    pwm_B.stop()

    # Reset the GPIO pins
    GPIO.cleanup()

# Test the motors
try:
    set_speed(100, 100)  # Set speed for both motors to 50%
    set_direction('FORWARD', 'FORWARD')  # Set both motors to move forward
    time.sleep(5)  # Run the motors for 5 seconds
finally:
    cleanup()