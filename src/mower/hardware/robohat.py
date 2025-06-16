
# FROZEN_DRIVER – do not edit (see .github/copilot-instructions.md)
#!/usr/bin/env python3
"""
Scripts for operating the RoboHAT MM1 by Robotics Masters.

Serial protocol: "steer,throttle\r" (e.g. 1500,1600\r)
Units are microseconds of pulse width.

Updated version based on recommendations.

- Separates controller and driver into two classes.
- Uses cfg for configurations.
- Ensures PWM values are integers.
- Removes navigation logic from controller.
"""

__all__ = ["RoboHATDriver", "RoboHATController"]

# Serial communication constants (centralized)
SERIAL_PORT = "/dev/ttyAMA4"
BAUD_RATE = 115200
SERIAL_TIMEOUT = 0.05

import os
import sys
import time

import serial
import serial.tools.list_ports

from mower.constants import MM1_MAX_FORWARD, MM1_MAX_REVERSE, MM1_STEERING_MID, MM1_STOPPED_PWM
from mower.utilities.logger_config import LoggerConfigInfo
from mower.utilities.utils import Utils

logger = LoggerConfigInfo.get_logger(__name__)


class CommunicationModeHelper:
    """Helper class for RoboHAT communication mode detection and selection."""
    
    @staticmethod
    def detect_robohat_devices(device_pattern: str = "") -> list:
        """
        Detect potential RoboHAT devices on the system.
        
        Args:
            device_pattern: Optional pattern to filter devices
            
        Returns:
            List of potential device paths
        """
        potential_devices = []
        
        # Scan USB CDC devices (ttyACM*)
        usb_devices = []
        for i in range(10):  # Check ttyACM0 through ttyACM9
            device_path = f"/dev/ttyACM{i}"
            if os.path.exists(device_path):
                usb_devices.append(device_path)
        
        # Scan UART devices (ttyAMA*, ttyS*)
        uart_devices = []
        for i in range(5):  # Check common UART ports
            for prefix in ["/dev/ttyAMA", "/dev/ttyS"]:
                device_path = f"{prefix}{i}"
                if os.path.exists(device_path):
                    uart_devices.append(device_path)
        
        # Apply device pattern filter if specified
        all_devices = usb_devices + uart_devices
        if device_pattern:
            all_devices = [d for d in all_devices if device_pattern in d]
        
        logger.debug(f"Detected potential RoboHAT devices: {all_devices}")
        return all_devices
    
    @staticmethod
    def probe_device_for_robohat(device_path: str, timeout: float = 2.0) -> bool:
        """
        Probe a device to check if it's a RoboHAT by sending a test command.
        
        Args:
            device_path: Path to the serial device
            timeout: Timeout for the probe
            
        Returns:
            True if device responds like a RoboHAT
        """
        try:
            with serial.Serial(device_path, 115200, timeout=0.5) as test_port:
                # Clear buffers
                test_port.reset_input_buffer()
                test_port.reset_output_buffer()
                
                # Send a harmless test command
                test_port.write(b"rc=disable\r")
                time.sleep(0.2)
                
                # Send neutral PWM command
                test_port.write(b"1500,1500\r")
                time.sleep(0.2)
                
                # RoboHAT doesn't typically send responses to these commands,
                # but if it accepts them without error, it's likely a RoboHAT
                logger.debug(f"Device {device_path} accepted RoboHAT commands")
                return True
                
        except (serial.SerialException, OSError) as e:
            logger.debug(f"Device {device_path} probe failed: {e}")
            return False
    
    @staticmethod
    def determine_communication_mode(
        specified_port: str, 
        communication_mode: str, 
        device_pattern: str = ""
    ) -> tuple[str, str]:
        """
        Determine the best communication mode and device path.
        
        Args:
            specified_port: User-specified port (from MM1_SERIAL_PORT)
            communication_mode: Desired communication mode
            device_pattern: Optional device pattern filter
            
        Returns:
            Tuple of (selected_device_path, actual_mode_used)
        """
        logger.info(f"Determining communication mode: {communication_mode}")
        
        if communication_mode == "manual":
            # Use exact port specified, no auto-detection
            if os.path.exists(specified_port):
                logger.info(f"Manual mode: Using specified port {specified_port}")
                return specified_port, "manual"
            else:
                logger.error(f"Manual mode: Specified port {specified_port} does not exist")
                raise FileNotFoundError(f"Specified port {specified_port} not found")
        
        available_devices = CommunicationModeHelper.detect_robohat_devices(device_pattern)
        
        if communication_mode == "usb":
            # Force USB CDC mode (ttyACM*)
            usb_devices = [d for d in available_devices if "ttyACM" in d]
            if not usb_devices:
                raise FileNotFoundError("No USB CDC devices found for RoboHAT")
            
            # Try specified port first if it's a USB device
            if specified_port in usb_devices:
                logger.info(f"USB mode: Using specified USB port {specified_port}")
                return specified_port, "usb"
            
            # Otherwise try the first available USB device
            selected_device = usb_devices[0]
            logger.info(f"USB mode: Auto-selected USB device {selected_device}")
            return selected_device, "usb"
        
        elif communication_mode == "uart":
            # Force UART mode (ttyAMA*, ttyS*)
            uart_devices = [d for d in available_devices if "ttyAMA" in d or "ttyS" in d]
            if not uart_devices:
                raise FileNotFoundError("No UART devices found for RoboHAT")
            
            # Try specified port first if it's a UART device
            if specified_port in uart_devices:
                logger.info(f"UART mode: Using specified UART port {specified_port}")
                return specified_port, "uart"
            
            # Otherwise try the first available UART device
            selected_device = uart_devices[0]
            logger.info(f"UART mode: Auto-selected UART device {selected_device}")
            return selected_device, "uart"
        
        elif communication_mode == "auto":
            # Auto-detection mode: try specified port first, then probe others
            
            # First, try the user-specified port if it exists
            if specified_port and os.path.exists(specified_port):
                logger.info(f"Auto mode: Trying specified port {specified_port}")
                if CommunicationModeHelper.probe_device_for_robohat(specified_port):
                    device_type = "usb" if "ttyACM" in specified_port else "uart"
                    logger.info(f"Auto mode: Specified port {specified_port} is a RoboHAT ({device_type})")
                    return specified_port, f"auto-{device_type}"
                else:
                    logger.warning(f"Auto mode: Specified port {specified_port} failed RoboHAT probe")
            
            # If specified port failed or wasn't specified, try auto-detection
            logger.info("Auto mode: Probing available devices for RoboHAT...")
            
            # Prioritize USB CDC devices (typically more reliable)
            usb_devices = [d for d in available_devices if "ttyACM" in d]
            uart_devices = [d for d in available_devices if "ttyAMA" in d or "ttyS" in d]
            
            for device_list, device_type in [(usb_devices, "usb"), (uart_devices, "uart")]:
                for device_path in device_list:
                    if device_path != specified_port:  # Skip if already tried
                        logger.debug(f"Auto mode: Probing {device_path}")
                        if CommunicationModeHelper.probe_device_for_robohat(device_path):
                            logger.info(f"Auto mode: Found RoboHAT at {device_path} ({device_type})")
                            return device_path, f"auto-{device_type}"
            
            # If nothing worked, raise an error
            logger.error("Auto mode: No RoboHAT devices found")
            raise FileNotFoundError("No RoboHAT devices detected in auto mode")
        
        else:
            raise ValueError(f"Unknown communication mode: {communication_mode}")


