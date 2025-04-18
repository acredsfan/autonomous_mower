# code.py — RP2040 RC/Serial Control Firmware with NeoPixel LED
#
# • Controls steering/throttle via UART commands (e.g., "1500,1500", "rc=disable")
# • Falls back to RC control if enabled ("rc=enable" command)
# • Uses onboard NeoPixel for status indication
# • Logs to both USB console and hardware UART
# Revision 2025-04-18-neopixel-uart

import time
import board  # type: ignore
import supervisor  # type: ignore
import digitalio  # type: ignore # Keep for potential future use?
import busio  # type: ignore
import neopixel  # type: ignore
from pwmio import PWMOut  # type: ignore
from pulseio import PulseIn  # type: ignore
import traceback  # type: ignore
import microcontroller  # For CPU temp/freq if needed later

# —————————————————————————————————————————————————————
# Configuration
# —————————————————————————————————————————————————————
UART_BAUD = 115200
UART_TX_PIN = board.GP0
UART_RX_PIN = board.GP1
# --- Verify these PWM/RC pins match your hardware ---
PWM_STEERING_PIN = board.GP10
PWM_THROTTLE_PIN = board.GP11
RC_STEERING_PIN = board.GP6
RC_THROTTLE_PIN = board.GP5
# --- Use NeoPixel for LED ---
# Most boards with an onboard NeoPixel use board.NEOPIXEL
NEOPIXEL_PIN = board.NEOPIXEL
NEOPIXEL_COUNT = 1
HEARTBEAT_COLOR = (0, 0, 255)  # Blue
OFF_COLOR = (0, 0, 0)

PWM_FREQUENCY = 50
LOOP_DELAY_SECONDS = 0.01  # Main loop delay

# —————————————————————————————————————————————————————
# Setup UART (GP0=TX, GP1=RX)
# —————————————————————————————————————————————————————
uart = None
try:
    uart = busio.UART(UART_TX_PIN, UART_RX_PIN,
                      baudrate=UART_BAUD, timeout=0.01)
    # Initial log via print only, as log() needs uart
    print(f"UART initialized on TX:{UART_TX_PIN}, RX:{UART_RX_PIN}")
except Exception as e:
    print(f"UART init failed: {e}")
    # Consider reload if UART is essential
    # supervisor.reload()

# —————————————————————————————————————————————————————
# Dual Logging Function
# —————————————————————————————————————————————————————


def log(msg: str) -> None:
    """Log to USB console and hardware UART."""
    print(msg)  # Log to USB console first
    if uart:
        try:
            # Ensure message ends with CR+LF for serial terminals
            if not msg.endswith('\r\n'):
                msg += '\r\n'
            uart.write(msg.encode('utf-8'))
        except Exception as e:
            # Print UART write errors to the console only to avoid recursion
            print(f"UART write error: {e}")


log(">>> code.py starting (neopixel-uart build)")

# —————————————————————————————————————————————————————
# NeoPixel Initialization
# —————————————————————————————————————————————————————
pixel = None
try:
    pixel = neopixel.NeoPixel(NEOPIXEL_PIN, NEOPIXEL_COUNT, auto_write=False)
    pixel.fill(OFF_COLOR)
    pixel.show()
    log(f"NeoPixel initialized on pin: {NEOPIXEL_PIN}")
except AttributeError:
    log(f"NeoPixel init failed: Pin {NEOPIXEL_PIN} not found.")
    log("Ensure board has NeoPixel and correct pin is defined.")
except Exception as e:
    log(f"NeoPixel init failed: {e}")

# Initial blink to show script start
if pixel:
    pixel.fill(HEARTBEAT_COLOR)
    pixel.show()
    time.sleep(0.1)
    pixel.fill(OFF_COLOR)
    pixel.show()

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
    # Initialize centered (1500us pulse equivalent if possible, otherwise 0)
    # Note: Duty cycle calculation depends on frequency. Start at 0 for safety.
    steering_pwm = PWMOut(PWM_STEERING_PIN, duty_cycle=0, frequency=PWM_FREQUENCY)
    throttle_pwm = PWMOut(PWM_THROTTLE_PIN, duty_cycle=0, frequency=PWM_FREQUENCY)
    log(f"PWM outputs initialized (Steering: {PWM_STEERING_PIN}, Throttle: {PWM_THROTTLE_PIN})")
