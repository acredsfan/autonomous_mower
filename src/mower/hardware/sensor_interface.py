import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

try:
    import board
    import busio
except Exception:  # pragma: no cover - optional on non-Pi systems
    board = None
    busio = None

from mower.hardware.bme280 import BME280Sensor
from mower.hardware.ina3221 import INA3221Sensor
from mower.interfaces.hardware import SensorInterface as HardwareSensorInterface
from mower.utilities.logger_config import LoggerConfigInfo
import dotenv

logging = LoggerConfigInfo.get_logger(__name__)


@dataclass
class SensorStatus:
    working: bool
    last_reading: datetime
    error_count: int
    last_error: Optional[str]


def _log_error(message: str, error: Exception):
    """Centralized error logging."""
    logging.error(f"{message}: {str(error)}")


# Sensor definitions with optional flag
SENSOR_DEFS = {
    "bme280": {"cls": "BME280Sensor", "optional": True},
    "bno085": {"cls": "BNO085Sensor", "optional": False},
    "ina3221": {"cls": "INA3221Sensor", "optional": True},  # Make optional to prevent hanging
    "vl53l0x": {"cls": "VL53L0XSensors", "optional": False},
}





class EnhancedSensorInterface(HardwareSensorInterface):
    """
    Enhanced sensor interface with improved error handling, health monitoring,
    and safety features.
    """

    def __init__(self):
        self.sensor_data = {}
        self._data = {}
        self._error_thresholds = {
            "bme280": 5,
            "bno085": 5,
            "ina3221": 5,
            "vl53l0x": 5,
        }
        self._sensor_status = {}
        self._stop_event = threading.Event()
        self._sensors = {}
        self.shutdown_lines = None
        self._i2c = None
        self._locks = {
            "i2c": threading.Lock(),
            "data": threading.Lock(),
            "status": threading.Lock(),
        }
        
        # INA3221 caching for less frequent reads (non-critical sensor)
        self._ina3221_cache = {
            "data": None,
            "last_read": 0,
            "cache_duration": 5.0  # Read INA3221 only every 5 seconds
        }

        # Initialize sensor status for all sensors
        for sensor_name in ["bme280", "bno085", "ina3221", "vl53l0x"]:
            self._sensor_status[sensor_name] = SensorStatus(
                working=False,
                last_reading=datetime.now(),
                error_count=0,
                last_error=None,
            )

        # Initialize I2C bus
        try:
            if board is None or busio is None:
                raise ImportError("board or busio not available - likely not on Raspberry Pi")
            self._i2c = busio.I2C(board.SCL, board.SDA)
            logging.info("I2C bus initialized successfully")
        except Exception as e:
            _log_error("I2C bus initialization failed", e)
            self._i2c = None  # Ensure i2c is None on failure
            # Do not raise, allow the interface to exist without a working I2C bus
        
        # Initialize all sensors
        self._initialize_sensors()

    def _initialize_sensors(self) -> None:
        """Initialize all sensors."""
        from mower.hardware.hardware_registry import get_hardware_registry
        hardware_registry = get_hardware_registry()
        
        # Initialize BME280 with optional handling
        try:
            self._sensors["bme280"] = hardware_registry.get_bme280()
            if self._sensors["bme280"] is None:
                logging.info("BME280 optional sensor not available")
            else:
                # Mark as working if initialization succeeded
                self._sensor_status["bme280"].working = True
                logging.info("BME280 sensor initialized successfully")
        except Exception as exc:
            logging.info(f"BME280 optional sensor unavailable: {exc}")
            self._sensors["bme280"] = None
        
        # Initialize INA3221 with proper I2C coordination (direct init works, hardware registry fails)
        try:
            logging.info("Initializing INA3221 power sensor...")
            # Use I2C lock to prevent bus contention during initialization
            with self._locks["i2c"]:
                # Try hardware registry first, but fall back to direct init which works
                self._sensors["ina3221"] = hardware_registry.get_ina3221()
                
                if self._sensors["ina3221"] is None:
                    logging.info("Hardware registry returned None, trying direct initialization...")
                    # Use direct initialization method (same as diagnostic tool)
                    from mower.hardware.ina3221 import INA3221Sensor
                    self._sensors["ina3221"] = INA3221Sensor.init_ina3221()
                
                if self._sensors["ina3221"] is not None:
                    self._sensor_status["ina3221"].working = True
                    logging.info("INA3221 sensor initialized successfully")
                else:
                    logging.info("INA3221 optional sensor not available after all attempts")
                    
        except Exception as exc:
            logging.info(f"INA3221 optional sensor unavailable: {exc}")
            self._sensors["ina3221"] = None
        
        # Initialize other sensors with timeout protection
        try:
            # BNO085 IMU with timeout protection
            logging.info("Initializing BNO085 IMU sensor...")
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("BNO085 initialization timed out")
            
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(10)  # 10-second timeout
            
            try:
                self._sensors["bno085"] = hardware_registry.get_bno085()
                signal.alarm(0)  # Cancel timeout
                if self._sensors["bno085"]:
                    self._sensor_status["bno085"].working = True
                    logging.info("BNO085 sensor initialized successfully")
                else:
                    logging.warning("BNO085 sensor returned None")
            except TimeoutError:
                signal.alarm(0)
                logging.error("BNO085 IMU initialization timed out - marking as unavailable")
                self._sensors["bno085"] = None
            except Exception as e:
                signal.alarm(0)
                logging.error(f"BNO085 IMU initialization failed: {e}")
                self._sensors["bno085"] = None
        except Exception as e:
            logging.error(f"Failed to set up BNO085 timeout protection: {e}")
            self._sensors["bno085"] = None
            
        # VL53L0X ToF sensors
        try:
            logging.info("Initializing VL53L0X ToF sensors...")
            self._sensors["vl53l0x"] = hardware_registry.get_vl53l0x()
            if self._sensors["vl53l0x"]:
                self._sensor_status["vl53l0x"].working = True
                logging.info("VL53L0X sensors initialized successfully")
        except Exception as e:
            logging.error(f"VL53L0X sensor initialization failed: {e}")
            self._sensors["vl53l0x"] = None

    def start(self) -> None:
        """Start the sensor interface."""
        self._start_monitoring()
        logging.info("Sensor interface started successfully")

    def stop(self) -> None:
        """Stop the sensor interface."""
        self.shutdown()

    def cleanup(self) -> None:
        """Clean up resources used by the sensor interface."""
        self._cleanup_sensors()

    def _cleanup_sensors(self) -> None:
        """Clean up individual sensor resources."""
        try:
            # Stop any ongoing operations
            self._stop_event.set()
            
            # Clean up individual sensors
            for sensor_name, sensor in self._sensors.items():
                try:
                    if sensor and hasattr(sensor, 'cleanup'):
                        sensor.cleanup()
                    elif sensor and hasattr(sensor, '_cleanup'):
                        sensor._cleanup()
                except Exception as e:
                    logging.warning(f"Error cleaning up {sensor_name} sensor: {e}")
            
            # Clean up I2C resources
            if self._i2c:
                try:
                    self._i2c.deinit()
                except Exception as e:
                    logging.warning(f"Error deinitializing I2C bus: {e}")
                    
            logging.info("Sensor interface cleanup completed")
        except Exception as e:
            logging.error(f"Error during sensor cleanup: {e}")

    

    

    

    def _read_bme280(self) -> Dict[str, float]:
        """Read BME280 environmental data with basic debounce/retry logic."""
        sensor = self._sensors.get("bme280")
        if sensor is None:
            return {}

        # one‑time warm‑up (BME280 often needs a few ms after power‑up)
        if not hasattr(self, "_bme280_warmed"):
            time.sleep(0.2)                 # 200 ms settle
            self._bme280_warmed = True

        # running failure counter (stored on the instance)
        fail_attr = "_bme280_consecutive_failures"
        consecutive = getattr(self, fail_attr, 0)
        max_failures = 3                    # mark dead after three in a row

        try:
            raw = BME280Sensor.read_bme280(sensor)  # may raise or return {}
            if not raw:
                raise ValueError("empty frame")

            # success → reset counter and return converted dict
            setattr(self, fail_attr, 0)
            return {
                "temperature": raw.get("temperature_f"),
                "humidity":    raw.get("humidity"),
                "pressure":    raw.get("pressure"),
            }

        except Exception as exc:
            consecutive += 1
            setattr(self, fail_attr, consecutive)

            # only escalate after N consecutive failures
            if consecutive >= max_failures:
                self._handle_sensor_error("bme280", exc)

            return {}

    def _read_bno085(self):
        """Read BNO085 IMU data."""
        if not self._sensors["bno085"]:
            return {}

        try:
            # Get IMU instance
            imu = self._sensors["bno085"]

            # Read acceleration data
            accel = imu.get_acceleration()

            # Read other sensor data
            heading = imu.get_heading()
            roll = imu.get_roll()
            pitch = imu.get_pitch()

            # Get gyroscope and magnetometer data
            gyro = imu.get_gyroscope()
            magnetometer = imu.get_magnetometer()

            # Get calibration and safety status
            calibration = imu.get_calibration()
            safety_status = imu.get_safety_status()

            return {
                "acceleration": {"x": accel[0], "y": accel[1], "z": accel[2]},
                "gyroscope": {"x": gyro[0], "y": gyro[1], "z": gyro[2]},
                "magnetometer": {"x": magnetometer[0], "y": magnetometer[1], "z": magnetometer[2]},
                "heading": heading,
                "roll": roll,
                "pitch": pitch,
                "calibration": calibration,
                "safety_status": safety_status,
            }
        except Exception as e:
            self._handle_sensor_error("bno085", e)
            return {}

    def _read_ina3221(self) -> Dict[str, Any]:
        """Read INA3221 power data with I2C coordination."""
        sensor = self._sensors.get("ina3221")
        if not sensor:  # Check if sensor was initialized
            # For optional sensors, return empty dict instead of error
            if SENSOR_DEFS.get("ina3221", {}).get("optional", False):
                return {}
            else:
                self._handle_sensor_error("ina3221", Exception("INA3221 sensor not initialized or failed to initialize."))
                return {"error": "INA3221 sensor not available"}

        try:
            # Use I2C lock to prevent bus contention
            with self._locks["i2c"]:
                # Import the INA3221Sensor class
                from mower.hardware.ina3221 import INA3221Sensor
                
                all_channels_data = {}
                # Channel assignments corrected per user specification:
                # Channel 1: Solar panel monitoring
                # Channel 2: Motors (future use)
                # Channel 3: Battery monitoring
                for channel_num in [1, 2, 3]:  # INA3221Sensor expects 1-indexed channels (static method)
                    # Use the static method from our INA3221Sensor class
                    channel_data = INA3221Sensor.read_ina3221(sensor, channel_num)
                    if channel_data: # If data was read successfully
                        all_channels_data[f"channel_{channel_num}"] = channel_data
                    else:
                        # Log specific channel read error, but continue to try other channels
                        logging.debug(f"No data from INA3221 channel {channel_num}")
                        all_channels_data[f"channel_{channel_num}"] = {"error": f"Failed to read channel {channel_num}"}
                    all_channels_data[f"channel_{channel_num}"] = channel_data
                else:
                    # Log specific channel read error, but continue to try other channels
                    logging.warning(f"Failed to read data for INA3221 channel {channel_num}")
                    all_channels_data[f"channel_{channel_num}"] = {"error": f"Failed to read channel {channel_num}"}
            
            # Get solar panel data from channel 1 and battery data from channel 3
            solar_data = all_channels_data.get("channel_1", {})
            battery_data = all_channels_data.get("channel_3", {})
            
            # Basic battery percentage calculation from channel 3
            voltage = battery_data.get("bus_voltage")
            percentage = None
            if voltage is not None:
                # Retrieved from .env values for BATTERY_MIN_VOLTAGE and BATTERY_MAX_VOLTAGE
                min_volt = float(dotenv.get_key('.env', 'BATTERY_MIN_VOLTAGE', default='10.5'))
                max_volt = float(dotenv.get_key('.env', 'BATTERY_MAX_VOLTAGE', default='14.6'))
                if voltage <= min_volt:
                    percentage = 0.0
                elif voltage >= max_volt:
                    percentage = 100.0
                else:
                    percentage = ((voltage - min_volt) / (max_volt - min_volt)) * 100
                percentage = round(percentage, 1)

            # Update sensor status with timeout protection
            try:
                self._update_sensor_status("ina3221", all_channels_data)
            except Exception as status_error:
                logging.warning(f"Failed to update INA3221 sensor status: {status_error}")

            # Convert current from milliamps to amps for display
            battery_current = battery_data.get("current")
            solar_current = solar_data.get("current")
            
            if battery_current is not None:
                battery_current = round(battery_current / 1000.0, 3)  # mA to A
            if solar_current is not None:
                solar_current = round(solar_current / 1000.0, 3)  # mA to A

            return {
                # Battery data (channel 3)
                "bus_voltage": battery_data.get("bus_voltage"),
                "current": battery_current,
                "shunt_voltage": battery_data.get("shunt_voltage"),
                "power": battery_data.get("power"),
                "percentage": percentage,
                
                # Solar panel data (channel 1) 
                "solar_voltage": solar_data.get("bus_voltage"),
                "solar_current": solar_current,
                "solar_power": solar_data.get("power"),
                
                # Raw channel data for debugging
                "all_channels": all_channels_data,
            }
        except Exception as e:
            self._handle_sensor_error("ina3221", e)
            return {"error": str(e)}

    def _read_vl53l0x(self) -> Dict[str, Any]:
        """Read VL53L0X ToF sensor data."""
        sensor_wrapper = self._sensors.get("vl53l0x")
        if not sensor_wrapper or not sensor_wrapper.is_hardware_available:
            self._handle_sensor_error("vl53l0x", Exception("VL53L0X sensors not available"))
            return {"error": "VL53L0X sensors not available"}

        try:
            # Get distance readings from both sensors
            distances = sensor_wrapper.get_distances()
            
            # Update sensor status based on readings
            left_working = distances["left"] != -1
            right_working = distances["right"] != -1
            
            self._sensor_status["vl53l0x"].working = left_working or right_working
            
            if not left_working and not right_working:
                self._handle_sensor_error("vl53l0x", Exception("Both ToF sensors returning error readings"))
            elif not left_working:
                logging.warning("Left ToF sensor returning error readings")
            elif not right_working:
                logging.warning("Right ToF sensor returning error readings")
            
            return {
                "front_left": distances["left"] if left_working else None,
                "front_right": distances["right"] if right_working else None,
                "left_working": left_working,
                "right_working": right_working
            }

        except Exception as e:
            self._handle_sensor_error("vl53l0x", e)
            return {"error": str(e)}

    def _handle_sensor_error(self, sensor_name: str, error: Exception):
        """Handle sensor errors with enhanced logging and recovery options."""
        try:
            # Check if sensor is optional
            sensor_def = SENSOR_DEFS.get(sensor_name, {})
            is_optional = sensor_def.get("optional", False)
            
            # Increment error count and update last error message
            with self._locks["status"]:
                status = self._sensor_status[sensor_name]
                status.error_count += 1
                status.last_error = str(error)
                
                # Log appropriately based on optional flag
                if is_optional:
                    logging.info(f"Optional sensor '{sensor_name}' unavailable (#{status.error_count}): {str(error)}")
                else:
                    logging.error(f"Sensor '{sensor_name}' error (#{status.error_count}): {str(error)}")

                # Check if the error exceeds the threshold
                if status.error_count >= self._error_thresholds[sensor_name]:
                    status.working = False
                    if is_optional:
                        logging.info(f"Optional sensor '{sensor_name}' marked as unavailable after {status.error_count} attempts.")
                    else:
                        logging.error(f"Sensor '{sensor_name}' has exceeded the error threshold and is now disabled.")
                    
                    # For optional sensors, don't mark the sensor interface as unhealthy
                    if is_optional:
                        # Don't affect overall system health for optional sensors
                        pass
                    else:
                        # Optionally, trigger a sensor reset or reinitialization for critical sensors
                        # self._reset_sensor(sensor_name)
                        pass
        except Exception as e:
            logging.error(f"Error handling sensor error for '{sensor_name}': {str(e)}")

    def _reset_sensor(self, sensor_name: str):
        """Reset a sensor to recover from an error state."""
        try:
            with self._locks["status"]:
                status = self._sensor_status[sensor_name]
                logging.info(f"Resetting sensor '{sensor_name}'...")
                status.working = True
                status.error_count = 0
                status.last_error = None

                # Reinitialize the sensor
                if sensor_name == "bme280":
                    self._sensors["bme280"] = self.__initialize()
                elif sensor_name == "bno085":
                    self._sensors["bno085"] = _init_bno085()
                elif sensor_name == "ina3221":
                    self._sensors["ina3221"] = self._init_ina3221()
                elif sensor_name == "vl53l0x":
                    self._sensors["vl53l0x"] = self._init_vl53l0x()

                logging.info(f"Sensor '{sensor_name}' reset successfully.")
        except Exception as e:
            logging.error(f"Error resetting sensor '{sensor_name}': {str(e)}")

    def _update_sensor_status(self, sensor_name: str, data: Dict[str, Any]):
        """Update the status of a sensor based on the latest data."""
        try:
            with self._locks["status"]:
                status = self._sensor_status[sensor_name]
                status.last_reading = datetime.now()

                # Example: update working status based on specific data conditions
                if sensor_name == "ina3221":
                    # For INA3221, check if at least one channel is reporting data
                    status.working = any(
                        channel_data.get("current") is not None for channel_data in data.values()
                    )
                elif sensor_name == "vl53l0x":
                    # For VL53L0X, check if both sensors are reporting valid distances
                    distances = data.get("distances", {})
                    status.working = (
                        distances.get("left") != -1 and distances.get("right") != -1
                    )
                else:
                    # General case: if data is received without error, mark as working
                    status.working = True

                logging.info(f"Sensor '{sensor_name}' status updated: {status}")
        except Exception as e:
            logging.error(f"Error updating sensor status for '{sensor_name}': {str(e)}")

    def _start_monitoring(self):
        """Start the sensor monitoring threads."""
        try:
            # Start a thread for each sensor
            for sensor_name in self._sensors.keys():
                thread = threading.Thread(target=self._monitor_sensor, args=(sensor_name,))
                thread.daemon = True  # Daemon threads will not prevent the program from exiting
                thread.start()
                logging.info(f"Started monitoring thread for sensor '{sensor_name}'")
        except Exception as e:
            logging.error(f"Error starting monitoring threads: {str(e)}")

    def _monitor_sensor(self, sensor_name: str):
        """Monitor a specific sensor for errors and health status."""
        try:
            # Check if sensor is optional
            sensor_def = SENSOR_DEFS.get(sensor_name, {})
            is_optional = sensor_def.get("optional", False)
            
            while not self._stop_event.is_set():
                with self._locks["status"]:
                    status = self._sensor_status[sensor_name]

                    # Check if the sensor is working
                    if not status.working:
                        if is_optional:
                            logging.info(f"Optional sensor '{sensor_name}' is not working: {status.last_error}")
                        else:
                            logging.warning(f"Sensor '{sensor_name}' is not working. Error: {status.last_error}")
                            # Attempt to reset the sensor if it has failed
                            self._reset_sensor(sensor_name)

                # Sleep for a while before the next status check
                time.sleep(5)
        except Exception as e:
            logging.error(f"Error monitoring sensor '{sensor_name}': {str(e)}")

    def shutdown(self):
        """Shutdown the sensor interface, stopping all sensors and freeing resources."""
        try:
            self._stop_event.set()  # Signal all threads to stop
            self.cleanup()  # Clean up sensors
            logging.info("Sensor interface shut down successfully.")
        except Exception as e:
            logging.error(f"Error during shutdown: {str(e)}")

    def get_sensor_data(self) -> Dict[str, Any]:
        """
        Get the current sensor readings with comprehensive error handling.

        Returns:
            Dict[str, Any]: Dictionary containing sensor readings
        """
        import time
        
        start_time = time.time()
        sensor_data = {}
        
        try:
            # Use lock with timeout to prevent deadlocks
            if not self._locks["data"].acquire(timeout=5.0):
                logging.error("Failed to acquire sensor data lock within 5 seconds")
                return self._get_emergency_fallback_data()
            
            try:
                # Read environmental data with individual error handling
                try:
                    if self._sensors.get("bme280") is not None:
                        bme_data = self._read_bme280()
                        if bme_data:
                            sensor_data["environment"] = {
                                "temperature": bme_data.get("temperature"),
                                "humidity": bme_data.get("humidity"),
                                "pressure": bme_data.get("pressure")
                            }
                        else:
                            sensor_data["environment"] = self._get_fallback_environment()
                    else:
                        sensor_data["environment"] = self._get_fallback_environment()
                except Exception as bme_error:
                    logging.warning(f"BME280 sensor read failed: {bme_error}")
                    sensor_data["environment"] = self._get_fallback_environment()
                
                # Read IMU data with individual error handling  
                try:
                    imu_data = self._read_bno085()
                    if imu_data:
                        sensor_data["imu"] = imu_data
                    else:
                        sensor_data["imu"] = self._get_fallback_imu()
                except Exception as imu_error:
                    logging.warning(f"IMU sensor read failed: {imu_error}")
                    sensor_data["imu"] = self._get_fallback_imu()
                
                # Read power data with individual error handling (cached for less frequent reads)
                try:
                    current_time = time.time()
                    
                    # Check if we need to read INA3221 or use cached data
                    if (self._sensors.get("ina3221") is not None and 
                        (self._ina3221_cache["data"] is None or 
                         current_time - self._ina3221_cache["last_read"] > self._ina3221_cache["cache_duration"])):
                        
                        # Time to read fresh INA3221 data
                        power_data = self._read_ina3221()
                        if power_data and "error" not in power_data:
                            self._ina3221_cache["data"] = power_data
                            self._ina3221_cache["last_read"] = current_time
                            sensor_data["power"] = power_data
                            logging.debug(f"INA3221 fresh read completed, cached for {self._ina3221_cache['cache_duration']}s")
                        else:
                            sensor_data["power"] = self._get_fallback_power()
                    elif self._ina3221_cache["data"] is not None:
                        # Use cached data
                        sensor_data["power"] = self._ina3221_cache["data"]
                        logging.debug("Using cached INA3221 data")
                    else:
                        # No sensor and no cache
                        sensor_data["power"] = self._get_fallback_power()
                        
                except Exception as power_error:
                    logging.warning(f"INA3221 power sensor read failed: {power_error}")
                    sensor_data["power"] = self._get_fallback_power()
                
                # Read distance sensors with individual error handling
                try:
                    tof_data = self._read_vl53l0x()
                    if tof_data and "error" not in tof_data:
                        # Convert to WebUI expected format
                        sensor_data["tof"] = {
                            "left": tof_data.get("front_left", "N/A"),
                            "right": tof_data.get("front_right", "N/A"),
                            "working": tof_data.get("left_working", False) or tof_data.get("right_working", False)
                        }
                    else:
                        sensor_data["tof"] = self._get_fallback_tof()
                except Exception as tof_error:
                    logging.warning(f"ToF distance sensors read failed: {tof_error}")
                    sensor_data["tof"] = self._get_fallback_tof()
                
                # Update internal data store safely
                try:
                    self._data.update(sensor_data)
                except Exception as update_error:
                    logging.warning(f"Failed to update internal sensor data: {update_error}")
                
                # Log collection performance
                collection_time = time.time() - start_time
                if collection_time > 2.0:  # Warn if collection takes more than 2 seconds
                    logging.warning(f"Sensor collection took {collection_time:.3f}s (slow performance)")
                else:
                    logging.debug(f"Sensor collection completed in {collection_time:.3f}s")
                
                return sensor_data
                
            finally:
                # Always release the lock
                self._locks["data"].release()
                
        except Exception as critical_error:
            logging.error(f"Critical error in sensor data collection: {critical_error}", exc_info=True)
            return self._get_emergency_fallback_data()

    def _get_fallback_environment(self) -> Dict[str, str]:
        """Get fallback environment sensor data."""
        return {
            "temperature": "N/A",
            "humidity": "N/A", 
            "pressure": "N/A"
        }

    def _get_fallback_imu(self) -> Dict[str, Any]:
        """Get fallback IMU sensor data."""
        return {
            "heading": "N/A",
            "roll": "N/A",
            "pitch": "N/A",
            "acceleration": {"x": "N/A", "y": "N/A", "z": "N/A"},
            "gyroscope": {"x": "N/A", "y": "N/A", "z": "N/A"},
            "magnetometer": {"x": "N/A", "y": "N/A", "z": "N/A"},
            "calibration": "N/A",
            "safety_status": {"is_safe": False, "status": "sensor_unavailable"}
        }

    def _get_fallback_power(self) -> Dict[str, float]:
        """Get fallback power sensor data with numeric zeros to prevent frontend crashes."""
        return {
            "voltage": 0.0,
            "current": 0.0,
            "power": 0.0,
            "percentage": 0.0,
            "solar_voltage": 0.0,
            "solar_current": 0.0,
            "solar_power": 0.0
        }

    def _get_fallback_tof(self) -> Dict[str, Any]:
        """Get fallback ToF sensor data with numeric zeros to prevent frontend crashes."""
        return {
            "left": 0,
            "right": 0, 
            "working": False
        }

    def _get_emergency_fallback_data(self) -> Dict[str, Any]:
        """Get complete emergency fallback data for critical failures."""
        return {
            "environment": self._get_fallback_environment(),
            "imu": self._get_fallback_imu(),
            "power": self._get_fallback_power(),
            "tof": self._get_fallback_tof(),
            "error": "Emergency fallback - sensor collection failed critically"
        }

    def get_sensor_status(self) -> Dict[str, Any]:
        """
        Get the status of all sensors.

        Returns:
            Dict[str, Any]: Dictionary containing sensor status information
        """
        try:
            # Try to acquire lock with timeout
            if self._locks["status"].acquire(timeout=2.0):
                try:
                    status_dict = {}
                    for sensor_name, status in self._sensor_status.items():
                        status_dict[sensor_name] = {
                            "working": status.working,
                            "last_reading": status.last_reading.isoformat(),
                            "error_count": status.error_count,
                            "last_error": status.last_error
                        }
                    return status_dict
                finally:
                    self._locks["status"].release()
            else:
                logging.warning("Failed to acquire status lock within timeout")
                return {"error": "Status lock timeout"}
        except Exception as e:
            logging.error(f"Error getting sensor status: {e}")
            return {"error": str(e)}

    def is_safe_to_operate(self) -> bool:
        """
        Check if it's safe to operate based on sensor readings.

        Returns:
            bool: True if safe to operate, False otherwise
        """
        try:
            # Check critical sensors
            critical_sensors = ["ina3221"]  # Battery monitoring is critical
            
            for sensor_name in critical_sensors:
                status = self._sensor_status.get(sensor_name)
                if status and not status.working:
                    logging.warning(f"Critical sensor {sensor_name} not working")
                    return False
            
            # Check for proximity violations using ToF sensors
            sensor_data = self.get_sensor_data()
            if _check_proximity_violation(sensor_data):
                logging.warning("Proximity violation detected")
                return False
            
            # Check for tilt violations using IMU
            if _check_tilt_violation(sensor_data):
                logging.warning("Tilt violation detected")
                return False
            
            return True
            
        except Exception as e:
            logging.error(f"Error checking safety: {e}")
            return False  # Err on the side of caution


