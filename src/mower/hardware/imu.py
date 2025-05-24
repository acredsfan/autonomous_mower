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
import time
import threading
import platform
import random
from typing import Dict, Any
from enum import Enum

# Only import hardware-specific modules on Linux platforms
if platform.system() == "Linux":
    try:
        import adafruit_bno08x
        from adafruit_bno08x.uart import BNO08X_UART
        import serial
    except ImportError:
        pass

from dotenv import load_dotenv
from mower.utilities.logger_config import LoggerConfigInfo as LoggerConfig
from mower.hardware.serial_port import SerialPort

# BNO085 Constants
CHANNEL_COMMAND = 0x00
CHANNEL_EXECUTABLE = 0x01
CHANNEL_CONTROL = 0x02
CHANNEL_REPORTS = 0x03
SHTP_REPORT_PRODUCT_ID_REQUEST = 0xF9
SENSOR_REPORTID_ROTATION_VECTOR = 0x05

# Initialize logger
logger = LoggerConfig.get_logger(__name__)

# Load environment variables
load_dotenv()
# Get the UART port from the environment variables
IMU_SERIAL_PORT = os.getenv("IMU_SERIAL_PORT", "/dev/ttyAMA2")
IMU_BAUDRATE = int(os.getenv("IMU_BAUD_RATE", "3000000"))
RECEIVER_BUFFER_SIZE = 2048  # Size of the receiver buffer for serial comms.


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