class RoboHATController:
    """
    Controller to read signals from the RC controller via serial
    and convert into steering and throttle outputs.
    Input signal range: 1000 to 2000
    Output range: -1.00 to 1.00
    """

    def __init__(self, cfg, debug=False):
        # Standard variables
        self.angle = 0.0
        self.throttle = 0.0
        self.mode = "user"
        self.recording = False
        self.recording_latch = None
        self.auto_record_on_throttle = cfg.AUTO_RECORD_ON_THROTTLE
        self.STEERING_MID = cfg.MM1_STEERING_MID
        self.MAX_FORWARD = cfg.MM1_MAX_FORWARD
        self.STOPPED_PWM = cfg.MM1_STOPPED_PWM
        self.MAX_REVERSE = cfg.MM1_MAX_REVERSE
        self.SHOW_STEERING_VALUE = cfg.MM1_SHOW_STEERING_VALUE
        self.DEAD_ZONE = cfg.JOYSTICK_DEADZONE
        self.debug = debug
        self.control_mode = "serial"  # Set default control mode to 'serial'

        # Initialize serial port for reading RC inputs
        try:
            self.serial = serial.Serial(cfg.MM1_SERIAL_PORT, 115200, timeout=1)
            logger.info(f"Serial port {cfg.MM1_SERIAL_PORT} opened for controller " "input.")
        except serial.SerialException:
            logger.error("Serial port for controller input not found! " "Please enable: sudo raspi-config")
            self.serial = None

    def shutdown(self):
        if self.serial and self.serial.is_open:
            try:
                self.serial.close()
                logger.info("Controller serial connection closed.")
            except serial.SerialException:
                logger.error("Failed to close the controller serial connection.")

    def read_serial(self):
        """
        Read the RC controller value from serial port. Map the value into
        steering and throttle.

        Expected format: '####,####\r', where the first number is steering
        and the second is throttle.
        """
        if not self.serial or not self.serial.is_open:
            logger.warning("Controller serial port is not open.")
            return

        # read a frame terminated by carriage‑return (CR = 13)
        frame = self.serial.read_until(b'\r').decode(errors="ignore").strip()
        parts = frame.split(',', 1)          # no space after comma

        if len(parts) == 2 and all(p.isnumeric() for p in parts):
            angle_pwm    = float(parts[0])
            throttle_pwm = float(parts[1])

        if self.debug:
            logger.debug(f"angle_pwm = {angle_pwm}, " f"throttle_pwm= {throttle_pwm}")

        if throttle_pwm >= self.STOPPED_PWM:
            # Scale down the input PWM (1500 - 2000) to our max forward
            throttle_pwm_mapped = Utils.map_range_float(
                throttle_pwm,
                1500,
                2000,
                self.STOPPED_PWM,
                self.MAX_FORWARD,
            )
            # Go forward
            self.throttle = Utils.map_range_float(
                throttle_pwm_mapped,
                self.STOPPED_PWM,
                self.MAX_FORWARD,
                0,
                1.0,
            )
        else:
            throttle_pwm_mapped = Utils.map_range_float(
                throttle_pwm,
                1000,
                1500,
                self.MAX_REVERSE,
                self.STOPPED_PWM,
            )
            # Go backward
            self.throttle = Utils.map_range_float(
                throttle_pwm_mapped,
                self.MAX_REVERSE,
                self.STOPPED_PWM,
                -1.0,
                0,
            )

        if angle_pwm >= self.STEERING_MID:
            # Turn left
            self.angle = Utils.map_range_float(angle_pwm, 2000, self.STEERING_MID, -1, 0)
        else:
            # Turn right
            self.angle = Utils.map_range_float(angle_pwm, self.STEERING_MID, 1000, 0, 1)

        if self.debug:
            logger.debug(f"angle = {self.angle}, throttle = {self.throttle}")

        if self.auto_record_on_throttle:
            was_recording = self.recording
            self.recording = abs(self.throttle) > self.DEAD_ZONE
            if was_recording != self.recording:
                self.recording_latch = self.recording
                logger.debug(f"Recording state changed to {self.recording}")

        time.sleep(0.01)

    def update(self):
        # Delay on startup to avoid crashing
        logger.info("Warming up controller serial port...")
        time.sleep(3)

        while True:
            try:
                # Only process RC input if enabled
                if self.control_mode == "rc":
                    self.read_serial()
            except Exception as e:
                logger.error(f"MM1: Error reading serial input: {e}")
                break

    def run(self, img_arr=None, mode=None, recording=None):
        """
        :param img_arr: current camera image or None
        :param mode: default user/mode
        :param recording: default recording mode
        """
        return self.run_threaded(img_arr, mode, recording)

    def run_threaded(self, img_arr=None, mode=None, recording=None):
        """
        :param img_arr: current camera image
        :param mode: default user/mode
        :param recording: default recording mode
        """
        self.img_arr = img_arr

        # Enforce defaults if they are not None.
        if mode is not None:
            self.mode = mode
        if recording is not None and recording != self.recording:
            logger.debug(f"Setting recording from default = {recording}")
            self.recording = recording
        if self.recording_latch is not None:
            logger.debug(f"Setting recording from latch = {self.recording_latch}")
            self.recording = self.recording_latch
            self.recording_latch = None

        return self.angle, self.throttle, self.mode, self.recording


