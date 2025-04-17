# code.py — UART + Console dual logging firmware for RoboHAT RP2040‑Zero
#
# • log() writes to both USB console (print) and hardware UART
# • Startup banner, init steps, RX bytes, commands all visible on /dev/serial0
# • Retains PWM & RC‑fallback features
# Revision 2025-04-18-isolate-pulsein

import time
import board  # type: ignore
import supervisor  # type: ignore
import digitalio  # type: ignore
import busio  # type: ignore
from pwmio import PWMOut  # type: ignore
from pulseio import PulseIn  # type: ignore
import traceback  # type: ignore
import microcontroller # For CPU temp/freq if needed later

# —————————————————————————————————————————————————————
# Configuration
# —————————————————————————————————————————————————————
UART_BAUD = 115200
UART_TX_PIN = board.GP0
UART_RX_PIN = board.GP1
PWM_STEERING_PIN = board.GP10
PWM_THROTTLE_PIN = board.GP11
RC_STEERING_PIN = board.GP6
RC_THROTTLE_PIN = board.GP5
# *** IMPORTANT: Verify this is the correct LED pin for your RP2040-Zero board! ***
LED_PIN = board.GP25
PWM_FREQUENCY = 50
LOOP_DELAY_SECONDS = 0.01 # Small delay to yield time

# —————————————————————————————————————————————————————
# Setup UART (GP0=TX, GP1=RX)
# —————————————————————————————————————————————————————
uart = None # Initialize uart to None
try:
    uart = busio.UART(UART_TX_PIN, UART_RX_PIN, baudrate=UART_BAUD, timeout=0.01) # Reduced timeout slightly
    # Initial log attempt via print only, as UART might not be ready for log() yet
    print("UART initialized")
except Exception as e:
    print(f"UART init failed: {e}")
    # supervisor.reload()

# —————————————————————————————————————————————————————
# Dual Logging Function
# —————————————————————————————————————————————————————
def log(msg: str) -> None:
    """Log to USB console and hardware UART."""
    print(msg)
    if uart:
        try:
            if not msg.endswith('\r\n'):
                msg += '\r\n'
            uart.write(msg.encode('utf-8'))
        except Exception as e:
            print(f"UART write error: {e}") # Log UART write errors to console only

log(">>> code.py starting (dual-logging build)")

# —————————————————————————————————————————————————————
# LED Initialization
# —————————————————————————————————————————————————————
led = None
try:
    led = digitalio.DigitalInOut(LED_PIN)
    led.direction = digitalio.Direction.OUTPUT
    led.value = False
    log(f"LED initialized on pin: {LED_PIN}")
except AttributeError:
    log(f"LED init failed: Pin {LED_PIN} not found or invalid.")
except Exception as e:
    log(f"LED init failed: {e}")

if led:
    led.value = True
    time.sleep(0.1)
    led.value = False

# —————————————————————————————————————————————————————
# Send Startup Banner
# —————————————————————————————————————————————————————
log("RP2040_UART_READY")

# —————————————————————————————————————————————————————
# PWM Outputs
# —————————————————————————————————————————————————————
steering_pwm = None
throttle_pwm = None
try:
    steering_pwm = PWMOut(PWM_STEERING_PIN, duty_cycle=0, frequency=PWM_FREQUENCY)
    throttle_pwm = PWMOut(PWM_THROTTLE_PIN, duty_cycle=0, frequency=PWM_FREQUENCY)
    log(f"PWM outputs initialized (Steering: {PWM_STEERING_PIN}, Throttle: {PWM_THROTTLE_PIN})")
except Exception as e:
    log(f"PWM init failed: {e}")
    log("Reloading due to PWM init failure...")
    time.sleep(1)
    supervisor.reload()

# —————————————————————————————————————————————————————
# PulseIn Inputs (RC fallback) - Still initialize, but won't read in loop for now
# —————————————————————————————————————————————————————
rc_steering_in = None
rc_throttle_in = None
try:
    rc_steering_in = PulseIn(RC_STEERING_PIN, maxlen=32, idle_state=0)
    rc_throttle_in = PulseIn(RC_THROTTLE_PIN, maxlen=32, idle_state=0)
    rc_steering_in.clear()
    rc_throttle_in.clear()
    rc_steering_in.resume()
    rc_throttle_in.resume()
    log(f"PulseIn inputs initialized (Steering: {RC_STEERING_PIN}, Throttle: {RC_THROTTLE_PIN})")
