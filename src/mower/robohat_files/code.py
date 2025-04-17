"""
code.py  —  UART‑only control firmware for RoboHAT RP2040‑Zero

• Listens on hardware UART (GP0/GP1) at 115200 baud
• Parses rc=enable, rc=disable, “steer,throttle” tuples
• Applies PWM (50 Hz) to pins GP10/GP11
Revision 2025‑04‑17
"""

import time
import board  # type: ignore
import supervisor  # type: ignore
import digitalio  # type: ignore
from pwmio import PWMOut  # type: ignore
from pulseio import PulseIn  # type: ignore
import busio  # type: ignore

# ——————————————————————————————————————————————
# UART setup (GP0→Pi RX, GP1←Pi TX)
uart = busio.UART(board.TX, board.RX, baudrate=115200, timeout=0.1)
uart.write(b"RP2040_UART_READY\r\n")

# ——————————————————————————————————————————————
# State
rc_control_enabled = True

# ——————————————————————————————————————————————
# Pin mapping
RC1_PIN = board.GP6
RC2_PIN = board.GP5
STEERING_PIN = board.GP10
THROTTLE_PIN = board.GP11

# ——————————————————————————————————————————————
# PWM outputs (50 Hz for servos/motors)
steering_pwm = PWMOut(STEERING_PIN, duty_cycle=0, frequency=50)
throttle_pwm = PWMOut(THROTTLE_PIN, duty_cycle=0, frequency=50)

# Optional RC fallback inputs
rc_steering_in = PulseIn(RC1_PIN, maxlen=32, idle_state=0)
rc_throttle_in = PulseIn(RC2_PIN, maxlen=32, idle_state=0)
rc_steering_in.resume()
rc_throttle_in.resume()

# Heartbeat LED if available
try:
    led = digitalio.DigitalInOut(board.LED)
    led.direction = digitalio.Direction.OUTPUT
    led.value = True
except Exception:
    led = None

# ——————————————————————————————————————————————


def us_to_duty(us: int, freq: int = 50) -> int:
    period_ms = 1000.0 / freq
    return int((us / 1000.0) / (period_ms / 65535.0))


def read_last_pulse(chan: PulseIn) -> int | None:
    if len(chan) == 0:
        return None
    v = chan[-1]
    return v if 1000 <= v <= 2000 else None


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
            s, t = [int(x.strip()) for x in cmd.split(",", 1)]
        except Exception:
            uart.write(b"parse_error\r\n")
            return
        uart.write(f"{s},{t}\r\n".encode())
        if not rc_control_enabled:
            steering_pwm.duty_cycle = us_to_duty(s)
            throttle_pwm.duty_cycle = us_to_duty(t)
    else:
        uart.write(b"unknown_cmd\r\n")


def main() -> None:
    buf = ""
    err = 0
    while True:
        try:
            # UART parsing
            if uart.in_waiting:
                ch = uart.read(1)
                if ch:
                    c = ch.decode(errors="ignore")
                    if c == "\r":
                        process_cmd(buf.lower().strip())
                        buf = ""
                    else:
                        buf = (buf + c)[-64:]
            # RC fallback
            if rc_control_enabled:
                s_us = read_last_pulse(rc_steering_in)
                t_us = read_last_pulse(rc_throttle_in)
                if s_us is not None:
                    steering_pwm.duty_cycle = us_to_duty(s_us)
                if t_us is not None:
                    throttle_pwm.duty_cycle = us_to_duty(t_us)
            # LED heartbeat
            if led:
                led.value = not led.value
            time.sleep(0.01)
            err = 0
        except Exception:
            err += 1
            uart.write(b"error\r\n")
            if led:
                for _ in range(4):
                    led.value = not led.value
                    time.sleep(0.05)
            if err >= 3:
                supervisor.reload()


if __name__ == "__main__":
    main()
