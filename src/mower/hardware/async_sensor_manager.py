"""
Async Sensor Manager - Refactored sensor pipeline for improved reliability.

This module implements the async sensor stack refactor to address critical failures
and correctly manage all attached sensor modules.
"""

import asyncio
import logging
import time
import os
import platform
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional

# Hardware imports - conditional on platform
if platform.system() == "Linux":
    try:
        import board
        import busio
    except ImportError:
        board = None
        busio = None
else:
    board = None
    busio = None

# Import all specific sensor classes
from mower.hardware.bme280 import BME280Sensor
from mower.hardware.ina3221 import INA3221Sensor
from mower.hardware.imu import BNO085Sensor
from mower.hardware.tof import VL53L0XSensors
from mower.utilities.logger_config import LoggerConfigInfo

logger = LoggerConfigInfo.get_logger(__name__)

# --- Configuration ---
SENSOR_CONFIG = {
    "imu_update_rate": 20.0,  # Hz, higher for better obstacle/tilt detection
    "i2c_update_rate": 2.0,   # Hz, for less critical sensors
    "timeout_seconds": 2.0,
    "max_consecutive_errors": 5,
}

class SensorState(Enum):
    """Sensor operational states"""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    FAILED = "failed"

@dataclass
class SensorStatus:
    """Enhanced sensor status tracking"""
    state: SensorState
    last_reading: Optional[datetime] = None
    error_count: int = 0
    consecutive_errors: int = 0
    last_error: Optional[str] = None
    is_hardware_available: bool = False