except Exception as e:
    log(f"PulseIn init failed: {e}")

# —————————————————————————————————————————————————————
# Global State
# —————————————————————————————————————————————————————
rc_control_enabled = True # Keep state logic, though it won't be applied for now
last_rc_steer_us = 1500
last_rc_throttle_us = 1500
last_cmd_steer_us = 1500
last_cmd_throttle_us = 1500

# —————————————————————————————————————————————————————
# Helper Functions (us_to_duty not used in loop currently)
# —————————————————————————————————————————————————————
def us_to_duty(us: int, freq: int = PWM_FREQUENCY) -> int:
    """Converts microseconds pulse width to PWM duty cycle (0-65535)."""
    period_ms = 1000.0 / freq
    us_clamped = max(1000, min(2000, us))
    duty = int((us_clamped / 1000.0) * (65535.0 / period_ms))
    return max(0, min(65535, duty))

def read_last_pulse(chan: PulseIn | None) -> int | None:
    """Reads the most recent valid pulse (1000-2000us) from a PulseIn channel."""
    # *** TEMPORARILY DISABLED FOR DEBUGGING ***
    # if chan is None or len(chan) == 0:
    #     return None
    # try:
    #     pulse_us = chan[-1]
    #     chan.clear()
    #     if 1000 <= pulse_us <= 2000:
    #         return pulse_us
    #     else:
    #         return None
    # except Exception as e:
    #     log(f"Error reading PulseIn: {e}")
    #     return None
    return None # Always return None while disabled

# —————————————————————————————————————————————————————
# Command Processing (Simplified - doesn't apply PWM directly now)
# —————————————————————————————————————————————————————
def process_cmd(cmd: str) -> None:
    """Processes a command received via UART."""
    global rc_control_enabled, last_cmd_steer_us, last_cmd_throttle_us
    cmd = cmd.strip().lower()
    log(f"Processing cmd: '{cmd}'")

    if not cmd: return

    if cmd == "rc=disable":
        rc_control_enabled = False
        log("RC control DISABLED")
        uart.write(b"ack:rc=disable\r\n")
    elif cmd == "rc=enable":
        rc_control_enabled = True
        log("RC control ENABLED")
        uart.write(b"ack:rc=enable\r\n")
    elif "," in cmd:
        try:
            parts = cmd.split(",", 1)
            s_str = parts[0].strip()
            t_str = parts[1].strip()
            if not s_str.isdigit() or not t_str.isdigit():
                 raise ValueError("Non-digit characters")
            s = int(s_str)
            t = int(t_str)
            if not (1000 <= s <= 2000 and 1000 <= t <= 2000):
                raise ValueError(f"Values out of range (1000-2000)")

            last_cmd_steer_us = s
            last_cmd_throttle_us = t
            log(f"Command stored: steer={s}, throttle={t}")

            # *** PWM update TEMPORARILY DISABLED FOR DEBUGGING ***
            # if not rc_control_enabled:
            #     log(f"Applying command: steer={s}, throttle={t}")
            #     if steering_pwm: steering_pwm.duty_cycle = us_to_duty(s)
            #     if throttle_pwm: throttle_pwm.duty_cycle = us_to_duty(t)

            uart.write(f"ack:{s},{t}\r\n".encode('utf-8'))

        except ValueError as e:
            log(f"Cmd parse/value error: {e} for '{cmd}'")
            uart.write(f"error:invalid_format_or_value:{cmd}\r\n".encode('utf-8'))
        except Exception as e:
            log(f"Unexpected error processing cmd '{cmd}': {e}")
            uart.write(b"error:processing_failed\r\n")
    else:
        log(f"Unknown command format: '{cmd}'")
        uart.write(f"error:unknown_command:{cmd}\r\n".encode('utf-8'))

# —————————————————————————————————————————————————————
# Main Loop
# —————————————————————————————————————————————————————
log("Entering main loop...")
uart_buffer = ""
loop_errors = 0
last_led_toggle_time = time.monotonic()
led_state = False

