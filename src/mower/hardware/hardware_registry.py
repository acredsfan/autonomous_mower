"""
Hardware Registry
This module provides a single point of access for all hardware resources.
"""
import threading
import time
from typing import Optional

import os
from smbus2 import SMBus
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
        Uses the shared I2C bus if available.

        Returns:
            Optional[object]: The INA3221 instance or None if not available.

        @hardware_interface
        @i2c_address 0x40
        """
        try:
            if not hasattr(self, "_ina3221"):
                from mower.hardware.ina3221 import INA3221Sensor
                if self._i2c_bus:
                    # Pass shared I2C bus instead of creating new one
                    self._ina3221 = INA3221Sensor.init_ina3221(i2c_bus=self._i2c_bus)
                    logger.info("INA3221 initialized using shared I2C bus")
                else:
                    # Fallback to creating its own bus
                    logger.warning("Shared I2C bus not available, INA3221 creating its own bus")
                    self._ina3221 = INA3221Sensor.init_ina3221()
            return self._ina3221
        except Exception as e:
            logger.info(f"INA3221 optional sensor unavailable: {e}")
            return None
    def get_bme280(self):
        """
        Returns the BME280 environmental sensor instance if available.
        Returns:
            BME280 sensor object or None if not initialized.
            
        @hardware_interface
        @i2c_address 0x76
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
                logger.info(f"BME280 optional sensor unavailable: {e}")
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
            self._i2c_bus = None  # Shared I2C bus
            self._initialized = True

    def initialize(self):
        with self._lock:
            logger.info("Initializing hardware registry...")
            
            # Initialize shared I2C bus first
            try:
                self._i2c_bus = SMBus(1)  # Default I2C bus on Raspberry Pi
                logger.info("Shared I2C bus initialized on bus 1")
            except Exception as e:
                logger.error(f"Failed to initialize I2C bus: {e}")
                self._i2c_bus = None
                
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

    def cleanup(self):
        """Clean up all hardware resources including shared I2C bus."""
        logger.info("Starting hardware registry cleanup...")
        try:
            # Clean up individual resources with timeout
            cleanup_start = time.time()
            for resource_name, resource in self._resources.items():
                if time.time() - cleanup_start > 30:  # 30 second timeout
                    logger.warning("Cleanup timeout reached, forcing exit")
                    break
                try:
                    if hasattr(resource, 'cleanup'):
                        logger.info(f"Cleaning up {resource_name}...")
                        resource.cleanup()
                    elif hasattr(resource, 'close'):
                        logger.info(f"Closing {resource_name}...")
                        resource.close()
                except Exception as e:
                    logger.warning(f"Error cleaning up {resource_name}: {e}")
            
            # Close shared I2C bus
            if self._i2c_bus:
                try:
                    logger.info("Closing shared I2C bus...")
                    self._i2c_bus.close()
                    logger.info("Shared I2C bus closed")
                except Exception as e:
                    logger.warning(f"Error closing I2C bus: {e}")
                    
        except Exception as e:
            logger.error(f"Error during hardware registry cleanup: {e}")


def get_hardware_registry() -> HardwareRegistry:
    return _hardware_registry