def _check_proximity_violation(sensor_data: Dict) -> bool:
    """
    Check if there's a proximity violation based on ToF sensor data.
    
    Args:
        sensor_data: Dictionary containing sensor readings
        
    Returns:
        bool: True if proximity violation detected, False otherwise
    """
    try:
        distance_data = sensor_data.get("distance", {})
        left_distance = distance_data.get("left", float('inf'))
        right_distance = distance_data.get("right", float('inf'))
        
        # Check if either sensor detects an object too close (< 100mm)
        MIN_SAFE_DISTANCE = 100  # mm
        
        if (left_distance > 0 and left_distance < MIN_SAFE_DISTANCE) or \
           (right_distance > 0 and right_distance < MIN_SAFE_DISTANCE):
            return True
            
        return False
        
    except Exception as e:
        logging.error(f"Error checking proximity: {e}")
        return True  # Err on the side of caution


def _check_tilt_violation(sensor_data: Dict) -> bool:
    """
    Check if there's a dangerous tilt based on IMU data.
    
    Args:
        sensor_data: Dictionary containing sensor readings
        
    Returns:
        bool: True if tilt violation detected, False otherwise
    """
    try:
        imu_data = sensor_data.get("imu", {})
        roll = imu_data.get("roll", 0.0)
        pitch = imu_data.get("pitch", 0.0)
        
        # Check for dangerous tilt angles
        MAX_SAFE_ANGLE = 25.0  # degrees
        
        if abs(roll) > MAX_SAFE_ANGLE or abs(pitch) > MAX_SAFE_ANGLE:
            return True
            
        return False
        
    except Exception as e:
        logging.error(f"Error checking tilt: {e}")
        return True  # Err on the side of caution


