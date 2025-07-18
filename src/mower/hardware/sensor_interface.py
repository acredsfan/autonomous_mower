"""
Sensor Interface Module - Compatibility layer for async sensor management.

This module provides a compatibility interface for modules that expect the
traditional sensor_interface.py. It delegates to the AsyncSensorManager for
actual sensor data collection.

This resolves circular dependencies by providing a clean interface layer.
"""

from typing import Any, Dict, Optional
from mower.hardware.async_sensor_manager import AsyncSensorInterface


class EnhancedSensorInterface:
    """
    Enhanced sensor interface with compatibility for legacy code.
    
    This class provides backward compatibility for modules expecting
    the EnhancedSensorInterface while delegating to AsyncSensorManager.
    """
    
    def __init__(self, simulate: bool = False):
        """Initialize the enhanced sensor interface."""
        self._async_interface = AsyncSensorInterface(simulate=simulate)
        self._started = False
    
    def start(self) -> None:
        """Start the sensor interface."""
        if not self._started:
            self._async_interface.start()
            self._started = True
    
    def stop(self) -> None:
        """Stop the sensor interface."""
        if self._started:
            self._async_interface.stop()
            self._started = False
    
    def get_sensor_data(self) -> Dict[str, Any]:
        """Get sensor data from all sensors."""
        if not self._started:
            self.start()
        return self._async_interface.get_sensor_data()
    
    def is_healthy(self) -> bool:
        """Check if sensor interface is healthy."""
        return self._started and self._async_interface._running
    
    def cleanup(self) -> None:
        """Clean up sensor interface resources."""
        self.stop()


# Legacy compatibility alias
SensorInterface = EnhancedSensorInterface


def get_sensor_interface(simulate: bool = False) -> EnhancedSensorInterface:
    """
    Get a sensor interface instance.
    
    Args:
        simulate: Whether to run in simulation mode
        
    Returns:
        EnhancedSensorInterface instance
    """
    return EnhancedSensorInterface(simulate=simulate)


# Global singleton for modules that expect it
_global_sensor_interface: Optional[EnhancedSensorInterface] = None


def get_global_sensor_interface(simulate: bool = False) -> EnhancedSensorInterface:
    """
    Get the global sensor interface singleton.
    
    Args:
        simulate: Whether to run in simulation mode
        
    Returns:
        Global EnhancedSensorInterface instance
    """
    global _global_sensor_interface
    if _global_sensor_interface is None:
        _global_sensor_interface = EnhancedSensorInterface(simulate=simulate)
    return _global_sensor_interface
