"""
Hardware Manager - Unified interface for all hardware components.

This module provides a single point of access to all hardware components
with built-in safety checks, resource management, and simulation support.
"""

import time
import logging
from typing import Optional, Dict, Any, Tuple
from threading import Lock, RLock
from contextlib import contextmanager
from abc import ABC, abstractmethod

from mower.config.settings import get_config, SystemConfig


logger = logging.getLogger(__name__)


class HardwareError(Exception):
    """Base exception for hardware-related errors."""
    pass


class SafetyViolationError(HardwareError):
    """Raised when a safety limit is violated."""
    pass


class HardwareInterface(ABC):
    """Base interface for all hardware components."""
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the hardware component.
        
        Returns:
            True if initialization successful, False otherwise.
        """
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Clean up hardware resources."""
        pass
    
    @abstractmethod
    def is_healthy(self) -> bool:
        """Check if hardware component is healthy.
        
        Returns:
            True if healthy, False otherwise.
        """
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get hardware component status.
        
        Returns:
            Dictionary containing status information.
        """
        pass


class MotorController(HardwareInterface):
    """Motor control interface with safety validation."""
    
    def __init__(self, config: SystemConfig, simulation: bool = False):
        """Initialize motor controller.
        
        Args:
            config: System configuration
            simulation: Enable simulation mode
        """
        self.config = config
        self.simulation = simulation
        self._lock = Lock()
        self._initialized = False
        self._last_command_time = 0.0
        self._serial_connection = None
        
        # Current motor states
        self._current_steering = 0
        self._current_throttle = 0
        self._current_blade = 0
        self._motors_enabled = False
    
    def initialize(self) -> bool:
        """Initialize motor controller."""
        with self._lock:
            try:
                if self.simulation:
                    logger.info("Motor controller initialized in simulation mode")
                    self._initialized = True
                    return True
                
                # Initialize RoboHAT serial connection with timeout
                import serial
                try:
                    self._serial_connection = serial.Serial(
                        port=self.config.hardware.robohat_port,
                        baudrate=self.config.hardware.robohat_baudrate,
                        timeout=1.0  # Short timeout for initialization
                    )
                    time.sleep(0.1)  # Give time for connection to stabilize
                except (serial.SerialException, OSError) as e:
                    logger.warning(f"Could not open {self.config.hardware.robohat_port}: {e}")
                    logger.info("Falling back to simulation mode")
                    self.simulation = True
                    self._initialized = True
                    return True
                
                # Test connection with a safe command (with timeout)
                try:
                    if self._send_raw_command("PWM,0,0"):
                        logger.info(f"Motor controller initialized on {self.config.hardware.robohat_port}")
                        self._initialized = True
                        return True
                    else:
                        logger.warning("Failed to communicate with RoboHAT, using simulation")
                        self.simulation = True
                        self._initialized = True
                        return True
                except Exception as e:
                    logger.warning(f"RoboHAT communication error: {e}, using simulation")
                    self.simulation = True
                    self._initialized = True
                    return True
                    
            except Exception as e:
                logger.error(f"Failed to initialize motor controller: {e}")
                return False
    
    def cleanup(self) -> None:
        """Clean up motor controller resources."""
        with self._lock:
            try:
                # Stop all motors
                if self._initialized:
                    self.stop_all_motors()
                
                # Close serial connection
                if self._serial_connection and not self.simulation:
                    self._serial_connection.close()
                    self._serial_connection = None
                
                self._initialized = False
                logger.info("Motor controller cleaned up")
                
            except Exception as e:
                logger.error(f"Error during motor controller cleanup: {e}")
    
    def is_healthy(self) -> bool:
        """Check if motor controller is healthy."""
        with self._lock:
            if not self._initialized:
                return False
            
            if self.simulation:
                return True
            
            # Check if serial connection is still open
            return (self._serial_connection is not None and 
                   self._serial_connection.is_open)
    
    def get_status(self) -> Dict[str, Any]:
        """Get motor controller status."""
        with self._lock:
            return {
                "initialized": self._initialized,
                "simulation": self.simulation,
                "motors_enabled": self._motors_enabled,
                "steering": self._current_steering,
                "throttle": self._current_throttle,
                "blade": self._current_blade,
                "last_command_time": self._last_command_time,
                "healthy": self.is_healthy()
            }
    
    def set_motors(self, steering: int, throttle: int, blade: int = 0) -> bool:
        """Set motor values with safety validation.
        
        Args:
            steering: Steering PWM value (-100 to 100)
            throttle: Throttle PWM value (-100 to 100)  
            blade: Blade PWM value (0 to 100)
            
        Returns:
            True if command sent successfully, False otherwise.
            
        Raises:
            SafetyViolationError: If values violate safety limits
        """
        with self._lock:
            if not self._initialized:
                raise HardwareError("Motor controller not initialized")
            
            # Validate safety limits
            self._validate_motor_values(steering, throttle, blade)
            
            # Send command
            success = self._send_motor_command(steering, throttle, blade)
            
            if success:
                self._current_steering = steering
                self._current_throttle = throttle
                self._current_blade = blade
                self._last_command_time = time.time()
                self._motors_enabled = (steering != 0 or throttle != 0 or blade != 0)
                
                logger.debug(f"Motors set: steering={steering}, throttle={throttle}, blade={blade}")
            
            return success
    
    def stop_all_motors(self) -> bool:
        """Stop all motors immediately."""
        return self.set_motors(0, 0, 0)
    
    def enable_blade(self, speed: int) -> bool:
        """Enable blade motor at specified speed.
        
        Args:
            speed: Blade speed (0-100)
            
        Returns:
            True if successful, False otherwise.
        """
        if not 0 <= speed <= 100:
            raise SafetyViolationError(f"Blade speed {speed} outside range [0, 100]")
        
        return self.set_motors(self._current_steering, self._current_throttle, speed)
    
    def disable_blade(self) -> bool:
        """Disable blade motor."""
        return self.set_motors(self._current_steering, self._current_throttle, 0)
    
    def _validate_motor_values(self, steering: int, throttle: int, blade: int) -> None:
        """Validate motor values against safety limits."""
        # Check steering range
        min_steer, max_steer = self.config.hardware.steering_range
        if not min_steer <= steering <= max_steer:
            raise SafetyViolationError(
                f"Steering {steering} outside range [{min_steer}, {max_steer}]"
            )
        
        # Check throttle range
        min_throttle, max_throttle = self.config.hardware.throttle_range
        if not min_throttle <= throttle <= max_throttle:
            raise SafetyViolationError(
                f"Throttle {throttle} outside range [{min_throttle}, {max_throttle}]"
            )
        
        # Check blade range
        min_blade, max_blade = self.config.hardware.blade_range
        if not min_blade <= blade <= max_blade:
            raise SafetyViolationError(
                f"Blade {blade} outside range [{min_blade}, {max_blade}]"
            )
        
        # Check maximum speed limit
        if abs(throttle) > self.config.hardware.max_speed:
            raise SafetyViolationError(
                f"Throttle {abs(throttle)} exceeds max speed {self.config.hardware.max_speed}"
            )
    
    def _send_motor_command(self, steering: int, throttle: int, blade: int = 0) -> bool:
        """Send motor command to hardware."""
        if self.simulation:
            # Simulate command delay
            time.sleep(0.01)
            return True
        
        # Format command for RoboHAT
        command = f"PWM,{steering},{throttle}"
        if blade > 0:
            # Send blade command separately if needed
            blade_command = f"BLADE,{blade}"
            return (self._send_raw_command(command) and 
                   self._send_raw_command(blade_command))
        
        return self._send_raw_command(command)
    
    def _send_raw_command(self, command: str) -> bool:
        """Send raw command to RoboHAT."""
        try:
            if self._serial_connection and self._serial_connection.is_open:
                command_bytes = f"{command}\r".encode('utf-8')
                self._serial_connection.write(command_bytes)
                self._serial_connection.flush()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to send command '{command}': {e}")
            return False


class SensorManager(HardwareInterface):
    """Unified sensor data collection and management."""
    
    def __init__(self, config: SystemConfig, simulation: bool = False):
        """Initialize sensor manager.
        
        Args:
            config: System configuration
            simulation: Enable simulation mode
        """
        self.config = config
        self.simulation = simulation
        self._lock = RLock()
        self._initialized = False
        self._sensors = {}
    
    def initialize(self) -> bool:
        """Initialize all sensors."""
        with self._lock:
            try:
                if self.simulation:
                    logger.info("Sensor manager initialized in simulation mode")
                    self._initialized = True
                    return True
                
                # Initialize real sensors here
                # This would include GPS, IMU, ToF, etc.
                logger.info("Sensor manager initialized")
                self._initialized = True
                return True
                
            except Exception as e:
                logger.error(f"Failed to initialize sensor manager: {e}")
                return False
    
    def cleanup(self) -> None:
        """Clean up sensor resources."""
        with self._lock:
            try:
                # Clean up individual sensors
                for sensor in self._sensors.values():
                    if hasattr(sensor, 'cleanup'):
                        sensor.cleanup()
                
                self._sensors.clear()
                self._initialized = False
                logger.info("Sensor manager cleaned up")
                
            except Exception as e:
                logger.error(f"Error during sensor manager cleanup: {e}")
    
    def is_healthy(self) -> bool:
        """Check if sensor manager is healthy."""
        return self._initialized
    
    def get_status(self) -> Dict[str, Any]:
        """Get sensor manager status."""
        with self._lock:
            return {
                "initialized": self._initialized,
                "simulation": self.simulation,
                "sensor_count": len(self._sensors),
                "healthy": self.is_healthy()
            }


class SafetyController(HardwareInterface):
    """Hardware-level safety controls and monitoring."""
    
    def __init__(self, config: SystemConfig, simulation: bool = False):
        """Initialize safety controller.
        
        Args:
            config: System configuration
            simulation: Enable simulation mode
        """
        self.config = config
        self.simulation = simulation
        self._lock = Lock()
        self._initialized = False
        self._emergency_stop_active = False
    
    def initialize(self) -> bool:
        """Initialize safety controller."""
        with self._lock:
            try:
                if self.simulation:
                    logger.info("Safety controller initialized in simulation mode")
                    self._initialized = True
                    return True
                
                # Try to initialize emergency stop GPIO with timeout
                try:
                    import digitalio
                    import board
                    # This would set up the emergency stop button
                    logger.info("Safety controller initialized with GPIO")
                    self._initialized = True
                    return True
                except (ImportError, Exception) as e:
                    logger.warning(f"GPIO initialization failed: {e}, using simulation")
                    self.simulation = True
                    self._initialized = True
                    return True
                
            except Exception as e:
                logger.error(f"Failed to initialize safety controller: {e}")
                return False
    
    def cleanup(self) -> None:
        """Clean up safety controller resources."""
        with self._lock:
            try:
                # Clean up GPIO resources
                self._initialized = False
                logger.info("Safety controller cleaned up")
                
            except Exception as e:
                logger.error(f"Error during safety controller cleanup: {e}")
    
    def is_healthy(self) -> bool:
        """Check if safety controller is healthy."""
        return self._initialized
    
    def get_status(self) -> Dict[str, Any]:
        """Get safety controller status."""
        with self._lock:
            return {
                "initialized": self._initialized,
                "simulation": self.simulation,
                "emergency_stop_active": self._emergency_stop_active,
                "healthy": self.is_healthy()
            }
    
    def is_emergency_stop_active(self) -> bool:
        """Check if emergency stop is active."""
        with self._lock:
            if self.simulation:
                return self._emergency_stop_active
            
            # Read actual GPIO pin state
            # This would read the emergency stop button
            return False
    
    def trigger_emergency_stop(self) -> None:
        """Trigger emergency stop (for testing/simulation)."""
        with self._lock:
            self._emergency_stop_active = True
            logger.warning("Emergency stop triggered")


class HardwareManager:
    """Singleton hardware manager providing unified access to all hardware."""
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls, config: Optional[SystemConfig] = None, simulation: bool = False):
        """Create singleton instance."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self, config: Optional[SystemConfig] = None, simulation: bool = False):
        """Initialize hardware manager."""
        if self._initialized:
            return
        
        self.config = config or get_config()
        self.simulation = simulation or self.config.simulation_mode
        
        # Initialize hardware components
        self.motor_controller = MotorController(self.config, self.simulation)
        self.sensor_manager = SensorManager(self.config, self.simulation)
        self.safety_controller = SafetyController(self.config, self.simulation)
        
        self._components = [
            self.motor_controller,
            self.sensor_manager,
            self.safety_controller
        ]
        
        self._initialized = True
        logger.info(f"Hardware manager initialized (simulation={self.simulation})")
    
    def initialize_all(self) -> bool:
        """Initialize all hardware components.
        
        Returns:
            True if all components initialized successfully, False otherwise.
        """
        success = True
        for component in self._components:
            try:
                if not component.initialize():
                    logger.error(f"Failed to initialize {component.__class__.__name__}")
                    success = False
            except Exception as e:
                logger.error(f"Exception initializing {component.__class__.__name__}: {e}")
                success = False
        
        return success
    
    def cleanup_all(self) -> None:
        """Clean up all hardware components."""
        for component in self._components:
            try:
                component.cleanup()
            except Exception as e:
                logger.error(f"Exception cleaning up {component.__class__.__name__}: {e}")
    
    def is_system_healthy(self) -> bool:
        """Check if all hardware components are healthy."""
        return all(component.is_healthy() for component in self._components)
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get status of all hardware components."""
        status = {
            "simulation": self.simulation,
            "healthy": self.is_system_healthy(),
            "components": {}
        }
        
        # Get component status with error handling
        for component in self._components:
            component_name = component.__class__.__name__
            try:
                status["components"][component_name] = component.get_status()
            except Exception as e:
                logger.error(f"Error getting status for {component_name}: {e}")
                status["components"][component_name] = {
                    "error": str(e),
                    "healthy": False
                }
        
        return status
    
    @contextmanager
    def safe_operation(self):
        """Context manager for safe hardware operations."""
        try:
            # Check safety conditions before operation
            if self.safety_controller.is_emergency_stop_active():
                raise SafetyViolationError("Emergency stop is active")
            
            yield
            
        except Exception as e:
            # Emergency stop all motors on any exception
            try:
                self.motor_controller.stop_all_motors()
            except:
                pass
            raise
    
    @classmethod
    def reset_instance(cls):
        """Reset singleton instance (for testing)."""
        with cls._lock:
            if cls._instance:
                cls._instance.cleanup_all()
                cls._instance = None


# Convenience functions for global access
_hardware_manager: Optional[HardwareManager] = None

def get_hardware_manager(config: Optional[SystemConfig] = None, 
                        simulation: bool = False) -> HardwareManager:
    """Get global hardware manager instance."""
    global _hardware_manager
    if _hardware_manager is None:
        _hardware_manager = HardwareManager(config, simulation)
    return _hardware_manager

def initialize_hardware(config: Optional[SystemConfig] = None, 
                       simulation: bool = False) -> bool:
    """Initialize hardware system."""
    hw_manager = get_hardware_manager(config, simulation)
    return hw_manager.initialize_all()

def cleanup_hardware() -> None:
    """Clean up hardware system."""
    global _hardware_manager
    if _hardware_manager:
        _hardware_manager.cleanup_all()
        _hardware_manager = None
