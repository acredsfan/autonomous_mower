# FROZEN_DRIVER – do not edit (see .github/copilot-instructions.md)
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

# --- hardware constants ------------------------------------------------
STEER_PWM_PIN = board.GP10  # PWM out
THROTTLE_PWM_PIN = board.GP11
STEER_RC_PIN = board.GP6    # RC input
THROTTLE_RC_PIN = board.GP5
TIMEOUT_S = 10              # serial silence before RC‑fallback
LED_BLINK_S = 1             # onboard LED heartbeat

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
    steering_pwm = PWMOut(STEER_PWM_PIN, duty_cycle=2 ** 15, frequency=60)  # STEERING_PIN
    print("Steering PWM (GP10) initialized")
except Exception as e:
    print("Steering PWM initialization failed: " + str(e))
    raise

try:
    throttle_pwm = PWMOut(THROTTLE_PWM_PIN, duty_cycle=2 ** 15, frequency=60)  # THROTTLE_PIN
    print("Throttle PWM (GP11) initialized")
except Exception as e:
    print("Throttle PWM initialization failed: " + str(e))
    raise


# set up RC channels - RC inputs from receiver
# Using project-specific pin assignments with error handling
try:
    steering_channel = PulseIn(STEER_RC_PIN, maxlen=64, idle_state=0)  # RC1 - steering
    print("Steering RC input (GP6) initialized")
except Exception as e:
    print("Steering RC input initialization failed: " + str(e))
    steering_channel = None

try:
    throttle_channel = PulseIn(THROTTLE_RC_PIN, maxlen=64, idle_state=0)  # RC2 - throttle
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



def build_frame(steer: int, thro: int) -> bytes:
    return f"{steer},{thro}\r".encode()

def main():
    global last_update

    data = bytearray()
    datastr = ''
    last_input = 0
    steering_val = steering.value
    throttle_val = throttle.value
    last_blink = time.monotonic()

    print("Donkeycar-based RoboHAT MM1 Driver Started")
    print("Pin Config: RC Inputs GP6/GP5, PWM Outputs GP10/GP11")
    print("RC control enabled by default")

    while True:
        now = time.monotonic()
        # only update every smoothing interval (to avoid jumping)
        if(last_update + SMOOTHING_INTERVAL_IN_S > now):
            continue
        last_update = now

        # LED heartbeat (configurable interval)
        if led and (now - last_blink > LED_BLINK_S):
            led.value = not led.value
            last_blink = now

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
                uart.write(build_frame(int(steering.value), int(throttle.value)))
        except Exception as e:
            print("UART write error: " + str(e))

        # --- serial receive & parse (memory‑safe, frame‑safe) -----------
        while uart.in_waiting:
            byte_val = uart.read(1)
            if not byte_val:
                break
            byte = byte_val[0]          # 0‑255

            if byte == 13:              # '\r' marks end‑of‑frame
                if 4 <= len(data) <= 12:    #  e.g.  "1500,1500"
                    try:
                        steer_s, thro_s = data.decode().split(",", 1)
                        steer   = int(steer_s)
                        thro    = int(thro_s)
                        # discard obviously bad pulses
                        if 1000 <= steer <= 2000 and 1000 <= thro <= 2000:
                            steering_val, throttle_val = steer, thro
                            logger.info(f"Set: steering={steer}, throttle={thro}")
                    except (ValueError, UnicodeError):
                        pass            # ignore malformed frame
                data = bytearray()      # reset buffer every frame
            else:
                if len(data) < 16:      # cap size to avoid runaway
                    data.append(byte)
                else:
                    data = bytearray()  # too long → start fresh


        # Set servo positions based on control mode
        if last_input + TIMEOUT_S < time.monotonic():
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
