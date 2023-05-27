# Code to control the 12V 2 channel relay module

#IMPORTS
import RPi.GPIO as GPIO
import time

#CONSTANTS
SPEED_CONTROLLER_PIN = 5

#VARIABLES
relay_controller_state = False

# Set up GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(SPEED_CONTROLLER_PIN, GPIO.OUT)

#FUNCTIONS
class RelayController:
    #Set up GPIO
    @staticmethod
    def init():
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(SPEED_CONTROLLER_PIN, GPIO.OUT)

    #toggle_speed_controller
    #toggles the speed controller connected to GPIO 5
    @staticmethod
    def toggle_speed_controller():
        global relay_controller_state
        if relay_controller_state == False:
            GPIO.output(SPEED_CONTROLLER_PIN, GPIO.HIGH)
            relay_controller_state = True
        else:
            GPIO.output(SPEED_CONTROLLER_PIN, GPIO.LOW)
            relay_controller_state = False

    #set_speed_controller
    #sets the speed controller connected to GPIO 5
    @staticmethod
    def set_speed_controller(state):
        global relay_controller_state
        if state == "on":
            GPIO.output(SPEED_CONTROLLER_PIN, GPIO.HIGH)
            relay_controller_state = True
        else:
            GPIO.output(SPEED_CONTROLLER_PIN, GPIO.LOW)
            relay_controller_state = False

    #get_speed_controller_state
    #returns the state of the speed controller connected to GPIO 5
    @staticmethod
    def get_speed_controller_state():
        global relay_controller_state
        return relay_controller_state
    
    #clean_up
    #cleans up the GPIO pins
    @staticmethod
    def clean_up():
        GPIO.cleanup()