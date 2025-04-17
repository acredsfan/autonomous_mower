# code.py — UART + Console dual logging firmware for RoboHAT RP2040‑Zero
#
# • log() writes to both USB console (print) and hardware UART
# • Startup banner, init steps, RX bytes, commands all visible on /dev/serial0
# • Retains PWM & RC‑fallback features
# Revision 2025-04-18-debug

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
# Common options: board.GP25, board.GP16, board.GP17
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
    # Optionally, trigger a safe mode or reboot if UART is critical
    # supervisor.reload()

# —————————————————————————————————————————————————————
# Dual Logging Function
# —————————————————————————————————————————————————————
def log(msg: str) -> None:
    """Log to USB console and hardware UART."""
    # Log to USB console first
    print(msg)
    # Log to hardware UART if initialized
    if uart:
        try:
            # Ensure message ends with CR+LF for serial terminals
            if not msg.endswith('\r\n'):
                msg += '\r\n'
            uart.write(msg.encode('utf-8'))
        except Exception as e:
            # Print UART write errors to the console only to avoid recursion
            print(f"UART write error: {e}")

log(">>> code.py starting (dual-logging build)")

# —————————————————————————————————————————————————————
# LED Initialization
# —————————————————————————————————————————————————————
led = None
try:
    # Use the configured LED_PIN
    led = digitalio.DigitalInOut(LED_PIN)
    led.direction = digitalio.Direction.OUTPUT
    led.value = False # Start with LED off
    log(f"LED initialized on pin: {LED_PIN}")
except AttributeError:
    log(f"LED init failed: Pin {LED_PIN} not found or invalid. Check board definition.")
except Exception as e:
    log(f"LED init failed: {e}")

# Blink LED once quickly to show script start
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
    time.sleep(1) # Give time for log message to potentially send
    supervisor.reload()

# —————————————————————————————————————————————————————
# PulseIn Inputs (RC fallback)
# —————————————————————————————————————————————————————
rc_steering_in = None
rc_throttle_in = None
try:
    rc_steering_in = PulseIn(RC_STEERING_PIN, maxlen=32, idle_state=0)
    rc_throttle_in = PulseIn(RC_THROTTLE_PIN, maxlen=32, idle_state=0)
    # Clear any initial stale pulses
    rc_steering_in.clear()
    rc_throttle_in.clear()
    rc_steering_in.resume()
    rc_throttle_in.resume()
    log(f"PulseIn inputs initialized (Steering: {RC_STEERING_PIN}, Throttle: {RC_THROTTLE_PIN})")
except Exception as e:
    log(f"PulseIn init failed: {e}")
    # Decide if this is fatal. If RC is essential, maybe reload.
    # supervisor.reload()

# —————————————————————————————————————————————————————
# Global State
# —————————————————————————————————————————————————————
rc_control_enabled = True
last_rc_steer_us = 1500 # Default center
last_rc_throttle_us = 1500 # Default center
last_cmd_steer_us = 1500
last_cmd_throttle_us = 1500

# —————————————————————————————————————————————————————
# Helper Functions
# —————————————————————————————————————————————————————
def us_to_duty(us: int, freq: int = PWM_FREQUENCY) -> int:
    """Converts microseconds pulse width to PWM duty cycle (0-65535)."""
    period_ms = 1000.0 / freq
    # Clamp us to valid range (e.g., 1000-2000) before conversion
    us_clamped = max(1000, min(2000, us))
    duty = int((us_clamped / 1000.0) * (65535.0 / period_ms))
    # Clamp duty cycle to ensure it's within 16-bit range
    return max(0, min(65535, duty))

def read_last_pulse(chan: PulseIn | None) -> int | None:
    """Reads the most recent valid pulse (1000-2000us) from a PulseIn channel."""
    if chan is None or len(chan) == 0:
        return None
    # Read the last pulse
    try:
        pulse_us = chan[-1]
        # It's often good to clear the buffer after reading to avoid stale data
        chan.clear()
        if 1000 <= pulse_us <= 2000:
            return pulse_us
        else:
            # Log invalid pulse width if needed for debugging
            # log(f"Debug: Invalid pulse width {pulse_us}us on {chan.pin}")
            return None
    except Exception as e:
        log(f"Error reading PulseIn: {e}")
        return None