class RoboHATDriver:
    """
    PWM motor controller using Robo HAT MM1 boards.
    """

    def __init__(self, debug=False):
        # Initialize the Robo HAT using the serial port
        self.debug = debug
        self.MAX_FORWARD = MM1_MAX_FORWARD
        self.MAX_REVERSE = MM1_MAX_REVERSE
        self.STOPPED_PWM = MM1_STOPPED_PWM
        self.STEERING_MID = MM1_STEERING_MID
        self._rc_disabled = False  # Track if we've disabled RC mode

        # Read communication configuration from environment variables
        specified_port = os.getenv("MM1_SERIAL_PORT", "/dev/ttyACM1")
        communication_mode = os.getenv("MM1_COMMUNICATION_MODE", "auto").lower()
        device_pattern = os.getenv("MM1_DEVICE_PATTERN", "")
        
        logger.info(f"RoboHAT Driver initializing with mode: {communication_mode}")
        
        try:
            # Determine the best communication mode and device
            selected_device, actual_mode = CommunicationModeHelper.determine_communication_mode(
                specified_port, communication_mode, device_pattern
            )
            
            # Initialize serial port
            self.pwm = serial.Serial(selected_device, 115200, timeout=1)
            logger.info(f"Serial port {selected_device} opened for PWM output (mode: {actual_mode})")
            
            # Store communication info for debugging
            self.communication_info = {
                "device_path": selected_device,
                "mode": actual_mode,
                "requested_mode": communication_mode,
                "specified_port": specified_port
            }
            
            # Initialize the connection
            self._initialize_connection()
            
        except (serial.SerialException, FileNotFoundError) as e:
            logger.error(f"Failed to open RoboHAT serial port: {e}")
            logger.error("Available devices for troubleshooting:")
            available_devices = CommunicationModeHelper.detect_robohat_devices()
            for device in available_devices:
                logger.error(f"  - {device}")
            
            self.pwm = None
            self.communication_info = {
                "device_path": None,
                "mode": "failed",
                "error": str(e),
                "requested_mode": communication_mode,
                "specified_port": specified_port
            }

    def _initialize_connection(self):
        """Initialize the connection with the RP2040."""
        if not self.pwm or not self.pwm.is_open:
            return
        try:
            # Clear any pending data
            self.pwm.reset_input_buffer()
            self.pwm.reset_output_buffer()

            # Send RC disable command to enable serial control
            logger.info("Disabling RC mode on RP2040...")
            self.pwm.write(b"rc=disable\r")
            if self.debug:
                try:
                    echo = self.pwm.read_until(b'\r', timeout=SERIAL_TIMEOUT)
                    if echo.strip(b'\r') != b"rc=disable":
                        logger.warning(f"Mismatch echo: {echo}")
                except Exception as e:
                    logger.debug(f"No echo or error: {e}")
            print("Command sent to RP2040 to disable RC mode.")
            time.sleep(0.2)  # Give RP2040 time to process
            # Send initial neutral position
            self.pwm.write(b"1500,1500\r")
            if self.debug:
                try:
                    echo = self.pwm.read_until(b'\r', timeout=SERIAL_TIMEOUT)
                    if echo.strip(b'\r')  != b"1500,1500":
                        logger.warning(f"Mismatch echo: {echo}")
                except Exception as e:
                    logger.debug(f"No echo or error: {e}")
            time.sleep(0.1)
            self._rc_disabled = True
            logger.info("✓ RP2040 initialized for serial control")
        except Exception as e:
            logger.error(f"Failed to initialize RP2040 connection: {e}")

    def trim_out_of_bound_value(self, value):
        """Trim steering and throttle values to be within -1.0 and 1.0"""
        if value > 1:
            logger.warning(f"MM1: Warning, value out of bound. Value = {value}")
            return 1.0
        elif value < -1:
            logger.warning(f"MM1: Warning, value out of bound. Value = {value}")
            return -1.0
        else:
            return value

    def set_pulse(self, steering, throttle):
        try:
            steering = self.trim_out_of_bound_value(steering)
            throttle = self.trim_out_of_bound_value(throttle)

            if throttle > 0:
                output_throttle = Utils.map_range(throttle, 0, 1.0, self.STOPPED_PWM, self.MAX_FORWARD)
            else:
                output_throttle = Utils.map_range(throttle, -1, 0, self.MAX_REVERSE, self.STOPPED_PWM)

            if steering > 0:
                output_steering = Utils.map_range(steering, 0, 1.0, self.STEERING_MID, 1000)
            else:
                output_steering = Utils.map_range(steering, -1, 0, 2000, self.STEERING_MID)

            # Ensure PWM values are integers
            output_steering = int(output_steering)
            output_throttle = int(output_throttle)

            if self.is_valid_pwm_value(output_steering) and self.is_valid_pwm_value(output_throttle):
                if self.debug:
                    logger.debug(f"output_steering={output_steering}, " f"output_throttle={output_throttle}")
                self.write_pwm(output_steering, output_throttle)
            else:
                logger.warning(f"Invalid PWM values: steering = {output_steering}, " f"throttle = {output_throttle}")
                logger.warning("Not sending PWM value to MM1")

        except OSError as err:
            logger.error(f"Unexpected issue setting PWM " f"(check wires to motor board): {err}")

    def is_valid_pwm_value(self, value):
        """Check if the PWM value is within valid range (1000 to 2000)"""
        return 1000 <= value <= 2000

    def write_pwm(self, steering, throttle):
        if self.pwm and self.pwm.is_open:
            try:
                # Ensure RC mode is disabled first time
                if not self._rc_disabled:
                    self.pwm.write(b"rc=disable\r")
                    if self.debug:
                        try:
                            echo = self.pwm.read_until(b'\r', timeout=SERIAL_TIMEOUT)
                            if echo.strip(b'\r')  != b"rc=disable":
                                logger.warning(f"Mismatch echo: {echo}")
                        except Exception as e:
                            logger.debug(f"No echo or error: {e}")
                    time.sleep(0.1)
                    self._rc_disabled = True
                # Send PWM command in correct format (no space after comma)
                pwm_command = b"%d,%d\r" % (steering, throttle)
                self.pwm.write(pwm_command)
                if self.debug:
                    try:
                        echo = self.pwm.read_until(b'\r', timeout=SERIAL_TIMEOUT)
                        if echo.strip(b'\r')  != pwm_command.strip():
                            logger.warning(f"Mismatch echo: {echo}")
                    except Exception as e:
                        logger.debug(f"No echo or error: {e}")
                logger.debug(f"Sent PWM command: {pwm_command}")
            except Exception as e:
                logger.error(f"Failed to write PWM command: {e}")
        else:
            logger.error("Cannot write PWM command. PWM serial port is not open.")

    def run(self, steering, throttle):
        self.set_pulse(steering, throttle)

    def shutdown(self):
        if self.pwm and self.pwm.is_open:
            try:
                # Send stop command and re-enable RC mode
                logger.info("Sending stop command and re-enabling RC mode...")
                self.pwm.write(b"1500,1500\r")  # Neutral position
                if self.debug:
                    try:
                        echo = self.pwm.read_until(b'\r', timeout=0.05)
                        logger.debug(f"RP2040 echo: {echo}")
                    except Exception as e:
                        logger.debug(f"No echo or error: {e}")
                time.sleep(0.1)
                self.pwm.write(b"rc=enable\r")   # Re-enable RC mode
                if self.debug:
                    try:
                        echo = self.pwm.read_until(b'\r', timeout=0.05)
                        logger.debug(f"RP2040 echo: {echo}")
                    except Exception as e:
                        logger.debug(f"No echo or error: {e}")
                time.sleep(0.1)
                
                self.pwm.close()
                logger.info("PWM serial connection closed.")
            except serial.SerialException:
                logger.error("Failed to close the PWM serial connection.")

    def stop_motors(self):
        """Stop all motors."""
        logger.info("RoboHAT: Stopping all motors")
        self.set_pulse(0, 0)  # Assuming 0 steering, 0 throttle stops motors

    def get_current_heading(self) -> float:
        """Get the current heading in degrees."""
        logger.info("RoboHAT: Getting current heading")
        # Placeholder for actual heading retrieval logic
        # This might involve reading from an IMU or GPS connected via RoboHAT
        return 0.0  # Replace with actual heading

    def get_current_position(self) -> tuple[float, float]:
        """Get the current position (x, y)."""
        logger.info("RoboHAT: Getting current position")
        # Placeholder for actual position retrieval logic
        # This might involve reading from GPS or odometry
        return (0.0, 0.0)  # Replace with actual position

    def rotate_to_heading(self, target_heading: float) -> bool:
        """Rotate the mower to a target heading."""
        logger.info(f"RoboHAT: Rotating to heading {target_heading}")
        # Placeholder for actual rotation logic
        # This would involve controlling motors based on current and target heading
        # For now, we'll simulate success
        current_heading = self.get_current_heading()
        logger.info(f"RoboHAT: Current heading {current_heading}, Target {target_heading}")
        # Simulate rotation
        time.sleep(1)  # Simulate time taken to rotate
        logger.info(f"RoboHAT: Rotation to {target_heading} complete.")
        return True

    def move_distance(self, distance: float, speed: float = 0.5) -> bool:
        """Move the mower a specific distance."""
        logger.info(f"RoboHAT: Moving distance {distance}m at speed {speed}")
        # Placeholder for actual movement logic
        # This would involve controlling motors for a certain duration or based on encoders
        # For now, we'll simulate success
        if distance > 0:  # Forward
            self.set_pulse(0, speed)
        elif distance < 0:  # Backward
            self.set_pulse(0, -speed)
        else:  # No movement
            self.set_pulse(0, 0)
            return True

        # Simulate time taken to move
        # This is a very rough approximation
        # Actual implementation would use encoders or GPS
        move_time = abs(distance / (speed * 0.5))  # Assuming average speed of 0.5 m/s for speed=1
        logger.info(f"RoboHAT: Estimated move time {move_time:.2f}s")
        time.sleep(move_time)
        self.stop_motors()  # Stop after moving
        logger.info(f"RoboHAT: Movement of {distance}m complete.")
        return True

    def get_status(self) -> dict:
        """Get the status of the RoboHAT."""
        logger.info("RoboHAT: Getting status")
        # Get status of motors and wheel encoders
        status = {
            "motors": "stopped",  # Placeholder, replace with actual motor status
            "encoders": "not implemented",  # Placeholder for encoder status
            "heading": self.get_current_heading(),
            "position": self.get_current_position(),
            "communication": getattr(self, 'communication_info', {}),
        }
        return status


