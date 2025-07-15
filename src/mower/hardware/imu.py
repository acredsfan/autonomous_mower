# FROZEN_DRIVER – do not edit (see .github/copilot-instructions.md)
"""
IMU (Inertial Measurement Unit) module for the autonomous mower.

This module provides a simplified, direct interface for the BNO085 IMU sensor,
designed to be used with an asynchronous manager. It focuses on providing
reliable sensor readings without managing its own threads or loops.

Based on the Adafruit CircuitPython BNO08x library.
https://learn.adafruit.com/adafruit-9-dof-orientation-imu-fusion-breakout-bno085/python-circuitpython
"""

import os
import platform
import math
import random
import time
from typing import Any, Dict, Tuple

# Only import hardware-specific modules on Linux platforms
if platform.system() == "Linux":
    try:
        import serial
        import adafruit_bno08x
        from adafruit_bno08x.uart import BNO08X_UART
        HARDWARE_AVAILABLE = True
    except ImportError:
        HARDWARE_AVAILABLE = False
        BNO08X_UART = None
        serial = None
        adafruit_bno08x = None
else:
    HARDWARE_AVAILABLE = False
    BNO08X_UART = None
    serial = None
    adafruit_bno08x = None

from dotenv import load_dotenv
from mower.utilities.logger_config import LoggerConfigInfo

# Initialize logger
logger = LoggerConfigInfo.get_logger(__name__)

# Load environment variables
load_dotenv()
IMU_SERIAL_PORT = os.getenv("IMU_SERIAL_PORT", "/dev/ttyAMA4")
IMU_BAUDRATE = int(os.getenv("IMU_BAUD_RATE", "3000000"))
TILT_THRESHOLD_DEG = float(os.getenv("TILT_THRESHOLD_DEG", "45.0"))