class SafetyMonitor:
    """
    Monitor safety-critical sensor conditions and provide alerts.
    """
    
    def __init__(self, sensor_interface: 'EnhancedSensorInterface'):
        self.sensor_interface = sensor_interface
        self.last_safety_check = datetime.now()
        
    def check_safety_conditions(self) -> Dict[str, Any]:
        """
        Perform comprehensive safety checks.
        
        Returns:
            Dict containing safety status and any warnings
        """
        safety_status = {
            "is_safe": True,
            "warnings": [],
            "critical_issues": []
        }
        
        try:
            sensor_data = self.sensor_interface.get_sensor_data()
            
            # Check proximity
            if _check_proximity_violation(sensor_data):
                safety_status["warnings"].append("Proximity violation detected")
                safety_status["is_safe"] = False
                
            # Check tilt
            if _check_tilt_violation(sensor_data):
                safety_status["critical_issues"].append("Dangerous tilt detected")
                safety_status["is_safe"] = False
                
            # Check battery
            power_data = sensor_data.get("power", {})
            voltage = power_data.get("bus_voltage", 0)
            if voltage > 0 and voltage < 10.5:  # Low battery threshold
                safety_status["warnings"].append(f"Low battery voltage: {voltage}V")
                
            self.last_safety_check = datetime.now()
            
        except Exception as e:
            logging.error(f"Error during safety check: {e}")
            safety_status["is_safe"] = False
            safety_status["critical_issues"].append(f"Safety check failed: {e}")
            
        return safety_status