def test_communication_modes():
    """Test and demonstrate different communication modes for RoboHAT."""
    logger.info("=== Testing RoboHAT Communication Modes ===")
    
    # Show available devices
    logger.info("Available devices:")
    available_devices = CommunicationModeHelper.detect_robohat_devices()
    for device in available_devices:
        logger.info(f"  - {device}")
    
    if not available_devices:
        logger.warning("No potential RoboHAT devices found!")
        return False
    
    # Test each communication mode
    modes_to_test = ["auto", "usb", "uart", "manual"]
    test_results = {}
    
    for mode in modes_to_test:
        logger.info(f"\n--- Testing {mode.upper()} mode ---")
        
        # Temporarily set environment variables for testing
        original_mode = os.getenv("MM1_COMMUNICATION_MODE", "auto")
        original_port = os.getenv("MM1_SERIAL_PORT", "/dev/ttyACM1")
        
        try:
            os.environ["MM1_COMMUNICATION_MODE"] = mode
            
            if mode == "manual":
                # Use the first available device for manual test
                os.environ["MM1_SERIAL_PORT"] = available_devices[0]
            
            # Try to initialize the driver
            driver = RoboHATDriver(debug=True)
            
            if driver.pwm and driver.pwm.is_open:
                logger.info(f"✓ {mode.upper()} mode: Successfully connected")
                
                # Test basic communication
                driver.set_pulse(0, 0)  # Send neutral command
                time.sleep(0.5)
                
                # Get status
                status = driver.get_status()
                logger.info(f"✓ {mode.upper()} mode: Communication info: {status.get('communication', {})}")
                
                test_results[mode] = "SUCCESS"
                driver.shutdown()
            else:
                logger.error(f"❌ {mode.upper()} mode: Failed to connect")
                test_results[mode] = "FAILED"
                
        except Exception as e:
            logger.error(f"❌ {mode.upper()} mode: Error - {e}")
            test_results[mode] = f"ERROR: {e}"
        
        finally:
            # Restore original environment variables
            os.environ["MM1_COMMUNICATION_MODE"] = original_mode
            os.environ["MM1_SERIAL_PORT"] = original_port
    
    # Report results
    logger.info("\n=== Communication Mode Test Results ===")
    for mode, result in test_results.items():
        status_icon = "✓" if result == "SUCCESS" else "❌"
        logger.info(f"{status_icon} {mode.upper()}: {result}")
    
    successful_modes = [mode for mode, result in test_results.items() if result == "SUCCESS"]
    
    if successful_modes:
        logger.info(f"\n🎉 Working communication modes: {', '.join(successful_modes)}")
        logger.info("Recommendation: Use 'auto' mode for best compatibility")
        return True
    else:
        logger.error("\n❌ No communication modes are working!")
        logger.error("Check connections and ensure RoboHAT is properly connected")
        return False


    """Test the RoboHAT driver functionality."""
    logger.info("=== Testing RoboHAT Driver ===")
    
    try:
        # No configuration needed for driver test
        
        # Initialize driver only (not controller to avoid infinite loop)
        driver = RoboHATDriver(debug=True)
        logger.info("✓ RoboHAT driver initialized successfully")
        
        # Test basic movement commands
        logger.info("Testing basic movement commands...")
        
        # Forward at 50% speed
        logger.info("Moving forward at 50% speed for 2 seconds...")
        driver.run(0, 0.5)
        time.sleep(2)
        
        # Stop
        logger.info("Stopping motors...")
        driver.stop_motors()
        time.sleep(1)
        
        # Backward at 50% speed
        logger.info("Moving backward at 50% speed for 2 seconds...")
        driver.run(0, -0.5)
        time.sleep(2)
        
        # Stop
        driver.stop_motors()
        time.sleep(1)
        
        # Turn left at 50% steering
        logger.info("Turning left at 50% steering for 2 seconds...")
        driver.run(-0.5, 0)
        time.sleep(2)
        
        # Stop
        driver.stop_motors()
        time.sleep(1)
        
        # Turn right at 50% steering
        logger.info("Turning right at 50% steering for 2 seconds...")
        driver.run(0.5, 0)
        time.sleep(2)
        
        # Stop
        driver.stop_motors()
        time.sleep(1)
        
        # Test status retrieval
        logger.info("Getting driver status...")
        status = driver.get_status()
        logger.info(f"Driver status: {status}")
        
        logger.info("✓ All driver tests completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Error during RoboHAT driver testing: {e}")
        return False
    finally:
        # Always clean up
        try:
            driver.shutdown()
            logger.info("Driver shutdown complete.")
        except Exception as e:
            logger.error(f"Error during driver shutdown: {e}")


