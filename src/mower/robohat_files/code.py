# code.py — UART + Console dual logging firmware for RoboHAT RP2040‑Zero
#
# • log() writes to both USB console (print) and hardware UART
# • Startup banner, init steps, RX bytes, commands all visible on /dev/serial0
# • Retains PWM & RC‑fallback features
# Revision 2025-04-18-minimal-blink

import time
import board  # type: ignore
import supervisor  # type: ignore
import digitalio  # type: ignore
# import busio  # type: ignore # UART DISABLED FOR TEST
from pwmio import PWMOut  # type: ignore
from pulseio import PulseIn  # type: ignore
import traceback  # type: ignore
import microcontroller # For CPU temp/freq if needed later

# —————————————————————————————————————————————————————
# Configuration
# —————————————————————————————————————————————————————
# UART_BAUD = 115200 # UART DISABLED FOR TEST
# UART_TX_PIN = board.GP0 # UART DISABLED FOR TEST
# UART_RX_PIN = board.GP1 # UART DISABLED FOR TEST
PWM_STEERING_PIN = board.GP10
PWM_THROTTLE_PIN = board.GP11
RC_STEERING_PIN = board.GP6
RC_THROTTLE_PIN = board.GP5
LED_PIN = board.GP25 # Verify this pin is correct!
PWM_FREQUENCY = 50
LOOP_DELAY_SECONDS = 0.05 # Slightly increased delay

# —————————————————————————————————————————————————————
# Setup UART (GP0=TX, GP1=RX)
# —————————————————————————————————————————————————————
uart = None # UART DISABLED FOR TEST
# try:
#     uart = busio.UART(UART_TX_PIN, UART_RX_PIN, baudrate=UART_BAUD, timeout=0.01)
#     print("UART initialized") # Print to console only
# except Exception as e:
#     print(f"UART init failed: {e}")
#     # supervisor.reload()

# —————————————————————————————————————————————————————
# Logging Function (Console Only)
# —————————————————————————————————————————————————————
def log(msg: str) -> None:
    """Log ONLY to USB console."""
    print(msg)
    # UART write attempt removed

log(">>> code.py starting (minimal-blink build)")
log("NOTE: Hardware UART TX/RX is DISABLED for this test.")

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
# Send Startup Banner (Console Only)
# —————————————————————————————————————————————————————
log("RP2040_CONSOLE_READY") # Changed message as UART is off

# —————————————————————————————————————————————————————
# PWM Outputs (Initialize but not used in loop)
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
# PulseIn Inputs (Initialize but not used in loop)
# —————————————————————————————————————————————————————
rc_steering_in = None
rc_throttle_in = None
try:
    rc_steering_in = PulseIn(RC_STEERING_PIN, maxlen=32, idle_state=0)
    rc_throttle_in = PulseIn(RC_THROTTLE_PIN, maxlen=32, idle_state=0)
    rc_steering_in.clear(); rc_throttle_in.clear()
    rc_steering_in.resume(); rc_throttle_in.resume()
    log(f"PulseIn inputs initialized (Steering: {RC_STEERING_PIN}, Throttle: {RC_THROTTLE_PIN})")
except Exception as e:
    log(f"PulseIn init failed: {e}")

# —————————————————————————————————————————————————————
# Global State (Not used in loop)
# —————————————————————————————————————————————————————
# rc_control_enabled = True
# last_rc_steer_us = 1500
# last_rc_throttle_us = 1500
# last_cmd_steer_us = 1500
# last_cmd_throttle_us = 1500

# —————————————————————————————————————————————————————
# Helper Functions (Not used in loop)
# —————————————————————————————————————————————————————
# def us_to_duty(us: int, freq: int = PWM_FREQUENCY) -> int: ...
# def read_last_pulse(chan: PulseIn | None) -> int | None: ...

# —————————————————————————————————————————————————————
# Command Processing (Disabled)
# —————————————————————————————————————————————————————
# def process_cmd(cmd: str) -> None: ...

# —————————————————————————————————————————————————————
# Main Loop - MINIMAL TEST
# —————————————————————————————————————————————————————
log("Entering main loop (minimal blink test)...")
loop_errors = 0
last_led_toggle_time = time.monotonic()
led_state = False

while True:
    try:
        current_time = time.monotonic()

        # --- UART Input Handling ---
        # *** ENTIRELY DISABLED FOR THIS TEST ***

        # --- RC Fallback / Control Logic ---
        # *** DISABLED ***
        pass

        # --- LED Heartbeat ---
        if led and (current_time - last_led_toggle_time >= 0.5): # Toggle every 0.5 seconds
             led_state = not led_state
             led.value = led_state
             last_led_toggle_time = current_time
             # Maybe print a dot to the console periodically to show activity
             # if led_state: print(".", end="")


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
            traceback.print_exc() # Print to console
        except Exception as trace_e:
            log(f"Error printing traceback: {trace_e}")

        # No UART error reporting possible
        if loop_errors >= 3:
            log("Too many consecutive errors. Reloading...")
            time.sleep(1)
            supervisor.reload()
        else:
            time.sleep(0.5)

# —————————————————————————————————————————————————————
# Cleanup
# —————————————————————————————————————————————————————
log("Exiting script.")
if steering_pwm: steering_pwm.duty_cycle = 0
if throttle_pwm: throttle_pwm.duty_cycle = 0
log("PWMs zeroed.")

# Deinitialize peripherals
if rc_steering_in: rc_steering_in.deinit()
if rc_throttle_in: rc_throttle_in.deinit()
if led: led.deinit()
log("Peripherals deinitialized.")
# No UART to deinitialize