# —————————————————————————————————————————————————————
# Command Processing
# —————————————————————————————————————————————————————
def process_cmd(cmd: str) -> None:
    """Processes a command received via UART."""
    global rc_control_enabled, last_cmd_steer_us, last_cmd_throttle_us
    cmd = cmd.strip().lower()
    log(f"Processing cmd: '{cmd}'") # Log the exact command received

    if not cmd: # Ignore empty commands
        return

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

            # Validate input looks like numbers before converting
            if not s_str.isdigit() or not t_str.isdigit():
                 raise ValueError("Non-digit characters in command values")

            s = int(s_str)
            t = int(t_str)

            # Validate range (typical RC servo range)
            if not (1000 <= s <= 2000 and 1000 <= t <= 2000):
                raise ValueError(f"Command values out of range (1000-2000): s={s}, t={t}")

            last_cmd_steer_us = s
            last_cmd_throttle_us = t
            log(f"Command received: steer={s}, throttle={t}")

            # Apply immediately ONLY if RC control is disabled
            if not rc_control_enabled:
                log(f"Applying command: steer={s}, throttle={t}")
                if steering_pwm:
                    steering_pwm.duty_cycle = us_to_duty(s)
                if throttle_pwm:
                    throttle_pwm.duty_cycle = us_to_duty(t)
            else:
                log("RC enabled, command stored but not applied directly.")

            # Acknowledge successful command processing
            uart.write(f"ack:{s},{t}\r\n".encode('utf-8'))

        except ValueError as e:
            log(f"Command parse/value error: {e} for command '{cmd}'")
            uart.write(f"error:invalid_format_or_value:{cmd}\r\n".encode('utf-8'))
        except Exception as e:
            log(f"Unexpected error processing command '{cmd}': {e}")
            uart.write(b"error:processing_failed\r\n")
            # Optionally print traceback for unexpected errors
            # traceback.print_exc()
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
        # log("Loop start") # DEBUG: Uncomment to see loop frequency

        # --- UART Input Handling (Non-blocking) ---
        if uart and uart.in_waiting > 0:
            # log(f"UART data available: {uart.in_waiting} bytes") # DEBUG
            try:
                data = uart.read(uart.in_waiting) # Read all available bytes
                if data:
                    try:
                        # Decode received bytes
                        char_in = data.decode("utf-8")
                        # log(f"HW_RX raw: {repr(char_in)}") # DEBUG: Show exact chars received
                        # Append to buffer
                        uart_buffer += char_in
                        # Process complete lines (ending with \r or \n)
                        while '\r' in uart_buffer or '\n' in uart_buffer:
                            # Find the first newline (\r or \n)
                            split_idx = -1
                            cr_idx = uart_buffer.find('\r')
                            lf_idx = uart_buffer.find('\n')
                            if cr_idx != -1 and lf_idx != -1:
                                split_idx = min(cr_idx, lf_idx)
                            elif cr_idx != -1:
                                split_idx = cr_idx
                            else: # lf_idx must be != -1
                                split_idx = lf_idx

                            # Extract the command (part before the newline)
                            cmd_line = uart_buffer[:split_idx].strip()
                            # Remove the command and the newline character(s) from buffer
                            # Handle different line endings (\r, \n, \r\n)
                            next_char_idx = split_idx + 1
                            if (uart_buffer.startswith('\r\n', split_idx) or
                                uart_buffer.startswith('\n\r', split_idx)):
                                next_char_idx = split_idx + 2 # Skip both CR and LF
                            uart_buffer = uart_buffer[next_char_idx:]

                            # Process the extracted command if it's not empty
                            if cmd_line:
                                process_cmd(cmd_line)
                            # log(f"Buffer remaining: '{uart_buffer}'") # DEBUG

                        # Limit buffer size to prevent memory issues
                        if len(uart_buffer) > 128:
                            log("Warning: UART buffer overflow, discarding old data.")
                            uart_buffer = uart_buffer[-128:] # Keep the most recent part

                    except UnicodeDecodeError:
                        log(f"HW_RX: Received non-UTF-8 data: {repr(data)}")
                        # Consider clearing buffer or handling binary data if expected
                        uart_buffer = "" # Clear buffer on decode error
                    except Exception as e:
                        log(f"Error processing UART input: {e}")
                        # traceback.print_exc() # DEBUG: Uncomment for detailed traceback
                        uart_buffer = "" # Clear buffer on unexpected error
            except Exception as e:
                log(f"Error reading UART: {e}")
                # Consider actions like re-initializing UART if errors persist


        # --- RC Fallback / Control Logic ---
        # log("Checking RC") # DEBUG
        s_rc = read_last_pulse(rc_steering_in)
        t_rc = read_last_pulse(rc_throttle_in)

        # Update last known RC values if valid pulses received
        if s_rc is not None:
            last_rc_steer_us = s_rc
        if t_rc is not None:
            last_rc_throttle_us = t_rc

        # Apply control based on whether RC is enabled
        if rc_control_enabled:
            # Use last known valid RC values
            if steering_pwm:
                steering_pwm.duty_cycle = us_to_duty(last_rc_steer_us)
            if throttle_pwm:
                throttle_pwm.duty_cycle = us_to_duty(last_rc_throttle_us)
            # Log RC values periodically if needed for debugging
            # if current_time - last_rc_log_time > 1.0:
            #    log(f"RC Active: Steer={last_rc_steer_us}, Throttle={last_rc_throttle_us}")
            #    last_rc_log_time = current_time
        else:
            # Use last received command values when RC is disabled
            if steering_pwm:
                steering_pwm.duty_cycle = us_to_duty(last_cmd_steer_us)
            if throttle_pwm:
                throttle_pwm.duty_cycle = us_to_duty(last_cmd_throttle_us)
            # Log command values periodically if needed
            # if current_time - last_cmd_log_time > 1.0:
            #    log(f"CMD Active: Steer={last_cmd_steer_us}, Throttle={last_cmd_throttle_us}")
            #    last_cmd_log_time = current_time


        # --- LED Heartbeat ---
        # log("Toggling LED") # DEBUG
        if led and (current_time - last_led_toggle_time >= 0.5): # Toggle every 0.5 seconds
             led_state = not led_state
             led.value = led_state
             last_led_toggle_time = current_time

        # --- Loop Delay ---
        # log("Sleeping") # DEBUG
        time.sleep(LOOP_DELAY_SECONDS)
        # Reset error counter on successful loop iteration
        loop_errors = 0
        # log("Loop end") # DEBUG

    except KeyboardInterrupt:
        # Allow clean exit via Ctrl+C
        log("KeyboardInterrupt detected. Exiting loop.")
        break # Exit the while True loop
    except Exception as e:
        loop_errors += 1
        log(f"Main loop exception ({loop_errors}/3): {e}")
        # Print detailed traceback to console for debugging
        try:
            traceback.print_exc()
        except Exception as trace_e:
            log(f"Error printing traceback: {trace_e}")

        # Attempt to send error message via UART
        if uart:
            try:
                uart.write(b"error:main_loop_exception\r\n")
            except Exception as uart_e:
                log(f"Failed to send error via UART: {uart_e}")

        if loop_errors >= 3:
            log("Too many consecutive errors. Reloading...")
            time.sleep(1) # Short delay before reload
            supervisor.reload()
        else:
            # Delay briefly after an error before retrying
            time.sleep(0.5)

# —————————————————————————————————————————————————————
# Cleanup (optional, runs after loop exits e.g. on Ctrl+C)
# —————————————————————————————————————————————————————
log("Exiting script.")
if steering_pwm:
    steering_pwm.duty_cycle = 0
if throttle_pwm:
    throttle_pwm.duty_cycle = 0
if uart:
    uart.deinit()
if rc_steering_in:
    rc_steering_in.deinit()
if rc_throttle_in:
    rc_throttle_in.deinit()
if led:
    led.deinit()
log("Peripherals deinitialized.")
