"""
Adapter for the blade controller.

This module provides an adapter for the blade controller that implements
the BladeControllerInterface and wraps the BladeController class, mapping
the interface methods to the methods expected by the business logic.
"""

from typing import Dict, Any

from mower.hardware.blade_controller import BladeController
from mower.interfaces.hardware import BladeControllerInterface
from mower.utilities.logger_config import LoggerConfigInfo

# Initialize logger
logger = LoggerConfigInfo.get_logger(__name__)


class BladeControllerAdapter(BladeControllerInterface):
    """
    Adapter for the blade controller.

    This class implements the BladeControllerInterface and wraps the
    BladeController class, mapping the interface methods to the methods
    expected by the business logic.
    """

    def __init__(self, blade_controller: BladeController = None):
        """
        Initialize the blade controller adapter.

        Args:
            blade_controller: The blade controller to wrap, or None to create a new one
        """
        self._blade_controller = blade_controller or BladeController()
        logger.info("BladeControllerAdapter initialized")

    def enable(self) -> bool:
        """
        Enable the blade motor.

        This method is called by the business logic as start_blade().

        Returns:
            bool: True if successful, False otherwise
        """
        logger.debug("BladeControllerAdapter.enable() called")
        return self._blade_controller.enable()

    def disable(self) -> bool:
        """
        Disable the blade motor.

        This method is called by the business logic as stop_blade().

        Returns:
            bool: True if successful, False otherwise
        """
        logger.debug("BladeControllerAdapter.disable() called")
        return self._blade_controller.disable()

    def set_speed(self, speed: float) -> bool:
        """
        Set the blade motor speed.

        Args:
            speed: Speed value between 0.0 (stopped) and 1.0 (full speed).

        Returns:
            bool: True if successful, False otherwise.
        """
        logger.debug(f"BladeControllerAdapter.set_speed({speed}) called")
        return self._blade_controller.set_speed(speed)

    def is_enabled(self) -> bool:
        """
        Check if the blade motor is enabled.

        This method is called by the business logic as is_running().

        Returns:
            bool: True if enabled, False otherwise
        """
        logger.debug("BladeControllerAdapter.is_enabled() called")
        return self._blade_controller.is_enabled()

    def cleanup(self) -> None:
        """Clean up resources used by the blade controller."""
        logger.debug("BladeControllerAdapter.cleanup() called")
        self._blade_controller.cleanup()

    def get_state(self) -> Dict[str, Any]:
        """
        Get the current state of the blade controller.

        Returns:
            Dict[str, Any]: Dictionary containing state information
        """
        logger.debug("BladeControllerAdapter.get_state() called")
        return self._blade_controller.get_state()

    # Additional methods to provide compatibility with existing code

    def start_blade(self) -> bool:
        """
        Start the blade motor.

        This is an alias for enable() to maintain compatibility with existing code.

        Returns:
            bool: True if successful, False otherwise
        """
        logger.debug("BladeControllerAdapter.start_blade() called")
        return self.enable()

    def stop_blade(self) -> bool:
        """
        Stop the blade motor.

        This is an alias for disable() to maintain compatibility with existing code.

        Returns:
            bool: True if successful, False otherwise
        """
        logger.debug("BladeControllerAdapter.stop_blade() called")
        return self.disable()

    def is_running(self) -> bool:
        """
        Check if the blade motor is running.

        This is an alias for is_enabled() to maintain compatibility with existing code.

        Returns:
            bool: True if running, False otherwise
        """
        logger.debug("BladeControllerAdapter.is_running() called")
        return self.is_enabled()