class BNO085Sensor:
    """
    Interface for the BNO085 IMU sensor with fallback for development.

    This class handles communication with the BNO085, providing orientation
    and motion data. When running on non-Linux platforms or when hardware is
    unavailable, it provides simulated values for development.
    """

    def __init__(self, simulate: bool = False):
        """
        Initializes the BNO085 sensor.

        Args:
            simulate (bool): If True, forces simulation mode.
        """
        self.sensor = None
        self.is_hardware_available = False

        if simulate or not HARDWARE_AVAILABLE:
            logger.info("IMU: Using simulated data.")
            self.is_hardware_available = False
        else:
            try:
                logger.info(f"IMU: Initializing on port {IMU_SERIAL_PORT} at {IMU_BAUDRATE} baud.")
                uart = serial.Serial(IMU_SERIAL_PORT, baudrate=IMU_BAUDRATE, timeout=2)
                self.sensor = BNO08X_UART(uart)
                self.is_hardware_available = True

                # Enable required reports
                self.sensor.enable_feature(adafruit_bno08x.BNO_REPORT_ROTATION_VECTOR)
                self.sensor.enable_feature(adafruit_bno08x.BNO_REPORT_ACCELEROMETER)
                self.sensor.enable_feature(adafruit_bno08x.BNO_REPORT_GYROSCOPE)
                self.sensor.enable_feature(adafruit_bno08x.BNO_REPORT_MAGNETOMETER)
                self.sensor.enable_feature(adafruit_bno08x.BNO_REPORT_LINEAR_ACCELERATION)
                # This report is needed for the calibration_status property
                # self.sensor.enable_feature(adafruit_bno08x.BNO_REPORT_CALIBRATION_STATUS)
                logger.info("IMU: BNO085 initialized and features enabled successfully.")
            except Exception as e:
                logger.error(f"IMU: Hardware initialization failed: {e}", exc_info=True)
                self.is_hardware_available = False
                self.sensor = None

    def get_sensor_data(self) -> Dict[str, Any]:
        """
        Get all IMU sensor data in one call.

        This method is designed to be called from the async_sensor_manager's executor.
        It fetches all relevant sensor values from the hardware.

        Returns:
            dict: All sensor data including orientation, acceleration, etc.
        """
        if not self.is_hardware_available:
            return self._get_simulated_data()

        try:
            # Fetch all data points from the sensor
            quat_i, quat_j, quat_k, quat_real = self.sensor.quaternion
            accel_x, accel_y, accel_z = self.sensor.acceleration
            gyro_x, gyro_y, gyro_z = self.sensor.gyro
            mag_x, mag_y, mag_z = self.sensor.magnetic
            linear_accel_x, linear_accel_y, linear_accel_z = self.sensor.linear_acceleration

            # Calculate roll, pitch, and yaw from the quaternion
            roll, pitch, yaw = self._quaternion_to_euler(quat_real, quat_i, quat_j, quat_k)

            return {
                "heading": yaw,
                "roll": roll,
                "pitch": pitch,
                "quaternion": {"w": quat_real, "x": quat_i, "y": quat_j, "z": quat_k},
                "acceleration": {"x": accel_x, "y": accel_y, "z": accel_z},
                "linear_acceleration": {"x": linear_accel_x, "y": linear_accel_y, "z": linear_accel_z},
                "gyroscope": {"x": gyro_x, "y": gyro_y, "z": gyro_z},
                "magnetometer": {"x": mag_x, "y": mag_y, "z": mag_z},
                "calibration": self._get_calibration_status(),
                "safety_status": self._get_safety_status(roll, pitch)
            }
        except Exception as e:
            logger.error(f"IMU: Failed to read sensor data: {e}")
            # Fallback to simulated data on read error to prevent crashes
            return self._get_simulated_data(is_error=True)

    def _get_calibration_status(self) -> Dict[str, int]:
        """
        Gets the calibration status from the sensor.
        
        CORRECTED: Uses the 'calibration_status' attribute which returns a single
        integer representing the overall calibration level.
        """
        status = self.sensor.calibration_status
        # Map the single status value to the dictionary structure for API consistency.
        return {
            "system": status,
            "gyro": status,
            "accel": status,
            "mag": status
        }

    def _get_safety_status(self, roll: float, pitch: float) -> Dict[str, Any]:
        """Determines safety status based on tilt."""
        # You can adjust these thresholds
        is_safe = abs(roll) < TILT_THRESHOLD_DEG and abs(pitch) < TILT_THRESHOLD_DEG
        status = "ok" if is_safe else "tilt_exceeded"
        
        return {"is_safe": is_safe, "status": status}

    def _quaternion_to_euler(self, w: float, x: float, y: float, z: float) -> Tuple[float, float, float]:
        """Converts a quaternion into roll, pitch, and yaw in degrees."""
        # Roll (x-axis rotation)
        t0 = +2.0 * (w * x + y * z)
        t1 = +1.0 - 2.0 * (x * x + y * y)
        roll_rad = math.atan2(t0, t1)

        # Pitch (y-axis rotation)
        t2 = +2.0 * (w * y - z * x)
        t2 = +1.0 if t2 > +1.0 else t2
        t2 = -1.0 if t2 < -1.0 else t2
        pitch_rad = math.asin(t2)

        # Yaw (z-axis rotation)
        t3 = +2.0 * (w * z + x * y)
        t4 = +1.0 - 2.0 * (y * y + z * z)
        yaw_rad = math.atan2(t3, t4)

        # Convert to degrees and adjust yaw to be 0-360
        roll = math.degrees(roll_rad)
        pitch = math.degrees(pitch_rad)
        yaw = (math.degrees(yaw_rad) + 360) % 360

        return roll, pitch, yaw
        
    def _get_simulated_data(self, is_error: bool = False) -> Dict[str, Any]:
        """Generates a full set of simulated sensor data."""
        return {
            "heading": round(random.uniform(0, 360), 1),
            "roll": round(random.uniform(-5, 5), 1),
            "pitch": round(random.uniform(-5, 5), 1),
            "quaternion": {"w": 1.0, "x": 0.0, "y": 0.0, "z": 0.0},
            "acceleration": {
                "x": round(random.uniform(-0.5, 0.5), 2),
                "y": round(random.uniform(-0.5, 0.5), 2),
                "z": round(9.8 + random.uniform(-0.2, 0.2), 2)
            },
            "linear_acceleration": {
                "x": round(random.uniform(-0.5, 0.5), 2),
                "y": round(random.uniform(-0.5, 0.5), 2),
                "z": round(random.uniform(-0.5, 0.5), 2)
            },
            "gyroscope": {
                "x": round(random.uniform(-0.1, 0.1), 3),
                "y": round(random.uniform(-0.1, 0.1), 3),
                "z": round(random.uniform(-0.1, 0.1), 3)
            },
            "magnetometer": {
                "x": round(random.uniform(-50, 50), 1),
                "y": round(random.uniform(-50, 50), 1),
                "z": round(random.uniform(-50, 50), 1)
            },
            "calibration": {"system": 3, "gyro": 3, "accel": 3, "mag": 3},
            "safety_status": {"is_safe": not is_error, "status": "simulated" if not is_error else "sensor_unavailable"}
        }

    def cleanup(self):
        """Cleans up resources, specifically the serial port."""
        if self.is_hardware_available and self.sensor:
            try:
                # The BNO08X_UART class holds the serial.Serial object in ._uart
                if hasattr(self.sensor, '_uart') and self.sensor._uart.is_open:
                    self.sensor._uart.close()
                    logger.info("IMU: Serial port closed.")
            except Exception as e:
                logger.error(f"IMU: Error during cleanup: {e}")
        self.sensor = None
        self.is_hardware_available = False


if __name__ == "__main__":
    """Test the BNO085Sensor class."""
    
    # To test simulation, use: imu = BNO085Sensor(simulate=True)
    imu = BNO085Sensor()

    if not imu.is_hardware_available and not imu.sensor:
        print("IMU hardware not found or failed to initialize. Exiting test.")
    else:
        try:
            print("Reading IMU data for 30 seconds... Press Ctrl+C to stop.")
            for _ in range(30):
                data = imu.get_sensor_data()
                print(
                    f"Heading: {data['heading']:.1f}°, "
                    f"Roll: {data['roll']:.1f}°, "
                    f"Pitch: {data['pitch']:.1f}°"
                )
                print(f"  Accel: X={data['acceleration']['x']:.2f} "
                      f"Y={data['acceleration']['y']:.2f} "
                      f"Z={data['acceleration']['z']:.2f} m/s^2")
                print(f"  Lin Accel: X={data['linear_acceleration']['x']:.2f} "
                      f"Y={data['linear_acceleration']['y']:.2f} "
                      f"Z={data['linear_acceleration']['z']:.2f} m/s^2")
                print(f"  Calib: Sys={data['calibration']['system']}, "
                      f"Gyr={data['calibration']['gyro']}, "
                      f"Acc={data['calibration']['accel']}, "
                      f"Mag={data['calibration']['mag']}")
                print("-" * 20)
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nTest stopped by user.")
        finally:
            imu.cleanup()
