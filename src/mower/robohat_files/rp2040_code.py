"""
RP2040 Code for Donkey Car Driver

This script is designed to run on RP2040-based boards such as the Raspberry Pi
Pico and KB2040. It handles RC control, serial communication, and motor
control for the RoboHAT MM1.

Features:
- Reads RC signals and processes them for steering and throttle.
- Handles serial communication with a Raspberry Pi for remote control.
- Supports both RC and serial control modes.
- Provides encoder feedback for motor position.

Dependencies:
- CircuitPython 9.x

Last Updated: 10/07/2024
"""

import time
import board  # type:ignore
import busio  # type:ignore
import neopixel  # type:ignore
from pulseio import PulseIn  # type:ignore
from pwmio import PWMOut  # type:ignore
import digitalio  # type:ignore
import rotaryio  # type:ignore

# Customisation variables
DEBUG = False
USB_SERIAL = True
SMOOTHING_INTERVAL_IN_S = 0.025
ACCEL_RATE = 10
USE_QUADRATURE = False  # Set to False to use regular encoder

# Pin assignments
RC1 = board.GP6
RC2 = board.GP5
RC3 = board.GP4
Steering = board.GP10
Throttle = board.GP11
Encoder1A_pin = board.GP8
Encoder1B_pin = board.GP9
Encoder2A_pin = board.GP13
Encoder2B_pin = board.GP14

if USE_QUADRATURE:
    # Set up the quadrature encoders
    encoder1 = rotaryio.IncrementalEncoder(Encoder1A_pin, Encoder1B_pin)
    encoder2 = rotaryio.IncrementalEncoder(Encoder2A_pin, Encoder2B_pin)
else:
    # Set up pins for regular encoders
    encoder1 = digitalio.DigitalInOut(Encoder1A_pin)
    encoder1.direction = digitalio.Direction.INPUT
    encoder1.pull = digitalio.Pull.DOWN

    encoder2 = digitalio.DigitalInOut(Encoder2A_pin)
    encoder2.direction = digitalio.Direction.INPUT
    encoder2.pull = digitalio.Pull.DOWN

pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)

# cannot have DEBUG and USB_SERIAL
if USB_SERIAL:
    DEBUG = False

# functions


def servo_duty_cycle(pulse_ms, frequency=5):
    """
    Calculate the servo duty cycle for a given pulse width in milliseconds.

    Args:
        pulse_ms (float): The pulse width in milliseconds.
        frequency (int): The frequency of the PWM signal in Hz (default is 60).

    Returns:
        int: The duty cycle value for the servo (16-bit resolution).
    """
    period_ms = 1.0 / frequency * 1000.0
    duty_cycle = int(pulse_ms / 1000 / (period_ms / 65535.0))
    return duty_cycle


def state_changed(control):
    """
    Process and smooth the RC channel values.

    Args:
        control (Control): The RC control object
        containing the channel and value.

    Updates:
        control.value: Smoothed RC value.
    """
    control.channel.pause()
    for i in range(0, len(control.channel)):
        val = control.channel[i]
        # prevent ranges outside of control space
        if val < 1000 or val > 2000:
            continue
        # set new value
        control.value = (control.value + val) / 2
        if control.value > 1475 and control.value < 1525:
            control.value = 1500

    control.channel.clear()
    control.channel.resume()


class Control:
    """
    Represents an RC control channel.

    Attributes:
        name (str): Name of the control (e.g., 'Steering', 'Throttle').
        servo (PWMOut): The PWM output object for the control.
        channel (PulseIn): The RC channel input object.
        value (int): The current value of the control (e.g., 1500 for neutral).
    """

    def __init__(self, name, servo, channel, value):
        """
        Initialize the Control object.

        Args:
            name (str): Name of the control.
            servo (PWMOut): The PWM output object.
            channel (PulseIn): The RC channel input object.
            value (int): Initial value for the control.
        """
        self.name = name
        self.servo = servo
        self.channel = channel
        self.value = value
        self.servo.duty_cycle = servo_duty_cycle(value)


# set up serial UART to Raspberry Pi
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
continuous_mode = False
continuous_delay = 0

position1 = 0
position2 = 0


