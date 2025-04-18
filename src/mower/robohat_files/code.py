"""
Donkey Car Driver for 2040-based boards (Raspberry Pi Pico, KB2040)
====================================================================

This script is designed to run on CircuitPython 9.x and interfaces with RC receivers and a Raspberry Pi via UART.

Features:
---------
- Reads RC PWM signals for steering and throttle via PulseIn.
- Accepts steering/throttle commands from a Raspberry Pi over UART (TX/RX pins).
- Controls servos for steering and throttle using PWM.
- Tracks encoder pulses for position feedback.
- Toggles a NeoPixel LED for status indication.

How to Send Commands via UART (from Raspberry Pi):
--------------------------------------------------
- The Pico expects to receive a string of the form:
    "<ssss>, <tttt>\r\n"
  where:
    - <ssss> is a 4-digit integer for steering PWM (e.g., 1500)
    - <tttt> is a 4-digit integer for throttle PWM (e.g., 1500)
    - Example: b"1500, 1600\r\n"
- The code reads UART input byte-by-byte, accumulating until a carriage return (\r) is received.
- Upon receiving a valid command (at least 10 characters), it parses the first 4 and last 4 digits as steering and throttle values, respectively.

How the Code Determines RC vs UART Control:
-------------------------------------------
- The code always reads RC signals from the receiver (PulseIn on RC1/RC2).
- If UART data has been received in the last 10 seconds, the servos are set using the UART-provided values.
- If no UART data has been received for 10 seconds, the servos revert to RC receiver control.
- This allows seamless fallback to manual RC control if the Pi stops sending commands.

Pin Assignments:
----------------
- RC1, RC2, RC3: PWM input from RC receiver (channels 1-3)
- Steering: PWM output to steering servo
- Throttle: PWM output to throttle ESC
- Encoder1A: Digital input for wheel encoder
- NeoPixel: Status LED
- UART: Serial communication with Raspberry Pi (TX, RX)

Usage:
------
- Flash this script to your CircuitPython board as code.py.
- Connect RC receiver, servos, encoder, and UART as per pin assignments.
- To control from Raspberry Pi, send UART commands as described above.
- The NeoPixel will toggle color every second as a heartbeat indicator.

"""

# Donkey Car Driver for 2040-based boards such as the Raspberry Pi Pico and KB2040
#
# Notes:
#   This is to be run using CircuitPython 9.x
#   Last Updated: 4/08/2024

import time
import board
import busio
import busio
import neopixel
from pulseio import PulseIn
from pwmio import PWMOut
import digitalio


# Customisation these variables
DEBUG = False
USB_SERIAL = False
ENCODER = False
SMOOTHING_INTERVAL_IN_S = 0.01
ACCEL_RATE = 10

# Pin assignments
RC1 = board.GP4
RC2 = board.GP5
RC3 = board.GP6
Steering = board.GP10
Throttle = board.GP11
Encoder1A = board.GP8
Encoder1B = board.GP9
Encoder2A = board.GP13
Encoder2B = board.GP14


# Set up pin for encoder channel
encoder = digitalio.DigitalInOut(Encoder1A)
encoder.direction = digitalio.Direction.INPUT
encoder.pull = digitalio.Pull.DOWN

pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)

## cannot have DEBUG and USB_SERIAL
if USB_SERIAL:
    DEBUG = False

## functions

def servo_duty_cycle(pulse_ms, frequency = 60):
    """
    Formula for working out the servo duty_cycle at 16 bit input
    """
    period_ms = 1.0 / frequency * 1000.0
    duty_cycle = int(pulse_ms / 1000 / (period_ms / 65535.0))
    return duty_cycle


def state_changed(control):
    """
    Reads the RC channel and smooths value
    """
    control.channel.pause()
    for i in range(0, len(control.channel)):
        val = control.channel[i]
        # prevent ranges outside of control space
        if(val < 1000 or val > 2000):
            continue
        # set new value
        control.value = (control.value + val) / 2

    control.channel.clear()
    control.channel.resume()