# Singleton accessor function
sensor_interface_instance: Optional[EnhancedSensorInterface] = None

def get_sensor_interface() -> Optional[EnhancedSensorInterface]:
    """
    Get or create the singleton sensor interface instance.
    
    Returns:
        EnhancedSensorInterface: The sensor interface singleton instance, or MockSensorInterface if initialization fails.
    """
    global sensor_interface_instance
    
    if sensor_interface_instance is None:
        try:
            logging.info("Attempting to create EnhancedSensorInterface instance...")
            sensor_interface_instance = EnhancedSensorInterface()
            sensor_interface_instance.start()
            logging.info("Created and started new sensor interface instance")
        except Exception as e:
            logging.error(f"Failed to create sensor interface instance: {e}", exc_info=True)
            logging.info("Falling back to MockSensorInterface for testing/simulation...")
            try:
                sensor_interface_instance = MockSensorInterface()
                sensor_interface_instance.start()
                logging.info("Created and started MockSensorInterface as fallback")
            except Exception as mock_e:
                logging.error(f"Even MockSensorInterface failed to initialize: {mock_e}", exc_info=True)
                sensor_interface_instance = None  # Ensure instance is None on total failure
            
    return sensor_interface_instance


class MockSensorInterface(HardwareSensorInterface):
    """
    Mock sensor interface for testing purposes.
    """
    
    def __init__(self):
        self._mock_data = {
            "temperature": 20.0,
            "humidity": 50.0,
            "pressure": 1013.25,
            "imu": {
                "heading": 0.0,
                "roll": 0.0,
                "pitch": 0.0,
                "acceleration": {"x": 0.0, "y": 0.0, "z": 9.81},
                "gyroscope": {"x": 0.0, "y": 0.0, "z": 0.0},
                "magnetometer": {"x": 0.0, "y": 0.0, "z": 0.0},
                "calibration": {"system": 3, "gyro": 3, "accel": 3, "mag": 3},
                "safety_status": {"tilt_warning": False, "calibration_warning": False}
            },
            "power": {
                "voltage": 12.0,
                "current": 1.5,
                "power": 18.0,
                "percentage": 75.0,
                "status": "Mock Sensor"
            },
            "distance": {
                "left": 200.0,
                "right": 200.0
            }
        }
    
    def start(self) -> None:
        """Start the mock sensor interface."""
        pass
    
    def stop(self) -> None:
        """Stop the mock sensor interface."""
        pass
    
    def shutdown(self) -> None:
        """Shutdown the mock sensor interface."""
        pass
    
    def get_sensor_data(self) -> Dict[str, Any]:
        """Get mock sensor data."""
        return self._mock_data.copy()
    
    def get_safety_status(self) -> Dict[str, Any]:
        """Get mock safety status."""
        return {
            "emergency_stop_active": False,
            "obstacle_detected_nearby": False,
            "low_battery_warning": False,
            "system_error": False,
            "status_message": "Mock sensor interface - all systems nominal",
            "is_safe": True
        }
    
    def get_sensor_status(self) -> Dict[str, Any]:
        """Get mock sensor status."""
        return {
            "bme280": {"working": True, "last_reading": datetime.now().isoformat(), "error_count": 0, "last_error": None},
            "bno085": {"working": True, "last_reading": datetime.now().isoformat(), "error_count": 0, "last_error": None},
            "ina3221": {"working": True, "last_reading": datetime.now().isoformat(), "error_count": 0, "last_error": None},
            "vl53l0x": {"working": True, "last_reading": datetime.now().isoformat(), "error_count": 0, "last_error": None}
        }
    
    def is_safe_to_operate(self) -> bool:
        """Mock safety check - always returns True."""
        return True
    
    def cleanup(self) -> None:
        """Clean up mock resources."""
        pass
