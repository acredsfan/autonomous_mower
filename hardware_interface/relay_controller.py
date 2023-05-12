# Code to control the 12V 2 channel relay module

#IMPORTS
import RPi.GPIO as GPIO
import time

#CONSTANTS
SPEED_CONTROLLER_PIN = 5
MOWER_BLADES_PIN = 6

#VARIABLES
relay_controller_state = False
mower_blades_state = False

#FUNCTIONS
class RelayController:
#init_relay_controller
    #initializes the relay controller
    def init_relay_controller():
        GPIO.setup(SPEED_CONTROLLER_PIN, GPIO.OUT)
        GPIO.setup(MOWER_BLADES_PIN, GPIO.OUT)

    #toggle_mower_blades
    #toggles the mower blades connected to GPIO 6
    def toggle_mower_blades():
        global mower_blades_state
        if mower_blades_state == False:
            GPIO.output(MOWER_BLADES_PIN, GPIO.HIGH)
            mower_blades_state = True
        else:
            GPIO.output(MOWER_BLADES_PIN, GPIO.LOW)
            mower_blades_state = False

    #toggle_speed_controller
    #toggles the speed controller connected to GPIO 5
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
    def set_speed_controller(state):
        global relay_controller_state
        if state == "on":
            GPIO.output(SPEED_CONTROLLER_PIN, GPIO.HIGH)
            relay_controller_state = True
        else:
            GPIO.output(SPEED_CONTROLLER_PIN, GPIO.LOW)
            relay_controller_state = False

    #set_mower_blades
    #sets the mower blades connected to GPIO 6
    def set_mower_blades(state):
        global mower_blades_state
        if state == "on":
            GPIO.output(MOWER_BLADES_PIN, GPIO.HIGH)
            mower_blades_state = True
        else:
            GPIO.output(MOWER_BLADES_PIN, GPIO.LOW)
            mower_blades_state = False

    #END OF FILE