def test_robohat_controller():
    """Test the RoboHAT controller functionality (without infinite loop)."""
    logger.info("=== Testing RoboHAT Controller ===")
    
    try:
        # Create a minimal configuration object for testing
        class TestConfig:
            MM1_SERIAL_PORT = os.getenv("MM1_SERIAL_PORT", "/dev/ttyACM1")
            AUTO_RECORD_ON_THROTTLE = False
            MM1_STEERING_MID = MM1_STEERING_MID
            MM1_MAX_FORWARD = MM1_MAX_FORWARD
            MM1_STOPPED_PWM = MM1_STOPPED_PWM
            MM1_MAX_REVERSE = MM1_MAX_REVERSE
            MM1_SHOW_STEERING_VALUE = False
            JOYSTICK_DEADZONE = 0.1
        
        cfg = TestConfig()
        
        # Initialize controller
        controller = RoboHATController(cfg, debug=True)
        logger.info("✓ RoboHAT controller initialized successfully")
        
        # Test serial connection
        if controller.serial and controller.serial.is_open:
            logger.info("✓ Serial connection established")
        else:
            logger.warning("⚠ Serial connection not available - this is expected if no RoboHAT is connected")
        
        # Test a few iterations of reading (instead of infinite loop)
        logger.info("Testing serial reading (5 iterations)...")
        for i in range(5):
            try:
                controller.read_serial()
                logger.info(f"Read iteration {i + 1}: angle={controller.angle:.2f}, throttle={controller.throttle:.2f}")
                time.sleep(0.1)
            except Exception as e:
                logger.warning(f"Read iteration {i + 1} failed: {e}")
        
        logger.info("✓ Controller test completed!")
        return True
        
    except Exception as e:
        logger.error(f"Error during RoboHAT controller testing: {e}")
        return False
    finally:
        # Always clean up
        try:
            controller.shutdown()
            logger.info("Controller shutdown complete.")
        except Exception as e:
            logger.error(f"Error during controller shutdown: {e}")

