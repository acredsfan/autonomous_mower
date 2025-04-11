import threading
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import board
import busio
from mower.utilities.logger_config import (
    LoggerConfigInfo as LoggerConfig
    )
from mower.hardware.bme280 import BME280Sensor
from mower.hardware.imu import BNO085Sensor
from mower.hardware.ina3221 import (
    INA3221Sensor
    )
from mower.hardware.tof import (
    VL53L0XSensors
    )

logging = LoggerConfig.get_logger(__name__)


@dataclass
class SensorStatus:
    working: bool
    last_reading: datetime
    error_count: int
    last_error: Optional[str]


def _log_error(message: str, error: Exception):
    """Centralized error logging."""
    logging.error(f"{message}: {str(error)}")


def _init_bno085():
    """Initialize BNO085 sensor."""
    try:
        return BNO085Sensor()
    except Exception as e:
        _log_error("BNO085 initialization failed", e)
        return None


class EnhancedSensorInterface:
    """
    Enhanced sensor interface with improved error handling, health monitoring,
    and safety features.
    """

    def __init__(self):
        self.sensor_data = None
        self._data = None
        self._error_thresholds = None
        self._sensor_status = None
        self._stop_event = None
        self._sensors = None
        self.shutdown_lines = None
        self._i2c = None
        self._locks = None

        # Initialize I2C bus
        try:
            self._i2c = busio.I2C(board.SCL, board.SDA)
            self._locks = {'i2c': threading.Lock()}
            logging.info("I2C bus initialized successfully")
        except Exception as e:
            _log_error("I2C bus initialization failed", e)
            raise

    def __initialize(self):
        """Initialize BME280 sensor."""
        try:
            with self._locks['i2c']:
                self._sensors['bme280'] = BME280Sensor._initialize(self._i2c)
        except Exception as e:
            _log_error("BME280 initialization failed", e)
            return None

    def _init_ina3221(self):
        """Initialize INA3221 sensor."""
        try:
            with self._locks['i2c']:
                return INA3221Sensor.init_ina3221(self._i2c)
        except Exception as e:
            _log_error("INA3221 initialization failed", e)
            return None

    def _init_vl53l0x(self):
        """Initialize VL53L0X sensors."""
        try:
            with self._locks['i2c']:
                return VL53L0XSensors.init_vl53l0x_sensors(
                    self._i2c, self.shutdown_lines)
        except Exception as e:
            _log_error("VL53L0X initialization failed", e)
            return None

    def _read_bme280(self):
        """Read BME280 environmental data."""
        if not self._sensors['bme280']:
            return {}

        try:
            data = BME280Sensor.read_bme280(self._sensors['bme280'])
            return {
                'temperature': data.get('temperature_f'),
                'humidity': data.get('humidity'),
                'pressure': data.get('pressure')
                }
        except Exception as e:
            self._handle_sensor_error('bme280', e)
            return {}

    def _read_bno085(self):
        """Read BNO085 IMU data."""
        if not self._sensors['bno085']:
            return {}

        try:
            accel = BNO085Sensor.read_bno085_accel(self._sensors['bno085'])
            heading = BNO085Sensor.calculate_heading(self._sensors['bno085'])
            roll = BNO085Sensor.calculate_roll(self._sensors['bno085'])
            speed = BNO085Sensor.calculate_speed(self._sensors['bno085'])
            compass = BNO085Sensor.read_bno085_magnetometer(
                self._sensors['bno085']
                )
            # Get safety status
            safety_status = self._sensors['bno085'].get_safety_status()

            return {
                'acceleration': accel,
                'heading': heading,
                'roll': roll,
                'speed': speed,
                'compass': compass,
                'safety_status': safety_status
                }
        except Exception as e:
            self._handle_sensor_error('bno085', e)
            return {}

    def _read_ina3221(self):
        """Read INA3221 power monitoring data."""
        if not self._sensors['ina3221']:
            return {}

        try:
            solar_data = INA3221Sensor.read_ina3221(
                self._sensors['ina3221'], 1
                )
            battery_data = INA3221Sensor.read_ina3221(
                self._sensors['ina3221'], 3
                )
            return {
                'solar_voltage': solar_data.get('bus_voltage'),
                'solar_current': solar_data.get('current'),
                'battery_voltage': battery_data.get('bus_voltage'),
                'battery_current': battery_data.get('current'),
                'battery_level': battery_data.get('charge_level')
                }
        except Exception as e:
            self._handle_sensor_error('ina3221', e)
            return {}

    def _read_vl53l0x(self):
        """Read VL53L0X distance sensor data."""
        if not self._sensors['vl53l0x']:
            return {}

        try:
            left, right = self._sensors['vl53l0x']
            return {
                'left_distance': VL53L0XSensors.read_vl53l0x(left),
                'right_distance': VL53L0XSensors.read_vl53l0x(right)
                }
        except Exception as e:
            self._handle_sensor_error('vl53l0x', e)
            return {}

    def _start_monitoring(self):
        """Start sensor monitoring threads."""
        self._monitoring_thread = threading.Thread(
            target=self._monitor_sensors,
            daemon=True
            )
        self._monitoring_thread.start()

        self._update_thread = threading.Thread(
            target=self._update_sensor_data,
            daemon=True
            )
        self._update_thread.start()

    def _monitor_sensors(self):
        """Monitor sensor health and perform recovery if needed."""
        while not self._stop_event.is_set():
            for sensor_name in self._sensors:
                self._check_sensor_health(sensor_name)
            time.sleep(1)

    def _check_sensor_health(self, sensor_name: str):
        """Check health of a specific sensor and attempt recovery if needed."""
        with self._locks['status']:
            status = self._sensor_status[sensor_name]
            if not status.working:
                if status.error_count >= self._error_thresholds[sensor_name]:
                    self._attempt_sensor_recovery(sensor_name)
                    return

            # Check if readings are stale
            if (datetime.now() - status.last_reading).seconds > 5:
                status.working = False
                status.error_count += 1
                status.last_error = "Stale readings"

    def _attempt_sensor_recovery(self, sensor_name: str):
        """Attempt to recover a failed sensor."""
        logging.info(f"Attempting to recover {sensor_name}")
        initializer = getattr(self, f"_init_{sensor_name}")
        self._init_sensor_with_retry(sensor_name, initializer)

    def _update_sensor_data(self):
        """Update sensor readings with error handling."""
        while not self._stop_event.is_set():
            for sensor_name in self._sensors:
                try:
                    self._update_single_sensor(sensor_name)
                except Exception as e:
                    self._handle_sensor_error(sensor_name, e)
            time.sleep(0.1)

    def _update_single_sensor(self, sensor_name: str):
        """Update readings for a single sensor."""
        sensor = self._sensors[sensor_name]
        if not sensor:
            return

        with self._locks['data']:
            if sensor_name == 'bme280':
                self._data.update(self._read_bme280())
            elif sensor_name == 'bno085':
                self._data.update(self._read_bno085())
            elif sensor_name == 'ina3221':
                self._data.update(self._read_ina3221())
            elif sensor_name == 'vl53l0x':
                self._data.update(self._read_vl53l0x())

            # Update sensor status
            with self._locks['status']:
                status = self._sensor_status[sensor_name]
                status.last_reading = datetime.now()
                status.working = True
                status.error_count = 0
                status.last_error = None

    def _handle_sensor_error(self, sensor_name: str, error: Exception):
        """Handle sensor errors with proper logging and status updates."""
        with self._locks['status']:
            status = self._sensor_status[sensor_name]
            status.working = False
            status.error_count += 1
            status.last_error = str(error)
            _log_error(f"{sensor_name} reading failed", error)

    def get_sensor_data(self) -> Dict[str, Any]:
        """Get current sensor data in a thread-safe way."""
        with self._locks['data']:
            return self._data.copy()

    def get_sensor_status(self) -> Dict[str, SensorStatus]:
        """Get current sensor status in a thread-safe way."""
        with self._locks['status']:
            return self._sensor_status.copy()

    def shutdown(self):
        """Properly shutdown all sensors and threads."""
        self._stop_event.set()
        if hasattr(self, '_monitoring_thread'):
            self._monitoring_thread.join()
        if hasattr(self, '_update_thread'):
            self._update_thread.join()
        self._cleanup_sensors()

    def _cleanup_sensors(self):
        """Clean up sensor resources."""
        for sensor_name, sensor in self._sensors.items():
            try:
                if hasattr(sensor, 'cleanup'):
                    sensor.cleanup()
            except Exception as e:
                _log_error(f"Error cleaning up {sensor_name}", e)

    def is_safe_to_operate(self) -> bool:
        """
        Check if all critical sensors are functioning
        properly for safe operation.
        """
        with self._locks['status']:
            critical_sensors = ['bno085', 'vl53l0x']  # Add or remove as needed
            return all(
                self._sensor_status[sensor].working
                for sensor in critical_sensors
                )

    def _init_sensor_with_retry(self, sensor_name, initializer):
        pass

    def start(self):
        """Start the EnhancedSensorInterface."""
        logging.info("EnhancedSensorInterface started successfully.")

    def cleanup(self):
        """Clean up resources used by the EnhancedSensorInterface."""
        try:
            # Add specific cleanup logic here
            logging.info("EnhancedSensorInterface cleaned up successfully.")
        except Exception as e:
            logging.error(f"Error cleaning up EnhancedSensorInterface: {e}")


