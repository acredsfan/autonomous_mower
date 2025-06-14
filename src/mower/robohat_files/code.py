# Donkey Car Driver for Robotics Masters Robo HAT MM1
# Adapted for Autonomous Mower Project - FIXED VERSION
#
# Notes:
#   This is to be run using CircuitPython 5.3+
#   Compatible with CircuitPython 5.x through 9.x
#   Pin Assignments for Autonomous Mower Project:
#   - RC inputs: GP6 (steering), GP5 (throttle)
#   - PWM outputs: GP10 (steering to Cytron MDDRC10), GP11 (throttle to Cytron MDDRC10)
#   - Encoders: GP8 (Encoder1A), GP9 (Encoder1B)

import time
import board
import busio
from digitalio import DigitalInOut, Direction

# Handle CircuitPython version differences for PWM and Pulse
try:
    # Try newer CircuitPython (8.x+) 
    from pwmio import PWMOut
    from pulseio import PulseIn
    print("Using pwmio.PWMOut (CircuitPython 8.x+)")
except ImportError:
    try:
        # Fallback to older CircuitPython (5.x-7.x)
        from pulseio import PWMOut, PulseIn
        print("Using pulseio.PWMOut (CircuitPython 5.x-7.x)")
    except ImportError:
        # Last resort - try different module names
        print("ERROR: Cannot import PWMOut from pwmio or pulseio")
        raise

# Simple logging replacement for CircuitPython (no adafruit_logging needed)
class SimpleLogger:
    def __init__(self, name):
        self.name = name
    
    def info(self, msg):
        print("INFO [" + self.name + "]: " + str(msg))
    
    def debug(self, msg):
        if DEBUG:
            print("DEBUG [" + self.name + "]: " + str(msg))
    
    def error(self, msg):
        print("ERROR [" + self.name + "]: " + str(msg))

# Configuration variables
DEBUG = False
USB_SERIAL = False
SMOOTHING_INTERVAL_IN_S = 0.025
ACCEL_RATE = 10

# cannot have DEBUG and USB_SERIAL
if USB_SERIAL:
    DEBUG = False

logger = SimpleLogger('code')

## functions
def servo_duty_cycle(pulse_ms, frequency=60):
    """
    Formula for working out the servo duty_cycle at 16 bit input
    """
    period_ms = 1.0 / frequency * 1000.0
    duty_cycle = int(pulse_ms / 1000 / (period_ms / 65535.0))
    return duty_cycle


class Control:
    """
    Class for a RC Control Channel
    """

    def __init__(self, name, servo, channel, value):
        self.name = name
        self.servo = servo
        self.channel = channel  # Can be None if RC input not available
        self.value = value
        self.servo.duty_cycle = servo_duty_cycle(value)


def state_changed(control):
    """
    Reads the RC channel and smooths value
    """
    if not control.channel:
        return  # Skip if no RC channel available
        
    control.channel.pause()
    for i in range(0, len(control.channel)):
        val = control.channel[i]
        # prevent ranges outside of control space
        if(val < 1000 or val > 2000):
            continue
        # set new value
        control.value = (control.value + val) / 2

    if DEBUG:
        logger.debug(str(time.monotonic()) + "\t" + control.name + " (" + str(len(control.channel)) + "): " + str(int(control.value)) + " (" + str(servo_duty_cycle(control.value)) + ")")
    control.channel.clear()
    control.channel.resume()


# set up on-board LED with fallback for different RP2040 boards
led = None
try:
    # Try common LED pin locations for different RP2040 boards
    if hasattr(board, 'LED'):
        led = DigitalInOut(board.LED)
        print("Using board.LED")
    elif hasattr(board, 'GP25'):
        led = DigitalInOut(board.GP25)
        print("Using GP25 for LED (common RP2040 LED pin)")
    else:
        print("No LED pin available - LED status disabled")
except Exception as e:
    print("LED initialization failed: " + str(e))
    led = None

if led:
    led.direction = Direction.OUTPUT

# set up serial UART to Raspberry Pi
# note UART(TX, RX, baudrate) - using GP0/GP1 (board.TX/RX)
try:
    uart = busio.UART(board.TX, board.RX, baudrate=115200, timeout=0.001)
    print("UART initialized successfully")
except Exception as e:
    print("UART initialization failed: " + str(e))
    raise

# set up servos - PWM outputs to Cytron MDDRC10
# Using project-specific pin assignments with error handling
try:
    steering_pwm = PWMOut(board.GP10, duty_cycle=2 ** 15, frequency=60)  # STEERING_PIN
    print("Steering PWM (GP10) initialized")
except Exception as e:
    print("Steering PWM initialization failed: " + str(e))
    raise

try:
    throttle_pwm = PWMOut(board.GP11, duty_cycle=2 ** 15, frequency=60)  # THROTTLE_PIN
    print("Throttle PWM (GP11) initialized")
except Exception as e:
    print("Throttle PWM initialization failed: " + str(e))
    raise

