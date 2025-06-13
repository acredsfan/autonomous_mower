# Donkey Car Driver for Robotics Masters Robo HAT MM1
# Adapted for Autonomous Mower Project
#
# Notes:
#   This is to be run using CircuitPython 5.3+
#   Date: 15/05/2019
#   Updated: 20/02/2020
#   Updated: 8/03/2020 (sctse999)
#   Updated: 11/05/2020 (wallarug)
#   Adapted: 2024 (Autonomous Mower Project - Pin assignments for RoboHAT MM1)
#
# Pin Assignments for Autonomous Mower Project:
# - RC inputs: GP6 (steering), GP5 (throttle)
# - PWM outputs: GP10 (steering to Cytron MDDRC10), GP11 (throttle to Cytron MDDRC10)
# - Encoders: GP8 (Encoder1A), GP9 (Encoder1B)

import time
import board
import busio
from digitalio import DigitalInOut, Direction
from pulseio import PWMOut, PulseIn
import adafruit_logging as logging

logger = logging.getLogger('code')
logger.setLevel(logging.INFO)

# Customisation these variables
DEBUG = False
USB_SERIAL = False
SMOOTHING_INTERVAL_IN_S = 0.025
ACCEL_RATE = 10

## cannot have DEBUG and USB_SERIAL
if USB_SERIAL:
    DEBUG = False

# RC reading
rc_steering_in = PulseIn(RC1, maxlen=64, idle_state=0)
rc_throttle_in = PulseIn(RC2, maxlen=64, idle_state=0)

# Setup UART for Pi <-> Pico with enhanced error handling
try:
    if USB_SERIAL:
        # Use USB CDC for communication (development mode)
        uart = usb_cdc.data
        if uart is None:
            print("ERROR: USB CDC not available, falling back to UART")
            uart = busio.UART(board.TX, board.RX, baudrate=115200, timeout=0.001)
            USB_SERIAL = False  # Update flag to reflect actual mode
            print("Using hardware UART for communication (fallback)")
        else:
            print("Using USB CDC for communication")
    else:
        # Use hardware UART for communication (production mode)
        uart = busio.UART(board.TX, board.RX, baudrate=115200, timeout=0.001)
        print("Using hardware UART for communication")
except Exception as e:
    print(f"UART initialization error: {e}")
    # Try fallback mode
    try:
        uart = busio.UART(board.TX, board.RX, baudrate=115200, timeout=0.001)
        USB_SERIAL = False
        print("Using hardware UART for communication (fallback after error)")
    except Exception as e2:
        print(f"UART fallback failed: {e2}")
        uart = None

# For a NeoPixel “heartbeat”
pixel = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.2)

# Utility to convert microseconds to 16-bit PWM duty cycle
def us_to_duty(us, freq=60):
    """Convert microseconds pulse width to PWM duty cycle.
    
    Args:
        us: Pulse width in microseconds (typically 1000-2000 for servo/RC)
        freq: PWM frequency in Hz
        
    Returns:
        int: 16-bit duty cycle value (0-65535)
    """
    if us < 1000:
        us = 1000
    elif us > 2000:
        us = 2000
        
    # Calculate duty cycle for 16-bit PWM (0-65535)
    # For servo PWM: pulse width (us) / period (us) * max_duty_cycle
    period_us = 1000000.0 / freq  # Period in microseconds (e.g. ~16667 us for 60Hz)
    duty_cycle = int((us / period_us) * 65535)
    
    # Ensure duty cycle is within valid range
    if duty_cycle < 0:
        duty_cycle = 0
    elif duty_cycle > 65535:
        duty_cycle = 65535
        
    return duty_cycle


def handle_command(cmd):
    """Handle command strings from the Raspberry Pi.
    
    Commands:
        rc=enable: Enable RC passthrough mode
        rc=disable: Disable RC, enable serial control mode
        status: Report current status and communication info
        comm=usb: Switch to USB CDC mode (if available)
        comm=uart: Switch to UART mode (if available)
    """
    global rc_control_enabled, USB_SERIAL, uart
    cmd = cmd.strip().lower()
    
    if cmd == "rc=enable":
        rc_control_enabled = True
        print("RC Control Enabled - RC passthrough active")
    elif cmd == "rc=disable":
        rc_control_enabled = False
        print("RC Control Disabled - Serial control active")
    elif cmd == "status":
        # Report current status
        comm_mode = "USB_CDC" if USB_SERIAL else "UART"
        rc_status = "enabled" if rc_control_enabled else "disabled"
        print(f"STATUS: RC={rc_status}, COMM={comm_mode}, UART_OK={uart is not None}")
    elif cmd == "comm=usb":
        # Try to switch to USB CDC mode
        try:
            if usb_cdc.data is not None:
                uart = usb_cdc.data
                USB_SERIAL = True
                print("Switched to USB CDC communication")
            else:
                print("USB CDC not available")
        except Exception as e:
            print(f"USB CDC switch failed: {e}")
    elif cmd == "comm=uart":
        # Try to switch to UART mode
        try:
            uart = busio.UART(board.TX, board.RX, baudrate=115200, timeout=0.001)
            USB_SERIAL = False
            print("Switched to UART communication")
        except Exception as e:
            print(f"UART switch failed: {e}")
    else:
        print(f"Unknown command: {cmd}")