except Exception as e:
    log(f"PWM init failed: {e}")
    log("Reloading due to PWM init failure...")
    time.sleep(1)
    supervisor.reload()

# —————————————————————————————————————————————————————
# PulseIn Inputs (RC fallback)
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
    # Decide if this is fatal. If RC is essential, maybe reload.
    # supervisor.reload()

# —————————————————————————————————————————————————————
# Global State
# —————————————————————————————————————————————————————
rc_control_enabled = True  # Default to RC control enabled
last_rc_steer_us = 1500    # Default center
last_rc_throttle_us = 1500 # Default center/stop
last_cmd_steer_us = 1500
last_cmd_throttle_us = 1500

# —————————————————————————————————————————————————————
# Helper Functions
# —————————————————————————————————————————————————————


def us_to_duty(us: int, freq: int = PWM_FREQUENCY) -> int:
    """Converts microseconds pulse width to PWM duty cycle (0-65535)."""
    period_ms = 1000.0 / freq
    # Clamp us to valid RC range before conversion
    us_clamped = max(1000, min(2000, us))
    # Calculate duty cycle relative to the period
    duty = int((us_clamped / 1000.0) * (65535.0 / period_ms))
    # Clamp duty cycle to ensure it's within 16-bit range
    return max(0, min(65535, duty))


def read_last_pulse(chan: PulseIn | None) -> int | None:
    """Reads the most recent valid pulse (1000-2000us) from a PulseIn channel."""
    if chan is None or len(chan) == 0:
        return None
    # Read the last pulse from buffer
    try:
        # Iterate backwards to find the most recent valid pulse if buffer > 1
        for i in range(len(chan) - 1, -1, -1):
            pulse_us = chan[i]
            if 1000 <= pulse_us <= 2000:
                chan.clear()  # Clear buffer after finding a valid pulse
                return pulse_us
        # If no valid pulse found in buffer
        chan.clear() # Still clear buffer
        return None
    except Exception as e:
        log(f"Error reading PulseIn {chan.pin}: {e}")
        if chan: chan.clear() # Attempt to clear buffer on error
        return None

# —————————————————————————————————————————————————————
# Command Processing
# —————————————————————————————————————————————————————


def process_cmd(cmd: str) -> None:
    """Processes a command received via UART."""
    global rc_control_enabled, last_cmd_steer_us, last_cmd_throttle_us
    cmd = cmd.strip().lower()
    log(f"Processing cmd: '{cmd}'")

    if not cmd:  # Ignore empty commands
        return

    if cmd == "rc=disable":
        rc_control_enabled = False
        log("RC control DISABLED")
        # Apply last command values immediately
        if steering_pwm:
            steering_pwm.duty_cycle = us_to_duty(last_cmd_steer_us)
        if throttle_pwm:
            throttle_pwm.duty_cycle = us_to_duty(last_cmd_throttle_us)
        if uart: uart.write(b"ack:rc=disable\r\n")
    elif cmd == "rc=enable":
        rc_control_enabled = True
        log("RC control ENABLED")
        # RC values will take over in the main loop's next iteration
        if uart: uart.write(b"ack:rc=enable\r\n")
    elif "," in cmd:
        try:
            parts = cmd.split(",", 1)
            s_str = parts[0].strip()
            t_str = parts[1].strip()

            # Validate input looks like numbers before converting
            if not s_str.lstrip('-').isdigit() or not t_str.lstrip('-').isdigit():
                 raise ValueError("Non-digit characters in command values")

            s = int(s_str)
            t = int(t_str)

            # Validate range (typical RC servo range 1000-2000)
            if not (1000 <= s <= 2000 and 1000 <= t <= 2000):
                raise ValueError(f"Values out of range (1000-2000): s={s}, t={t}")

            last_cmd_steer_us = s
            last_cmd_throttle_us = t
            log(f"Command stored: steer={s}, throttle={t}")

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
            if uart: uart.write(f"ack:{s},{t}\r\n".encode('utf-8'))

        except ValueError as e:
            log(f"Command parse/value error: {e} for command '{cmd}'")
            if uart: uart.write(f"error:invalid_format_or_value:{cmd}\r\n".encode('utf-8'))
        except Exception as e:
            log(f"Unexpected error processing command '{cmd}': {e}")
            if uart: uart.write(b"error:processing_failed\r\n")
            # Optionally print traceback for unexpected errors
            # traceback.print_exc()
    else:
        log(f"Unknown command format: '{cmd}'")
        if uart: uart.write(f"error:unknown_command:{cmd}\r\n".encode('utf-8'))