# set up RC channels - RC inputs from receiver
# Using project-specific pin assignments with error handling
try:
    steering_channel = PulseIn(board.GP6, maxlen=64, idle_state=0)  # RC1 - steering
    print("Steering RC input (GP6) initialized")
except Exception as e:
    print("Steering RC input initialization failed: " + str(e))
    steering_channel = None

try:
    throttle_channel = PulseIn(board.GP5, maxlen=64, idle_state=0)  # RC2 - throttle
    print("Throttle RC input (GP5) initialized")
except Exception as e:
    print("Throttle RC input initialization failed: " + str(e))
    throttle_channel = None

# setup Control objects.  1500 pulse is off and center steering
# Handle case where RC channels might not be available
steering = Control("Steering", steering_pwm, steering_channel, 1500)
throttle = Control("Throttle", throttle_pwm, throttle_channel, 1500)

print("Control objects initialized:")
if steering_channel:
    print("  Steering: PWM=GP10, RC=GP6")
else:
    print("  Steering: PWM=GP10, RC=DISABLED")
if throttle_channel:
    print("  Throttle: PWM=GP11, RC=GP5")
else:
    print("  Throttle: PWM=GP11, RC=DISABLED")

# Hardware Notification: starting
logger.info("preparing to start...")
print("Hardware initialization complete")

# LED startup sequence (only if LED is available)
if led:
    for i in range(0, 2):
        led.value = True
        time.sleep(0.5)
        led.value = False
        time.sleep(0.5)
    print("LED startup sequence complete")
else:
    print("LED not available - skipping startup sequence")
    time.sleep(2)  # Brief pause instead of LED sequence

last_update = time.monotonic()


def main():
    global last_update

    data = bytearray()
    datastr = ''
    last_input = 0
    steering_val = steering.value
    throttle_val = throttle.value

    print("Donkeycar-based RoboHAT MM1 Driver Started")
    print("Pin Config: RC Inputs GP6/GP5, PWM Outputs GP10/GP11")
    print("RC control enabled by default")
    
    while True:
        # only update every smoothing interval (to avoid jumping)
        if(last_update + SMOOTHING_INTERVAL_IN_S > time.monotonic()):
            continue
        last_update = time.monotonic()

        # check for new RC values (channel will contain data)
        # Only process RC if channels are available
        if throttle.channel and len(throttle.channel) != 0:
            state_changed(throttle)

        if steering.channel and len(steering.channel) != 0:
            state_changed(steering)

        if DEBUG:
            logger.info("Get: steering=" + str(int(steering.value)) + ", throttle=" + str(int(throttle.value)))

        # Send RC values to RPi via UART - using bytes directly
        try:
            if USB_SERIAL:
                # simulator USB
                print(str(int(steering.value)) + ", " + str(int(throttle.value)))
            else:
                # write the RC values to the RPi Serial
                # Create bytes message directly - this is the key fix!
                message_str = str(int(steering.value)) + ", " + str(int(throttle.value)) + "\r\n"
                message_bytes = bytes(message_str, 'utf-8')
                uart.write(message_bytes)
        except Exception as e:
            print("UART write error: " + str(e))

        # Read any incoming data from RPi

        while True:
            # wait for data on the serial port and read 1 byte
            try:
                byte = uart.read(1)
            except Exception as e:
                print("UART read error: " + str(e))
                break

            # if no data, break and continue with RC control
            if byte is None:
                break
            last_input = time.monotonic()

            if DEBUG:
                logger.debug("Read from UART: " + str(byte))

            # if data is received, check if it is the end of a stream
            if byte == b'\r':
                data = bytearray()
                break

            data[len(data):len(data)] = byte

        # convert bytearray to string
        datastr = ''.join([chr(c) for c in data]).strip()

        # if we make it here, there is serial data from the previous step
        if len(datastr) >= 9:
            try:
                steer_str, thr_str = datastr.split(',', 1)
                steering_val = int(steer_str)
                throttle_val = int(thr_str)
            except (ValueError, IndexError):
                pass

            data = bytearray()
            datastr = ''
            last_input = time.monotonic()
            logger.info("Set: steering=" + str(int(steering_val)) + ", throttle=" + str(int(throttle_val)))

        # Set servo positions based on control mode
        if last_input + 10 < time.monotonic():
            # set the servo for RC control (default values if RC not connected)
            steering.servo.duty_cycle = servo_duty_cycle(steering.value)
            throttle.servo.duty_cycle = servo_duty_cycle(throttle.value)
        else:
            # set the servo for serial data (received from RPi)
            steering.servo.duty_cycle = servo_duty_cycle(steering_val)
            throttle.servo.duty_cycle = servo_duty_cycle(throttle_val)


# Run
logger.info("Run!")
try:
    main()
except Exception as e:
    print("Main loop error: " + str(e))
    # Keep PWM outputs in safe state
    if 'steering' in locals():
        steering.servo.duty_cycle = servo_duty_cycle(1500)
    if 'throttle' in locals():
        throttle.servo.duty_cycle = servo_duty_cycle(1500)
    raise