def test_robohat_driver():
    """Test the RoboHAT driver functionality."""
    logger.info("=== Testing RoboHAT Driver ===")
    
    try:
        # Initialize driver only (not controller to avoid infinite loop)
        driver = RoboHATDriver(debug=True)
        logger.info("✓ RoboHAT driver initialized successfully")
        
        # Test basic movement commands
        logger.info("Testing basic movement commands...")
        
        # Forward at 50% speed
        logger.info("Moving forward at 50% speed for 2 seconds...")
        driver.run(0, 0.5)
        time.sleep(2)
        
        # Stop
        logger.info("Stopping motors...")
        driver.stop_motors()
        time.sleep(1)
        
        # Backward at 50% speed
        logger.info("Moving backward at 50% speed for 2 seconds...")
        driver.run(0, -0.5)
        time.sleep(2)
        
        # Stop
        driver.stop_motors()
        time.sleep(1)
        
        # Turn left at 50% steering
        logger.info("Turning left at 50% steering for 2 seconds...")
        driver.run(-0.5, 0)
        time.sleep(2)
        
        # Stop
        driver.stop_motors()
        time.sleep(1)
        
        # Turn right at 50% steering
        logger.info("Turning right at 50% steering for 2 seconds...")
        driver.run(0.5, 0)
        time.sleep(2)
        
        # Stop
        driver.stop_motors()
        time.sleep(1)
        
        # Test status retrieval
        logger.info("Getting driver status...")
        status = driver.get_status()
        logger.info(f"Driver status: {status}")
        
        logger.info("✓ All driver tests completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Error during RoboHAT driver testing: {e}")
        return False
    finally:
        # Always clean up
        try:
            driver.shutdown()
            logger.info("Driver shutdown complete.")
        except Exception as e:
            logger.error(f"Error during driver shutdown: {e}")