class Control:
    """
    Class for a RC Control Channel
    """

    def __init__(self, name, servo, channel, value):
        self.name = name
        self.servo = servo
        self.channel = channel
        self.value = value
        self.servo.duty_cycle = servo_duty_cycle(value)


# set up serial UART to Raspberry Pi
# note UART(TX, RX, baudrate)
uart = busio.UART(board.TX, board.RX, baudrate=115200, timeout=0.001)

# set up servos
steering_pwm = PWMOut(Steering, duty_cycle=2 ** 15, frequency=60)
throttle_pwm = PWMOut(Throttle, duty_cycle=2 ** 15, frequency=60)

# set up RC channels.
steering_channel = PulseIn(RC1, maxlen=64, idle_state=0)
throttle_channel = PulseIn(RC2, maxlen=64, idle_state=0)
mode_channel = PulseIn(RC3, maxlen=64, idle_state=0)


# setup Control objects.  1500 pulse is off and center steering
steering = Control("Steering", steering_pwm, steering_channel, 1500)
throttle = Control("Throttle", throttle_pwm, throttle_channel, 1500)

last_update = time.monotonic()

def main():
    global last_update
    last_toggle_time = time.monotonic()
    interval = 1  # Seconds
    data = bytearray()
    datastr = ''
    last_input = 0
    steering_val = steering.value
    throttle_val = throttle.value
    led_state = False
    color=(0, 0, 255)
    position = 0
    last_state = encoder.value


    while True:
        current_time = time.monotonic()
        current_state = encoder.value
        if current_state != last_state:
            if current_state == False:  # Detect falling edge
                position += 1
                print("Position:", position)
        last_state = current_state
        time.sleep(0.01)  # Debounce delay

        if current_time - last_toggle_time >= interval:
            if led_state:
                pixel.fill((0, 0, 0))  # Turn off the NeoPixel
            else:
                pixel.fill(color)  # Set the NeoPixel to the specified color
            pixel.show()
            led_state = not led_state
            last_toggle_time = current_time
        # only update every smoothing interval (to avoid jumping)
        if(last_update + SMOOTHING_INTERVAL_IN_S > current_time):
            continue
        last_update = time.monotonic()

        # check for new RC values (channel will contain data)
        if(len(throttle.channel) != 0):
            state_changed(throttle)

        if(len(steering.channel) != 0):
            state_changed(steering)

        if(USB_SERIAL):
            # simulator USB
            print("%i, %i" % (int(steering.value), int(throttle.value)))
        else:
            # write the RC values to the RPi Serial
            uart.write(b"%i, %i\r\n" % (int(steering.value), int(throttle.value)))
            print(int(steering.value), int(throttle.value))

        while True:
            # wait for data on the serial port and read 1 byte
            byte = uart.read(1)

            # if no data, break and continue with RC control
            if(byte is None):
                break
            last_input = time.monotonic()

            # if data is received, check if it is the end of a stream
            if(byte == b'\r'):
                data = bytearray()
                break

            data[len(data):len(data)] = byte

            # convert bytearray to string
            datastr = ''.join([chr(c) for c in data]).strip()

        # if we make it here, there is serial data from the previous step
        if(len(datastr) >= 10):
            steering_val = steering.value
            throttle_val = throttle.value
            try:
                steering_val = int(datastr[:4])
                throttle_val = int(datastr[-4:])
            except ValueError:
                None

            data = bytearray()
            datastr = ''
            last_input = time.monotonic()
            print("Set: steering=%i, throttle=%i" % (steering_val, throttle_val))

        if(last_input + 10 < time.monotonic()):
            # set the servo for RC control
            steering.servo.duty_cycle = servo_duty_cycle(steering.value)
            throttle.servo.duty_cycle = servo_duty_cycle(throttle.value)
        else:
            # set the servo for serial data (recieved)
            steering.servo.duty_cycle = servo_duty_cycle(steering_val)
            throttle.servo.duty_cycle = servo_duty_cycle(throttle_val)


# Run
print("Run!")
main()