# —————————————————————————————————————————————————————
# Main Loop
# —————————————————————————————————————————————————————
log("Entering main loop...")
uart_buffer = ""
loop_errors = 0
last_heartbeat_time = time.monotonic()
pixel_state = False

while True:
    try:
        current_time = time.monotonic()

        # --- UART Input Handling (Non-blocking) ---
        if uart and uart.in_waiting > 0:
            try:
                data = uart.read(uart.in_waiting)  # Read all available bytes
                if data:
                    try:
                        # Decode received bytes
                        char_in = data.decode("utf-8")
                        # Append to buffer
                        uart_buffer += char_in
                        # Process complete lines (ending with \r or \n)
                        while '\r' in uart_buffer or '\n' in uart_buffer:
                            split_idx = -1
                            cr_idx = uart_buffer.find('\r')
                            lf_idx = uart_buffer.find('\n')
                            if cr_idx != -1 and lf_idx != -1:
                                split_idx = min(cr_idx, lf_idx)
                            elif cr_idx != -1:
                                split_idx = cr_idx
                            else:  # lf_idx must be != -1
                                split_idx = lf_idx

                            # Extract the command (part before the newline)
                            cmd_line = uart_buffer[:split_idx].strip()
                            # Remove the command and the newline character(s)
                            next_char_idx = split_idx + 1
                            if (uart_buffer.startswith('\r\n', split_idx) or
                                    uart_buffer.startswith('\n\r', split_idx)):
                                next_char_idx = split_idx + 2
                            uart_buffer = uart_buffer[next_char_idx:]

                            if cmd_line:
                                process_cmd(cmd_line)

                        # Limit buffer size
                        if len(uart_buffer) > 128:
                            log("Warning: UART buffer overflow")
                            uart_buffer = uart_buffer[-128:]

                    except UnicodeDecodeError:
                        log(f"HW_RX: Non-UTF-8 data: {repr(data)}")
                        uart_buffer = ""  # Clear buffer on decode error
                    except Exception as e:
                        log(f"Error processing UART input: {e}")
                        uart_buffer = ""
            except Exception as e:
                log(f"Error reading UART: {e}")

        # --- RC Fallback / Control Logic ---
        if rc_control_enabled:
            s_rc = read_last_pulse(rc_steering_in)
            t_rc = read_last_pulse(rc_throttle_in)

            # Update last known RC values if valid pulses received
            if s_rc is not None:
                last_rc_steer_us = s_rc
            if t_rc is not None:
                last_rc_throttle_us = t_rc

            # Apply last known valid RC values
            if steering_pwm:
                steering_pwm.duty_cycle = us_to_duty(last_rc_steer_us)
            if throttle_pwm:
                throttle_pwm.duty_cycle = us_to_duty(last_rc_throttle_us)
        # else:
            # If RC is disabled, PWM is controlled by process_cmd

        # --- NeoPixel Heartbeat ---
        if pixel and (current_time - last_heartbeat_time >= 0.5):
            pixel_state = not pixel_state
            pixel.fill(HEARTBEAT_COLOR if pixel_state else OFF_COLOR)
            pixel.show()
            last_heartbeat_time = current_time

        # --- Loop Delay ---
        time.sleep(LOOP_DELAY_SECONDS)
        loop_errors = 0  # Reset error counter on successful loop iteration

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
log("Exiting script.")
# Turn off PWM outputs
if steering_pwm:
    steering_pwm.duty_cycle = 0
if throttle_pwm:
    throttle_pwm.duty_cycle = 0
log("PWMs zeroed.")
# Turn off NeoPixel
if pixel:
    pixel.fill(OFF_COLOR)
    pixel.show()
    log("NeoPixel off.")

# Deinitialize peripherals
log("Deinitializing peripherals...") # Log before deinit
if uart:
    uart.deinit()
if rc_steering_in:
    rc_steering_in.deinit()
if rc_throttle_in:
    rc_throttle_in.deinit()
# NeoPixel does not have deinit
# PWM outputs deinitialized automatically? Check pwmio docs if needed.
log("Cleanup complete.")

