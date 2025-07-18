"""
Hardware Registry Module for Autonomous Mower.

This module provides centralized hardware component management and access.
It implements a singleton pattern to ensure consistent hardware access across
the application and prevents circular dependencies.

@hardware_interface: Manages GPIO, I2C, UART, and other hardware resources
@gpio_pin_usage: Various pins for sensors, motors, and controllers
@i2c_address: Multiple I2C devices on bus 1

Architecture:
    - Singleton pattern for global hardware access
    - Lazy initialization of hardware components
    - Resource cleanup and lifecycle management
    - Graceful degradation for optional hardware

Usage:
    from mower.hardware.hardware_registry import get_hardware_registry
    registry = get_hardware_registry()
    camera = registry.get_camera()
"""

import os
import threading
import time
from typing import Any, Dict, Optional

from mower.utilities.logger_config import LoggerConfigInfo


class HardwareRegistry:
    """
    Centralized hardware component registry with singleton pattern.
    
    This class manages the lifecycle of all hardware components and provides
    a unified interface for accessing them. It handles initialization,
    cleanup, and resource management to prevent conflicts.
    """
    
    _instance: Optional['HardwareRegistry'] = None
    _lock: threading.Lock = threading.Lock()
    
    def __init__(self) -> None:
        """Initialize the hardware registry."""
        if HardwareRegistry._instance is not None:
            raise RuntimeError("Use get_hardware_registry() to get the singleton instance")
            
        self.logger = LoggerConfigInfo.get_logger(__name__)
        self._components: Dict[str, Any] = {}
        self._initialized: bool = False
        self._component_lock: threading.Lock = threading.Lock()
        
        # Configuration
        self.simulate: bool = os.environ.get("USE_SIMULATION", "false").lower() in ("true", "1", "yes")
        
    @classmethod
    def get_instance(cls) -> 'HardwareRegistry':
        """Get singleton instance of hardware registry."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def initialize(self) -> bool:
        """
        Initialize all hardware components.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        with self._component_lock:
            if self._initialized:
                return True
                
            self.logger.info("Initializing hardware registry...")
            
            try:
                # Initialize hardware components in proper order
                self._initialize_core_hardware()
                self._initialize_sensors()
                self._initialize_actuators()
                
                self._initialized = True
                self.logger.info("Hardware registry initialization complete")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to initialize hardware registry: {e}", exc_info=True)
                self._initialized = False
                return False
    
    def _initialize_core_hardware(self) -> None:
        """Initialize core hardware components (GPIO, I2C, Serial)."""
        try:
            # Initialize serial port manager
            from mower.hardware.serial_port import SerialPort
            self._components["serial_port"] = SerialPort()
            self.logger.info("Serial port manager initialized")
            
        except Exception as e:
            self.logger.warning(f"Failed to initialize serial port: {e}")
            self._components["serial_port"] = None
    
    def _initialize_sensors(self) -> None:
        """Initialize sensor components."""
        try:
            # Initialize camera
            from mower.hardware.camera_instance import get_camera_instance
            self._components["camera"] = get_camera_instance()
            self.logger.info("Camera initialized")
            
        except Exception as e:
            self.logger.warning(f"Failed to initialize camera: {e}")
            self._components["camera"] = None
            
        # Initialize sensor interface will be added when available
        self._components["sensor_interface"] = None
    
    def _initialize_actuators(self) -> None:
        """Initialize actuator components (motors, blade controller)."""
        try:
            # Initialize RoboHAT motor controller
            if not self.simulate:
                from mower.hardware.robohat import RoboHATDriver
                robohat_port = os.environ.get("MM1_SERIAL_PORT", "/dev/ttyACM1")
                self._components["robohat"] = RoboHATDriver(port=robohat_port)
                self.logger.info(f"RoboHAT motor controller initialized on {robohat_port}")
            else:
                self.logger.info("RoboHAT simulation mode enabled")
                self._components["robohat"] = None
                
        except Exception as e:
            self.logger.warning(f"Failed to initialize RoboHAT: {e}")
            self._components["robohat"] = None
            
        try:
            # Initialize blade controller
            from mower.hardware.blade_controller import BladeController
            self._components["blade_controller"] = BladeController()
            self.logger.info("Blade controller initialized")
            
        except Exception as e:
            self.logger.warning(f"Failed to initialize blade controller: {e}")
            self._components["blade_controller"] = None
    
    def get_camera(self) -> Optional[Any]:
        """Get camera instance."""
        self._ensure_initialized()
        return self._components.get("camera")
    
    def get_robohat(self) -> Optional[Any]:
        """Get RoboHAT motor controller instance."""
        self._ensure_initialized()
        return self._components.get("robohat")
        
    def get_robohat_driver(self) -> Optional[Any]:
        """Get RoboHAT driver instance (alias for get_robohat)."""
        return self.get_robohat()
    
    def get_blade_controller(self) -> Optional[Any]:
        """Get blade controller instance."""
        self._ensure_initialized()
        return self._components.get("blade_controller")
    
    def get_serial_port(self) -> Optional[Any]:
        """Get serial port manager instance."""
        self._ensure_initialized()
        return self._components.get("serial_port")
        
    def get_serial_line_reader(self) -> Optional[Any]:
        """Get serial line reader instance."""
        serial_port = self.get_serial_port()
        if serial_port:
            return getattr(serial_port, 'line_reader', None)
        return None
    
    def get_sensor_interface(self) -> Optional[Any]:
        """Get sensor interface instance."""
        self._ensure_initialized()
        return self._components.get("sensor_interface")
    
    def get_ina3221(self) -> Optional[Any]:
        """Get INA3221 power sensor instance."""
        self._ensure_initialized()
        return self._components.get("ina3221")
    
    def get_component(self, name: str) -> Optional[Any]:
        """
        Get any hardware component by name.
        
        Args:
            name: Component name
            
        Returns:
            Hardware component instance or None if not found
        """
        self._ensure_initialized()
        return self._components.get(name)
    
    def _ensure_initialized(self) -> None:
        """Ensure hardware registry is initialized."""
        if not self._initialized:
            self.initialize()
    
    def cleanup(self) -> None:
        """Cleanup all hardware components."""
        self.logger.info("Cleaning up hardware registry...")
        
        with self._component_lock:
            # Cleanup components in reverse order
            for name, component in reversed(list(self._components.items())):
                try:
                    if component and hasattr(component, 'cleanup'):
                        component.cleanup()
                        self.logger.debug(f"Cleaned up {name}")
                except Exception as e:
                    self.logger.warning(f"Error cleaning up {name}: {e}")
            
            self._components.clear()
            self._initialized = False
            
        self.logger.info("Hardware registry cleanup complete")
    
    def is_initialized(self) -> bool:
        """Check if hardware registry is initialized."""
        return self._initialized
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get status of all hardware components.
        
        Returns:
            Dictionary with component status information
        """
        status = {
            "initialized": self._initialized,
            "simulate": self.simulate,
            "components": {}
        }
        
        for name, component in self._components.items():
            status["components"][name] = {
                "available": component is not None,
                "type": type(component).__name__ if component else None
            }
            
        return status


def get_hardware_registry() -> HardwareRegistry:
    """
    Get the singleton hardware registry instance.
    
    Returns:
        HardwareRegistry: The singleton hardware registry instance
    """
    return HardwareRegistry.get_instance()