def _check_proximity_violation(sensor_data: Dict) -> bool:
    """Check if any proximity sensor indicates an obstacle too close."""
    min_safe_distance = 30  # cm
    return any(
        sensor_data.get(
            f'{direction}_distance', float('inf')
            ) < min_safe_distance
        for direction in ['left', 'right', 'front']
        )


def _check_tilt_violation(sensor_data: Dict) -> bool:
    """Check if the mower's tilt angle is unsafe."""
    max_safe_tilt = 25  # degrees
    return abs(sensor_data.get('pitch', 0)) > max_safe_tilt or \
        abs(sensor_data.get('roll', 0)) > max_safe_tilt


class SafetyMonitor:
    """
    Safety monitoring system for the autonomous mower.
    """

    def __init__(self, enhanced_sensor_interface):
        self.sensor_interface = enhanced_sensor_interface
        self.safety_violations = []
        self.stop_event = threading.Event()
        self.monitoring_thread = threading.Thread(
            target=self._monitor_safety,
            daemon=True
            )
        self.monitoring_thread.start()

    def _monitor_safety(self):
        """Continuously monitor safety conditions."""
        while not self.stop_event.is_set():
            try:
                self._check_safety_conditions()
                time.sleep(0.1)
            except Exception as e:
                logging.error(f"Safety monitoring error: {e}")

    def _check_safety_conditions(self):
        """Check all safety conditions."""
        sensor_data = self.sensor_interface.get_sensor_data()

        # Check proximity sensors
        if _check_proximity_violation(sensor_data):
            self.safety_violations.append("Proximity violation")

        # Check orientation (tilt)
        if _check_tilt_violation(sensor_data):
            self.safety_violations.append("Tilt violation")

        # Check power system
        if self._check_power_violation(sensor_data):
            self.safety_violations.append("Power system violation")

    @staticmethod
    def _check_power_violation(sensor_data: Dict) -> bool:
        """Check if power system parameters are within safe ranges."""
        min_safe_voltage = 11.0  # volts
        max_safe_current = 20.0  # amps
        return sensor_data.get('battery_voltage', 12) < min_safe_voltage or \
            sensor_data.get('motor_current', 0) > max_safe_current

    def get_safety_status(self) -> Dict[str, Any]:
        """Get current safety status."""
        return {
            'violations': self.safety_violations.copy(),
            'is_safe': len(self.safety_violations) == 0,
            'sensors_ok': self.sensor_interface.is_safe_to_operate()
            }

    def clear_violations(self):
        """Clear safety violations after they've been addressed."""
        self.safety_violations.clear()

    def shutdown(self):
        """Properly shutdown the safety monitor."""
        self.stop_event.set()
        self.monitoring_thread.join()


