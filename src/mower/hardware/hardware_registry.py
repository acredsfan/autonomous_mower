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
            # BNO085 uses UART4, not I2C - use the frozen driver's initialization
            from mower.hardware.imu import BNO085Sensor
            bno085 = BNO085Sensor.init_bno085()
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
        Uses the frozen driver's own I2C initialization.

        Returns:
            Optional[object]: The INA3221 instance or None if not available.

        @hardware_interface
        @i2c_address 0x40
        """
        try:
            if not hasattr(self, "_ina3221"):
                from mower.hardware.ina3221 import INA3221Sensor
                # Let the frozen driver handle its own I2C initialization
                self._ina3221 = INA3221Sensor.init_ina3221()
                if self._ina3221:
                    logger.info("INA3221 initialized using frozen driver's I2C interface")
                else:
                    logger.info("INA3221 optional sensor unavailable")
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
            self._ina3221 = None  # Ensure attribute exists for INA3221 sensor
            self._initialized = True

    def initialize(self):
        with self._lock:
            logger.info("Initializing hardware registry...")
            
            # NOTE: Removed shared SMBus creation to fix I2C bus conflicts
            # All frozen drivers (INA3221, ToF, BME280) use busio.I2C which
            # handles its own I2C connections without conflicts
            self._i2c_bus = None
            logger.info("Hardware registry using individual I2C connections per driver")
                
            self._resources["gpio"] = GPIOManager()
            # NOTE: sensor_interface removed from hardware registry initialization
            # to prevent circular dependency. It will be initialized by ResourceManager
            # after hardware registry is ready.
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


    def cleanup(self):
        """Clean up all hardware resources."""
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
            
            # Note: No shared I2C bus to close - each driver handles its own I2C
            logger.info("Hardware registry cleanup complete")
                    
        except Exception as e:
            logger.error(f"Error during hardware registry cleanup: {e}")


# Create singleton instance after class definition is complete
_hardware_registry = HardwareRegistry()


def get_hardware_registry() -> HardwareRegistry:
    """
    Get the singleton instance of HardwareRegistry.
    
    Returns:
        HardwareRegistry: The singleton instance of HardwareRegistry.
    """
    return _hardware_registry
