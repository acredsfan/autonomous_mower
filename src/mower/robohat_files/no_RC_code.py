"""
serial_only_rp2040_code.py
A stripped-down version of rp2040_code.py that ignores RC input and uses ONLY serial.
Tested on CircuitPython 9.x for a Pico/KB2040-style board.
"""

import time
import board
import busio
import neopixel
import rotaryio
from pwmio import PWMOut

# --- USER SETTINGS ---
DEBUG = False
USE_QUADRATURE = False  # If True, uses rotaryio.IncrementalEncoder; if False, uses digital input edges
SERIAL_BAUD = 115200
SERIAL_TIMEOUT = 0.001  # 1ms
SERVO_FREQ = 60        # Standard servo frequency
# ----------------------

# Pins
STEERING_PIN = board.GP10
THROTTLE_PIN = board.GP11
ENCODER1A_PIN = board.GP8
ENCODER1B_PIN = board.GP9
ENCODER2A_PIN = board.GP13
ENCODER2B_PIN = board.GP14

# Create a NeoPixel for status (optional)
pixel = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.2)

# Setup the UART to communicate with the Pi
uart = busio.UART(board.TX, board.RX, baudrate=SERIAL_BAUD, timeout=SERIAL_TIMEOUT)

# Setup PWM outputs for servo signals
steering_pwm = PWMOut(STEERING_PIN, duty_cycle=0, frequency=SERVO_FREQ)
throttle_pwm = PWMOut(THROTTLE_PIN, duty_cycle=0, frequency=SERVO_FREQ)

# Encoders (optional)
if USE_QUADRATURE:
    encoder1 = rotaryio.IncrementalEncoder(ENCODER1A_PIN, ENCODER1B_PIN)
    encoder2 = rotaryio.IncrementalEncoder(ENCODER2A_PIN, ENCODER2B_PIN)
else:
    import digitalio
    encoder1A = digitalio.DigitalInOut(ENCODER1A_PIN)
    encoder1B = digitalio.DigitalInOut(ENCODER1B_PIN)
    encoder2A = digitalio.DigitalInOut(ENCODER2A_PIN)
    encoder2B = digitalio.DigitalInOut(ENCODER2B_PIN)
    encoder1A.direction = digitalio.Direction.INPUT
    encoder1B.direction = digitalio.Direction.INPUT
    encoder2A.direction = digitalio.Direction.INPUT
    encoder2B.direction = digitalio.Direction.INPUT
    encoder1A.pull = digitalio.Pull.DOWN
    encoder1B.pull = digitalio.Pull.DOWN
    encoder2A.pull = digitalio.Pull.DOWN
    encoder2B.pull = digitalio.Pull.DOWN

# Track positions
position1 = 0
position2 = 0

# Helper to convert a pulse (in microseconds) to 16-bit PWM duty_cycle
def servo_duty_cycle(us, freq=SERVO_FREQ):
    period_ms = 1000.0 / freq  # e.g. for 60Hz => ~16.67ms
    return int((us / 1000.0) / (period_ms / 65535.0))

# Single-letter commands
def handle_command(cmd_str):
    global position1, position2

    if cmd_str == "r":
        # Reset encoders
        position1 = 0
        position2 = 0
        if USE_QUADRATURE:
            encoder1.position = 0
            encoder2.position = 0
        print("Positions reset to zero")

    elif cmd_str == "p":
        # Print positions
        now_ms = int(time.monotonic() * 1000)
        line = f"{position1}, {position2}, {now_ms}\r\n"
        uart.write(line.encode("utf-8"))
        print(f"Sent positions: {line.strip()}")

    # Add more single-letter commands if desired

def main():
    global position1, position2

    last_color_toggle = time.monotonic()
    led_on = False

    # Give everything a moment to start up
    pixel.fill((0, 0, 255))
    time.sleep(2)
    pixel.fill((0, 0, 0))

    # Pre-fill the servo with a neutral value (1500us)
    steering_pwm.duty_cycle = servo_duty_cycle(1500)
    throttle_pwm.duty_cycle = servo_duty_cycle(1500)

    datastr = ""
    while True:
        now = time.monotonic()

        # 1) Handle LED blink as a “heartbeat”
        if now - last_color_toggle > 1.0:
            pixel.fill((0, 100, 0) if led_on else (0, 0, 0))
            led_on = not led_on
            last_color_toggle = now

        # 2) Update encoders
        if USE_QUADRATURE:
            position1 = encoder1.position
            position2 = encoder2.position
        else:
            # Count falling edges (or however you want to measure)
            pass

        # 3) Read any available bytes from UART
        byte = uart.read(1)
        if byte is not None:
            char = byte.decode("utf-8", errors="ignore")
            if char == "\r":
                # The user pressed Enter or Pi sent \r
                # Check if single-letter command
                cmd = datastr.strip()
                datastr = ""

                # If it’s exactly one letter, treat it as a command
                if len(cmd) == 1:
                    handle_command(cmd)
                elif len(cmd) >= 9 and "," in cmd:
                    # Example: "1500, 1600" => 10 chars w/ space
                    try:
                        parts = cmd.split(",")
                        st_val = int(parts[0])
                        th_val = int(parts[1])
                        # Set servo duty cycle
                        steering_pwm.duty_cycle = servo_duty_cycle(st_val)
                        throttle_pwm.duty_cycle = servo_duty_cycle(th_val)
                        if DEBUG:
                            print(f"Serial control => steer={st_val}, throttle={th_val}")
                    except Exception as e:
                        print(f"Error parsing '{cmd}': {e}")
                else:
                    # Unrecognized
                    print(f"Ignoring: '{cmd}'")

            else:
                # Build up the string
                datastr += char

        # short sleep to avoid hogging CPU
        time.sleep(0.01)

# Entrypoint
if __name__ == "__main__":
    main()
