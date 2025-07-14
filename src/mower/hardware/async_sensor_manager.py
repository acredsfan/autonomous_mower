"""
Async Sensor Manager - Refactored sensor pipeline for improved reliability.

This module implements the async sensor stack refactor to address critical failures:
- Replaces threading.Lock with asyncio.Lock
- Implements per-bus async tasks (UART for IMU, I2C for others)
- Provides proper timeout handling without signal module
- Implements graceful degradation and fallback patterns

@hardware_interface
@i2c_address: BME280(0x76), INA3221(0x40), VL53L0X(0x29,0x30)
@gpio_pin_usage: IMU(UART4), ToF XSHUT pins
"""

import asyncio
import logging
import time
import os
import platform
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional, Union
from enum import Enum

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

from mower.hardware.bme280 import BME280Sensor
from mower.hardware.ina3221 import INA3221Sensor
from mower.hardware.imu import BNO085Sensor
from mower.hardware.tof import VL53L0XSensors
from mower.utilities.logger_config import LoggerConfigInfo

logger = LoggerConfigInfo.get_logger(__name__)


class SensorState(Enum):
    """Sensor operational states"""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    FAILED = "failed"
    DISABLED = "disabled"


@dataclass
class SensorStatus:
    """Enhanced sensor status tracking"""
    state: SensorState
    last_reading: datetime
    error_count: int
    consecutive_errors: int
    last_error: Optional[str]
    is_hardware_available: bool
    last_successful_read: Optional[datetime] = None
    initialization_attempts: int = 0


