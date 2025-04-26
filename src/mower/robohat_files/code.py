"""
rp2040_code.py - Hybrid: RC input by default, can be disabled via UART
"""

import time
import board
import busio
import neopixel
from pulseio import PulseIn
from pwmio import PWMOut

USB_SERIAL = False
rc_control_enabled = True  # <--- This is our global toggle

# RC input pins
RC1 = board.GP6  # steering input from real RC
RC2 = board.GP5  # throttle input from real RC

# PWM output pins
STEERING_PIN = board.GP10
THROTTLE_PIN = board.GP11

# Encoders or others if needed
Encoder1A_pin = board.GP8
Encoder1B_pin = board.GP9

# Initialize the servo PWM objects at ~60Hz
steering_pwm = PWMOut(STEERING_PIN, duty_cycle=0, frequency=60)
throttle_pwm = PWMOut(THROTTLE_PIN, duty_cycle=0, frequency=60)

# RC reading
rc_steering_in = PulseIn(RC1, maxlen=64, idle_state=0)
rc_throttle_in = PulseIn(RC2, maxlen=64, idle_state=0)

# Setup UART for Pi <-> Pico
uart = busio.UART(board.TX, board.RX, baudrate=115200, timeout=0.001)

# For a NeoPixel “heartbeat”
pixel = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.2)

# Utility to convert microseconds to 16-bit PWM


def us_to_duty(us, freq=60):
    period_ms = 1000.0 / freq  # e.g. ~16.67 ms
    return int((us / 1000.0) / (period_ms / 65535.0))


def handle_command(cmd):
    global rc_control_enabled
    cmd = cmd.strip().lower()
    if cmd == "rc=enable":
        rc_control_enabled = True
        print("RC Control Enabled.")
    elif cmd == "rc=disable":
        rc_control_enabled = False
        print("RC Control Disabled.")
    else:
        # You can add other commands like 'r', 'p', etc.
        print(f"Ignoring unknown cmd: {cmd}")


def read_rc_pulse(rc_in):
    """
    Reads the latest RC pulse from a PulseIn channel,
    returns an integer microseconds (1000..2000) or None if invalid.
    """
    rc_in.pause()
    pulses = [p for p in rc_in]
    rc_in.clear()
    rc_in.resume()

    if not pulses:
        return None  # no new data
    # pick the last valid pulse
    val = pulses[-1]
    if 1000 <= val <= 2000:
        return val
    return None


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

        # 2) Read any serial from Pi
        byte = uart.read(1)
        if byte is not None:
            c = byte.decode(errors="ignore")
            if c == "\r":
                # Reached end of a command
                cmd = buffer_str.strip()
                buffer_str = ""
                handle_command(cmd)
            else:
                buffer_str += c

            # If we gather >=10 chars with a comma => parse
            if len(buffer_str) >= 10 and "," in buffer_str:
                parts = buffer_str.split(",")
                if len(parts) == 2:
                    try:
                        serial_steering = int(parts[0].strip())
                        serial_throttle = int(parts[1].strip())
                        print(
                            f"Serial control => S={serial_steering}, "
                            f"T={serial_throttle}"
                        )
                        # If RC is disabled, apply these pulses
                        if not rc_control_enabled:
                            steering_pwm.duty_cycle = us_to_duty(
                                serial_steering
                            )
                            throttle_pwm.duty_cycle = us_to_duty(
                                serial_throttle
                            )
                    except ValueError:
                        print("Parse error for steering, throttle.")
                buffer_str = ""

        time.sleep(0.01)


print("Run!")
main()
