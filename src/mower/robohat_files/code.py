"""
rp2040_code.py - Hybrid control firmware for RoboHAT RP2040‑Zero

• Uses USB‑CDC data port for Pi communication (console stays on IF00).
• Gracefully handles boards without `board.LED` or NeoPixel.
• RC PWM passthrough unless Pi disables it.

Revision 2025‑04‑16‑c
"""

from __future__ import annotations
import time
import board  # type: ignore
import supervisor  # type: ignore
import digitalio  # type: ignore
from pwmio import PWMOut  # type: ignore
from pulseio import PulseIn  # type: ignore
import usb_cdc  # type:ignore

# -----------------------------------------------------------------------------
# Safe pin helpers ------------------------------------------------------------

LED_PIN = getattr(board, "LED", None)  # some boards have no board.LED
NEOPIXEL_PIN = getattr(board, "NEOPIXEL", None)

# -----------------------------------------------------------------------------
# Global state ----------------------------------------------------------------

rc_control_enabled = True  # toggled by UART cmd

# -----------------------------------------------------------------------------
# Pin map (change here if needed) ---------------------------------------------

RC1_PIN = board.GP6          # steering PWM in
RC2_PIN = board.GP5          # throttle PWM in

STEERING_PIN = board.GP10    # steering PWM out
THROTTLE_PIN = board.GP11    # throttle PWM out

# -----------------------------------------------------------------------------
# Hardware init ---------------------------------------------------------------

# LED heartbeat (optional)
led = None
if LED_PIN is not None:
    led = digitalio.DigitalInOut(LED_PIN)
    led.direction = digitalio.Direction.OUTPUT
    led.value = True

# NeoPixel heartbeat (optional)
pixel = None
if NEOPIXEL_PIN is not None:
    try:
        import neopixel  # type: ignore
        pixel = neopixel.NeoPixel(NEOPIXEL_PIN, 1, brightness=0.2)
    except ImportError:
        pixel = None

# Servo PWM at 50 Hz
steering_pwm = PWMOut(STEERING_PIN, duty_cycle=0, frequency=50)
throttle_pwm = PWMOut(THROTTLE_PIN, duty_cycle=0, frequency=50)

# RC capture
rc_steering_in = PulseIn(RC1_PIN, maxlen=32, idle_state=0)
rc_throttle_in = PulseIn(RC2_PIN, maxlen=32, idle_state=0)
rc_steering_in.resume()
rc_throttle_in.resume()

# -----------------------------------------------------------------------------
# UART selection --------------------------------------------------------------

if usb_cdc.data is not None and usb_cdc.data.connected:
    uart = usb_cdc.data  # preferred: USB‑CDC IF02
else:
    # Fallback to HW UART on GPIO14/15
    import busio  # type: ignore
    uart = busio.UART(board.TX, board.RX, baudrate=115200, timeout=0.1,
                      receiver_buffer_size=64)

# -----------------------------------------------------------------------------
# Helpers ---------------------------------------------------------------------


def us_to_duty(us: int, freq: int = 50) -> int:
    period_ms = 1000.0 / freq
    return int((us / 1000.0) / (period_ms / 65535.0))


def read_last_pulse(chan: PulseIn) -> int | None:
    if len(chan) == 0:
        return None
    val = chan[-1]
    return val if 1000 <= val <= 2000 else None


# -----------------------------------------------------------------------------
# Command handling ------------------------------------------------------------

def process_cmd(cmd: str) -> None:
    global rc_control_enabled

    if cmd == "rc=enable":
        rc_control_enabled = True
        uart.write(b"rc=enable\r\n")
    elif cmd == "rc=disable":
        rc_control_enabled = False
        uart.write(b"rc=disable\r\n")
    elif "," in cmd:
        try:
            s_str, t_str = cmd.split(",", 1)
            s_val = int(s_str.strip())
            t_val = int(t_str.strip())
        except ValueError:
            uart.write(b"parse_error\r\n")
            return
        uart.write(f"{s_val},{t_val}\r\n".encode())
        if not rc_control_enabled:
            steering_pwm.duty_cycle = us_to_duty(s_val)
            throttle_pwm.duty_cycle = us_to_duty(t_val)
    else:
        uart.write(b"unknown_cmd\r\n")


# -----------------------------------------------------------------------------
# Main loop -------------------------------------------------------------------

def main() -> None:
    buffer = ""
    error_count = 0

    while True:
        try:
            # UART byte‑wise read
            if uart.in_waiting:
                ch = uart.read(1).decode(errors="ignore")
                if ch == "\r":
                    process_cmd(buffer.strip().lower())
                    buffer = ""
                else:
                    buffer = (buffer + ch)[-64:]

            # RC passthrough when enabled
            if rc_control_enabled:
                s_us = read_last_pulse(rc_steering_in)
                t_us = read_last_pulse(rc_throttle_in)
                if s_us is not None:
                    steering_pwm.duty_cycle = us_to_duty(s_us)
                if t_us is not None:
                    throttle_pwm.duty_cycle = us_to_duty(t_us)

            # Heartbeat
            if led:
                led.value = not led.value
            if pixel:
                pixel[0] = (0, int(bool(led) and led.value) * 20, 0)

            time.sleep(0.01)
            error_count = 0
        except Exception:
            error_count += 1
            uart.write(b"error\r\n")
            if led:
                for _ in range(4):
                    led.value = not led.value
                    time.sleep(0.05)
            if error_count >= 3:
                supervisor.reload()


if __name__ == "__main__":
    print("RP2040 Hybrid Firmware (USB‑CDC data mode)")
    main()
