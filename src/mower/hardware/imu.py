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
"""

import math
import os
import time
import threading
import struct
from enum import Enum

import adafruit_bno08x
from adafruit_bno08x.uart import BNO08X_UART
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
IMU_SERIAL_PORT = os.getenv('IMU_SERIAL_PORT', '/dev/ttyAMA2')
IMU_BAUDRATE = int(os.getenv('IMU_BAUD_RATE', '3000000'))


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
    Interface for the BNO085 IMU sensor.

    This class handles communication with the BNO085 Inertial Measurement Unit,
    providing orientation data for navigation and stabilization. It manages the
    serial connection, data parsing, and provides thread-safe access to sensor
    data.

    Attributes:
        is_connected (bool): Status of connection to the IMU
        quaternion (list): Current orientation as quaternion [w, x, y, z]
        roll (float): Roll angle in degrees
        pitch (float): Pitch angle in degrees
        yaw (float): Yaw angle (heading) in degrees
        acceleration (list): Linear acceleration in m/s² [x, y, z]
        gyro (list): Angular rates in rad/s [x, y, z]
        calibration_status (int): Calibration level (0-3)

    Thread Safety:
        All sensor data access is protected by a read/write lock to ensure
        thread safety when reading sensor values from multiple threads.

    Troubleshooting:
        Connection issues:
        - Check serial port name and permissions
        - Verify baudrate matches sensor configuration
        - Ensure power supply to the sensor is stable

        Data inconsistencies:
        - Check if the sensor needs calibration
        - Verify physical mounting orientation
        - Look for magnetic interference sources

        No response:
        - Check if serial port exists and has correct permissions
        - Try restarting the sensor or cycling power
        - Verify wiring connections are secure
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
        # No-op stub for singleton initialization
        pass

    def __init__(self, serial_port_name=None, baudrate=None):
        """
        Initialize the BNO085 sensor interface.
        Args:
            serial_port_name (str, optional): Serial port name. If None,
                auto-discovery is attempted. Defaults to None.
            baudrate (int, optional): Baudrate for serial communication.
                Defaults to None, which will use the IMU_BAUD_RATE env var.

        The initialization process:
        1. Sets up initial values and threading locks
        2. Attempts to open the serial connection
        3. If successful, starts the read thread

        Note: Actual sensor initialization is done in the connect() method
        """
        # Serial communication attributes
        self.serial_port_name = serial_port_name
        self.baudrate = baudrate or IMU_BAUDRATE
        self.serial_port = None
        self.connected = False
        self.read_thread = None
        self.running = False

        # Thread safety
        self.lock = threading.RLock()

        # Sensor data
        self.quaternion = [1, 0, 0, 0]  # w, x, y, z
        self.roll = 0.0
        self.pitch = 0.0
        self.yaw = 0.0
        self.acceleration = [0, 0, 0]   # x, y, z
        self.gyro = [0, 0, 0]           # x, y, z
        self.calibration_status = 0

        # Connection management
        self.connect_attempts = 0
        self.max_connect_attempts = 5
        self.reconnection_delay = 2  # seconds

        # Safety monitoring attributes
        self.impact_threshold = float(
            os.getenv('IMPACT_THRESHOLD_G', '2.0'))
        self.tilt_threshold = float(
            os.getenv('TILT_THRESHOLD_DEG', '45.0'))
        self.last_impact_time = 0
        self.impact_cooldown = 1.0  # seconds between impact detections
        self.safety_callbacks = []

        # Try to establish a connection immediately
        self.connect()
        self.sensor = None  # Ensure sensor attribute exists for cleanup

    def connect(self):
        """
        Establish connection to the IMU sensor.

        This method:
        1. Tries to open the serial port (or auto-discover it).
        2. Sets up the communication parameters.
        3. Validates the connection by checking sensor response.
        4. Starts the read thread if successful.

        Returns:
            bool: True if connection successful, False otherwise

        Raises:
            RuntimeError: If repeated connection attempts fail.

        Troubleshooting:
            - If port not found, check device enumeration and permissions.
            - If connection fails, try cycling power to the IMU.
            - Verify correct wiring and voltage levels.
        """
        if self.connected:
            return True

        # Track repeated failures
        failure_count = 0
        # Define max retry attempts before raising error
        max_connect_attempts = 3
        reconnection_delay = 2    # Seconds to wait between retry attempts

        while failure_count < max_connect_attempts:
            try:
                # Create and open the serial port
                self.serial_port = SerialPort(
                    port=self.serial_port_name or IMU_SERIAL_PORT,
                    baudrate=self.baudrate
                    )
                success = self.serial_port.start()
                if not success:
                    logger.error("Failed to start IMU serial port")
                    failure_count += 1
                    time.sleep(reconnection_delay)
                    continue

                port_info = (
                    f"IMU serial port "
                    f"{self.serial_port_name or IMU_SERIAL_PORT} "
                    f"opened at {self.baudrate} baud"
                    )
                logger.info(port_info)

                # Try multiple times to initialize the sensor
                max_retries = 5
                for attempt in range(1, max_retries + 1):
                    try:
                        self.sensor = BNO08X_UART(self.serial_port.ser)
                        self.enable_features(self.sensor)
                        self.connected = True
                        init_msg = (
                            f"BNO085 sensor successfully initialized "
                            f"on attempt {attempt}"
                            )
                        logger.info(init_msg)
                        return True
                    except Exception as e:
                        error_msg = (
                            f"Failed to initialize BNO085 sensor on "
                            f"attempt {attempt}: {e}"
                            )
                        logger.warning(error_msg)
                        if attempt < max_retries:
                            time.sleep(1)  # Wait before retrying

                final_error = (
                    f"Failed to initialize BNO085 sensor after "
                    f"{max_retries} attempts"
                    )
                logger.error(final_error)
                # If we couldn't initialize the sensor, close the serial
                # port
                if self.serial_port:
                    self.serial_port.stop()

                failure_count += 1
                time.sleep(reconnection_delay)

            except Exception as e:
                logger.error(
                    f"Error during BNO085 sensor initialization: {e}")
                # Ensure port is closed if initialization fails
                if self.serial_port:
                    self.serial_port.stop()

                failure_count += 1
                time.sleep(reconnection_delay)

        # If we reach here, repeated attempts have failed
        raise RuntimeError(
            f"Repeated IMU connection failures exceeded threshold "
            f"({max_connect_attempts} attempts)"
            )

    def disconnect(self):
        """Disconnect from the BNO085 sensor"""
        try:
            sensor_to_cleanup = getattr(self, 'sensor', None)
            if sensor_to_cleanup:
                self.cleanup(sensor_to_cleanup)
                self.sensor = None

            if self.serial_port:
                self.serial_port.stop()
                self.serial_port = None

            self.connected = False
            logger.info("BNO085 sensor disconnected")
            return True
        except Exception as e:
            logger.error(f"Error disconnecting BNO085 sensor: {e}")
            return False

    def enable_features(self, sensor):
        """Enable BNO085 sensor features."""
        try:
            sensor.enable_feature(adafruit_bno08x.BNO_REPORT_ACCELEROMETER)
            sensor.enable_feature(adafruit_bno08x.BNO_REPORT_GYROSCOPE)
            sensor.enable_feature(adafruit_bno08x.BNO_REPORT_MAGNETOMETER)
            sensor.enable_feature(
                adafruit_bno08x.BNO_REPORT_ROTATION_VECTOR)
            logger.info("BNO085 features enabled.")
        except Exception as e:
            logger.error(f"Error enabling features on BNO085: {e}")
            raise

    def read_bno085_accel(self):
        """Read BNO085 accelerometer data."""
        if not self.connected or not self.sensor:
            logger.warning(
                "Cannot read accelerometer: BNO085 not connected")
            return {}

        try:
            accel_x, accel_y, accel_z = self.sensor.acceleration
            return {'x': accel_x, 'y': accel_y, 'z': accel_z}
        except Exception as e:
            logger.error(f"Error reading BNO085 accelerometer: {e}")
            return {}

    def read_bno085_gyro(self):
        """Read BNO085 gyroscope data."""
        if not self.connected or not self.sensor:
            logger.warning("Cannot read gyroscope: BNO085 not connected")
            return {}

        try:
            gyro_x, gyro_y, gyro_z = self.sensor.gyro
            return {'x': gyro_x, 'y': gyro_y, 'z': gyro_z}
        except Exception as e:
            logger.error(f"Error reading BNO085 gyroscope: {e}")
            return {}

    def read_bno085_magnetometer(self):
        """Read BNO085 magnetometer data."""
        if not self.connected or not self.sensor:
            logger.warning(
                "Cannot read magnetometer: BNO085 not connected")
            return {}

        try:
            mag_x, mag_y, mag_z = self.sensor.magnetic
            return {'x': mag_x, 'y': mag_y, 'z': mag_z}
        except Exception as e:
            logger.error(f"Error reading BNO085 magnetometer: {e}")
            return {}

    def calculate_quaternion(self):
        """Calculate Quaternion based on BNO085 rotation vector data."""
        if not self.connected or not self.sensor:
            logger.warning(
                "Cannot calculate quaternion: BNO085 not connected")
            return {}

        try:
            q0, q1, q2, q3 = self.sensor.quaternion
            return {'q0': q0, 'q1': q1, 'q2': q2, 'q3': q3}
        except Exception as e:
            logger.error(f"Error calculating Quaternion: {e}")
            return {}

    def calculate_heading(self):
        """Calculate heading from BNO085 sensor data."""
        if not self.connected or not self.sensor:
            logger.warning(
                "Cannot calculate heading: BNO085 not connected")
            return -1

        try:
            x, y, z = self.sensor.magnetic
            heading = math.degrees(math.atan2(y, x))
            if heading < 0:
                heading += 360
            return heading
        except Exception as e:
            logger.error(f"Error calculating heading: {e}")
            return -1

    def calculate_pitch(self):
        """Calculate pitch from BNO085 sensor data."""
        if not self.connected or not self.sensor:
            logger.warning("Cannot calculate pitch: BNO085 not connected")
            return -1

        try:
            x, y, z = self.sensor.acceleration
            x = max(min(x, 1.0), -1.0)  # Clamp x to the range [-1, 1]
            pitch = math.degrees(math.asin(-x))
            return pitch
        except Exception as e:
            logger.error(f"Error calculating pitch: {e}")
            return -1

    def calculate_roll(self):
        """Calculate roll from BNO085 sensor data."""
        if not self.connected or not self.sensor:
            logger.warning("Cannot calculate roll: BNO085 not connected")
            return -1

        try:
            x, y, z = self.sensor.acceleration
            y = max(min(y, 1.0), -1.0)  # Clamp y to the range [-1, 1]
            roll = math.degrees(math.asin(y))
            return roll
        except Exception as e:
            logger.error(f"Error calculating roll: {e}")
            return -1

    def calculate_speed(self):
        """Calculate speed from BNO085 sensor data."""
        if not self.connected or not self.sensor:
            logger.warning("Cannot calculate speed: BNO085 not connected")
            return -1

        try:
            x, y, z = self.sensor.acceleration
            speed = math.sqrt(x**2 + y**2 + z**2)
            return speed
        except Exception as e:
            logger.error(f"Error calculating speed: {e}")
            return -1

    def cleanup(self, sensor=None):
        """
        Reset and clean up BNO085 sensor resources.

        Args:
            sensor: Sensor instance to reset, uses self.sensor if None
        """
        sensor_to_cleanup = sensor or self.sensor
        if not sensor_to_cleanup:
            return

        try:
            sensor_to_cleanup.soft_reset()
            logger.info("BNO085 sensor reset.")
        except Exception as e:
            logger.error(f"Error resetting BNO085 sensor: {e}")

    def __del__(self):
        """Ensure resources are cleaned up when the object is destroyed."""
        self.disconnect()

    def _discover_serial_port(self):
        """
        Auto-discover a suitable serial port for the IMU.

        This method scans available serial ports and attempts to find
        a connected IMU by checking for expected responses.

        Returns:
            serial.Serial: Opened serial port if found, None otherwise

        Troubleshooting:
            - Ensure the IMU is powered
            - Check USB connections if using a USB-to-serial adapter
            - On Linux, verify user has permissions to access serial ports
        """
        import serial.tools.list_ports

        # Get list of available ports
        available_ports = list(serial.tools.list_ports.comports())
        logger.info(
            f"Available ports: {[port.device for port in available_ports]}")

        for port_info in available_ports:
            port_name = port_info.device
            try:
                # Skip Bluetooth ports and other obvious non-IMU ports
                if "rfcomm" in port_name or "AMA0" in port_name:
                    continue

                logger.info(f"Trying IMU on port {port_name}")
                test_port = serial.Serial(
                    port=port_name,
                    baudrate=self.baudrate,
                    bytesize=serial.EIGHTBITS,
                    timeout=1
                    )

                # Try to establish communication
                test_port.write(b'\x7E')  # Send any byte to wake up device
                time.sleep(0.1)

                # Read response (if any)
                response = test_port.read(10)

                # Check for any response (this is a simple check - can be
                # improved)
                if len(response) > 0:
                    logger.info(f"Found responsive device on {port_name}")
                    self.serial_port_name = port_name
                    return test_port

                test_port.close()

            except Exception as e:
                logger.debug(f"Error testing port {port_name}: {e}")
                continue

        return None

    def _initialize_sensor(self):
        """
        Initialize the IMU sensor after connecting.

        This method:
        1. Sends initialization commands to the sensor
        2. Sets up the desired reports (quaternion, acceleration, etc.)
        3. Verifies communication is working correctly

        Returns:
            bool: True if initialization succeeded, False otherwise

        Troubleshooting:
            - If initialization fails, try power cycling the sensor
            - Check for correct UART wiring (TX/RX may be swapped)
            - Verify correct baudrate is being used
        """
        try:
            # Reset the device first
            self._send_command(CHANNEL_EXECUTABLE, [1])
            time.sleep(0.5)

            # Request product ID to verify communication
            self._send_command(
                CHANNEL_COMMAND,
                [SHTP_REPORT_PRODUCT_ID_REQUEST])
            time.sleep(0.1)

            # Flush any pending data
            self.serial_port.flushInput()

            # Set up rotation vector report (quaternion orientation)
            self._enable_rotation_vector()

            # Wait a moment for the sensor to start reporting
            time.sleep(0.1)

            # Read some data to verify communication is working
            data = self.serial_port.read(100)
            if len(data) > 0:
                logger.info("IMU initialization successful")
                return True
            else:
                logger.error(
                    "IMU initialization failed - no data received")
                return False

        except Exception as e:
            logger.error(f"Error initializing IMU: {e}")
            return False

    def _enable_rotation_vector(self):
        """
        Enable the rotation vector report from the sensor.

        The rotation vector provides quaternion orientation data which
        is essential for determining the mower's orientation.

        Troubleshooting:
            - If no rotation data is received, check if
              sensor needs calibration
            - Verify the command is being properly sent to the device
        """
        try:
            # FRS write to enable rotation vector
            self._send_command(CHANNEL_CONTROL, [
                0x15, 0x00,  # Set feature report
                SENSOR_REPORTID_ROTATION_VECTOR, 0x00,  # Report ID
                0x05, 0x00,  # Set update rate to 20ms (50Hz)
                0x00, 0x00   # Specific settings
                ])
            logger.debug("Rotation vector report enabled")
        except Exception as e:
            logger.error(f"Error enabling rotation vector: {e}")

    def _send_command(self, channel, data):
        """
        Send a command to the IMU sensor.

        Args:
            channel (int): SHTP channel number
            data (list): List of bytes to send

        Troubleshooting:
            - If commands fail, check for correct packet format
            - Verify serial port is still open and connected
        """
        if not self.connected:
            logger.warning("Cannot send command, IMU not connected")
            return

        try:
            # Construct SHTP packet
            packet = bytearray()
            packet.append(len(data) & 0xFF)  # Length LSB
            packet.append((len(data) >> 8) & 0xFF)  # Length MSB
            packet.append(channel & 0xFF)  # Channel
            packet.append(0)  # Sequence number (handled by sensor)

            # Add data bytes
            for byte in data:
                packet.append(byte & 0xFF)

            # Send the packet
            self.serial_port.write(packet)
        except Exception as e:
            logger.error(f"Error sending command to IMU: {e}")
            self.connected = False

    def _read_loop(self):
        """
        Main reading loop that continuously reads and processes sensor data.

        This method runs in a separate thread and:
        1. Reads incoming data from the serial port
        2. Parses BNO085 data packets
        3. Updates orientation, acceleration, and calibration values
        4. Handles reconnection if the connection is lost

        Troubleshooting:
            - If the read loop stops, check for serial errors
            - For intermittent data, verify stable power supply to the sensor
            - If thread crashes, look for exceptions in the log
        """
        buffer = bytearray()

        while self.running:
            try:
                if not self.connected:
                    # Try to reconnect
                    if self.connect_attempts < self.max_connect_attempts:
                        logger.info(
                            "IMU disconnected. Attempting to reconnect...")
                        time.sleep(self.reconnection_delay)
                        self.connect()
                    else:
                        logger.error(
                            "Failed to reconnect to IMU after "
                            f"{self.max_connect_attempts} attempts")
                        time.sleep(5)  # Wait before trying again
                        self.connect_attempts = 0  # Reset counter to try again
                    continue

                # Read available data
                if self.serial_port and self.serial_port.is_open:
                    if self.serial_port.in_waiting > 0:
                        chunk = self.serial_port.read(
                            self.serial_port.in_waiting)
                        buffer.extend(chunk)

                        # Process complete packets
                        while len(
                                buffer) >= 4:  # Min packet size is 4 bytes
                            # Check for packet start
                            length = buffer[0] | (buffer[1] << 8)
                            channel = buffer[2]

                            # Check if we have the full packet
                            if len(buffer) >= length + 4:
                                packet = buffer[4:length + 4]
                                self._process_packet(channel, packet)
                                # Remove processed packet
                                buffer = buffer[length + 4:]
                            else:
                                break  # Wait for more data
                    else:
                        # Small delay to avoid high CPU usage
                        time.sleep(0.005)
                else:
                    logger.warning("Serial port not open in read loop")
                    self.connected = False

            except Exception as e:
                logger.error(f"Error in IMU read loop: {e}")
                self.connected = False
                time.sleep(1)

    def _process_packet(self, channel, packet):
        """
        Process a received data packet from the IMU.

        Args:
            channel (int): SHTP channel from which packet was received
            packet (bytearray): Data packet bytes

        This method parses various types of reports from the sensor
        and updates the corresponding attributes with new values.

        Troubleshooting:
            - For parsing errors, check the packet format documentation
            - Verify the firmware version is compatible with this code
        """
        if len(packet) < 1:
            return

        # Check report ID
        report_id = packet[0]

        # Process based on channel and report type
        if (channel == CHANNEL_REPORTS and
                report_id == SENSOR_REPORTID_ROTATION_VECTOR):
            # Parse rotation vector (quaternion)
            if len(packet) >= 17:
                with self.lock:
                    # Extract quaternion components (i, j, k, real) - BNO085
                    # specific format
                    i = struct.unpack('<h', packet[2:4])[0] / 16384.0
                    j = struct.unpack('<h', packet[4:6])[0] / 16384.0
                    k = struct.unpack('<h', packet[6:8])[0] / 16384.0
                    real = struct.unpack('<h', packet[8:10])[0] / 16384.0

                    # BNO085 uses different quaternion order, rearrange to w,
                    # x, y, z
                    self.quaternion = [real, i, j, k]

                    # Calculate roll, pitch, yaw (Euler angles)
                    self._update_euler_angles()

                    # Extract accuracy estimate if available
                    if len(packet) >= 18:
                        accuracy = struct.unpack(
                            '<h', packet[10:12])[0] / 16.0
                        self.calibration_status = min(
                            3, int(accuracy / 30))  # Convert to 0-3 scale

        # Accelerometer report
        elif channel == CHANNEL_REPORTS and report_id == 0x14:
            # Parse accelerometer data if needed
            if len(packet) >= 10:
                with self.lock:
                    x = struct.unpack('<h', packet[2:4])[0] / 100.0  # m/s²
                    y = struct.unpack('<h', packet[4:6])[0] / 100.0
                    z = struct.unpack('<h', packet[6:8])[0] / 100.0
                    self.acceleration = [x, y, z]

        # Gyroscope report
        elif channel == CHANNEL_REPORTS and report_id == 0x13:
            # Parse gyroscope data if needed
            if len(packet) >= 10:
                with self.lock:
                    x = struct.unpack('<h', packet[2:4])[0] / 16.0  # rad/s
                    y = struct.unpack('<h', packet[4:6])[0] / 16.0
                    z = struct.unpack('<h', packet[6:8])[0] / 16.0
                    self.gyro = [x, y, z]

        # After processing any packet, check safety conditions
        safety_status = self.check_safety_conditions()
        if not safety_status['is_safe']:
            logger.warning(
                "Unsafe condition detected: "
                f"{', '.join(safety_status['messages'])}")

    def _update_euler_angles(self):
        """
        Calculate Euler angles from quaternion.

        Converts the quaternion orientation to roll, pitch, and yaw angles
        in degrees. This provides a more intuitive representation of
        orientation.

        Troubleshooting:
            - For unusual angles, verify the sensor coordinate system
            - Check for gimbal lock situations at pitch = ±90°
        """
        # Extract quaternion components
        w, x, y, z = self.quaternion

        # Roll (x-axis rotation)
        sinr_cosp = 2.0 * (w * x + y * z)
        cosr_cosp = 1.0 - 2.0 * (x * x + y * y)
        self.roll = math.degrees(math.atan2(sinr_cosp, cosr_cosp))

        # Pitch (y-axis rotation)
        sinp = 2.0 * (w * y - z * x)
        if abs(sinp) >= 1:
            # Use 90 degrees if out of range
            self.pitch = math.copysign(90, sinp)
        else:
            self.pitch = math.degrees(math.asin(sinp))

        # Yaw (z-axis rotation)
        siny_cosp = 2.0 * (w * z + x * y)
        cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
        self.yaw = math.degrees(math.atan2(siny_cosp, cosy_cosp))

        # Normalize yaw to 0-360
        self.yaw = (self.yaw + 360) % 360

    def get_orientation(self):
        """
        Get the current orientation as Euler angles.

        Returns:
            tuple: (roll, pitch, yaw) in degrees

        Thread-safe method for obtaining the current orientation angles.
        """
        with self.lock:
            return (self.roll, self.pitch, self.yaw)

    def get_quaternion(self):
        """
        Get the current orientation as a quaternion.

        Returns:
            list: [w, x, y, z] quaternion components

        Quaternions are more suitable for orientation calculations
        as they avoid gimbal lock issues.
        """
        with self.lock:
            return self.quaternion.copy()

    def get_acceleration(self):
        """
        Get the current linear acceleration.

        Returns:
            list: [x, y, z] acceleration in m/s²

        Useful for detecting motion, impacts, or unexpected movements.
        """
        with self.lock:
            return self.acceleration.copy()

    def get_gyro(self):
        """
        Get the current angular rates.

        Returns:
            list: [x, y, z] angular rates in rad/s

        Useful for rotation speed detection and motion analysis.
        """
        with self.lock:
            return self.gyro.copy()

    def get_heading(self):
        """
        Get the current heading (yaw angle).

        Returns:
            float: Heading angle in degrees (0-360)

        This is the primary value used for navigation and direction control.
        """
        with self.lock:
            return self.yaw

    def get_calibration_status(self):
        """
        Get the current calibration status.

        Returns:
            int: Calibration level (0-3)

        Calibration levels:
            0: Uncalibrated
            1: Partially calibrated
            2: Mostly calibrated
            3: Fully calibrated

        Low calibration levels may result in inaccurate orientation data.
        """
        with self.lock:
            return self.calibration_status

    def start(self):
        """
        Start the IMU sensor operations.

        This is called when the sensor needs to be activated as part of
        the mower startup sequence. It ensures the connection is established
        and the read thread is running.

        Returns:
            bool: True if started successfully, False otherwise
        """
        if not self.connected:
            return self.connect()

        return True

    def stop(self):
        """Stop the read thread"""
        self.running = False
        if self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=1.0)

    def release_resources(self):
        """
        Clean up resources used by the IMU sensor.

        This should be called when the mower is shutting down.
        """
        logger.info("Cleaning up IMU sensor resources")

        # Stop the read thread
        self.running = False
        if self.read_thread and self.read_thread.is_alive():
            try:
                self.read_thread.join(timeout=2.0)
            except Exception as e:
                logger.warning(f"Error joining IMU read thread: {e}")

        # Close the serial port
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.close()
                logger.info("IMU serial port closed")
            except Exception as e:
                logger.error(f"Error closing IMU serial port: {e}")

        # Reset connection status
        self.connected = False
        self.serial_port = None
        self.read_thread = None

    def register_safety_callback(self, callback):
        """Register a callback for safety events."""
        self.safety_callbacks.append(callback)

    def check_safety_conditions(self):
        """
        Check all safety conditions and return a safety status.

        Returns:
            dict: Safety status containing:
                - is_safe (bool): Overall safety status
                - tilt_ok (bool): Tilt angle within limits
                - impact_detected (bool): Recent impact detection
                - acceleration_ok (bool): Acceleration within limits
                - messages (list): List of safety messages
        """
        with self.lock:
            status = {
                'is_safe': True,
                'tilt_ok': True,
                'impact_detected': False,
                'acceleration_ok': True,
                'messages': []
                }

            # Check tilt angle
            if abs(
                    self.roll) > self.tilt_threshold or abs(
                    self.pitch) > self.tilt_threshold:
                status['is_safe'] = False
                status['tilt_ok'] = False
                status['messages'].append(
                    "Dangerous tilt angle detected: "
                    f"Roll={self.roll:.1f}°, Pitch={self.pitch:.1f}°")

            # Check for impacts/collisions
            accel_magnitude = math.sqrt(
                sum(x * x for x in self.acceleration)
                )
            # Convert G to m/s²
            if accel_magnitude > self.impact_threshold * 9.81:
                current_time = time.time()
                if current_time - self.last_impact_time > self.impact_cooldown:
                    status['is_safe'] = False
                    status['impact_detected'] = True
                    status['messages'].append(
                        "Impact detected! Acceleration: "
                        f"{accel_magnitude:.1f} m/s²")
                    self.last_impact_time = current_time

            # Check for abnormal acceleration
            if any(
                    abs(a) > 20.0 for a in self.acceleration):  # 20 m/s²
                status['is_safe'] = False
                status['acceleration_ok'] = False
                status['messages'].append(
                    "Abnormal acceleration detected!")

            # Notify callbacks if unsafe condition detected
            if not status['is_safe']:
                for callback in self.safety_callbacks:
                    try:
                        callback(status)
                    except Exception as e:
                        logger.error(f"Error in safety callback: {e}")

            return status

    def get_safety_status(self):
        """
        Get the current safety status.

        Returns:
            dict: Current safety status including tilt, impact,
            and acceleration data
        """
        return self.check_safety_conditions()


# For backwards compatibility with static methods
def read_bno085_accel(sensor):
    try:
        accel_x, accel_y, accel_z = sensor.acceleration
        return {'x': accel_x, 'y': accel_y, 'z': accel_z}
    except Exception as e:
        logger.error(f"Error reading BNO085 accelerometer: {e}")
        return {}


def read_bno085_gyro(sensor):
    try:
        gyro_x, gyro_y, gyro_z = sensor.gyro
        return {'x': gyro_x, 'y': gyro_y, 'z': gyro_z}
    except Exception as e:
        logger.error(f"Error reading BNO085 gyroscope: {e}")
        return {}


def read_bno085_magnetometer(sensor):
    try:
        mag_x, mag_y, mag_z = sensor.magnetic
        return {'x': mag_x, 'y': mag_y, 'z': mag_z}
    except Exception as e:
        logger.error(f"Error reading BNO085 magnetometer: {e}")
        return {}


def calculate_quaternion(sensor):
    try:
        q0, q1, q2, q3 = sensor.quaternion
        return {'q0': q0, 'q1': q1, 'q2': q2, 'q3': q3}
    except Exception as e:
        logger.error(f"Error calculating Quaternion: {e}")
        return {}


def calculate_heading(sensor):
    try:
        x, y, z = sensor.magnetic
        heading = math.degrees(math.atan2(y, x))
        if heading < 0:
            heading += 360
        return heading
    except Exception as e:
        logger.error(f"Error calculating heading: {e}")
        return -1


def calculate_pitch(sensor):
    try:
        x, y, z = sensor.acceleration
        x = max(min(x, 1.0), -1.0)  # Clamp x to the range [-1, 1]
        pitch = math.degrees(math.asin(-x))
        return pitch
    except Exception as e:
        logger.error(f"Error calculating pitch: {e}")
        return -1


def calculate_roll(sensor):
    try:
        x, y, z = sensor.acceleration
        y = max(min(y, 1.0), -1.0)  # Clamp y to the range [-1, 1]
        roll = math.degrees(math.asin(y))
        return roll
    except Exception as e:
        logger.error(f"Error calculating roll: {e}")
        return -1


def calculate_speed(sensor):
    try:
        x, y, z = sensor.acceleration
        speed = math.sqrt(x**2 + y**2 + z**2)
        return speed
    except Exception as e:
        logger.error(f"Error calculating speed: {e}")
        return -1


def enable_features(sensor):
    try:
        sensor.enable_feature(adafruit_bno08x.BNO_REPORT_ACCELEROMETER)
        sensor.enable_feature(adafruit_bno08x.BNO_REPORT_GYROSCOPE)
        sensor.enable_feature(adafruit_bno08x.BNO_REPORT_MAGNETOMETER)
        sensor.enable_feature(adafruit_bno08x.BNO_REPORT_ROTATION_VECTOR)
        logger.info("BNO085 features enabled.")
    except Exception as e:
        logger.error(f"Error enabling features on BNO085: {e}")


if __name__ == '__main__':
    try:
        # Use the singleton BNO085Sensor instance
        imu = BNO085Sensor()
        if imu.connect():
            logger.info("BNO085 sensor connected successfully.")

            # Main loop to read and display sensor data
            while True:
                accel_data = imu.read_bno085_accel()
                gyro_data = imu.read_bno085_gyro()
                mag_data = imu.read_bno085_magnetometer()
                quaternion = imu.calculate_quaternion()
                heading = imu.calculate_heading()
                pitch = imu.calculate_pitch()
                roll = imu.calculate_roll()
                speed = imu.calculate_speed()

                print(f"Accelerometer: {accel_data}")
                print(f"Gyroscope: {gyro_data}")
                print(f"Magnetometer: {mag_data}")
                print(f"Quaternion: {quaternion}")
                print(f"Heading: {heading}")
                print(f"Pitch: {pitch}")
                print(f"Roll: {roll}")
                print(f"Speed: {speed}")
                time.sleep(1)
        else:
            logger.error("Failed to connect to BNO085 sensor.")
    except KeyboardInterrupt:
        logger.info("IMU test exiting due to keyboard interrupt...")
    except Exception as e:
        logger.exception(f"Error in IMU test: {e}")
    finally:
        if 'imu' in locals():
            imu.disconnect()
        logger.info("IMU test completed.")
