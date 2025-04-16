from __future__ import annotations
import time
import board  # type: ignore
import digitalio  # type: ignore
import supervisor  # type: ignore

import usb_cdc  # type:ignore
import busio  # type: ignore
from pwmio import PWMOut  # type: ignore
from pulseio import PulseIn  # type: ignore

# -----------------------------------------------------------------------------
#                              Pin assignments
# -----------------------------------------------------------------------------
RC1_PIN = board.GP6          # steering PWM in
RC2_PIN = board.GP5          # throttle PWM in

STEERING_PIN = board.GP10    # steering PWM out
THROTTLE_PIN = board.GP11    # throttle PWM out

# -----------------------------------------------------------------------------
#                          Global state & constants
# -----------------------------------------------------------------------------
USB_SERIAL = False           # reserved for future use
rc_control_enabled = True    # toggle via UART cmd  rc=enable / rc=disable

# -----------------------------------------------------------------------------
#                               Hardware init
# -----------------------------------------------------------------------------
# 50 Hz servo PWM (standard)
steering_pwm = PWMOut(STEERING_PIN, duty_cycle=0, frequency=50)
throttle_pwm = PWMOut(THROTTLE_PIN, duty_cycle=0, frequency=50)

# RC pulse capture
rc_steering_in = PulseIn(RC1_PIN, maxlen=32, idle_state=0)
rc_throttle_in = PulseIn(RC2_PIN, maxlen=32, idle_state=0)
rc_steering_in.resume()
rc_throttle_in.resume()

# Built‑in LED for heartbeat
led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT
led.value = True

# -----------------------------------------------------------------------------
#                         UART / USB‑CDC selection
# -----------------------------------------------------------------------------
# 1) Prefer USB‑CDC data channel (requires boot.py enabling it)
# 2) Fallback to Pi ↔ RP2040 hardware UART if not present
#    or powered only via GPIO

uart = None
if usb_cdc.data is not None and usb_cdc.data.connected:
    uart = usb_cdc.data
else:
    try:
        uart = busio.UART(board.TX, board.RX, baudrate=115200, timeout=0.1,
                          receiver_buffer_size=64)
    except Exception as _:
        # No UART available – blink rapidly & halt
        while True:
            led.value = not led.value
            time.sleep(0.1)

# -----------------------------------------------------------------------------
#                              Helper functions
# -----------------------------------------------------------------------------


def us_to_duty(us: int, freq: int = 50) -> int:
    """Convert microseconds (1000‑2000) to 16‑bit duty."""
    period_ms = 1000.0 / freq
    return int((us / 1000.0) / (period_ms / 65535.0))


def read_last_pulse(chan: PulseIn) -> int | None:
    if len(chan) == 0:
        return None
    val = chan[-1]
    return val if 1000 <= val <= 2000 else None


# -----------------------------------------------------------------------------
#                           Command parser & logic
# -----------------------------------------------------------------------------

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
#                               Main loop
# -----------------------------------------------------------------------------

def main() -> None:
    """Co‑operative loop: UART polling + RC PWM passthrough."""
    buffer = ""
    error_count = 0

    while True:
        try:
            # ---------------- UART polling -----------------
            if uart.in_waiting:
                ch = uart.read(1).decode(errors="ignore")
                if ch == "\r":
                    cmd = buffer.strip().lower()
                    buffer = ""
                    process_cmd(cmd)
                else:
                    buffer = (buffer + ch)[-64:]  # keep last 64 chars

            # ---------------- RC passthrough ---------------
            if rc_control_enabled:
                s_us = read_last_pulse(rc_steering_in)
                t_us = read_last_pulse(rc_throttle_in)
                if s_us is not None:
                    steering_pwm.duty_cycle = us_to_duty(s_us)
                if t_us is not None:
                    throttle_pwm.duty_cycle = us_to_duty(t_us)

            # ---------------- Heartbeat --------------------
            led.value = not led.value
            time.sleep(0.01)
            error_count = 0
        except Exception:
            error_count += 1
            uart.write(b"error\r\n")
            for _ in range(4):
                led.value = not led.value
                time.sleep(0.05)
            if error_count >= 3:
                supervisor.reload()


if __name__ == "__main__":
    print("RP2040 Hybrid Firmware: USB‑CDC ready")
    main()