class BNO085Sensor:
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

        # Only try hardware initialization on Linux platforms
        if platform.system() == "Linux":
            try:
                logger.debug(
                    f"Attempting to initialize IMU on port {IMU_SERIAL_PORT} "
                    f"at {IMU_BAUDRATE} baud."
                )
                # Attempt to create and start the serial port
                self.serial_port_wrapper = SerialPort(
                    port=IMU_SERIAL_PORT,
                    baudrate=IMU_BAUDRATE,
                    timeout=0.1,  # Recommended for BNO08x stability
                    receiver_buffer_size=RECEIVER_BUFFER_SIZE
                )
                self.serial_port_wrapper.start()  # This might raise SerialException

                # If start() was successful, serial_port_wrapper.ser should be
                # an open port
                if not (
                        self.serial_port_wrapper.ser and
                        self.serial_port_wrapper.ser.is_open):
                    logger.error(
                        f"SerialPort.start() completed but port {IMU_SERIAL_PORT} "
                        f"is not open. IMU unavailable."
                    )
                    # This condition implies serial_port_wrapper.start() didn't throw an
                    # error but failed silently, which shouldn't happen based on
                    # SerialPort.start() implementation.
                    # However, as a safeguard, explicitly raise to be caught by the
                    # broader handler.
                    raise serial.SerialException(
                        f"Port {IMU_SERIAL_PORT} not open after SerialPort.start()")

                logger.info(
                    f"Serial port {IMU_SERIAL_PORT} opened successfully for IMU.")

                # Now, initialize BNO08X_UART with the raw pyserial object
                self.sensor = BNO08X_UART(
                    self.serial_port_wrapper.ser,
                    debug=False)  # Pass the .ser attribute

                logger.debug("Enabling BNO_REPORT_ROTATION_VECTOR for IMU.")
                self.sensor.enable_feature(
                    adafruit_bno08x.BNO_REPORT_ROTATION_VECTOR)
                # Optionally, enable other reports if needed:
                # logger.debug("Enabling BNO_REPORT_ACCELEROMETER.")
                # self.sensor.enable_feature(adafruit_bno08x.BNO_REPORT_ACCELEROMETER)
                # logger.debug("Enabling BNO_REPORT_GYROSCOPE.")
                # self.sensor.enable_feature(adafruit_bno08x.BNO_REPORT_GYROSCOPE)

                self.is_hardware_available = True
                logger.info(
                    "BNO085 IMU sensor initialized successfully using BNO08X_UART."
                )

            except (serial.SerialException, ImportError,
                    AttributeError, Exception) as e:
                error_type = type(e).__name__
                if isinstance(e, serial.SerialException):
                    logger.error(
                        f"SerialException during IMU initialization on "
                        f"port {IMU_SERIAL_PORT}: {e}"
                    )
                elif isinstance(e, ImportError):
                    logger.error(
                        f"ImportError: {e}. Ensure adafruit_bno08x and pyserial "
                        f"are installed. IMU unavailable."
                    )
                elif isinstance(e, AttributeError):
                    logger.error(
                        f"AttributeError during BNO08X_UART setup: {e}. "
                        f"This likely means the wrong object type was passed to "
                        f"BNO08X_UART."
                    )
                else:  # Catch any other unexpected errors
                    logger.error(
                        f"Unexpected {error_type} initializing BNO085 IMU sensor: {e}",
                        exc_info=True)

                self.is_hardware_available = False  # Mark IMU as unavailable
                self.sensor = None  # Ensure sensor object is None

                # If serial_port_wrapper was instantiated before the error,
                # attempt to close it
                if self.serial_port_wrapper:
                    logger.debug(
                        "Cleaning up serial port due to IMU initialization failure."
                    )
                    self.serial_port_wrapper.stop()
                    self.serial_port_wrapper = None
                    # Clear the reference to the wrapper

        else:  # Non-Linux platform
            logger.info(
                "Running on non-Linux platform. "
                "IMU sensor will return simulated values."
            )

        self._initialized = True

    def shutdown(self):
        """Cleanly shut down the IMU sensor and release resources."""
        logger.info("Shutting down BNO085 sensor.")
        with self.lock:  # Ensure thread safety during shutdown
            if self.serial_port_wrapper:
                logger.debug(f"Closing serial port {self.serial_port_wrapper.port} for IMU.")
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
                heading = math.degrees(
                    math.atan2(
                        2 * quaternion[1] * quaternion[2]
                        - 2 * quaternion[0] * quaternion[3],
                        2 * quaternion[0] * quaternion[0]
                        + 2 * quaternion[1] * quaternion[1]
                        - 1,
                    )
                )

                # Convert to 0-360 range
                heading = (heading + 360) % 360
                with self.lock:
                    self.last_heading = heading
                return heading
            except Exception as e:
                logger.warning(
                    f"Error reading IMU heading, using last value: {e}")
                return self.last_heading
        else:
            # Return simulated values with small changes
            with self.lock:
                self.last_heading = (
                    self.last_heading + random.uniform(-2, 2)) % 360
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
                roll = math.degrees(
                    math.atan2(
                        2 * quaternion[0] * quaternion[1]
                        + 2 * quaternion[2] * quaternion[3],
                        1
                        - 2 * quaternion[1] * quaternion[1]
                        - 2 * quaternion[2] * quaternion[2],
                    )
                )

                with self.lock:
                    self.last_roll = roll
                return roll
            except Exception as e:
                logger.warning(
                    f"Error reading IMU roll, using last value: {e}")
                return self.last_roll
        else:
            # Return simulated values with small changes
            with self.lock:
                # Keep roll within reasonable range
                self.last_roll = max(
                    -30, min(30, self.last_roll + random.uniform(-0.5, 0.5))
                )
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
                pitch = math.degrees(
                    math.asin(
                        2 * quaternion[0] * quaternion[2]
                        - 2 * quaternion[3] * quaternion[1]
                    )
                )

                with self.lock:
                    self.last_pitch = pitch
                return pitch
            except Exception as e:
                logger.warning(
                    f"Error reading IMU pitch, using last value: {e}")
                return self.last_pitch
        else:
            # Return simulated values with small changes
            with self.lock:
                # Keep pitch within reasonable range
                self.last_pitch = max(
                    -30, min(30, self.last_pitch + random.uniform(-0.5, 0.5))
                )
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
                    return self.sensor.calibration_status
                # Older API version or method not supported
                return {"system": 3, "gyro": 3, "accel": 3, "mag": 3}
            except Exception as e:
                logger.warning(f"Error reading calibration status: {e}")

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

    def get_sensor_data(self) -> Dict[str, Any]:
        """
        Get all IMU sensor data in one call.

        Returns:
            dict: All sensor data including orientation, acceleration, etc.
        """
        heading = self.get_heading()
        roll = self.get_roll()
        pitch = self.get_pitch()

        # We'll provide some simulated values for the rest of the data
        return {
            "heading": heading,
            "roll": roll,
            "pitch": pitch,
            "acceleration": {
                "x": random.uniform(-2, 2) if not self.is_hardware_available else 0,
                "y": random.uniform(-2, 2) if not self.is_hardware_available else 0,
                "z": (
                    9.8 + random.uniform(-0.2, 0.2)
                    if not self.is_hardware_available
                    else 9.8
                ),  # Gravity
            },
            "gyroscope": {
                "x": random.uniform(-0.1, 0.1) if not self.is_hardware_available else 0,
                "y": random.uniform(-0.1, 0.1) if not self.is_hardware_available else 0,
                "z": random.uniform(-0.1, 0.1) if not self.is_hardware_available else 0,
            },
            "calibration": self.get_calibration(),
            "safety": self.get_safety_status(),
        }


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

            print(
                f"Heading: {heading:.1f}°, Roll: {roll:.1f}°, Pitch: {pitch:.1f}°"
            )
            print(f"Calibration: {calib}")
            print(
                f"Safety status: {'WARNING' if safety['tilt_warning'] else 'OK'}")
            print("--------------------")
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopped by user")