while True:
    try:
        current_time = time.monotonic()

        # --- UART Input Handling (Non-blocking) ---
        if uart and uart.in_waiting > 0:
            try:
                data = uart.read(uart.in_waiting)
                if data:
                    try:
                        char_in = data.decode("utf-8")
                        uart_buffer += char_in
                        while '\r' in uart_buffer or '\n' in uart_buffer:
                            split_idx = -1
                            cr_idx = uart_buffer.find('\r')
                            lf_idx = uart_buffer.find('\n')
                            if cr_idx != -1 and lf_idx != -1: split_idx = min(cr_idx, lf_idx)
                            elif cr_idx != -1: split_idx = cr_idx
                            else: split_idx = lf_idx

                            cmd_line = uart_buffer[:split_idx].strip()
                            next_char_idx = split_idx + 1
                            if (uart_buffer.startswith('\r\n', split_idx) or
                                uart_buffer.startswith('\n\r', split_idx)):
                                next_char_idx = split_idx + 2
                            uart_buffer = uart_buffer[next_char_idx:]

                            if cmd_line: process_cmd(cmd_line)

                        if len(uart_buffer) > 128:
                            log("Warning: UART buffer overflow")
                            uart_buffer = uart_buffer[-128:]

                    except UnicodeDecodeError:
                        log(f"HW_RX: Non-UTF-8 data: {repr(data)}")
                        uart_buffer = ""
                    except Exception as e:
                        log(f"Error processing UART input: {e}")
                        uart_buffer = ""
            except Exception as e:
                log(f"Error reading UART: {e}")


        # --- RC Fallback / Control Logic ---
        # *** TEMPORARILY DISABLED FOR DEBUGGING ***
        # s_rc = read_last_pulse(rc_steering_in)
        # t_rc = read_last_pulse(rc_throttle_in)
        # if s_rc is not None: last_rc_steer_us = s_rc
        # if t_rc is not None: last_rc_throttle_us = t_rc
        #
        # if rc_control_enabled:
        #     if steering_pwm: steering_pwm.duty_cycle = us_to_duty(last_rc_steer_us)
        #     if throttle_pwm: throttle_pwm.duty_cycle = us_to_duty(last_rc_throttle_us)
        # else:
        #     # Apply stored command values if RC disabled (already handled in process_cmd)
        #     # This section might be redundant if process_cmd applies directly when rc disabled
        #     if steering_pwm: steering_pwm.duty_cycle = us_to_duty(last_cmd_steer_us)
        #     if throttle_pwm: throttle_pwm.duty_cycle = us_to_duty(last_cmd_throttle_us)
        pass # Placeholder for disabled section


        # --- LED Heartbeat ---
        if led and (current_time - last_led_toggle_time >= 0.5):
             led_state = not led_state
             led.value = led_state
             last_led_toggle_time = current_time

        # --- Loop Delay ---
        time.sleep(LOOP_DELAY_SECONDS)
        loop_errors = 0 # Reset error counter on successful loop iteration

    except KeyboardInterrupt:
        log("KeyboardInterrupt detected. Exiting loop.")
        break
    except Exception as e:
        loop_errors += 1
        log(f"Main loop exception ({loop_errors}/3): {e}")
        try:
            traceback.print_exc()
        except Exception as trace_e:
            log(f"Error printing traceback: {trace_e}")
        if uart:
            try:
                uart.write(b"error:main_loop_exception\r\n")
            except Exception as uart_e:
                log(f"Failed to send error via UART: {uart_e}")
        if loop_errors >= 3:
            log("Too many consecutive errors. Reloading...")
            time.sleep(1)
            supervisor.reload()
        else:
            time.sleep(0.5)

# —————————————————————————————————————————————————————
# Cleanup
# —————————————————————————————————————————————————————
log("Exiting script.") # Log before deinit
if steering_pwm: steering_pwm.duty_cycle = 0
if throttle_pwm: throttle_pwm.duty_cycle = 0

# Deinitialize peripherals
# Log the final message *before* deinitializing UART
log("Peripherals deinitialized.") # Moved this log message up

if uart: uart.deinit() # Now deinit UART
if rc_steering_in: rc_steering_in.deinit()
if rc_throttle_in: rc_throttle_in.deinit()
if led: led.deinit()
# PWM outputs deinitialized automatically? Check pwmio docs if needed.
