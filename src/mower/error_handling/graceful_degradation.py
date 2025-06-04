#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Graceful degradation module for the autonomous mower.

This module provides functionality to handle component failures gracefully,
allowing the mower to continue operating with reduced functionality when
certain components fail. It implements fallback mechanisms and degraded
operation modes to ensure the mower remains operational even in the face
of hardware or software failures.

Key features:
- Component failure detection
- Fallback mechanisms for critical components
- Degraded operation modes
- Automatic recovery attempts
- Failure notification
- Logging of degradation events

Example usage:
    # Initialize the graceful degradation handler
    degradation_handler = GracefulDegradationHandler()

    # Register components with fallback options
    degradation_handler.register_component("gps", primary_gps, fallback_gps)

    # Use components with graceful degradation
    position = degradation_handler.use_component("gps", lambda gps: gps.get_position())
"""

import functools
import time
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from mower.utilities.logger_config import LoggerConfigInfo

# Configure logging
logger = LoggerConfigInfo.get_logger(__name__)


class ComponentStatus(Enum):
    """Status of a component in the graceful degradation system."""

    NORMAL = auto()  # Component is functioning normally
    DEGRADED = auto()  # Component is functioning in a degraded state
    FAILED = auto()  # Component has failed and no fallback is available


class DegradationLevel(Enum):
    """Level of degradation for the mower system."""

    NONE = auto()  # No degradation, all systems normal
    MINOR = auto()  # Minor degradation, non-critical systems affected
    MODERATE = auto()  # Moderate degradation, some critical systems affected
    SEVERE = auto()  # Severe degradation, multiple critical systems affected
    CRITICAL = auto()  # Critical degradation, mower should stop operations


class ComponentInfo:
    """Information about a component in the graceful degradation system."""

    def __init__(
        self,
        name: str,
        primary: Any,
        fallbacks: List[Any] = None,
        is_critical: bool = False,
        recovery_attempts: int = 3,
        recovery_interval: int = 60,
    ):
        """
        Initialize component information.

        Args:
            name: Name of the component.
            primary: Primary implementation of the component.
            fallbacks: List of fallback implementations, in order of preference.
            is_critical: Whether the component is critical for mower operation.
            recovery_attempts: Number of recovery attempts before giving up.
            recovery_interval: Interval between recovery attempts in seconds.
        """
        self.name = name
        self.primary = primary
        self.fallbacks = fallbacks or []
        self.is_critical = is_critical
        self.recovery_attempts = recovery_attempts
        self.recovery_interval = recovery_interval

        self.status = ComponentStatus.NORMAL
        self.active_implementation = primary
        self.failure_count = 0
        self.last_failure_time = 0
        self.last_recovery_attempt = 0
        self.current_fallback_index = -1  # -1 means using primary


class GracefulDegradationHandler:
    """
    Handler for graceful degradation of the autonomous mower.

    This class provides methods to handle component failures gracefully,
    allowing the mower to continue operating with reduced functionality when
    certain components fail.
    """

    def __init__(self):
        """Initialize the graceful degradation handler."""
        self.components: Dict[str, ComponentInfo] = {}
        self.degradation_level = DegradationLevel.NONE
        self.degradation_callbacks: List[Callable[[DegradationLevel], None]] = []

    def register_component(
        self,
        name: str,
        primary: Any,
        fallbacks: List[Any] = None,
        is_critical: bool = False,
        recovery_attempts: int = 3,
        recovery_interval: int = 60,
    ) -> None:
        """
        Register a component with the graceful degradation handler.

        Args:
            name: Name of the component.
            primary: Primary implementation of the component.
            fallbacks: List of fallback implementations, in order of preference.
            is_critical: Whether the component is critical for mower operation.
            recovery_attempts: Number of recovery attempts before giving up.
            recovery_interval: Interval between recovery attempts in seconds.
        """
        self.components[name] = ComponentInfo(
            name=name,
            primary=primary,
            fallbacks=fallbacks,
            is_critical=is_critical,
            recovery_attempts=recovery_attempts,
            recovery_interval=recovery_interval,
        )
        logger.info((f"Registered component '{name}' with {len(fallbacks) if fallbacks else 0} fallbacks"))

    def register_degradation_callback(self, callback: Callable[[DegradationLevel], None]) -> None:
        """
        Register a callback to be called when the degradation level changes.

        Args:
            callback: Function to call with the new degradation level.
        """
        self.degradation_callbacks.append(callback)

    def use_component(self, name: str, operation: Callable[[Any], Any], *args, **kwargs) -> Any:
        """
        Use a component with graceful degradation.

        This method attempts to use the primary implementation of the component.
        If it fails, it falls back to alternative implementations if available.

        Args:
            name: Name of the component.
            operation: Function to call with the component implementation.
            *args: Additional positional arguments to pass to the operation.
            **kwargs: Additional keyword arguments to pass to the operation.

        Returns:
            Result of the operation, or None if all implementations fail.

        Raises:
            KeyError: If the component is not registered.
            RuntimeError: If the component is critical and all implementations fail.
        """
        if name not in self.components:
            raise KeyError(f"Component '{name}' not registered")

        component = self.components[name]

        # Try to use the active implementation
        try:
            result = operation(component.active_implementation, *args, **kwargs)

            # If we were using a fallback and the operation succeeded,
            # try to recover the primary implementation
            if component.current_fallback_index >= 0:
                self._attempt_recovery(component)

            return result

        except Exception as e:
            logger.warning(f"Operation on component '{name}' failed: {e}")

            # Record the failure
            component.failure_count += 1
            component.last_failure_time = time.time()

            # Try fallbacks
            return self._try_fallbacks(component, operation, *args, **kwargs)

    def _try_fallbacks(
        self,
        component: ComponentInfo,
        operation: Callable[[Any], Any],
        *args,
        **kwargs,
    ) -> Any:
        """
        Try fallback implementations for a component.

        Args:
            component: Component information.
            operation: Function to call with the component implementation.
            *args: Additional positional arguments to pass to the operation.
            **kwargs: Additional keyword arguments to pass to the operation.

        Returns:
            Result of the operation, or None if all implementations fail.

        Raises:
            RuntimeError: If the component is critical and all implementations fail.
        """
        # Start with the next fallback after the current one
        start_index = component.current_fallback_index + 1

        # Try each fallback
        for i in range(start_index, len(component.fallbacks)):
            fallback = component.fallbacks[i]
            try:
                result = operation(fallback, *args, **kwargs)

                # Update component status and active implementation
                component.status = ComponentStatus.DEGRADED
                component.active_implementation = fallback
                component.current_fallback_index = i

                logger.info((f"Component '{component.name}' degraded to" f" fallback {i+1}/{len(component.fallbacks)}"))

                # Update overall degradation level
                self._update_degradation_level()

                return result

            except Exception as e:
                logger.warning(
                    (f"Fallback {i+1}/{len(component.fallbacks)} for" f" component '{component.name}' failed: {e}")
                )

        # All fallbacks failed
        component.status = ComponentStatus.FAILED
        logger.error(f"All implementations of component '{component.name}' failed")

        # Update overall degradation level
        self._update_degradation_level()

        # If the component is critical, raise an exception
        if component.is_critical:
            raise RuntimeError((f"Critical component '{component.name}' failed with" f" no working fallbacks"))

        return None

    def _attempt_recovery(self, component: ComponentInfo) -> bool:
        """
        Attempt to recover the primary implementation of a component.

        Args:
            component: Component information.

        Returns:
            bool: True if recovery was successful, False otherwise.
        """
        # Check if we've exceeded the recovery attempts
        if component.recovery_attempts <= 0:
            return False

        # Check if enough time has passed since the last recovery attempt
        current_time = time.time()
        if current_time - component.last_recovery_attempt < component.recovery_interval:
            return False

        component.last_recovery_attempt = current_time

        # Try to use the primary implementation
        try:
            # This is a simple test to see if the primary implementation is working
            # In a real implementation, you would need a more specific test
            if hasattr(component.primary, "is_available") and callable(component.primary.is_available):
                if not component.primary.is_available():
                    return False

            # Update component status and active implementation
            component.status = ComponentStatus.NORMAL
            component.active_implementation = component.primary
            component.current_fallback_index = -1

            logger.info(f"Component '{component.name}' recovered to primary implementation")

            # Update overall degradation level
            self._update_degradation_level()

            return True

        except Exception as e:
            logger.warning(f"Recovery attempt for component '{component.name}' failed: {e}")
            return False

    def _update_degradation_level(self) -> None:
        """
        Update the overall degradation level based on component statuses.

        This method calculates the overall degradation level based on the
        status of all registered components, with emphasis on critical components.
        """
        # Count components in each status
        normal_count = 0
        degraded_count = 0
        failed_count = 0
        critical_degraded_count = 0
        critical_failed_count = 0

        for component in self.components.values():
            if component.status == ComponentStatus.NORMAL:
                normal_count += 1
            elif component.status == ComponentStatus.DEGRADED:
                degraded_count += 1
                if component.is_critical:
                    critical_degraded_count += 1
            elif component.status == ComponentStatus.FAILED:
                failed_count += 1
                if component.is_critical:
                    critical_failed_count += 1

        # Determine degradation level
        old_level = self.degradation_level

        if critical_failed_count > 0:
            # Any critical component failure is a critical degradation
            self.degradation_level = DegradationLevel.CRITICAL
        elif critical_degraded_count > 1:
            # Multiple critical components degraded is severe
            self.degradation_level = DegradationLevel.SEVERE
        elif critical_degraded_count == 1:
            # One critical component degraded is moderate
            self.degradation_level = DegradationLevel.MODERATE
        elif failed_count > 0 or degraded_count > 2:
            # Non-critical failures or multiple degraded components is minor
            self.degradation_level = DegradationLevel.MINOR
        else:
            # Everything else is normal
            self.degradation_level = DegradationLevel.NONE

        # If the degradation level changed, log it and call callbacks
        if self.degradation_level != old_level:
            logger.info((f"Degradation level changed from {old_level.name} to" f" {self.degradation_level.name}"))

            for callback in self.degradation_callbacks:
                try:
                    callback(self.degradation_level)
                except Exception as e:
                    logger.error(f"Error in degradation callback: {e}")

    def get_component_status(self, name: str) -> ComponentStatus:
        """
        Get the status of a component.

        Args:
            name: Name of the component.

        Returns:
            ComponentStatus: Status of the component.

        Raises:
            KeyError: If the component is not registered.
        """
        if name not in self.components:
            raise KeyError(f"Component '{name}' not registered")

        return self.components[name].status

    def get_degradation_level(self) -> DegradationLevel:
        """
        Get the overall degradation level.

        Returns:
            DegradationLevel: Overall degradation level.
        """
        return self.degradation_level

    def get_status_report(self) -> Dict[str, Any]:
        """
        Get a status report of all components.

        Returns:
            Dict[str, Any]: Status report with component statuses and overall degradation level.
        """
        report = {
            "degradation_level": self.degradation_level.name,
            "components": {},
        }

        for name, component in self.components.items():
            report["components"][name] = {
                "status": component.status.name,
                "is_critical": component.is_critical,
                "failure_count": component.failure_count,
                "using_fallback": component.current_fallback_index >= 0,
                "fallback_index": (component.current_fallback_index if component.current_fallback_index >= 0 else None),
                "fallback_count": len(component.fallbacks),
            }

        return report


# Decorator for graceful degradation
def with_graceful_degradation(handler: GracefulDegradationHandler, component_name: str):
    """
    Decorator for methods that should use graceful degradation.

    This decorator wraps a method to use the graceful degradation handler.

    Args:
        handler: Graceful degradation handler.
        component_name: Name of the component to use.

    Returns:
        Decorated method.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # The operation to perform on the component
            def operation(component, *operation_args, **operation_kwargs):
                # Replace self.component with the provided component
                original_component = getattr(self, component_name, None)
                setattr(self, component_name, component)

                try:
                    # Call the original method
                    return func(self, *operation_args, **operation_kwargs)
                finally:
                    # Restore the original component
                    setattr(self, component_name, original_component)

            # Use the component with graceful degradation
            return handler.use_component(component_name, operation, *args, **kwargs)

        return wrapper

    return decorator


