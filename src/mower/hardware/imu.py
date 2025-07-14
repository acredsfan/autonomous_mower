# FROZEN_DRIVER – do not edit (see .github/copilot-instructions.md)
"""
IMU (Inertial Measurement Unit) module for the autonomous mower.

This module provides functionality for reading and processing data from the
BNO085 IMU sensor, which provides orientation and motion tracking capabilities.

The module:
1. Manages communication with the BNO085 sensor
2. Provides real-time orientation data (roll, pitch, yaw)
3. Handles sensor calibration and error recovery
4. Implements data filtering and processing

Key features:
- Thread-safe operation with proper synchronization
- Automatic sensor calibration
- Error detection and recovery
- Data filtering for smooth readings
- Platform detection and fallback for development environments
"""

import math
import os
import platform
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from enum import Enum
from typing import Any, Dict, Tuple

# Only import hardware-specific modules on Linux platforms
if platform.system() == "Linux":
    try:
        import adafruit_bno08x
        import serial
        from adafruit_bno08x.uart import BNO08X_UART

        HARDWARE_AVAILABLE = True
    except ImportError:
        HARDWARE_AVAILABLE = False
        # Create dummy classes/modules for type checking
        adafruit_bno08x = None
        BNO08X_UART = None
        serial = None
else:
    HARDWARE_AVAILABLE = False
    adafruit_bno08x = None
    BNO08X_UART = None
    serial = None

from dotenv import load_dotenv

from mower.hardware.serial_port import SerialPort
from mower.interfaces.sensors import IMUSensorInterface
from mower.utilities.logger_config import LoggerConfigInfo

# BNO085 Constants
CHANNEL_COMMAND = 0x00
CHANNEL_EXECUTABLE = 0x01
CHANNEL_CONTROL = 0x02
CHANNEL_REPORTS = 0x03
SHTP_REPORT_PRODUCT_ID_REQUEST = 0xF9
SENSOR_REPORTID_ROTATION_VECTOR = 0x05

# Initialize logger
logger = LoggerConfigInfo.get_logger(__name__)

# Load environment variables
load_dotenv()
# Get the UART port from the environment variables - support both UART_PORT and IMU_SERIAL_PORT for compatibility
UART_PORT = os.getenv("UART_PORT", os.getenv("IMU_SERIAL_PORT", "/dev/ttyAMA4"))
IMU_SERIAL_PORT = UART_PORT  # Maintain backward compatibility
IMU_BAUDRATE = int(os.getenv("IMU_BAUD_RATE", "115200"))
RECEIVER_BUFFER_SIZE = 2048  # Size of the receiver buffer for serial comms.
IMU_INIT_TIMEOUT_S = 15.0  # Timeout for IMU hardware initialization in seconds


class IMUStatus(Enum):
    """
    Enum representing the different states of the IMU sensor.

    These states define the current operational status of the sensor
    and help manage error recovery and calibration procedures.

    States:
        INITIALIZING: Sensor is being initialized
        CALIBRATING: Sensor is undergoing calibration
        READY: Sensor is ready for operation
        ERROR: Sensor has encountered an error
        RECOVERING: Sensor is attempting to recover from an error
    """

    INITIALIZING = 0
    CALIBRATING = 1
    READY = 2
    ERROR = 3
    RECOVERING = 4


