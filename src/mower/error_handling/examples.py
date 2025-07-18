"""
Examples of using circuit breaker patterns with hardware interfaces.

This module demonstrates how to apply circuit breaker decorators to hardware
operations to improve system reliability and fault tolerance. It showcases
different specialized circuit breaker decorators for various hardware components.
"""

import asyncio
import logging
import random
import time
from typing import Any, Dict, List, Optional

from mower.error_handling.circuit_breaker import (
    CircuitBreakerOpenError,
    circuit_breaker,
    get_circuit_breaker_manager,
    hardware_circuit_breaker,
    i2c_circuit_breaker,
    motor_circuit_breaker,
    sensor_circuit_breaker,
)
from mower.error_handling.exceptions import HardwareError

logger = logging.getLogger(__name__)


class ExampleSensorInterface:
    """
    Example sensor interface demonstrating circuit breaker usage.
    
    This class shows how to apply circuit breaker decorators to hardware
    operations that may fail due to I2C communication issues, sensor
    malfunctions, or other hardware-related problems.
    """
    
    def __init__(self, sensor_name: str = "example_sensor"):
        self.sensor_name = sensor_name
        self.is_initialized = False
        self._last_reading = None
        self._failure_count = 0
    
    @sensor_circuit_breaker(
        name="sensor_initialization",
        failure_threshold=2,
        timeout=30.0
    )
    def initialize(self) -> bool:
        """
        Initialize the sensor with circuit breaker protection.
        
        Returns:
            bool: True if initialization successful
            
        Raises:
            HardwareError: If sensor initialization fails
        """
        logger.info(f"Initializing {self.sensor_name}")
        
        # Simulate potential I2C communication failure
        if self._failure_count < 2:
            self._failure_count += 1
            raise HardwareError(f"Failed to initialize {self.sensor_name}")
        
        self.is_initialized = True
        logger.info(f"{self.sensor_name} initialized successfully")
        return True   
 
    @sensor_circuit_breaker(
        name="sensor_reading",
        failure_threshold=3,
        timeout=15.0,
        fallback=lambda: {"timestamp": time.time(), "value": None, "status": "fallback", "sensor": "fallback_sensor"}
    )
    def read_sensor(self) -> Dict[str, Any]:
        """
        Read sensor data with circuit breaker protection.
        
        Returns:
            Dict[str, Any]: Sensor reading data
            
        Raises:
            HardwareError: If sensor reading fails
        """
        if not self.is_initialized:
            raise HardwareError(f"{self.sensor_name} not initialized")
        
        # Simulate intermittent sensor reading failures
        if random.random() < 0.3:  # 30% failure rate for demonstration
            raise HardwareError(f"Failed to read from {self.sensor_name}")
        
        # Simulate successful reading
        reading = {
            "timestamp": time.time(),
            "value": random.uniform(0, 100),
            "status": "ok",
            "sensor": self.sensor_name
        }
        
        self._last_reading = reading
        return reading
        
    @i2c_circuit_breaker(
        name="sensor_calibration",
        failure_threshold=2,
        timeout=45.0
    )
    def calibrate(self) -> bool:
        """
        Calibrate the sensor with I2C circuit breaker protection.
        
        Returns:
            bool: True if calibration successful
            
        Raises:
            HardwareError: If sensor calibration fails
        """
        logger.info(f"Calibrating {self.sensor_name}")
        
        # Simulate I2C bus contention or timing issues
        if random.random() < 0.4:  # 40% failure rate
            raise HardwareError(f"I2C bus error during calibration of {self.sensor_name}")
        
        logger.info(f"{self.sensor_name} calibrated successfully")
        return True
        
    async def async_read_sensor(self) -> Dict[str, Any]:
        """
        Asynchronous sensor reading with circuit breaker protection.
        
        Returns:
            Dict[str, Any]: Sensor reading data
        """
        # Get the circuit breaker manager and create a breaker for this method
        manager = get_circuit_breaker_manager()
        breaker = manager.create_breaker(
            name=f"{self.sensor_name}_async_read",
            failure_threshold=3,
            timeout=10.0,
            expected_exception=(HardwareError, OSError, IOError),
            failure_window=30.0
        )
        
        try:
            # Use the circuit breaker to protect the async operation
            return await breaker.call_async(self._async_read_impl)
        except CircuitBreakerOpenError:
            logger.warning(f"Circuit open for {self.sensor_name} async read, returning default value")
            return {
                "timestamp": time.time(),
                "value": None,
                "status": "circuit_open",
                "sensor": self.sensor_name
            }
    
    async def _async_read_impl(self) -> Dict[str, Any]:
        """Implementation of async sensor reading."""
        await asyncio.sleep(0.1)  # Simulate I/O operation
        
        if not self.is_initialized:
            raise HardwareError(f"{self.sensor_name} not initialized")
        
        # Simulate intermittent failures
        if random.random() < 0.3:
            raise HardwareError(f"Async read failed for {self.sensor_name}")
        
        return {
            "timestamp": time.time(),
            "value": random.uniform(0, 100),
            "status": "ok",
            "sensor": self.sensor_name
        }


