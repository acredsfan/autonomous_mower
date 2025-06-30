"""
Hardware Registry
This module provides a single point of access for all hardware resources.
"""
import threading
from typing import Optional


import os
from mower.hardware.blade_controller import BladeController
from mower.hardware.camera_instance import get_camera_instance
from mower.hardware.gpio_manager import GPIOManager
from mower.hardware.imu import BNO085Sensor
from mower.hardware.ina3221 import INA3221Sensor
from mower.hardware.robohat import RoboHATDriver
from mower.hardware.sensor_interface import get_sensor_interface
from mower.hardware.serial_port import GPS_BAUDRATE, GPS_PORT, SerialPort
from mower.hardware.tof import VL53L0XSensors
from mower.utilities.logger_config import LoggerConfigInfo

logger = LoggerConfigInfo.get_logger(__name__)

class HardwareRegistry:
    def get_vl53l0x(self):
        """
        Returns the VL53L0X ToF sensor(s) instance if available.
        Returns:
            VL53L0XSensors object or None if not initialized.
        @hardware_interface
        @i2c_address 0x29 (default for VL53L0X)
        """
        try:
            if hasattr(self, '_resources') and 'vl53l0x' in self._resources:
                return self._resources['vl53l0x']
            from mower.hardware.tof import VL53L0XSensors
            vl53l0x = VL53L0XSensors()
            if hasattr(self, '_resources'):
                self._resources['vl53l0x'] = vl53l0x
            return vl53l0x
        except Exception as e:
            logger = None
            try:
                from mower.utilities.logger_config import LoggerConfigInfo
                logger = LoggerConfigInfo.get_logger(__name__)
            except Exception:
                pass
            if logger:
                logger.error(f"Failed to initialize VL53L0X sensors: {e}")
            return None
    def get_bno085(self):
        """
        Returns the BNO085 IMU sensor instance if available.

        Returns:
            BNO08x sensor object or None if not initialized.

        @hardware_interface
        @i2c_address 0x4B
        """
        try:
            # Try to get from resources if already initialized
            if hasattr(self, '_resources') and 'bno085' in self._resources:
                return self._resources['bno085']
            # Otherwise, try to initialize
            from adafruit_bno08x import BNO08X_I2C
            import board
            import busio
            i2c = busio.I2C(board.SCL, board.SDA)
            bno085 = BNO08X_I2C(i2c, address=0x4B)
            if hasattr(self, '_resources'):
                self._resources['bno085'] = bno085
            return bno085
        except Exception as e:
            logger = None
            try:
                from mower.utilities.logger_config import LoggerConfigInfo
                logger = LoggerConfigInfo.get_logger(__name__)
            except Exception:
                pass
            if logger:
                logger.error(f"Failed to initialize BNO085 sensor: {e}")
            return None

    def get_ina3221(self) -> Optional[object]:
        """
        Returns the INA3221 power monitor instance if available.

        Returns:
            Optional[object]: The INA3221 instance or None if not available.

        @hardware_interface
        """
        try:
            from src.mower.hardware import ina3221
            if not hasattr(self, "_ina3221"):
                self._ina3221 = ina3221.INA3221()
            return self._ina3221
        except Exception as e:
            logger = None
            try:
                from mower.utilities.logger_config import LoggerConfigInfo
                logger = LoggerConfigInfo.get_logger(__name__)
            except Exception:
                pass
            if logger:
                logger.warning(f"INA3221 not available: {e}")
            return None
    def get_bme280(self):
        """
        Returns the BME280 environmental sensor instance if available.
        Returns:
            BME280 sensor object or None if not initialized.
        """
        try:
            # Try to get from resources if already initialized
            if hasattr(self, '_resources') and 'bme280' in self._resources:
                return self._resources['bme280']
            # Otherwise, try to initialize
            from mower.hardware.bme280 import BME280Sensor
            import board
            import busio
            i2c = busio.I2C(board.SCL, board.SDA)
            bme280 = BME280Sensor._initialize(i2c)
            if hasattr(self, '_resources'):
                self._resources['bme280'] = bme280
            return bme280
        except Exception as e:
            logger = None
            try:
                from mower.utilities.logger_config import LoggerConfigInfo
                logger = LoggerConfigInfo.get_logger(__name__)
            except Exception:
                pass
            if logger:
                logger.error(f"Failed to initialize BME280 sensor: {e}")
            return None
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._resources = {}
            self._bno085 = None  # Ensure attribute exists for IMU sensor
            self._initialized = True

    def initialize(self):
        with self._lock:
            logger.info("Initializing hardware registry...")
            self._resources["gpio"] = GPIOManager()
            self._resources["sensor_interface"] = get_sensor_interface()
            self._resources["camera"] = get_camera_instance()
            self._resources["blade"] = BladeController()
            self._resources["motor_driver"] = RoboHATDriver()
            try:
                gps_port_val = GPS_PORT if GPS_PORT is not None else "/dev/ttyACM0"
                self._resources["gps_serial"] = SerialPort(gps_port_val, GPS_BAUDRATE)
                logger.info(f"GPS serial port initialized on {gps_port_val} at {GPS_BAUDRATE} baud")
            except Exception as e:
                logger.warning(f"Error initializing GPS serial port: {e}")
                self._resources["gps_serial"] = None
            logger.info("Hardware registry initialized.")

    def get_bno085(self):
        """
        Get the BNO085 IMU sensor instance.

        Returns:
            BNO085Sensor: The BNO085 IMU sensor object.

        Raises:
            Exception: If the sensor cannot be initialized.

        @hardware_interface: BNO085 IMU sensor
        @uart_port /dev/ttyAMA4 - IMU UART port (default, see .env)
        """
        if self._bno085 is not None:
            return self._bno085
        try:
            # Port and baudrate can be made configurable via .env if needed
            import serial
            from mower.hardware.imu import BNO085Sensor
            imu_port = os.getenv("IMU_UART_PORT", "/dev/ttyAMA4")
            imu_baud = int(os.getenv("IMU_BAUDRATE", "3000000"))
            ser = serial.Serial(imu_port, imu_baud, timeout=1)
            self._bno085 = BNO085Sensor()
            if hasattr(self._bno085, "initialize"):
                self._bno085.serial = ser
                self._bno085.initialize()
            logger.info(f"BNO085 IMU initialized on {imu_port} at {imu_baud} baud.")
            return self._bno085
        except Exception as e:
            logger.error(f"Failed to initialize BNO085 IMU: {e}", exc_info=True)
            raise
    def get_resource(self, name: str):
        return self._resources.get(name)

    def get_gpio_manager(self) -> Optional[GPIOManager]:
        return self.get_resource("gpio")

    def get_sensor_interface(self):
        return self.get_resource("sensor_interface")

    def get_camera(self):
        return self.get_resource("camera")

    def get_blade_controller(self) -> Optional[BladeController]:
        return self.get_resource("blade")

    def get_robohat(self) -> Optional[RoboHATDriver]:
        return self.get_resource("motor_driver")

    def get_gps_serial(self) -> Optional[SerialPort]:
        return self.get_resource("gps_serial")

_hardware_registry = HardwareRegistry()

def get_hardware_registry() -> HardwareRegistry:
    return _hardware_registry