def parse_pwm_values(data_str):
    """Parse PWM values from serial data.
    
    Args:
        data_str: String in format "steering,throttle"
        
    Returns:
        tuple: (steering, throttle) as integers or None if invalid
    """
    try:
        parts = data_str.split(",")
        if len(parts) == 2:
            steering = int(parts[0].strip())
            throttle = int(parts[1].strip())
            
            # Validate range (standard RC PWM range)
            if 1000 <= steering <= 2000 and 1000 <= throttle <= 2000:
                return steering, throttle
            else:
                print(f"PWM values out of range: S={steering}, T={throttle}")
                return None
        else:
            print(f"Invalid PWM format: {data_str}")
            return None
    except ValueError as e:
        print(f"Parse error: {e}")
        return None
    """Parse PWM values from serial data.
    
    Args:
        data_str: String in format "steering,throttle"
        
    Returns:
        tuple: (steering, throttle) as integers or None if invalid
    """
    try:
        parts = data_str.split(",")
        if len(parts) == 2:
            steering = int(parts[0].strip())
            throttle = int(parts[1].strip())
            
            # Validate range (standard RC PWM range)
            if 1000 <= steering <= 2000 and 1000 <= throttle <= 2000:
                return steering, throttle
            else:
                print(f"PWM values out of range: S={steering}, T={throttle}")
                return None
        else:
            print(f"Invalid PWM format: {data_str}")
            return None
    except ValueError as e:
        print(f"Parse error: {e}")
        return None


def read_rc_pulse(rc_in):
    """Read the latest RC pulse from a PulseIn channel.
    
    Args:
        rc_in: PulseIn object to read from
        
    Returns:
        int: Pulse width in microseconds (1000-2000) or None if invalid
    """
    # Check if there are any pulses available
    if len(rc_in) == 0:
        return None  # no new data
    
    # Pause to get a consistent read
    rc_in.pause()
    
    # Get the most recent pulse (last one in the buffer)
    # PulseIn in MicroPython stores pulses in microseconds
    try:
        # Get the last pulse from the buffer
        pulse_count = len(rc_in)
        if pulse_count > 0:
            # Access the last pulse directly
            val = rc_in[pulse_count - 1]
        else:
            val = None
    except (IndexError, TypeError):
        val = None
    
    # Clear the buffer and resume
    rc_in.clear()
    rc_in.resume()

    # Validate the pulse is in RC range
    if val is not None and 1000 <= val <= 2000:
        return val
    return None


def apply_pwm_outputs(steering_us, throttle_us):
    """Apply PWM values to output pins for Cytron MDDRC10.
    
    Args:
        steering_us: Steering pulse width in microseconds
        throttle_us: Throttle pulse width in microseconds
    """
    steering_pwm.duty_cycle = us_to_duty(steering_us)
    throttle_pwm.duty_cycle = us_to_duty(throttle_us)


def main():
    # Last known “Serial control” pulses
    serial_steering = 1500
    serial_throttle = 1500

    buffer_str = ""
    last_led = time.monotonic()
    led_on = False

    while True:
        # Basic LED blink
        now = time.monotonic()
        if now - last_led > 1:
            pixel.fill((0, 50, 0) if led_on else (0, 0, 0))
            led_on = not led_on
            last_led = now

        # 1) Read RC pulses if rc_control_enabled
        if rc_control_enabled:
            # read steering
            val_s = read_rc_pulse(rc_steering_in)
            if val_s is not None:
                # set servo
                steering_pwm.duty_cycle = us_to_duty(val_s)

            # read throttle
            val_t = read_rc_pulse(rc_throttle_in)
            if val_t is not None:
                throttle_pwm.duty_cycle = us_to_duty(val_t)

        # 2) Read any serial from Pi (only if UART is available)
        if uart is not None:
            data = uart.read(32)  # Read up to 32 bytes at once
            if data is not None:
                try:
                    text = data.decode('utf-8', errors='ignore')
                    buffer_str += text
                    
                    # Process complete commands (ending with \r or \n)
                    while '\r' in buffer_str or '\n' in buffer_str:
                        # Find the first line ending
                        cr_pos = buffer_str.find('\r')
                        lf_pos = buffer_str.find('\n')
                        
                        if cr_pos >= 0 and (lf_pos < 0 or cr_pos < lf_pos):
                            end_pos = cr_pos
                        else:
                            end_pos = lf_pos
                        
                        # Extract the command
                        cmd = buffer_str[:end_pos].strip()
                        buffer_str = buffer_str[end_pos + 1:]
                        
                        if cmd:
                            # Check if it's a control command
                            if cmd.startswith('rc=') or cmd in ['status'] or cmd.startswith('comm='):
                                handle_command(cmd)
                            elif ',' in cmd:
                                # Parse PWM values
                                pwm_values = parse_pwm_values(cmd)
                                if pwm_values is not None:
                                    serial_steering, serial_throttle = pwm_values
                                    print(f"Serial control => S={serial_steering}, T={serial_throttle}")
                                    
                                    # If RC is disabled, apply these PWM values
                                    if not rc_control_enabled:
                                        apply_pwm_outputs(serial_steering, serial_throttle)
                            else:
                                print(f"Unknown command format: {cmd}")
                    
                    # Prevent buffer overflow
                    if len(buffer_str) > 100:
                        print("Buffer overflow, clearing...")
                        buffer_str = ""
                        
                except Exception as e:
                    print(f"Serial processing error: {e}")
                    buffer_str = ""

        time.sleep(0.01)


print("Run!")
main()