class ExampleMotorController:
    """
    Example motor controller demonstrating circuit breaker usage for actuators.
    
    This class shows how to apply specialized motor circuit breaker decorators
    to protect motor control operations and prevent damage to motors.
    """
    
    def __init__(self, motor_name: str = "example_motor"):
        self.motor_name = motor_name
        self.is_enabled = False
        self.current_speed = 0.0
        self.error_count = 0
        self.last_error_time = None
    
    @motor_circuit_breaker(
        name="motor_control",
        failure_threshold=2,
        timeout=20.0,
        fallback=lambda speed: False  # Safe fallback that doesn't change motor state
    )
    def set_speed(self, speed: float) -> bool:
        """
        Set motor speed with circuit breaker protection.
        
        Args:
            speed: Motor speed (-1.0 to 1.0)
            
        Returns:
            bool: True if speed set successfully
            
        Raises:
            HardwareError: If motor control fails
        """
        if not self.is_enabled:
            raise HardwareError(f"{self.motor_name} not enabled")
        
        if abs(speed) > 1.0:
            raise ValueError("Speed must be between -1.0 and 1.0")
        
        # Simulate potential motor control failure
        if random.random() < 0.2:  # 20% failure rate
            self.error_count += 1
            self.last_error_time = time.time()
            raise HardwareError(f"Failed to set speed for {self.motor_name}")
        
        self.current_speed = speed
        logger.info(f"{self.motor_name} speed set to {speed}")
        return True
    
    @motor_circuit_breaker(
        name="motor_enable",
        failure_threshold=1,
        timeout=60.0
    )
    def enable(self) -> bool:
        """
        Enable motor with circuit breaker protection.
        
        Returns:
            bool: True if motor enabled successfully
            
        Raises:
            HardwareError: If motor enable fails
        """
        # Simulate enable operation that might fail
        if random.random() < 0.1:  # 10% failure rate
            raise HardwareError(f"Failed to enable {self.motor_name}")
            
        self.is_enabled = True
        logger.info(f"{self.motor_name} enabled")
        return True
        
    @motor_circuit_breaker(
        name="motor_disable",
        failure_threshold=1,
        timeout=30.0
    )
    def disable(self) -> bool:
        """
        Disable motor with circuit breaker protection.
        
        Returns:
            bool: True if motor disabled successfully
            
        Raises:
            HardwareError: If motor disable fails
        """
        # Safety-critical operation - should rarely fail
        if random.random() < 0.05:  # 5% failure rate
            raise HardwareError(f"Failed to disable {self.motor_name}")
            
        self.is_enabled = False
        self.current_speed = 0.0
        logger.info(f"{self.motor_name} disabled")
        return True
        
    def emergency_stop(self) -> bool:
        """
        Emergency stop without circuit breaker.
        
        This method bypasses the circuit breaker since it's a critical
        safety operation that must always be attempted.
        
        Returns:
            bool: True if emergency stop successful
        """
        try:
            self.is_enabled = False
            self.current_speed = 0.0
            logger.info(f"{self.motor_name} emergency stopped")
            return True
        except Exception as e:
            logger.critical(f"EMERGENCY STOP FAILED for {self.motor_name}: {e}")
            return False