# Example usage
if __name__ == "__main__":
    # This is just an example and won't be executed when the module is imported
    class GPSSensor:
        def __init__(self, name):
            self.name = name
            self.available = True

        def get_position(self):
            if not self.available:
                raise RuntimeError(f"GPS sensor {self.name} is not available")
            return {"latitude": 37.7749, "longitude": -122.4194}

        def is_available(self):
            return self.available

    # Create primary and fallback GPS sensors
    primary_gps = GPSSensor("Primary")
    fallback_gps1 = GPSSensor("Fallback 1")
    fallback_gps2 = GPSSensor("Fallback 2")

    # Create graceful degradation handler
    handler = GracefulDegradationHandler()

    # Register GPS component with fallbacks
    handler.register_component(
        name="gps",
        primary=primary_gps,
        fallbacks=[fallback_gps1, fallback_gps2],
        is_critical=True,
    )

    # Use GPS component
    try:
        # This should use the primary GPS
        position = handler.use_component("gps", lambda gps: gps.get_position())
        print(f"Position from primary GPS: {position}")

        # Simulate primary GPS failure
        primary_gps.available = False

        # This should use the first fallback
        position = handler.use_component("gps", lambda gps: gps.get_position())
        print(f"Position from fallback GPS: {position}")

        # Simulate first fallback failure
        fallback_gps1.available = False

        # This should use the second fallback
        position = handler.use_component("gps", lambda gps: gps.get_position())
        print(f"Position from second fallback GPS: {position}")

        # Simulate all GPS failures
        fallback_gps2.available = False

        # This should raise an exception
        position = handler.use_component("gps", lambda gps: gps.get_position())
        print(f"Position: {position}")  # This line should not be reached

    except Exception as e:
        print(f"Error: {e}")

    # Print status report
    print("\nStatus Report:")
    report = handler.get_status_report()
    print(f"Degradation Level: {report['degradation_level']}")
    for name, component in report["components"].items():
        print(f"Component '{name}':")
        for key, value in component.items():
            print(f"  {key}: {value}")