class BNO085Sensor(IMUSensorInterface):
    """
    Interface for the BNO085 IMU sensor with fallback for development environments.

    This class handles communication with the BNO085 Inertial Measurement Unit,
    providing orientation data for navigation and stabilization. It manages the
    serial connection, data parsing, and provides thread-safe access to sensor
    data.

    When running on non-Linux platforms or when hardware is unavailable, it
    provides simulated values for development purposes.

    Attributes:
        is_hardware_available (bool): Whether the hardware sensor is available
        last_heading (float): Last known heading value (degrees)
        last_roll (float): Last known roll value (degrees)
        last_pitch (float): Last known pitch value (degrees)
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        """Implement singleton pattern"""
        if cls._instance is None:
            cls._instance = super(BNO085Sensor, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize singleton instance."""
        if self._initialized:
            return

        self.sensor = None
        self.serial_port_wrapper = None  # To store the SerialPort instance
        self.is_hardware_available = False
        self.last_heading = 0.0
        self.last_roll = 0.0
        self.last_pitch = 0.0
        self.lock = threading.RLock()

        # Initialize sensor data
        self.quaternion = [1, 0, 0, 0]  # w, x, y, z
        self.roll = 0.0
        self.pitch = 0.0
        self.yaw = 0.0
        self.acceleration = [0, 0, 0]  # x, y, z
        self.gyro = [0, 0, 0]  # x, y, z
        self.calibration_status = 0

        # Safety monitoring attributes
        self.impact_threshold = float(os.getenv("IMPACT_THRESHOLD_G", "2.0"))
        self.tilt_threshold = float(os.getenv("TILT_THRESHOLD_DEG", "45.0"))
        self.last_impact_time = 0
        self.impact_cooldown = 1.0  # seconds between impact detections
        self.safety_callbacks = []

        if platform.system() == "Linux" and HARDWARE_AVAILABLE:
            # Use direct initialization with timeout instead of problematic threading
            start_time = time.monotonic()
            max_init_time = IMU_INIT_TIMEOUT_S
            
            try:
                logger.debug(f"IMU: Attempting to initialize IMU on port {IMU_SERIAL_PORT} at {IMU_BAUDRATE} baud.")
                
                # Initialize with timeout check and faster retry cycle
                while time.monotonic() - start_time < max_init_time:
                    try:
                        # Add timeout check within initialization attempt
                        self._perform_imu_hardware_init_attempt()
                        
                        # If we get here, initialization succeeded
                        if self.is_hardware_available:
                            logger.info(f"IMU: Hardware initialization completed successfully in {time.monotonic() - start_time:.2f}s")
                            break
                        else:
                            logger.warning("IMU: Hardware initialization attempt completed but hardware not available")
                            
                    except Exception as e:
                        elapsed = time.monotonic() - start_time
                        if elapsed >= max_init_time:
                            logger.error(f"IMU hardware initialization timed out after {elapsed:.2f}s: {e}")
                            self.is_hardware_available = False
                            self.sensor = None
                            break
                        logger.debug(f"IMU init attempt failed ({elapsed:.1f}s elapsed), retrying: {e}")
                        time.sleep(0.5)  # Brief pause before retry
                        
                if not self.is_hardware_available:
                    logger.error(f"IMU hardware initialization failed after {max_init_time}s timeout. IMU will be unavailable.")
                    
            except Exception as e:
                logger.error(f"IMU initialization failed with exception: {e}")
                self.is_hardware_available = False
                self.sensor = None

        else:  # Non-Linux platform or HARDWARE_AVAILABLE is False
            if platform.system() != "Linux":
                logger.info("Running on non-Linux platform. IMU sensor will return simulated values.")
            else: # HARDWARE_AVAILABLE was false
                logger.warning(
                    "Required hardware modules (adafruit_bno08x, serial) not available. "
                    "IMU sensor will return simulated values."
                )
            self.is_hardware_available = False # Explicitly set for simulation

        self._initialized = True

    def _perform_imu_hardware_init_attempt(self):
        """
        Attempts to initialize the IMU hardware with improved error handling.
        
        Addresses the TypeError: 'NoneType' object cannot be interpreted as an integer
        that occurs in the adafruit library when the serial port file descriptor is None.
        """
        # Ensure these are reset for the current attempt
        self.is_hardware_available = False
        self.sensor = None
        # Use a local variable for the serial port wrapper during this attempt
        current_attempt_serial_wrapper = None

        try:
            logger.debug(
                f"IMU Init Thread: Attempting to initialize IMU on port {IMU_SERIAL_PORT} "
                f"at {IMU_BAUDRATE} baud."
            )

            # First, try to open the serial port directly to validate it
            try:
                import serial
                test_serial = serial.Serial(IMU_SERIAL_PORT, IMU_BAUDRATE, timeout=0.1)
                
                # Validate that the file descriptor is valid
                if test_serial.fd is None or test_serial.fd < 0:
                    test_serial.close()
                    raise serial.SerialException(f"Invalid file descriptor for port {IMU_SERIAL_PORT}")
                
                test_serial.close()
                logger.debug(f"IMU: Serial port {IMU_SERIAL_PORT} validated successfully")
                
            except Exception as e:
                logger.error(f"IMU: Serial port validation failed: {e}")
                raise
            
            # Now use the SerialPort wrapper
            current_attempt_serial_wrapper = SerialPort(
                port=IMU_SERIAL_PORT,
                baudrate=IMU_BAUDRATE,
                timeout=0.1,
                receiver_buffer_size=RECEIVER_BUFFER_SIZE,
            )
            current_attempt_serial_wrapper.start()

            # Validate the wrapper state
            if not (current_attempt_serial_wrapper.ser and current_attempt_serial_wrapper.ser.is_open):
                logger.error(
                    f"IMU Init Thread: SerialPort.start() completed but port {IMU_SERIAL_PORT} "
                    f"is not open. IMU unavailable."
                )
                raise serial.SerialException(f"Port {IMU_SERIAL_PORT} not open after SerialPort.start()")
            
            # Additional validation of file descriptor
            if current_attempt_serial_wrapper.ser.fd is None or current_attempt_serial_wrapper.ser.fd < 0:
                logger.error(f"IMU: Invalid file descriptor ({current_attempt_serial_wrapper.ser.fd}) for serial port")
                raise serial.SerialException(f"Invalid file descriptor for {IMU_SERIAL_PORT}")

            logger.info(f"IMU Init Thread: Serial port {IMU_SERIAL_PORT} opened successfully for IMU.")
            # Assign to self.serial_port_wrapper only after successful open and start
            self.serial_port_wrapper = current_attempt_serial_wrapper

            # Initialize the BNO08X_UART sensor now that the serial port is successfully opened and started
            try:
                if BNO08X_UART is None:
                    logger.error("IMU Init Thread: BNO08X_UART class not available (adafruit_bno08x.uart import failed)")
                    raise ImportError("BNO08X_UART not available")

                logger.debug("IMU Init Thread: Creating BNO08X_UART instance...")
                
                # Clear serial buffers before BNO08X_UART initialization to help with reset issues
                try:
                    self.serial_port_wrapper.ser.reset_input_buffer()
                    self.serial_port_wrapper.ser.reset_output_buffer()
                    logger.debug("IMU Init Thread: Serial buffers cleared before BNO08X_UART init")
                except Exception as buffer_e:
                    logger.warning(f"IMU Init Thread: Could not clear serial buffers: {buffer_e}")
                
                # Try multiple approaches for BNO08X_UART initialization
                # Approach 1: Standard initialization with shorter timeout  
                logger.debug("IMU Init Thread: Attempt 1 - Standard BNO08X_UART initialization...")
                
                def create_bno08x_sensor_standard():
                    """Standard BNO08X_UART creation."""
                    return BNO08X_UART(uart=self.serial_port_wrapper.ser, debug=False)
                
                # Use ThreadPoolExecutor with shorter timeout for first attempt
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(create_bno08x_sensor_standard)
                    try:
                        # Short timeout for first attempt
                        self.sensor = future.result(timeout=5.0)
                        
                        if self.sensor is None:
                            logger.error("IMU Init Thread: BNO08X_UART constructor returned None!")
                            raise RuntimeError("BNO08X_UART constructor returned None")
                        
                        logger.info("IMU Init Thread: BNO08X_UART instance created successfully (standard approach)")
                        
                    except TimeoutError:
                        logger.warning("IMU Init Thread: Standard approach timed out after 5 seconds")
                        logger.info("IMU Init Thread: Attempting recovery approach...")
                        
                        # Approach 2: Close and reopen serial port before retry
                        try:
                            logger.debug("IMU Init Thread: Closing serial port for reset...")
                            self.serial_port_wrapper.ser.close()
                            time.sleep(0.5)  # Brief pause
                            
                            # Reopen serial port
                            logger.debug("IMU Init Thread: Reopening serial port...")
                            self.serial_port_wrapper.ser.open()
                            self.serial_port_wrapper.ser.reset_input_buffer()
                            self.serial_port_wrapper.ser.reset_output_buffer()
                            time.sleep(0.2)
                            
                            # Try BNO08X_UART again with fresh serial connection
                            def create_bno08x_sensor_retry():
                                """Retry BNO08X_UART creation with fresh serial port."""
                                return BNO08X_UART(uart=self.serial_port_wrapper.ser, debug=False)
                            
                            with ThreadPoolExecutor(max_workers=1) as retry_executor:
                                retry_future = retry_executor.submit(create_bno08x_sensor_retry)
                                try:
                                    # Longer timeout for retry attempt
                                    self.sensor = retry_future.result(timeout=8.0)
                                    
                                    if self.sensor is None:
                                        logger.error("IMU Init Thread: BNO08X_UART retry returned None!")
                                        raise RuntimeError("BNO08X_UART retry returned None")
                                    
                                    logger.info("IMU Init Thread: BNO08X_UART instance created successfully (retry approach)")
                                    
                                except TimeoutError:
                                    logger.error("IMU Init Thread: Both BNO08X_UART attempts timed out")
                                    logger.error("This indicates a persistent issue with the BNO085 reset sequence")
                                    logger.error("Possible causes:")
                                    logger.error("  - Hardware reset pin not properly managed")
                                    logger.error("  - Power supply issues during reset")
                                    logger.error("  - UART timing issues")
                                    logger.error("  - BNO085 firmware corruption")
                                    raise RuntimeError("BNO08X_UART initialization failed - reset sequence hanging")
                                    
                        except Exception as retry_e:
                            logger.error(f"IMU Init Thread: Serial port recovery failed: {retry_e}")
                            raise RuntimeError(f"BNO08X_UART initialization failed: {retry_e}")
                self.is_hardware_available = True
                
                # Enable the features we're interested in
                logger.debug("IMU Init Thread: Enabling rotation vector and calibration features...")
                
                # Enhanced feature enabling with timeout protection
                try:
                    executor = ThreadPoolExecutor(max_workers=1)
                    
                    def enable_features():
                        self.sensor.enable_feature(BNO_REPORT_ROTATION_VECTOR)
                        self.sensor.enable_feature(BNO_REPORT_CALIBRATION_STATUS)
                        logger.debug("IMU Init Thread: Enabled rotation vector and calibration features")

                    # Execute with timeout
                    future = executor.submit(enable_features)
                    future.result(timeout=3.0)  # 3-second timeout for feature enabling
                    
                except TimeoutError:
                    logger.warning("IMU Init Thread: Feature enabling timed out after 3s - continuing anyway")
                except Exception as e:
                    logger.warning(f"IMU Init Thread: Feature enabling failed: {e} - continuing anyway")
                finally:
                    executor.shutdown(wait=False)

                logger.info("IMU Init Thread: BNO085 IMU sensor initialization completed successfully")

            except Exception as e_sensor:
                logger.error(f"IMU Init Thread: Failed to create BNO08X_UART instance: {type(e_sensor).__name__}: {e_sensor}", exc_info=True)
                self.sensor = None
                self.is_hardware_available = False
                # Don't raise here, just mark as unavailable and continue

        except Exception as e_init:
            error_type = type(e_init).__name__
            logger.error(
                f"IMU Init Thread: Failed during hardware initialization: {error_type}: {e_init}", exc_info=True
            )
            self.is_hardware_available = False # Ensure this is false on any error
            self.sensor = None
            if current_attempt_serial_wrapper:
                logger.debug("IMU Init Thread: Cleaning up serial port due to initialization failure.")
                current_attempt_serial_wrapper.stop()
            # Ensure self.serial_port_wrapper is also None if it was assigned before an error
            self.serial_port_wrapper = None
        # No return value needed, method modifies instance attributes.

    def shutdown(self):
        """Cleanly shut down the IMU sensor and release resources."""
        logger.info("Shutting down BNO085 sensor.")
        with self.lock:  # Ensure thread safety during shutdown
            if self.serial_port_wrapper:
                logger.info(f"Closing serial port {self.serial_port_wrapper.port} for IMU.")
                self.serial_port_wrapper.stop()
                self.serial_port_wrapper = None
            self.sensor = None  # Clear the sensor instance
            self.is_hardware_available = False  # Mark as unavailable
        logger.info("BNO085 sensor shutdown complete.")

    def get_heading(self) -> float:
        """
        Get the current heading (yaw) from the IMU.

        Returns:
            float: Heading in degrees (0-360)
        """
        if self.is_hardware_available and self.sensor:
            try:
                quaternion = self.sensor.quaternion
                if quaternion is None or len(quaternion) < 4:
                    logger.warning("Invalid quaternion data from sensor")
                    return self.last_heading

                heading = math.degrees(
                    math.atan2(
                        2 * quaternion[1] * quaternion[2] - 2 * quaternion[0] * quaternion[3],
                        2 * quaternion[0] * quaternion[0] + 2 * quaternion[1] * quaternion[1] - 1,
                    )
                )

                # Convert to 0-360 range
                heading = (heading + 360) % 360
                with self.lock:
                    self.last_heading = heading
                return heading
            except Exception as e:
                logger.warning(f"Error reading IMU heading, using last value: {e}")
                return self.last_heading
        else:  # Return simulated values with small changes
            with self.lock:
                self.last_heading = (self.last_heading + random.uniform(-2, 2)) % 360
                return self.last_heading

    def get_roll(self) -> float:
        """
        Get the current roll from the IMU.

        Returns:
            float: Roll in degrees (-180 to 180)
        """
        if self.is_hardware_available and self.sensor:
            try:
                quaternion = self.sensor.quaternion
                if quaternion is None or len(quaternion) < 4:
                    logger.warning("Invalid quaternion data from sensor")
                    return self.last_roll

                roll = math.degrees(
                    math.atan2(
                        2 * quaternion[0] * quaternion[1] + 2 * quaternion[2] * quaternion[3],
                        1 - 2 * quaternion[1] * quaternion[1] - 2 * quaternion[2] * quaternion[2],
                    )
                )

                with self.lock:
                    self.last_roll = roll
                return roll
            except Exception as e:
                logger.warning(f"Error reading IMU roll, using last value: {e}")
                return self.last_roll
        else:
            # Return simulated values with small changes
            with self.lock:
                # Keep roll within reasonable range
                self.last_roll = max(-30, min(30, self.last_roll + random.uniform(-0.5, 0.5)))
                return self.last_roll

    def get_pitch(self) -> float:
        """
        Get the current pitch from the IMU.

        Returns:
            float: Pitch in degrees (-90 to 90)
        """
        if self.is_hardware_available and self.sensor:
            try:
                quaternion = self.sensor.quaternion
                if quaternion and len(quaternion) >= 4:
                    pitch = math.degrees(
                        math.asin(2 * quaternion[0] * quaternion[2] - 2 * quaternion[3] * quaternion[1])
                    )

                    with self.lock:
                        self.last_pitch = pitch
                    return pitch
                else:
                    logger.warning("Invalid quaternion data from IMU")
                    return self.last_pitch
            except Exception as e:
                logger.warning(f"Error reading IMU pitch, using last value: {e}")
                return self.last_pitch
        else:
            # Return simulated values with small changes
            with self.lock:
                # Keep pitch within reasonable range
                self.last_pitch = max(-30, min(30, self.last_pitch + random.uniform(-0.5, 0.5)))
                return self.last_pitch

    def get_calibration(self) -> Dict[str, int]:
        """
        Get calibration status from the IMU.

        Returns:
            dict: Calibration info (system, gyro, accel, mag).
        """
        if self.is_hardware_available and self.sensor:
            try:
                # Attempt to get real calibration data if supported
                if hasattr(self.sensor, "calibration_status"):
                    status = self.sensor.calibration_status
                    if isinstance(status, dict):
                        return status
                    else:
                        # Convert non-dict status to dict format
                        return {"system": 3, "gyro": 3, "accel": 3, "mag": 3}
                # Older API version or method not supported
                return {"system": 3, "gyro": 3, "accel": 3, "mag": 3}
            except Exception as e:
                logger.warning(f"Error reading calibration status: {e}")
                return {"system": 0, "gyro": 0, "accel": 0, "mag": 0}

        # Return simulated calibration data
        return {"system": 3, "gyro": 3, "accel": 3, "mag": 3}

    def get_safety_status(self) -> Dict[str, bool]:
        """
        Get safety status based on IMU readings.

        Returns:
            dict: Safety status with warnings and errors
        """
        roll = abs(self.get_roll())
        pitch = abs(self.get_pitch())

        # Define thresholds for warnings and errors
        tilt_warning = roll > 20 or pitch > 20
        tilt_error = roll > 30 or pitch > 30

        return {
            "tilt_warning": tilt_warning,
            "tilt_error": tilt_error,
            "vibration_warning": False,  # Could be implemented with real data
            "vibration_error": False,  # Could be implemented with real data
            "impact_detected": False,  # Could be implemented with real data
        }

    def get_quaternion(self) -> Tuple[float, float, float, float]:
        """
        Get the current quaternion from the IMU.

        Returns:
            Tuple[float, float, float, float]: Quaternion (w, x, y, z)
        """
        if self.is_hardware_available and self.sensor:
            try:
                quaternion = self.sensor.quaternion
                if quaternion is None or len(quaternion) < 4:
                    logger.warning("Invalid quaternion data from sensor")
                    return (1.0, 0.0, 0.0, 0.0)  # Default quaternion
                return tuple(quaternion)
            except Exception as e:
                logger.warning(f"Error reading IMU quaternion: {e}")
                return (1.0, 0.0, 0.0, 0.0)
        else:
            # Return simulated quaternion based on heading
            heading_rad = math.radians(self.get_heading())
            # Simple quaternion for rotation around Z axis
            return (
                math.cos(heading_rad / 2),  # w
                0.0,  # x
                0.0,  # y
                math.sin(heading_rad / 2)   # z
            )

    def get_sensor_data(self) -> Dict[str, Any]:
        """
        Get all IMU sensor data in one call.

        Returns:
            dict: All sensor data including orientation, acceleration, etc.
        """
        heading = self.get_heading()
        roll = self.get_roll()
        pitch = self.get_pitch()
        quaternion = self.get_quaternion()
        speed = 0  # TODO: Implement speed calculation based on acceleration data
        compass = 0  # TODO: Implement compass data based on heading

        # We'll provide some simulated values for the rest of the data
        return {
            "heading": heading,
            "roll": roll,
            "pitch": pitch,
            "quaternion": {"w": quaternion[0], "x": quaternion[1], "y": quaternion[2], "z": quaternion[3]},
            "acceleration": {
                "x": random.uniform(-2, 2) if not self.is_hardware_available else 0,
                "y": random.uniform(-2, 2) if not self.is_hardware_available else 0,
                "z": (9.8 + random.uniform(-0.2, 0.2) if not self.is_hardware_available else 9.8),  # Gravity
            },
            "gyroscope": {
                "x": random.uniform(-0.1, 0.1) if not self.is_hardware_available else 0,
                "y": random.uniform(-0.1, 0.1) if not self.is_hardware_available else 0,
                "z": random.uniform(-0.1, 0.1) if not self.is_hardware_available else 0,
            },
            "calibration": self.get_calibration(),
            "speed": speed,
            "compass": compass,
        }

    # IMUSensorInterface abstract method implementations
    def get_acceleration(self) -> Tuple[float, float, float]:
        """
        Get the current acceleration from the IMU.

        Returns:
            Tuple[float, float, float]: Acceleration in m/s² (x, y, z)
        """
        try:
            if self.is_hardware_available and self.sensor:
                # Get acceleration data from the BNO085 sensor
                accel_x, accel_y, accel_z = self.sensor.acceleration or (0.0, 0.0, 9.8)
                return (accel_x, accel_y, accel_z)
            else:
                # Return simulated acceleration values
                return (random.uniform(-0.1, 0.1), random.uniform(-0.1, 0.1), 9.8 + random.uniform(-0.1, 0.1))
        except Exception as e:
            logger.warning(f"Error reading IMU acceleration: {e}")
            return (0.0, 0.0, 9.8)

    def get_gyroscope(self) -> Tuple[float, float, float]:
        """
        Get the current gyroscope readings from the IMU.

        Returns:
            Tuple[float, float, float]: Angular velocity in rad/s (x, y, z)
        """
        try:
            if self.is_hardware_available and self.sensor:
                # Get gyroscope data from the BNO085 sensor
                gyro_x, gyro_y, gyro_z = self.sensor.gyro or (0.0, 0.0, 0.0)
                return (gyro_x, gyro_y, gyro_z)
            else:
                # Return simulated gyroscope values
                return (random.uniform(-0.1, 0.1), random.uniform(-0.1, 0.1), random.uniform(-0.1, 0.1))
        except Exception as e:
            logger.warning(f"Error reading IMU gyroscope: {e}")
            return (0.0, 0.0, 0.0)

    def get_magnetometer(self) -> Tuple[float, float, float]:
        """
        Get the current magnetometer readings from the IMU.

        Returns:
            Tuple[float, float, float]: Magnetic field in μT (x, y, z)
        """
        try:
            if self.is_hardware_available and self.sensor:
                # Get magnetometer data from the BNO085 sensor if available
                if hasattr(self.sensor, "magnetic"):
                    mag_x, mag_y, mag_z = self.sensor.magnetic or (0.0, 0.0, 0.0)
                    return (mag_x, mag_y, mag_z)
                else:
                    # Calculate magnetometer values based on heading
                    heading_rad = math.radians(self.get_heading())
                    mag_strength = 50.0  # Typical strength in μT
                    return (mag_strength * math.cos(heading_rad), mag_strength * math.sin(heading_rad), 0.0)
            else:
                # Return simulated magnetometer values based on simulated heading
                heading_rad = math.radians(self.get_heading())
                mag_strength = 50.0
                return (
                    mag_strength * math.cos(heading_rad) + random.uniform(-2, 2),
                    mag_strength * math.sin(heading_rad) + random.uniform(-2, 2),
                    random.uniform(-2, 2),
                )
        except Exception as e:
            logger.warning(f"Error reading IMU magnetometer: {e}")
            return (0.0, 0.0, 0.0)

    def get_orientation(self) -> Tuple[float, float, float]:
        """
        Get the current orientation from the IMU.

        Returns:
            Tuple[float, float, float]: Orientation in degrees (roll, pitch, yaw)
        """
        try:
            roll = self.get_roll()
            pitch = self.get_pitch()
            yaw = self.get_heading()
            return (roll, pitch, yaw)
        except Exception as e:
            logger.warning(f"Error reading IMU orientation: {e}")
            return (0.0, 0.0, 0.0)

    # SensorInterface abstract method implementations
    def initialize(self) -> bool:
        """
        Initialize the IMU sensor.

        Returns:
            bool: True if initialization was successful, False otherwise
        """
        return self.is_hardware_available

    def read(self) -> Dict[str, Any]:
        """
        Read data from the IMU sensor.

        Returns:
            Dict[str, Any]: Sensor readings
        """
        return self.get_sensor_data()

    def calibrate(self) -> bool:
        """
        Calibrate the IMU sensor.

        Returns:
            bool: True if calibration was successful, False otherwise
        """
        if self.is_hardware_available and self.sensor:
            try:
                # BNO085 handles its own calibration automatically
                # We can check if it's calibrated
                calib = self.get_calibration()
                return all(status >= 2 for status in calib.values())
            except Exception as e:
                logger.warning(f"Error checking IMU calibration: {e}")
                return False
        return True  # In simulation mode, assume calibrated

    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the IMU sensor.

        Returns:
            Dict[str, Any]: Sensor status information
        """
        return {
            "hardware_available": self.is_hardware_available,
            "last_heading": self.last_heading,
            "last_roll": self.last_roll,
            "last_pitch": self.last_pitch,
            "calibration": self.get_calibration(),
            "safety_status": self.get_safety_status(),
        }

    def cleanup(self) -> None:
        """Clean up resources used by the IMU sensor."""
        self.shutdown()


# For backwards compatibility with static methods
def read_bno085_accel(sensor):
    """Read BNO085 accelerometer data."""
    if sensor is None:
        return {}

    imu = BNO085Sensor()
    data = imu.get_sensor_data()
    return data["acceleration"]


def read_bno085_gyro(sensor):
    """Read BNO085 gyroscope data."""
    if sensor is None:
        return {}

    imu = BNO085Sensor()
    data = imu.get_sensor_data()
    return data["gyroscope"]


def read_bno085_magnetometer(sensor):
    """Read BNO085 magnetometer data."""
    if sensor is None:
        return {}

    imu = BNO085Sensor()
    data = imu.get_sensor_data()
    # Simulate magnetometer data based on heading
    heading_rad = math.radians(data["heading"])
    mag_strength = 50.0  # Typical strength in μT
    return {
        "x": mag_strength * math.cos(heading_rad),
        "y": mag_strength * math.sin(heading_rad),
        "z": 0,
    }


def calculate_quaternion(sensor):
    """Calculate quaternion orientation."""
    if sensor is None:
        return {}

    imu = BNO085Sensor()
    heading_rad = math.radians(imu.get_heading())
    # Simple quaternion for rotation around Z axis
    return {
        "q0": math.cos(heading_rad / 2),  # w
        "q1": 0,  # x
        "q2": 0,  # y
        "q3": math.sin(heading_rad / 2),  # z
    }


def calculate_heading(sensor):
    """Calculate heading in degrees."""
    if sensor is None:
        return -1

    imu = BNO085Sensor()
    return imu.get_heading()


def calculate_pitch(sensor):
    """Calculate pitch in degrees."""
    if sensor is None:
        return -1

    imu = BNO085Sensor()
    return imu.get_pitch()


def calculate_roll(sensor):
    """Calculate roll in degrees."""
    if sensor is None:
        return -1

    imu = BNO085Sensor()
    return imu.get_roll()


def calculate_speed(sensor):
    """Calculate speed from acceleration data."""
    if sensor is None:
        return -1

    accel_data = read_bno085_accel(sensor)
    if not accel_data:
        return -1

    # Simply return the magnitude of the acceleration vector
    x = accel_data.get("x", 0)
    y = accel_data.get("y", 0)
    z = accel_data.get("z", 0)
    return math.sqrt(x**2 + y**2 + z**2)


if __name__ == "__main__":
    print("Initializing BNO085 sensor...")
    imu = BNO085Sensor()

    # Read sensor data continuously
    try:
        while True:
            heading = imu.get_heading()
            roll = imu.get_roll()
            pitch = imu.get_pitch()
            calib = imu.get_calibration()
            safety = imu.get_safety_status()

            print(f"Heading: {heading:.1f}°, Roll: " f"{roll:.1f}°, Pitch: {pitch:.1f}°")
            print(f"Calibration: {calib}")
            print(f"Safety status: " f"{'WARNING' if safety['tilt_warning'] else 'OK'}")
            print("--------------------")
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopped by user")
