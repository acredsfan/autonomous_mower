"""
rp2040_code.py - Hybrid: RC input by default, can be disabled via UART.

Changes:
- Safe NeoPixel import for boards without onboard LED.
- PulseIn resume() calls added.
- Servo PWM frequency set to 50 Hz (standard).
- Memory‑safe RC pulse read.
- Bounded UART command buffer.
- Avoid frequent supervisor.reload(); soft‑reset after several errors.
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
rc_control_enabled = True  # Global toggle

# ---------------- Pin definitions ---------------- #
RC1 = board.GP6         # Steering input from real RC
RC2 = board.GP5         # Throttle input from real RC

STEERING_PIN = board.GP10
THROTTLE_PIN = board.GP11

ENCODER1A_PIN = board.GP8
ENCODER1B_PIN = board.GP9
# -------------------------------------------------- #

# Servo PWM objects at 50 Hz
steering_pwm = PWMOut(STEERING_PIN, duty_cycle=0, frequency=50)
throttle_pwm = PWMOut(THROTTLE_PIN, duty_cycle=0, frequency=50)

# RC reading channels
rc_steering_in = PulseIn(RC1, maxlen=32, idle_state=0)
rc_throttle_in = PulseIn(RC2, maxlen=32, idle_state=0)
rc_steering_in.resume()
rc_throttle_in.resume()

# Basic on‑board LED
led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT
led.value = True

# Safe NeoPixel (many RP2040‑Zero boards have no built‑in pixel)
try:
    pixel = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.2)
except AttributeError:
    pixel = None

# UART for Pi ↔ RP2040
try:
    uart = busio.UART(
        board.TX,
        board.RX,
        baudrate=115200,
        timeout=0.1,
        receiver_buffer_size=64,
    )
except Exception:  # pragma: no cover
    # Blink rapidly and halt if UART fails
    while True:
        led.value = not led.value
        time.sleep(0.1)

# ------------- Helper functions ------------------ #


def us_to_duty(us: int, freq: int = 50) -> int:
    """Convert microseconds (1000‑2000) to 16‑bit duty cycle."""
    period_ms = 1000.0 / freq  # 20 ms for 50 Hz
    return int((us / 1000.0) / (period_ms / 65535.0))


def read_last_pulse(chan: PulseIn) -> int | None:
    """Return the most recent valid pulse width in μs, or None."""
    if len(chan) == 0:
        return None
    val = chan[-1]
    if 1000 <= val <= 2000:
        return val
    return None

# -------------------------------------------------- #


def handle_uart_step() -> None:
    """Process one byte from UART and handle commands."""
    if not uart:
        return
    data = uart.read(1)
    if not data:
        return

    char = data.decode(errors="ignore")
    if not hasattr(handle_uart_step, "buffer"):
        handle_uart_step.buffer = ""
    buffer: str = handle_uart_step.buffer

    if char == "\r":
        process_command(buffer.strip().lower())
        handle_uart_step.buffer = ""
    else:
        if len(buffer) < 64:
            handle_uart_step.buffer = buffer + char
        else:
            # Prevent runaway allocation
            handle_uart_step.buffer = ""


def process_command(cmd: str) -> None:
    """Execute a single text command coming from Pi."""
    global rc_control_enabled

    if cmd == "rc=enable":
        rc_control_enabled = True
        uart.write(b"rc=enable\r\n")
    elif cmd == "rc=disable":
        rc_control_enabled = False
        uart.write(b"rc=disable\r\n")
    elif "," in cmd:
        try:
            s_str, t_str = (p.strip() for p in cmd.split(",", 1))
            s_val = int(s_str)
            t_val = int(t_str)
        except ValueError:
            uart.write(b"parse_error\r\n")
            return

        uart.write(f"{s_val},{t_val}\r\n".encode())
        if not rc_control_enabled:
            steering_pwm.duty_cycle = us_to_duty(s_val)
            throttle_pwm.duty_cycle = us_to_duty(t_val)
    else:
        uart.write(b"unknown_cmd\r\n")


def apply_rc_if_enabled() -> None:
    """Apply incoming RC PWM to outputs when RC mode enabled."""
    if not rc_control_enabled:
        return

    steering_us = read_last_pulse(rc_steering_in)
    throttle_us = read_last_pulse(rc_throttle_in)

    if steering_us is not None:
        steering_pwm.duty_cycle = us_to_duty(steering_us)
    if throttle_us is not None:
        throttle_pwm.duty_cycle = us_to_duty(throttle_us)


# -------------------------------------------------- #

def main() -> None:
    """Main cooperative loop."""
    error_count = 0
    while True:
        try:
            handle_uart_step()
            apply_rc_if_enabled()

            # Simple heartbeat LED
            led.value = not led.value
            if pixel:
                pixel[0] = (0, led.value * 20, 0)

            time.sleep(0.01)
            error_count = 0
        except Exception:  # pragma: no cover
            # Minimal error backoff
            error_count += 1
            uart.write(b"error\r\n")
            for _ in range(4):
                led.value = not led.value
                time.sleep(0.05)
            if error_count >= 3:
                supervisor.reload()


if __name__ == "__main__":
    print("RP2040 control firmware starting.")
    main()
