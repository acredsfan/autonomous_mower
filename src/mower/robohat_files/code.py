"""
rp2040_code.py - Hybrid: RC input by default, can be disabled via UART
"""

import time
import board  # type: ignore
import busio  # type: ignore
import neopixel  # type: ignore
from pulseio import PulseIn  # type: ignore
from pwmio import PWMOut  # type: ignore
import supervisor  # type: ignore
import digitalio  # type: ignore

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

# Minimal startup LED indicator for debugging
led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT
led.value = True  # Turn on LED to show code.py is running

try:
    # Setup UART for Pi <-> Pico
    uart = busio.UART(board.TX, board.RX, baudrate=115200, timeout=0.1)
except Exception as e:
    # If UART fails, blink LED rapidly and halt
    while True:
        led.value = not led.value
        time.sleep(0.1)

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
        uart.write(b"rc=enable\r\n")
        print("RC Control Enabled.")
    elif cmd == "rc=disable":
        rc_control_enabled = False
        uart.write(b"rc=disable\r\n")
        print("RC Control Disabled.")
    else:
        # You can add other commands like 'r', 'p', etc.
        uart.write((cmd + "\r\n").encode())
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


def handle_uart():
    buffer = ""
    while True:
        try:
            data = uart.read(1)
            if data:
                char = data.decode(errors="ignore")
                if char == "\r":
                    cmd = buffer.strip()
                    buffer = ""
                    try:
                        if cmd == "rc=enable":
                            global rc_control_enabled
                            rc_control_enabled = True
                            uart.write(b"rc=enable\r\n")
                        elif cmd == "rc=disable":
                            rc_control_enabled = False
                            uart.write(b"rc=disable\r\n")
                        elif "," in cmd:
                            parts = cmd.split(",")
                            if len(parts) == 2:
                                s = int(parts[0].strip())
                                t = int(parts[1].strip())
                                uart.write(f"{s}, {t}\r\n".encode())
                                # If RC is disabled, apply these pulses
                                if not rc_control_enabled:
                                    steering_pwm.duty_cycle = us_to_duty(s)
                                    throttle_pwm.duty_cycle = us_to_duty(t)
                            else:
                                uart.write(b"parse_error\r\n")
                        else:
                            uart.write(b"unknown_cmd\r\n")
                    except Exception:
                        uart.write(b"error\r\n")
                else:
                    buffer += char
            # Blink LED to show main loop is alive
            led.value = not led.value
            time.sleep(0.2)
        except Exception as e:
            uart.write(b"error\r\n")
            # Blink LED rapidly to indicate error
            for _ in range(10):
                led.value = not led.value
                time.sleep(0.05)
            # Optionally, soft reset if in a bad state
            supervisor.reload()


if __name__ == "__main__":
    print("Run!")
    handle_uart()