class AsyncSensorManager:
    """
    Async sensor manager implementing the refactored sensor pipeline.
    """
    
    def __init__(self, simulate: bool = False):
        self.simulate = simulate or not (platform.system() == "Linux")
        self._running = False
        self._lock = asyncio.Lock()
        
        self._sensors: Dict[str, Any] = {}
        self._sensor_status: Dict[str, SensorStatus] = {
            name: SensorStatus(state=SensorState.UNINITIALIZED)
            for name in ["imu", "environment", "power", "tof"]
        }
        
        self._sensor_data: Dict[str, Any] = {}
        self._last_update: Optional[float] = None
        self._tasks: Dict[str, asyncio.Task] = {}
        self._config = SENSOR_CONFIG

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()

    async def start(self):
        if self._running:
            return
        logger.info("Starting AsyncSensorManager...")
        self._running = True
        await self._initialize_sensors()
        await self._start_tasks()
        logger.info("AsyncSensorManager started successfully")

    async def stop(self):
        if not self._running:
            return
        logger.info("Stopping AsyncSensorManager...")
        self._running = False
        for task in self._tasks.values():
            task.cancel()
        await asyncio.gather(*self._tasks.values(), return_exceptions=True)
        await self._cleanup_sensors()
        logger.info("AsyncSensorManager stopped")

    async def _run_in_executor(self, func, *args):
        """Helper to run blocking I/O in a thread pool."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, func, *args)

    async def _initialize_sensors(self):
        """Initialize all sensors."""
        logger.info("Initializing sensors...")
        if self.simulate:
            logger.info("Running in SIMULATION mode.")
            self._sensor_status = {
                name: SensorStatus(state=SensorState.OPERATIONAL, is_hardware_available=False)
                for name in self._sensor_status
            }
            return

        # Initialize I2C Bus First
        i2c_bus = None
        try:
            i2c_bus = busio.I2C(board.SCL, board.SDA)
            logger.info("I2C bus initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize I2C bus: {e}. I2C sensors will be unavailable.")

        # Initialize sensors concurrently
        init_tasks = [
            self._initialize_imu(),
            self._initialize_bme280(i2c_bus),
            self._initialize_ina3221(i2c_bus),
            self._initialize_tof(i2c_bus),
        ]
        await asyncio.gather(*init_tasks)
        logger.info("Sensor initialization complete.")

    async def _initialize_imu(self):
        """Initialize the BNO085 IMU sensor."""
        status = self._sensor_status["imu"]
        status.state = SensorState.INITIALIZING
        try:
            logger.info("Initializing IMU...")
            sensor = await self._run_in_executor(BNO085Sensor)
            if sensor.is_hardware_available:
                self._sensors["imu"] = sensor
                status.state = SensorState.OPERATIONAL
                status.is_hardware_available = True
                logger.info("IMU initialized successfully.")
            else:
                raise RuntimeError("IMU hardware not available per sensor class")
        except Exception as e:
            status.state = SensorState.FAILED
            status.last_error = str(e)
            logger.error(f"IMU initialization failed: {e}")

    async def _initialize_bme280(self, i2c_bus):
        """Initialize the BME280 Environment sensor."""
        if not i2c_bus: return
        status = self._sensor_status["environment"]
        status.state = SensorState.INITIALIZING
        try:
            logger.info("Initializing BME280...")
            sensor = await self._run_in_executor(BME280Sensor, i2c_bus)
            self._sensors["bme280"] = sensor
            status.state = SensorState.OPERATIONAL
            status.is_hardware_available = True
            logger.info("BME280 initialized successfully.")
        except Exception as e:
            status.state = SensorState.FAILED
            status.last_error = str(e)
            logger.error(f"BME280 (Environment) initialization failed: {e}")

    async def _initialize_ina3221(self, i2c_bus):
        """Initialize the INA3221 Power sensor."""
        if not i2c_bus: return
        status = self._sensor_status["power"]
        status.state = SensorState.INITIALIZING
        try:
            logger.info("Initializing INA3221...")
            sensor = await self._run_in_executor(INA3221Sensor.init_ina3221, i2c_bus)
            self._sensors["ina3221"] = sensor
            status.state = SensorState.OPERATIONAL
            status.is_hardware_available = True
            logger.info("INA3221 (Power) initialized successfully.")
        except Exception as e:
            status.state = SensorState.FAILED
            status.last_error = str(e)
            logger.error(f"INA3221 (Power) initialization failed: {e}")

    async def _initialize_tof(self, i2c_bus):
        """Initialize the VL53L0X Time-of-Flight sensors."""
        if not i2c_bus: return
        status = self._sensor_status["tof"]
        status.state = SensorState.INITIALIZING
        try:
            logger.info("Initializing ToF...")
            sensor = await self._run_in_executor(VL53L0XSensors, i2c_bus)
            if sensor.is_hardware_available:
                self._sensors["tof"] = sensor
                status.state = SensorState.OPERATIONAL
                status.is_hardware_available = True
                logger.info("ToF sensors initialized successfully.")
            else:
                raise RuntimeError("ToF hardware not available per sensor class")
        except Exception as e:
            status.state = SensorState.FAILED
            status.last_error = str(e)
            logger.error(f"ToF sensors initialization failed: {e}")

    async def _start_tasks(self):
        """Start async sensor reading tasks."""
        self._tasks["imu_task"] = asyncio.create_task(self._sensor_reading_loop("imu", self._read_imu, self._config["imu_update_rate"]))
        self._tasks["i2c_task"] = asyncio.create_task(self._i2c_sensors_loop(self._config["i2c_update_rate"]))

    async def _sensor_reading_loop(self, name, read_func, rate):
        """Generic loop for reading a sensor at a given rate."""
        interval = 1.0 / rate
        while self._running:
            try:
                start_time = time.monotonic()
                await read_func()
                elapsed = time.monotonic() - start_time
                await asyncio.sleep(max(0, interval - elapsed))
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in {name} reading loop: {e}")
                self._sensor_status[name].state = SensorState.DEGRADED
                self._sensor_status[name].consecutive_errors += 1
                await asyncio.sleep(1.0) # Backoff on error
    
    async def _i2c_sensors_loop(self, rate):
        """A single loop to read all I2C sensors."""
        interval = 1.0 / rate
        while self._running:
            try:
                start_time = time.monotonic()
                # Read all I2C sensors sequentially in one go
                await self._read_bme280()
                await self._read_ina3221()
                await self._read_tof()
                elapsed = time.monotonic() - start_time
                await asyncio.sleep(max(0, interval - elapsed))
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in I2C sensors loop: {e}")
                await asyncio.sleep(1.0)

    # --- Data Reading Methods ---

    async def _read_imu(self):
        key, sensor_name = "imu", "imu"
        if self._sensor_status[key].state != SensorState.OPERATIONAL: return
        try:
            data = await self._run_in_executor(self._sensors[sensor_name].get_sensor_data)
            async with self._lock: self._sensor_data[key] = data
            self._sensor_status[key].consecutive_errors = 0
        except Exception as e:
            self._sensor_status[key].consecutive_errors += 1
            logger.warning(f"Failed to read IMU: {e}")

    async def _read_bme280(self):
        key, sensor_name = "environment", "bme280"
        if self._sensor_status[key].state != SensorState.OPERATIONAL: return
        try:
            data = await self._run_in_executor(BME280Sensor.read_bme280, self._sensors[sensor_name])
            async with self._lock: self._sensor_data[key] = data
            self._sensor_status[key].consecutive_errors = 0
        except Exception as e:
            self._sensor_status[key].consecutive_errors += 1
            logger.warning(f"Failed to read Environment (BME280): {e}")

    async def _read_ina3221(self):
        key, sensor_name = "power", "ina3221"
        if self._sensor_status[key].state != SensorState.OPERATIONAL: return
        try:
            # Read all 3 channels
            all_channels = {}
            for i in range(1, 4):
                channel_data = await self._run_in_executor(INA3221Sensor.read_ina3221, self._sensors[sensor_name], i)
                all_channels[f"channel_{i}"] = channel_data
            async with self._lock: self._sensor_data[key] = all_channels
            self._sensor_status[key].consecutive_errors = 0
        except Exception as e:
            self._sensor_status[key].consecutive_errors += 1
            logger.warning(f"Failed to read Power (INA3221): {e}")
            
    async def _read_tof(self):
        key, sensor_name = "tof", "tof"
        if self._sensor_status[key].state != SensorState.OPERATIONAL: return
        try:
            data = await self._run_in_executor(self._sensors[sensor_name].get_distances)
            async with self._lock: self._sensor_data[key] = data
            self._sensor_status[key].consecutive_errors = 0
        except Exception as e:
            self._sensor_status[key].consecutive_errors += 1
            logger.warning(f"Failed to read ToF: {e}")

    async def get_sensor_data(self) -> Dict[str, Any]:
        """Get current sensor data with status and fallbacks."""
        async with self._lock:
            # Start with a copy of the latest data
            final_data = self._sensor_data.copy()

        # Provide fallbacks for any missing sensor data
        if 'imu' not in final_data: final_data['imu'] = self._get_fallback_imu()
        if 'environment' not in final_data: final_data['environment'] = self._get_fallback_environment()
        if 'power' not in final_data: final_data['power'] = self._get_fallback_power()
        if 'tof' not in final_data: final_data['tof'] = self._get_fallback_tof()

        # Add timestamps and status
        final_data["timestamp"] = time.time()
        final_data["status"] = {name: status.__dict__ for name, status in self._sensor_status.items()}
        return final_data

    async def _cleanup_sensors(self):
        """Cleanup sensor resources."""
        logger.debug("Cleaning up sensor resources...")
        for sensor in self._sensors.values():
            if hasattr(sensor, "cleanup"):
                try:
                    await self._run_in_executor(sensor.cleanup)
                except Exception as e:
                    logger.warning(f"Error during sensor cleanup: {e}")
        self._sensors.clear()

    # --- Fallback Data Methods ---
    def _get_fallback_imu(self): return {"heading": "N/A", "roll": "N/A", "pitch": "N/A", "safety_status": {"is_safe": False}}
    def _get_fallback_environment(self): return {"temperature_c": "N/A", "humidity": "N/A", "pressure": "N/A"}
    def _get_fallback_power(self): return {f"channel_{i}": {"bus_voltage": "N/A"} for i in range(1,4)}
    def _get_fallback_tof(self): return {"left": -1, "right": -1}


class AsyncSensorInterface:
    """Compatibility wrapper to bridge main_controller to the AsyncSensorManager."""
    
    def __init__(self, simulate: bool = False):
        self._manager = AsyncSensorManager(simulate=simulate)
        self._loop = None
        self._thread = None

    def start(self):
        """Starts the asyncio event loop in a separate thread."""
        if self._running:
            return
        logger.info("Starting AsyncSensorInterface thread...")
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self):
        """The target for the dedicated asyncio thread."""
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._manager.start())
            self._loop.run_forever()
        finally:
            self._loop.run_until_complete(self._manager.stop())
            self._loop.close()

    def stop(self):
        """Stops the asyncio event loop from the main thread."""
        if not self._running:
            return
        logger.info("Stopping AsyncSensorInterface thread...")
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=5)

    @property
    def _running(self):
        return self._thread and self._thread.is_alive()

    def get_sensor_data(self) -> Dict[str, Any]:
        """Gets sensor data from the manager in a thread-safe way."""
        if not self._running:
            logger.warning("Sensor interface not running, returning empty data.")
            return {}
        
        future = asyncio.run_coroutine_threadsafe(self._manager.get_sensor_data(), self._loop)
        try:
            return future.result(timeout=2.0)
        except Exception as e:
            logger.error(f"Failed to get sensor data from async manager: {e}")
            return {}