# if __name__ == "__main__":
#     """Test script for RoboHAT MM1 functionality."""
#     logger.info("Starting RoboHAT MM1 test suite...")
#     logger.info("⚠️ Note: This test assumes the RoboHAT MM1 is connected and configured correctly.")
    
#     # Check command line arguments for specific tests
#     if len(sys.argv) > 1 and sys.argv[1] == "--test-comm":
#         # Run communication mode tests only
#         comm_success = test_communication_modes()
#         sys.exit(0 if comm_success else 1)
    
#     # Test communication modes first
#     logger.info("\n" + "="*50)
#     logger.info("PHASE 1: Communication Mode Testing")
#     logger.info("="*50)
#     comm_success = test_communication_modes()
    
#     if not comm_success:
#         logger.error("Communication mode testing failed. Cannot proceed with driver/controller tests.")
#         sys.exit(1)
    
#     # Test both components
#     logger.info("\n" + "="*50)
#     logger.info("PHASE 2: Driver and Controller Testing")
#     logger.info("="*50)
#     driver_success = test_robohat_driver()
#     controller_success = test_robohat_controller()
    
#     # Report results
#     logger.info("\n=== Final Test Results ===")
#     logger.info(f"Communication Tests: {'✓ PASSED' if comm_success else '❌ FAILED'}")
#     logger.info(f"Driver Test: {'✓ PASSED' if driver_success else '❌ FAILED'}")
#     logger.info(f"Controller Test: {'✓ PASSED' if controller_success else '❌ FAILED'}")
    
