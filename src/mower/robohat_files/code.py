# code.py — UART + Console dual logging firmware for RoboHAT RP2040‑Zero
#
# • log() writes to both USB console (print) and hardware UART
# • Startup banner, init steps, RX bytes, commands all visible on /dev/serial0
# • Retains PWM & RC‑fallback features
# Revision 2025‑04‑18‑dual

import time
import board  # type: ignore
import supervisor  # type: ignore
import digitalio  # type: ignore
import busio  # type: ignore
from pwmio import PWMOut  # type: ignore
from pulseio import PulseIn  # type: ignore
import traceback  # type: ignore

# —————————————————————————————————————————————————————
# Setup UART (GP0=TX, GP1=RX)
uart = busio.UART(board.GP0, board.GP1, baudrate=115200, timeout=0.1)

def log(msg: str) -> None:
    """Log to USB console and hardware UART."""
    print(msg)
    try:
        uart.write((msg + "\r\n").encode())
    except Exception:
        pass

log(">>> code.py starting (dual-logging build)")

# LED init
try:
    led = digitalio.DigitalInOut(board.LED)
    led.direction = digitalio.Direction.OUTPUT
    log("LED initialized")
except Exception as e:
    log(f"LED init failed: {e}")
    led = None

# Send startup banner
log("RP2040_UART_READY")

# PWM outputs
try:
    steering_pwm = PWMOut(board.GP10, duty_cycle=0, frequency=50)
    throttle_pwm = PWMOut(board.GP11, duty_cycle=0, frequency=50)
    log("PWM outputs initialized (GP10/GP11)")
except Exception as e:
    log(f"PWM init failed: {e}")
    supervisor.reload()

# PulseIn inputs (RC fallback)
try:
    rc_steering_in = PulseIn(board.GP6, maxlen=32, idle_state=0)
    rc_throttle_in = PulseIn(board.GP5, maxlen=32, idle_state=0)
    rc_steering_in.resume()
    rc_throttle_in.resume()
    log("PulseIn inputs initialized (GP6/GP5)")
except Exception as e:
    log(f"PulseIn init failed: {e}")

rc_control_enabled = True

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
    log(f"Processing cmd: {cmd}")
    if cmd == "rc=disable":
        rc_control_enabled = False
        uart.write(b"rc=disable\r\n")
    elif cmd == "rc=enable":
        rc_control_enabled = True
        uart.write(b"rc=enable\r\n")
    elif "," in cmd:
        try:
            s, t = [int(x.strip()) for x in cmd.split(",",1)]
            uart.write(f"{s},{t}\r\n".encode())
            log(f"Applied steer={s},throttle={t}")
            if not rc_control_enabled:
                steering_pwm.duty_cycle = us_to_duty(s)
                throttle_pwm.duty_cycle = us_to_duty(t)
        except Exception as e:
            uart.write(b"parse_error\r\n")
            log(f"parse_error: {e}")
    else:
        uart.write(b"unknown_cmd\r\n")
        log(f"unknown_cmd: {cmd}")

log("Entering main loop")
buf = ""
errors = 0

while True:
    try:
        data = uart.read(1)
        if data:
            # Always log raw chars
            try:
                ch = data.decode("utf-8")
            except:
                ch = repr(data)
            log(f"HW_RX: {ch}")
            if ch == "\r":
                process_cmd(buf)
                buf = ""
            elif ch != "\n":
                buf = (buf + ch)[-64:]

        # RC fallback
        if rc_control_enabled:
            s_us = read_last_pulse(rc_steering_in)
            t_us = read_last_pulse(rc_throttle_in)
            if s_us is not None:
                steering_pwm.duty_cycle = us_to_duty(s_us)
            if t_us is not None:
                throttle_pwm.duty_cycle = us_to_duty(t_us)

        if led:
            led.value = not led.value

        time.sleep(0.01)
        errors = 0

    except Exception as e:
        errors += 1
        log(f"Loop exception: {e}")
        traceback.print_exc()
        uart.write(b"error\r\n")
        if errors >= 3:
            supervisor.reload()
