"""
Simulated blade controller.

This module provides a simulated version of the BladeController class that interacts
with the virtual world model to provide realistic blade control behavior without
requiring physical hardware.
"""

import time
import threading
from typing import Dict, Any, Optional, List, Tuple, Union, Type

from mower.simulation.hardware_sim import SimulatedActuator
from mower.simulation.world_model import get_world_instance, Vector2D
from mower.utilities.logger_config import LoggerConfigInfo as LoggerConfig

# Configure logging
logger = LoggerConfig.get_logger(__name__)


class SimulatedBladeController(SimulatedActuator):
    """
    Simulated BladeController.
    
    This class provides a simulated version of the BladeController class that interacts
    with the virtual world model to provide realistic blade control behavior without
    requiring physical hardware.
    """
    
    def __init__(self):
        """Initialize the simulated blade controller."""
        super().__init__("Blade Controller")
        
        # Initialize actuator state
        self.state = {
            "enabled": False,
            "speed": 0.0,  # 0.0 to 1.0
            "in1_pin": 24,  # Same as real controller for compatibility
            "in2_pin": 25   # Same as real controller for compatibility
        }
        
        # Initialize actuator parameters
        self.response_time = 0.5  # 500ms response time (blade motor is slower than drive motors)
        
        # Get the virtual world instance
        self.world = get_world_instance()
    
    def _initialize_sim(self, *args, **kwargs) -> None:
        """Initialize the simulated blade controller."""
        # Nothing special to initialize for the simulated blade controller
        pass
    
    def _cleanup_sim(self) -> None:
        """Clean up the simulated blade controller."""
        # Disable the blade
        self.disable()
    
    def _update_actuator_state(self, key: str, value: Any) -> None:
        """
        Update the state of the simulated blade controller.
        
        Args:
            key: The key for the value that was set
            value: The value that was set
        """
        # Update the state
        self.state[key] = value
        
        # If the key is enabled or speed, update the robot's blade state
        if key in ["enabled", "speed"]:
            self.world.set_robot_blade_state(
                self.state["enabled"],
                self.state["speed"]
            )
    
    # BladeController interface methods
    
    def enable(self) -> bool:
        """
        Enable the blade motor.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.state["enabled"]:
                self.set_value("enabled", True)
                logger.info("Blade motor enabled")
            return True
        except Exception as e:
            logger.error(f"Error enabling blade motor: {e}")
            return False
    
    def disable(self) -> bool:
        """
        Disable the blade motor.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if self.state["enabled"]:
                self.set_value("enabled", False)
                self.set_value("speed", 0.0)
                logger.info("Blade motor disabled")
            return True
        except Exception as e:
            logger.error(f"Error disabling blade motor: {e}")
            return False
    
    def set_speed(self, speed: float) -> bool:
        """
        Set the blade motor speed.
        
        Args:
            speed: Speed value between 0.0 (stopped) and 1.0 (full speed).
        
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            if not (0.0 <= speed <= 1.0):
                logger.error(f"Invalid speed value: {speed}")
                return False
            
            self.set_value("speed", speed)
            logger.info(f"Blade motor speed set to {speed}")
            return True
        except Exception as e:
            logger.error(f"Error setting blade motor speed: {e}")
            return False
    
    def is_enabled(self) -> bool:
        """
        Check if the blade motor is enabled.
        
        Returns:
            bool: True if enabled, False otherwise
        """
        return self.state["enabled"]
    
    def is_running(self) -> bool:
        """
        Check if the blade motor is running.
        
        Returns:
            bool: True if running, False otherwise
        """
        return self.state["enabled"] and self.state["speed"] > 0.0
    
    def start_blade(self) -> bool:
        """
        Start the blade motor.
        
        Returns:
            bool: True if successful, False otherwise
        """
        if self.enable():
            return self.set_speed(1.0)
        return False
    
    def stop_blade(self) -> bool:
        """
        Stop the blade motor.
        
        Returns:
            bool: True if successful, False otherwise
        """
        return self.disable()
    
    def cleanup(self) -> None:
        """Clean up resources."""
        try:
            self.disable()
            super().cleanup()
            logger.info("Blade controller cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up blade controller: {e}")
    
    def get_state(self) -> Dict[str, Any]:
        """
        Get the current state of the blade controller.
        
        Returns:
            Dict[str, Any]: Dictionary containing state information
        """
        return self.state.copy()


class SimulatedBladeControllerAdapter:
    """
    Adapter for SimulatedBladeController to match the BladeControllerAdapter interface.
    
    This class provides an adapter for the SimulatedBladeController class to match
    the interface of the BladeControllerAdapter class used in the real system.
    """
    
    def __init__(self, blade_controller: Optional[SimulatedBladeController] = None):
        """
        Initialize the simulated blade controller adapter.
        
        Args:
            blade_controller: Optional SimulatedBladeController instance to use
        """
        self.blade_controller = blade_controller or SimulatedBladeController()
    
    def start_blade(self) -> bool:
        """
        Start the blade motor.
        
        Returns:
            bool: True if successful, False otherwise
        """
        return self.blade_controller.start_blade()
    
    def stop_blade(self) -> bool:
        """
        Stop the blade motor.
        
        Returns:
            bool: True if successful, False otherwise
        """
        return self.blade_controller.stop_blade()
    
    def is_running(self) -> bool:
        """
        Check if the blade motor is running.
        
        Returns:
            bool: True if running, False otherwise
        """
        return self.blade_controller.is_running()
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self.blade_controller.cleanup()