def demonstrate_circuit_breaker_usage():
    """
    Demonstrate circuit breaker usage with example hardware components.
    
    This function shows how circuit breakers protect against failures and
    provide graceful degradation when hardware components fail.
    """
    logger.info("Starting circuit breaker demonstration")
    
    # Example 1: Sensor with circuit breaker protection
    sensor = ExampleSensorInterface("temperature_sensor")
    
    try:
        # This will fail initially but eventually succeed due to circuit breaker retry
        logger.info("=== Demonstrating sensor initialization with circuit breaker ===")
        try:
            sensor.initialize()
        except Exception as e:
            logger.error(f"First initialization attempt failed as expected: {e}")
            logger.info("Retrying initialization...")
            sensor.initialize()  # Should succeed on second attempt
        
        # Demonstrate sensor calibration with I2C circuit breaker
        logger.info("\n=== Demonstrating I2C circuit breaker for sensor calibration ===")
        try:
            sensor.calibrate()
            logger.info("Sensor calibration successful")
        except Exception as e:
            logger.error(f"Sensor calibration failed: {e}")
        
        # Read sensor multiple times - some will fail but fallback will be used
        logger.info("\n=== Demonstrating sensor reading with fallback ===")
        for i in range(5):
            try:
                reading = sensor.read_sensor()
                if reading["status"] == "fallback":
                    logger.warning(f"Reading {i+1} used fallback: {reading}")
                else:
                    logger.info(f"Reading {i+1} successful: {reading}")
            except Exception as e:
                logger.error(f"Reading {i+1} failed unexpectedly: {e}")
            
            time.sleep(0.5)
        
        # Demonstrate async sensor reading with circuit breaker
        logger.info("\n=== Demonstrating async sensor reading with circuit breaker ===")
        
        async def run_async_demo():
            for i in range(3):
                reading = await sensor.async_read_sensor()
                logger.info(f"Async reading {i+1}: {reading}")
                await asyncio.sleep(0.5)
        
        # Run the async demo
        asyncio.run(run_async_demo())
    
    except Exception as e:
        logger.error(f"Sensor demonstration failed: {e}")
    
    # Example 2: Motor controller with circuit breaker protection
    logger.info("\n=== Demonstrating motor controller with circuit breaker ===")
    motor = ExampleMotorController("drive_motor")
    
    try:
        # Enable the motor
        try:
            motor.enable()
            logger.info("Motor enabled successfully")
        except Exception as e:
            logger.error(f"Motor enable failed: {e}")
            return  # Can't continue if motor isn't enabled
        
        # Try to set various speeds - failures will trigger circuit breaker
        speeds = [0.5, 0.8, -0.3, 0.2, 0.0]
        for i, speed in enumerate(speeds):
            try:
                result = motor.set_speed(speed)
                if result:
                    logger.info(f"Speed {i+1}: Set to {speed}")
                else:
                    logger.warning(f"Speed {i+1}: Fallback used for {speed}")
            except CircuitBreakerOpenError as e:
                logger.warning(f"Speed {i+1}: Circuit breaker open: {e}")
            except Exception as e:
                logger.error(f"Speed {i+1}: Failed: {e}")
            
            time.sleep(0.5)
        
        # Demonstrate circuit breaker state inspection
        logger.info("\n=== Demonstrating circuit breaker state inspection ===")
        manager = get_circuit_breaker_manager()
        states = manager.get_all_states()
        
        for name, state in states.items():
            logger.info(f"Circuit breaker '{name}':")
            logger.info(f"  - State: {state['state']}")
            logger.info(f"  - Failures: {state['failure_count']}/{state['failure_threshold']}")
            logger.info(f"  - Timeout remaining: {state['timeout_remaining']:.1f}s")
        
        # Demonstrate emergency stop (bypasses circuit breaker)
        logger.info("\n=== Demonstrating emergency stop (bypasses circuit breaker) ===")
        motor.emergency_stop()
        
        # Demonstrate circuit breaker reset
        logger.info("\n=== Demonstrating manual circuit breaker reset ===")
        for name in states:
            breaker = manager.get_breaker(name)
            if breaker and breaker.state != CircuitState.CLOSED:
                logger.info(f"Resetting circuit breaker '{name}'")
                breaker.reset()
    
    except Exception as e:
        logger.error(f"Motor demonstration failed: {e}")
    
    logger.info("\nCircuit breaker demonstration completed")


if __name__ == "__main__":
    # Configure logging for demonstration
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)8s] %(message)s (%(filename)s:%(lineno)d)'
    )
    
    demonstrate_circuit_breaker_usage()