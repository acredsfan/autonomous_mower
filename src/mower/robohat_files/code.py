"""
rp2040_code.py - UART-only control firmware for RoboHAT RP2040‑Zero

• Listens exclusively on hardware UART (board.TX/RX) at 115200 baud
• Sends a startup banner over UART
• Parses commands: rc=enable, rc=disable, and "steer,throttle" tuples
• Applies PWM outputs accordingly

Revision 2025‑04‑17
"""

from __future__ import annotations
import time
import board  # type: ignore
import supervisor  # type: ignore
import digitalio  # type: ignore
from pwmio import PWMOut  # type: ignore
from pulseio import PulseIn  # type: ignore
import busio  # type: ignore

# -----------------------------------------------------------------------------
# Hardware UART setup ---------------------------------------------------------
# Use board.TX (GP0) → Pi RX, board.RX (GP1) ← Pi TX
uart = busio.UART(board.TX, board.RX,
                  baudrate=115200,
                  timeout=0.1,
                  receiver_buffer_size=64)
# Banner to indicate ready state
uart.write(b"RP2040_UART_READY\r\n")

# -----------------------------------------------------------------------------
# Global state ----------------------------------------------------------------
rc_control_enabled = True  # toggled by UART cmd

# -----------------------------------------------------------------------------
# Pin map (change here if needed) ---------------------------------------------
RC1_PIN = board.GP6          # steering PWM in (RC fallback)
RC2_PIN = board.GP5          # throttle PWM in
STEERING_PIN = board.GP10    # steering PWM out
THROTTLE_PIN = board.GP11    # throttle PWM out

# -----------------------------------------------------------------------------
# Hardware peripherals init ---------------------------------------------------
# Servo PWM at 50 Hz
steering_pwm = PWMOut(STEERING_PIN, duty_cycle=0, frequency=50)
throttle_pwm = PWMOut(THROTTLE_PIN, duty_cycle=0, frequency=50)
# RC capture (optional fallback)
rc_steering_in = PulseIn(RC1_PIN, maxlen=32, idle_state=0)
rc_throttle_in = PulseIn(RC2_PIN, maxlen=32, idle_state=0)
rc_steering_in.resume()
rc_throttle_in.resume()

# LED heartbeat (optional)
try:
    led = digitalio.DigitalInOut(board.LED)
    led.direction = digitalio.Direction.OUTPUT
    led.value = True
except (AttributeError, ValueError):
    led = None

# -----------------------------------------------------------------------------
# Helpers ---------------------------------------------------------------------


def us_to_duty(us: int, freq: int = 50) -> int:
    """Convert pulse width in µs (1000‑2000) to 16-bit duty."""
    period_ms = 1000.0 / freq
    return int((us / 1000.0) / (period_ms / 65535.0))


def read_last_pulse(chan: PulseIn) -> int | None:
    if len(chan) == 0:
        return None
    val = chan[-1]
    return val if 1000 <= val <= 2000 else None

# -----------------------------------------------------------------------------
# Command parsing -------------------------------------------------------------


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
            # UART byte read
            if uart.in_waiting:
                ch = uart.read(1)
                if ch:
                    char = ch.decode(errors="ignore")
                    if char == "\r":
                        process_cmd(buffer.strip().lower())
                        buffer = ""
                    else:
                        buffer = (buffer + char)[-64:]
            # RC passthrough if still enabled
            if rc_control_enabled:
                s_us = read_last_pulse(rc_steering_in)
                t_us = read_last_pulse(rc_throttle_in)
                if s_us is not None:
                    steering_pwm.duty_cycle = us_to_duty(s_us)
                if t_us is not None:
                    throttle_pwm.duty_cycle = us_to_duty(t_us)
            # Heartbeat LED
            if led:
                led.value = not led.value
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
    main()