# Singleton accessor function
sensor_interface_instance = EnhancedSensorInterface()


def get_sensor_interface():
    return sensor_interface_instance


if __name__ == "__main__":
    sensor_interface = EnhancedSensorInterface()
    while True:
        print(sensor_interface.sensor_data)
        time.sleep(1)


class SensorInterface:
    """
    Legacy wrapper around EnhancedSensorInterface for backward compatibility.

    This class provides the same interface as the original SensorInterface
    while delegating to the newer EnhancedSensorInterface implementation.
    """

    def __init__(self, resource_manager=None):
        """
        Initialize the sensor interface.

        Args:
            resource_manager: Optional ResourceManager for dependency injection
        """
        self._enhanced = EnhancedSensorInterface()
        self._resource_manager = resource_manager

    def start(self):
        """Start the sensor interface."""
        # Delegate to the enhanced implementation
        return self._enhanced.start()

    def stop(self):
        """Stop the sensor interface."""
        return self._enhanced.shutdown()

    def shutdown(self):
        """Shutdown the sensor interface."""
        return self._enhanced.shutdown()

    def get_sensor_data(self):
        """Get the current sensor readings."""
        return self._enhanced.get_sensor_data()

    def get_sensor_status(self):
        """Get the status of all sensors."""
        return self._enhanced.get_sensor_status()

    def is_safe_to_operate(self):
        """Check if it's safe to operate based on sensor readings."""
        return self._enhanced.is_safe_to_operate()

    # Additional compatibility methods to match the old interface

    def get_distance_left(self):
        """Get the left distance sensor reading."""
        data = self._enhanced.get_sensor_data()
        return data.get('left_distance', float('inf'))

    def get_distance_right(self):
        """Get the right distance sensor reading."""
        data = self._enhanced.get_sensor_data()
        return data.get('right_distance', float('inf'))

    def get_heading(self):
        """Get the current heading from IMU."""
        data = self._enhanced.get_sensor_data()
        return data.get('heading', 0.0)

    def get_temperature(self):
        """Get the current temperature."""
        data = self._enhanced.get_sensor_data()
        return data.get('temperature', 0.0)

    def get_battery_level(self):
        """Get the current battery level."""
        data = self._enhanced.get_sensor_data()
        return data.get('battery_level', 0.0)
