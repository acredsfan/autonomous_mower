# code.py  —  UART‑only control firmware for RoboHAT RP2040‑Zero
#
# • Listens on hardware UART (GP0→Pi RX, GP1←Pi TX) at 115200 baud
# • Parses rc=enable, rc=disable, “steer,throttle” tuples
# • Applies PWM (50 Hz) to GP10/GP11
# Revision 2025‑04‑17‑gp

import time
import board  # type: ignore
import supervisor  # type: ignore
import digitalio  # type: ignore
from pwmio import PWMOut  # type: ignore
from pulseio import PulseIn  # type: ignore
import busio  # type: ignore

# —————————————————————————————————————————————————————
# Explicit UART pins: GP0=TX, GP1=RX
uart = busio.UART(board.GP0, board.GP1, baudrate=115200, timeout=0.1)
# startup blink & banner
try:
    led = digitalio.DigitalInOut(board.LED)
    led.direction = digitalio.Direction.OUTPUT
    for _ in range(3):
        led.value = not led.value
        time.sleep(0.1)
    led.value = False
except Exception:
    pass
uart.write(b"RP2040_UART_READY\r\n")

# —————————————————————————————————————————————————————
# State
rc_control_enabled = True

# —————————————————————————————————————————————————————
# PWM outputs (50 Hz)
steering_pwm = PWMOut(board.GP10, duty_cycle=0, frequency=50)
throttle_pwm = PWMOut(board.GP11, duty_cycle=0, frequency=50)

# Optional RC fallback inputs
rc_steering_in = PulseIn(board.GP6, maxlen=32, idle_state=0)
rc_throttle_in = PulseIn(board.GP5, maxlen=32, idle_state=0)
rc_steering_in.resume()
rc_throttle_in.resume()
# —————————————————————————————————————————————————————


def us_to_duty(us: int, freq: int = 50) -> int:
    period_ms = 1000.0 / freq
    return int((us / 1000.0) / (period_ms / 65535.0))


def read_last_pulse(chan: PulseIn) -> int | None:
    if len(chan):
        v = chan[-1]
        return v if 1000 <= v <= 2000 else None
    return None


def process_cmd(cmd: str) -> None:
    global rc_control_enabled
    cmd = cmd.strip().lower()
    if cmd == "rc=disable":
        rc_control_enabled = False
        uart.write(b"rc=disable\r\n")
    elif cmd == "rc=enable":
        rc_control_enabled = True
        uart.write(b"rc=enable\r\n")
    elif "," in cmd:
        try:
            s_str, t_str = cmd.split(",", 1)
            s_val = int(s_str.strip())
            t_val = int(t_str.strip())
        except Exception:
            uart.write(b"parse_error\r\n")
            return
        uart.write(f"{s_val},{t_val}\r\n".encode())
        if not rc_control_enabled:
            steering_pwm.duty_cycle = us_to_duty(s_val)
            throttle_pwm.duty_cycle = us_to_duty(t_val)
    else:
        uart.write(b"unknown_cmd\r\n")


# —————————————————————————————————————————————————————
# Main loop
buf = ""
errors = 0
while True:
    try:
        data = uart.read(1)
        if data:
            c = data.decode(errors="ignore")
            if c == "\r":
                process_cmd(buf)
                buf = ""
            elif c != "\n":
                buf = (buf + c)[-64:]

        if rc_control_enabled:
            s_us = read_last_pulse(rc_steering_in)
            t_us = read_last_pulse(rc_throttle_in)
            if s_us is not None:
                steering_pwm.duty_cycle = us_to_duty(s_us)
            if t_us is not None:
                throttle_pwm.duty_cycle = us_to_duty(t_us)

        time.sleep(0.01)
        errors = 0

    except Exception:
        errors += 1
        uart.write(b"error\r\n")
        if errors >= 3:
            supervisor.reload()