def main():
    """
    Main loop for the RP2040 code.

    - Reads RC signals and updates steering and throttle values.
    - Handles serial communication with the Raspberry Pi.
    - Switches between RC and serial control modes based on input.
    - Provides encoder feedback for motor position.

    Runs indefinitely.
    """
    global last_update, continuous_mode, continuous_delay, position1, position2
    last_toggle_time = time.monotonic()
    interval = 1  # Seconds
    data = bytearray()
    datastr = ''
    last_input = 0
    steering_val = steering.value
    throttle_val = throttle.value
    led_state = False
    color = (0, 0, 255)
    if not USE_QUADRATURE:
        last_state1 = encoder1.value
        last_state2 = encoder2.value

    while True:
        current_time = time.monotonic()
        got_data = False
        if USE_QUADRATURE:
            # Read the positions from the quadrature encoders
            position1 = encoder1.position
            position2 = encoder2.position
        else:
            # Read the positions from the regular encoders
            current_state1 = encoder1.value
            current_state2 = encoder2.value

            if current_state1 != last_state1:  # encoder1 state changed
                if not current_state1:  # Detect falling edge
                    position1 += 1

            if current_state2 != last_state2:  # encoder2 state changed
                if not current_state2:  # Detect falling edge
                    position2 += 1

            last_state1 = current_state1
            last_state2 = current_state2

        time.sleep(0.01)  # Debounce delay

        if continuous_mode and (
                current_time -
                last_toggle_time >= continuous_delay /
                1000.0):
            uart.write(b"%i, %i, %i, %i; %i, %i\r\n" % (
                int(steering.value), int(throttle.value),
                position1, int(current_time * 1000),
                position2, int(current_time * 1000)))
            last_toggle_time = current_time

        if current_time - last_toggle_time >= interval:
            if led_state:
                pixel.fill((0, 0, 0))  # Turn off the NeoPixel
            else:
                pixel.fill(color)  # Set the NeoPixel to the specified color
            pixel.show()
            led_state = not led_state
            last_toggle_time = current_time

        # only update every smoothing interval (to avoid jumping)
        if last_update + SMOOTHING_INTERVAL_IN_S > current_time:
            continue
        last_update = time.monotonic()

        # check for new RC values (channel will contain data)
        if len(throttle.channel) != 0:
            state_changed(throttle)

        if len(steering.channel) != 0:
            state_changed(steering)

        if USB_SERIAL:
            # simulator USB
            print("%i, %i" % (int(steering.value), int(throttle.value)))
        else:
            # write the RC values to the RPi Serial
            uart.write(
                b"%i, %i\r\n" %
                (int(
                    steering.value), int(
                    throttle.value)))
            # print(int(steering.value), int(throttle.value))

        while True:
            # wait for data on the serial port and read 1 byte
            byte = uart.read(1)

            # if no data, break and continue with RC control
            if byte is None:
                break

            # if data is received, check if it is the end of a stream
            if byte == b'\r':
                command = datastr.strip()
                datastr = ''
                handle_command(command)
                data = bytearray()
                break

            data[len(data):len(data)] = byte
            datastr = ''.join([chr(c) for c in data]).strip()

            # if we make it here, there is serial data from the previous step
            if len(datastr) >= 10:
                steering_val = steering.value
                throttle_val = throttle.value
                try:
                    steering_val = int(datastr[:4])
                    throttle_val = int(datastr[-4:])
                except ValueError:
                    None

                data = bytearray()
                datastr = ''
                got_data = True
        # print("Set: steering=%i, throttle=%i" % (steering_val, throttle_val))
        if got_data:
            print("Serial control")
            # Set the servo for serial data (received)
            steering.servo.duty_cycle = servo_duty_cycle(steering_val)
            throttle.servo.duty_cycle = servo_duty_cycle(throttle_val)
            # Only update here when serial data is received
            last_input = time.monotonic()
            # Timeout to switch back to RC control
        elif time.monotonic() > (last_input + 0.1):
            print("RC control")
            # Set the servo for RC control
            steering.servo.duty_cycle = servo_duty_cycle(steering.value)
            throttle.servo.duty_cycle = servo_duty_cycle(throttle.value)


def handle_command(command):
    """
    Handle commands received via UART.

    Args:
        command (str): The command string received from the Raspberry Pi.

    Commands:
        - 'r': Reset encoder positions to zero.
        - 'p': Send current positions and control values to the Raspberry Pi.
        - 'c': Toggle continuous mode or set delay for continuous updates.
        - 'rc=enable': Enable RC control mode.
        - 'rc=disable': Disable RC control mode and enable serial control.
    """
    global position1, position2, continuous_mode, continuous_delay
    if command == 'r':
        position1 = 0
        position2 = 0
        if USE_QUADRATURE:
            encoder1.position = 0
            encoder2.position = 0
        print("Positions reset to zero")
    elif command == 'p':
        current_time = time.monotonic()
        uart.write(b"%i, %i, %i, %i; %i, %i\r\n" % (
            int(steering.value), int(throttle.value),
            position1, int(current_time * 1000),
            position2, int(current_time * 1000)))
        print("Position sent")
    elif command.startswith('c'):
        if len(command) > 1 and command[1:].isdigit():
            continuous_delay = int(command[1:])
            continuous_mode = True
            print(f"Continuous mode started with {continuous_delay} ms delay")
        else:
            continuous_mode = not continuous_mode
            if continuous_mode:
                print("Continuous mode started with default delay")
            else:
                print("Continuous mode stopped")


# Run the main loop
print("Run!")
main()