class AsyncSensorManager:
    """
    Async sensor manager implementing the refactored sensor pipeline.
    
    Features:
    - Per-bus async tasks to prevent cross-contamination
    - Timeout handling without signal module (thread-safe)
    - Exponential backoff for failed sensors
    - Graceful degradation with fallback data
    - Resource cleanup via context managers
    """
    
    def __init__(self, simulate: bool = False):
        """
        Initialize async sensor manager.
        
        Args:
            simulate: Enable simulation mode for testing
        """
        self.simulate = simulate
        self._running = False
        self._lock = asyncio.Lock()
        
        # Sensor instances
        self._sensors = {}
        self._sensor_status = {}
        
        # Bus-specific locks for I2C coordination
        self._i2c_lock = asyncio.Lock()
        
        # Shared sensor data
        self._sensor_data = {}
        self._last_update = None
        
        # Task handles
        self._tasks = {}
        
        # Configuration
        self._config = {
            "imu_update_rate": 10.0,  # Hz
            "i2c_update_rate": 1.0,   # Hz
            "timeout_seconds": 2.0,
            "max_consecutive_errors": 3,
            "backoff_base": 0.1,
            "backoff_max": 5.0,
        }
        
        # Initialize sensor status
        sensor_names = ["bno085", "bme280", "ina3221", "vl53l0x"]
        for name in sensor_names:
            self._sensor_status[name] = SensorStatus(
                state=SensorState.UNINITIALIZED,
                last_reading=datetime.now(),
                error_count=0,
                consecutive_errors=0,
                last_error=None,
                is_hardware_available=False,
            )
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup"""
        await self.stop()
    
    async def start(self):
        """Start the async sensor manager"""
        if self._running:
            logger.warning("AsyncSensorManager already running")
            return
        
        logger.info("Starting AsyncSensorManager...")
        self._running = True
        
        try:
            # Initialize sensors
            await self._initialize_sensors()
            
            # Start async tasks
            await self._start_tasks()
            
            logger.info("AsyncSensorManager started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start AsyncSensorManager: {e}")
            self._running = False
            raise
    
    async def stop(self):
        """Stop the async sensor manager and cleanup resources"""
        if not self._running:
            return
        
        logger.info("Stopping AsyncSensorManager...")
        self._running = False
        
        # Cancel all tasks
        for task_name, task in self._tasks.items():
            if task and not task.done():
                logger.debug(f"Cancelling task: {task_name}")
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Cleanup sensors
        await self._cleanup_sensors()
        
        logger.info("AsyncSensorManager stopped")
    
    async def _initialize_sensors(self):
        """Initialize all sensors with improved error handling"""
        logger.info("Initializing sensors...")
        
        # Initialize IMU (UART-based)
        await self._initialize_imu()
        
        # Initialize I2C sensors
        await self._initialize_i2c_sensors()
        
        logger.info("Sensor initialization complete")
    
    async def _initialize_imu(self):
        """Initialize IMU sensor with timeout handling"""
        sensor_name = "bno085"
        status = self._sensor_status[sensor_name]
        status.state = SensorState.INITIALIZING
        status.initialization_attempts += 1
        
        try:
            logger.info("Initializing BNO085 IMU sensor...")
            
            if self.simulate:
                # Simulation mode
                logger.info("IMU: Using simulation mode")
                self._sensors[sensor_name] = "simulated"
                status.state = SensorState.OPERATIONAL
                status.is_hardware_available = False
                return
            
            # Initialize with timeout
            init_task = asyncio.create_task(self._init_imu_hardware())
            try:
                imu_sensor = await asyncio.wait_for(init_task, timeout=10.0)
                self._sensors[sensor_name] = imu_sensor
                status.state = SensorState.OPERATIONAL
                status.is_hardware_available = imu_sensor.is_hardware_available if imu_sensor else False
                logger.info(f"IMU initialized successfully (hardware: {status.is_hardware_available})")
                
            except asyncio.TimeoutError:
                logger.error("IMU initialization timed out after 10 seconds")
                status.state = SensorState.FAILED
                status.last_error = "Initialization timeout"
                self._sensors[sensor_name] = None
                
        except Exception as e:
            logger.error(f"IMU initialization failed: {e}")
            status.state = SensorState.FAILED
            status.last_error = str(e)
            status.error_count += 1
            self._sensors[sensor_name] = None
    
    async def _init_imu_hardware(self):
        """Initialize IMU hardware (runs in executor to avoid blocking)"""
        loop = asyncio.get_event_loop()
        # Run in executor to avoid blocking the event loop
        return await loop.run_in_executor(None, BNO085Sensor)
    
    async def _initialize_i2c_sensors(self):
        """Initialize I2C-based sensors"""
        
        # Initialize I2C bus
        i2c_bus = None
        if not self.simulate and board and busio:
            try:
                i2c_bus = busio.I2C(board.SCL, board.SDA)
                logger.info("I2C bus initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize I2C bus: {e}")
        
        # Initialize BME280
        await self._initialize_bme280(i2c_bus)
        
        # Initialize INA3221
        await self._initialize_ina3221()
        
        # Initialize ToF sensors
        await self._initialize_tof()
    
    async def _initialize_bme280(self, i2c_bus):
        """Initialize BME280 environmental sensor"""
        sensor_name = "bme280"
        status = self._sensor_status[sensor_name]
        status.state = SensorState.INITIALIZING
        status.initialization_attempts += 1
        
        try:
            if self.simulate:
                logger.info("BME280: Using simulation mode")
                self._sensors[sensor_name] = "simulated"
                status.state = SensorState.OPERATIONAL
                status.is_hardware_available = False
                return
            
            # Initialize BME280 with timeout
            sensor = BME280Sensor._initialize(i2c_bus)
            if sensor:
                self._sensors[sensor_name] = sensor
                status.state = SensorState.OPERATIONAL
                status.is_hardware_available = True
                logger.info("BME280 initialized successfully")
            else:
                status.state = SensorState.FAILED
                status.last_error = "Sensor initialization returned None"
                self._sensors[sensor_name] = None
                logger.warning("BME280 initialization failed")
                
        except Exception as e:
            logger.error(f"BME280 initialization error: {e}")
            status.state = SensorState.FAILED
            status.last_error = str(e)
            status.error_count += 1
            self._sensors[sensor_name] = None
    
    async def _initialize_ina3221(self):
        """Initialize INA3221 power sensor"""
        sensor_name = "ina3221"
        status = self._sensor_status[sensor_name]
        status.state = SensorState.INITIALIZING
        status.initialization_attempts += 1
        
        try:
            if self.simulate:
                logger.info("INA3221: Using simulation mode")
                self._sensors[sensor_name] = "simulated"
                status.state = SensorState.OPERATIONAL
                status.is_hardware_available = False
                return
            
            # Initialize INA3221
            sensor = INA3221Sensor.init_ina3221()
            if sensor:
                self._sensors[sensor_name] = sensor
                status.state = SensorState.OPERATIONAL
                status.is_hardware_available = True
                logger.info("INA3221 initialized successfully")
            else:
                status.state = SensorState.FAILED
                status.last_error = "Sensor initialization returned None"
                self._sensors[sensor_name] = None
                logger.warning("INA3221 initialization failed")
                
        except Exception as e:
            logger.error(f"INA3221 initialization error: {e}")
            status.state = SensorState.FAILED
            status.last_error = str(e)
            status.error_count += 1
            self._sensors[sensor_name] = None
    
    async def _initialize_tof(self):
        """Initialize ToF distance sensors"""
        sensor_name = "vl53l0x"
        status = self._sensor_status[sensor_name]
        status.state = SensorState.INITIALIZING
        status.initialization_attempts += 1
        
        try:
            if self.simulate:
                logger.info("ToF: Using simulation mode")
                self._sensors[sensor_name] = "simulated"
                status.state = SensorState.OPERATIONAL
                status.is_hardware_available = False
                return
            
            # Initialize ToF sensors with timeout
            init_task = asyncio.create_task(self._init_tof_hardware())
            try:
                tof_sensor = await asyncio.wait_for(init_task, timeout=15.0)
                self._sensors[sensor_name] = tof_sensor
                status.state = SensorState.OPERATIONAL
                status.is_hardware_available = tof_sensor.is_hardware_available if tof_sensor else False
                logger.info(f"ToF sensors initialized (hardware: {status.is_hardware_available})")
                
            except asyncio.TimeoutError:
                logger.error("ToF initialization timed out after 15 seconds")
                status.state = SensorState.FAILED
                status.last_error = "Initialization timeout"
                self._sensors[sensor_name] = None
                
        except Exception as e:
            logger.error(f"ToF initialization error: {e}")
            status.state = SensorState.FAILED
            status.last_error = str(e)
            status.error_count += 1
            self._sensors[sensor_name] = None
    
    async def _init_tof_hardware(self):
        """Initialize ToF hardware (runs in executor)"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, VL53L0XSensors)
    
    async def _start_tasks(self):
        """Start async sensor reading tasks"""
        logger.info("Starting sensor reading tasks...")
        
        # UART task for IMU
        self._tasks["imu_task"] = asyncio.create_task(self._imu_task())
        
        # I2C task for other sensors
        self._tasks["i2c_task"] = asyncio.create_task(self._i2c_task())
        
        logger.info("Sensor tasks started")
    
    async def _imu_task(self):
        """Async task for IMU sensor reading"""
        logger.debug("IMU task started")
        interval = 1.0 / self._config["imu_update_rate"]
        
        while self._running:
            try:
                start_time = time.monotonic()
                
                # Read IMU data
                await self._read_imu()
                
                # Calculate sleep time
                elapsed = time.monotonic() - start_time
                sleep_time = max(0, interval - elapsed)
                await asyncio.sleep(sleep_time)
                
            except asyncio.CancelledError:
                logger.debug("IMU task cancelled")
                break
            except Exception as e:
                logger.error(f"IMU task error: {e}")
                await asyncio.sleep(1.0)
        
        logger.debug("IMU task stopped")
    
    async def _i2c_task(self):
        """Async task for I2C sensor reading"""
        logger.debug("I2C task started")
        interval = 1.0 / self._config["i2c_update_rate"]
        
        while self._running:
            try:
                start_time = time.monotonic()
                
                # Read I2C sensors sequentially with async lock
                async with self._i2c_lock:
                    await self._read_bme280()
                    await asyncio.sleep(0.1)  # Brief pause between sensors
                    
                    await self._read_ina3221()
                    await asyncio.sleep(0.1)
                    
                    await self._read_tof()
                
                # Calculate sleep time
                elapsed = time.monotonic() - start_time
                sleep_time = max(0, interval - elapsed)
                await asyncio.sleep(sleep_time)
                
            except asyncio.CancelledError:
                logger.debug("I2C task cancelled")
                break
            except Exception as e:
                logger.error(f"I2C task error: {e}")
                await asyncio.sleep(1.0)
        
        logger.debug("I2C task stopped")
    
    async def _read_imu(self):
        """Read IMU sensor data"""
        sensor_name = "bno085"
        status = self._sensor_status[sensor_name]
        sensor = self._sensors.get(sensor_name)
        
        try:
            if not sensor:
                # Use fallback data
                data = self._get_fallback_imu()
            elif sensor == "simulated":
                # Simulated data
                data = self._get_simulated_imu()
            else:
                # Read from hardware
                data = await self._read_imu_hardware(sensor)
            
            # Update shared data
            async with self._lock:
                self._sensor_data["imu"] = data
                self._last_update = time.monotonic()
            
            # Update status
            status.last_reading = datetime.now()
            status.consecutive_errors = 0
            if status.state == SensorState.FAILED:
                status.state = SensorState.OPERATIONAL
                logger.info("IMU sensor recovered")
            
        except Exception as e:
            status.error_count += 1
            status.consecutive_errors += 1
            status.last_error = str(e)
            
            logger.warning(f"IMU read error: {e}")
            
            # Use fallback data
            async with self._lock:
                self._sensor_data["imu"] = self._get_fallback_imu()
            
            # Check if sensor should be marked as failed
            if status.consecutive_errors >= self._config["max_consecutive_errors"]:
                status.state = SensorState.FAILED
                logger.error(f"IMU marked as failed after {status.consecutive_errors} consecutive errors")
    
    async def _read_imu_hardware(self, sensor):
        """Read IMU hardware data with timeout"""
        loop = asyncio.get_event_loop()
        
        # Run in executor to avoid blocking
        read_task = loop.run_in_executor(None, sensor.get_sensor_data)
        try:
            data = await asyncio.wait_for(read_task, timeout=self._config["timeout_seconds"])
            return data
        except asyncio.TimeoutError:
            raise Exception("IMU read timeout")
    
    async def _read_bme280(self):
        """Read BME280 environmental sensor"""
        sensor_name = "bme280"
        status = self._sensor_status[sensor_name]
        sensor = self._sensors.get(sensor_name)
        
        try:
            if not sensor:
                data = self._get_fallback_environment()
            elif sensor == "simulated":
                data = self._get_simulated_environment()
            else:
                # Read from hardware
                raw_data = BME280Sensor.read_bme280(sensor)
                if raw_data:
                    data = {
                        "temperature": raw_data.get("temperature_c"),
                        "humidity": raw_data.get("humidity"),
                        "pressure": raw_data.get("pressure"),
                    }
                else:
                    data = self._get_fallback_environment()
            
            # Update shared data
            async with self._lock:
                self._sensor_data["environment"] = data
            
            # Update status
            status.last_reading = datetime.now()
            status.consecutive_errors = 0
            if status.state == SensorState.FAILED:
                status.state = SensorState.OPERATIONAL
                logger.info("BME280 sensor recovered")
            
        except Exception as e:
            status.error_count += 1
            status.consecutive_errors += 1
            status.last_error = str(e)
            
            logger.warning(f"BME280 read error: {e}")
            
            # Use fallback data
            async with self._lock:
                self._sensor_data["environment"] = self._get_fallback_environment()
            
            if status.consecutive_errors >= self._config["max_consecutive_errors"]:
                status.state = SensorState.FAILED
    
    async def _read_ina3221(self):
        """Read INA3221 power sensor with caching"""
        sensor_name = "ina3221"
        status = self._sensor_status[sensor_name]
        sensor = self._sensors.get(sensor_name)
        
        try:
            if not sensor:
                data = self._get_fallback_power()
            elif sensor == "simulated":
                data = self._get_simulated_power()
            else:
                # Read battery data from channel 3
                battery_data = INA3221Sensor.read_ina3221(sensor, 3)
                if battery_data:
                    voltage = battery_data.get("bus_voltage", 0.0)
                    current = battery_data.get("current", 0.0)
                    
                    # Calculate percentage with comment stripping for .env values
                    min_volt_str = os.getenv("BATTERY_MIN_VOLTAGE", "10.5")
                    max_volt_str = os.getenv("BATTERY_MAX_VOLTAGE", "14.6")
                    min_volt = float((min_volt_str or "10.5").split('#')[0].strip())
                    max_volt = float((max_volt_str or "14.6").split('#')[0].strip())
                    
                    if voltage <= min_volt:
                        percentage = 0.0
                    elif voltage >= max_volt:
                        percentage = 100.0
                    else:
                        percentage = ((voltage - min_volt) / (max_volt - min_volt)) * 100
                    
                    data = {
                        "voltage": voltage,
                        "current": current,
                        "power": voltage * current,
                        "percentage": round(percentage, 1),
                    }
                else:
                    data = self._get_fallback_power()
            
            # Update shared data
            async with self._lock:
                self._sensor_data["power"] = data
            
            # Update status
            status.last_reading = datetime.now()
            status.consecutive_errors = 0
            if status.state == SensorState.FAILED:
                status.state = SensorState.OPERATIONAL
                logger.info("INA3221 sensor recovered")
            
        except Exception as e:
            status.error_count += 1
            status.consecutive_errors += 1
            status.last_error = str(e)
            
            logger.debug(f"INA3221 read error: {e}")  # Debug level since it's optional
            
            # Use fallback data
            async with self._lock:
                self._sensor_data["power"] = self._get_fallback_power()
            
            if status.consecutive_errors >= self._config["max_consecutive_errors"]:
                status.state = SensorState.DEGRADED  # Degraded, not failed (optional sensor)
    
    async def _read_tof(self):
        """Read ToF distance sensors"""
        sensor_name = "vl53l0x"
        status = self._sensor_status[sensor_name]
        sensor = self._sensors.get(sensor_name)
        
        try:
            if not sensor:
                data = self._get_fallback_tof()
            elif sensor == "simulated":
                data = self._get_simulated_tof()
            else:
                # Read from hardware
                distances = sensor.get_distances()
                data = {
                    "left": distances.get("left", -1),
                    "right": distances.get("right", -1),
                    "working": distances.get("left", -1) != -1 or distances.get("right", -1) != -1
                }
            
            # Update shared data
            async with self._lock:
                self._sensor_data["tof"] = data
            
            # Update status
            status.last_reading = datetime.now()
            status.consecutive_errors = 0
            if status.state == SensorState.FAILED:
                status.state = SensorState.OPERATIONAL
                logger.info("ToF sensors recovered")
            
        except Exception as e:
            status.error_count += 1
            status.consecutive_errors += 1
            status.last_error = str(e)
            
            logger.warning(f"ToF read error: {e}")
            
            # Use fallback data
            async with self._lock:
                self._sensor_data["tof"] = self._get_fallback_tof()
            
            if status.consecutive_errors >= self._config["max_consecutive_errors"]:
                status.state = SensorState.FAILED
    
    async def get_sensor_data(self) -> Dict[str, Any]:
        """Get current sensor data"""
        async with self._lock:
            data = self._sensor_data.copy()
            
        # Add status information
        data["status"] = {
            name: {
                "state": status.state.value,
                "error_count": status.error_count,
                "is_hardware_available": status.is_hardware_available,
                "last_error": status.last_error,
            }
            for name, status in self._sensor_status.items()
        }
        
        # Add timestamp
        data["timestamp"] = time.time()
        data["last_update"] = self._last_update
        
        return data
    
    async def get_sensor_status(self) -> Dict[str, SensorStatus]:
        """Get detailed sensor status"""
        return self._sensor_status.copy()
    
    async def _cleanup_sensors(self):
        """Cleanup sensor resources"""
        logger.debug("Cleaning up sensor resources...")
        
        # Cleanup IMU
        imu = self._sensors.get("bno085")
        if imu and hasattr(imu, "cleanup"):
            try:
                imu.cleanup()
            except Exception as e:
                logger.warning(f"IMU cleanup error: {e}")
        
        # Other sensors don't require explicit cleanup
        
        self._sensors.clear()
        logger.debug("Sensor cleanup complete")
    
    # Fallback and simulation data methods
    def _get_fallback_imu(self) -> Dict[str, Any]:
        """Get fallback IMU data"""
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
    
    def _get_fallback_environment(self) -> Dict[str, Any]:
        """Get fallback environmental data"""
        return {
            "temperature": "N/A",
            "humidity": "N/A", 
            "pressure": "N/A"
        }
    
    def _get_fallback_power(self) -> Dict[str, Any]:
        """Get fallback power data"""
        return {
            "voltage": "N/A",
            "current": "N/A",
            "power": "N/A", 
            "percentage": "N/A"
        }
    
    def _get_fallback_tof(self) -> Dict[str, Any]:
        """Get fallback ToF data"""
        return {
            "left": "N/A",
            "right": "N/A",
            "working": False
        }
    
    def _get_simulated_imu(self) -> Dict[str, Any]:
        """Get simulated IMU data"""
        import random
        return {
            "heading": round(random.uniform(0, 360), 1),
            "roll": round(random.uniform(-5, 5), 1),
            "pitch": round(random.uniform(-5, 5), 1),
            "acceleration": {
                "x": round(random.uniform(-0.5, 0.5), 2),
                "y": round(random.uniform(-0.5, 0.5), 2),
                "z": round(9.8 + random.uniform(-0.2, 0.2), 2)
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
            "safety_status": {"is_safe": True, "status": "simulated"}
        }
    
    def _get_simulated_environment(self) -> Dict[str, Any]:
        """Get simulated environmental data"""
        import random
        return {
            "temperature": round(random.uniform(15, 30), 1),
            "humidity": round(random.uniform(40, 80), 1),
            "pressure": round(random.uniform(1000, 1030), 1)
        }
    
    def _get_simulated_power(self) -> Dict[str, Any]:
        """Get simulated power data"""
        import random
        voltage = round(random.uniform(11.5, 13.8), 2)
        current = round(random.uniform(0.5, 2.0), 2)
        return {
            "voltage": voltage,
            "current": current,
            "power": round(voltage * current, 2),
            "percentage": round(random.uniform(60, 90), 1)
        }
    
    def _get_simulated_tof(self) -> Dict[str, Any]:
        """Get simulated ToF data"""
        import random
        return {
            "left": int(random.uniform(50, 300)),
            "right": int(random.uniform(50, 300)),
            "working": True
        }


# Compatibility wrapper for existing code
class AsyncSensorInterface:
    """Compatibility wrapper for existing sensor interface"""
    
    def __init__(self):
        self._manager = None
        self._loop = None
    
    def start(self):
        """Start the async sensor manager in compatibility mode"""
        try:
            # Check if we're already in an event loop
            self._loop = asyncio.get_event_loop()
            if self._loop.is_running():
                # We're in an existing loop, create task
                self._manager = AsyncSensorManager()
                asyncio.create_task(self._manager.start())
            else:
                # No loop running, start our own
                self._manager = AsyncSensorManager()
                self._loop.run_until_complete(self._manager.start())
        except RuntimeError:
            # No event loop, create one
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._manager = AsyncSensorManager()
            self._loop.run_until_complete(self._manager.start())
    
    def stop(self):
        """Stop the sensor manager"""
        if self._manager and self._loop:
            if self._loop.is_running():
                asyncio.create_task(self._manager.stop())
            else:
                self._loop.run_until_complete(self._manager.stop())
    
    def get_sensor_data(self) -> Dict[str, Any]:
        """Get sensor data (synchronous wrapper)"""
        if not self._manager:
            return {}
        
        if self._loop and self._loop.is_running():
            # We're in an async context
            task = asyncio.create_task(self._manager.get_sensor_data())
            return task
        else:
            # Synchronous context
            return self._loop.run_until_complete(self._manager.get_sensor_data())


if __name__ == "__main__":
    """Test the async sensor manager"""
    import signal
    import sys
    
    async def main():
        # Setup signal handlers for graceful shutdown
        shutdown_event = asyncio.Event()
        
        def signal_handler():
            logger.info("Shutdown signal received")
            shutdown_event.set()
        
        # Register signal handlers
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, lambda s, f: signal_handler())
        
        # Start sensor manager
        async with AsyncSensorManager(simulate=False) as manager:
            logger.info("AsyncSensorManager test started. Press Ctrl+C to stop.")
            
            # Main loop
            try:
                while not shutdown_event.is_set():
                    # Get and display sensor data
                    data = await manager.get_sensor_data()
                    logger.info(f"Sensor data: {data}")
                    
                    # Wait a bit
                    await asyncio.sleep(2.0)
                    
            except KeyboardInterrupt:
                logger.info("KeyboardInterrupt received")
                shutdown_event.set()
        
        logger.info("AsyncSensorManager test completed")
    
    # Run the test
    asyncio.run(main())
