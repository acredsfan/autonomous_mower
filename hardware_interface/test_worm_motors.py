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
    # Reset the GPIO pins
    GPIO.cleanup()

# Enable motors
GPIO.output(13, GPIO.HIGH)
GPIO.output(16, GPIO.HIGH)

# Test the motors
try:
    set_direction('FORWARD', 'FORWARD')  # Set both motors to move forward
    time.sleep(5)  # Run the motors for 5 seconds
finally:
    cleanup()