#     if comm_success and driver_success and controller_success:
#         logger.info("🎉 All RoboHAT tests passed!")
#         logger.info("\nRecommended settings for your .env file:")
#         logger.info("MM1_COMMUNICATION_MODE=auto")
#         logger.info("MM1_SERIAL_PORT=/dev/ttyACM1")
#         sys.exit(0)
#     else:
#         logger.error("❌ Some RoboHAT tests failed!")
#         logger.error("\nTroubleshooting:")
#         logger.error("1. Check RoboHAT connections")
#         logger.error("2. Verify device permissions (add user to dialout group)")
#         logger.error("3. Try different communication modes")
#         logger.error("4. Run: python3 robohat.py --test-comm")
#         sys.exit(1)

# Minimal direct movement test for RoboHAT MM1 (for hardware integration)
if __name__ == "__main__" and (len(sys.argv) == 1 or sys.argv[1] == "--direct-move-test"):
    print("\n=== RoboHAT MM1 Direct Movement Test ===")
    try:
        driver = RoboHATDriver(debug=True)
        print("Driver initialized. Moving forward...")
        driver.run(0, 0.5)
        time.sleep(2)
        print("Stopping...")
        driver.stop_motors()
        time.sleep(1)
        print("Moving backward...")
        driver.run(0, -0.5)
        time.sleep(2)
        print("Stopping...")
        driver.stop_motors()
        time.sleep(1)
        print("Turning left...")
        driver.run(-0.5, 0)
        time.sleep(2)
        print("Stopping...")
        driver.stop_motors()
        time.sleep(1)
        print("Turning right...")
        driver.run(0.5, 0)
        time.sleep(2)
        print("Stopping...")
        driver.stop_motors()
        print("Direct movement test complete. Shutting down driver.")
        driver.shutdown()
    except Exception as e:
        print(f"Direct movement test failed: {e}")
        try:
            driver.shutdown()
        except Exception:
            pass
    print("=== End of Direct Movement Test ===\n")