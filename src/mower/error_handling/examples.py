"""
Examples of using the error handling system.

This module provides examples of how to use the error handling system
in various scenarios. These examples can be used as templates for
implementing consistent error handling patterns throughout the codebase.
"""

import logging
import time
from typing import Dict, Any, Optional, List

from mower.error_handling import (
    MowerError,
    HardwareError,
    NavigationError,
    ErrorCode,
    report_error,
    with_error_handling,
    error_context,
    safe_call,
    get_error_reporter,
)


# Example 1: Basic error handling
def example_basic_error_handling():
    """Example of basic error handling."""
    try:
        # Some code that might raise an exception
        result = 1 / 0  # This will raise a ZeroDivisionError
    except Exception as e:
        # Convert to a MowerError with an appropriate error code
        error = MowerError.from_exception(
            e,
            ErrorCode.SOFTWARE_ALGORITHM_ERROR,
            context={"operation": "division"},
        )
        # Report the error
        report_error(error)
        # Handle the error appropriately
        print(f"Error occurred: {error}")


# Example 2: Using decorators
@with_error_handling(error_code=ErrorCode.HARDWARE_SENSOR_FAILURE)
def read_sensor(sensor_id: str) -> float:
    """
    Example of using the with_error_handling decorator.

    Args:
        sensor_id: ID of the sensor to read

    Returns:
        float: Sensor reading
    """
    # Simulate a sensor reading
    if sensor_id == "temperature":
        return 25.0
    elif sensor_id == "humidity":
        return 50.0
    else:
        # This will be caught by the decorator
        raise ValueError(f"Unknown sensor: {sensor_id}")


# Example 3: Using context managers
def example_context_manager():
    """Example of using the error_context context manager."""
    try:
        with error_context(
            error_code=ErrorCode.NAVIGATION_GPS_SIGNAL_LOST,
            context={"source": "example"},
        ):
            # Simulate a GPS error
            raise TimeoutError("GPS timeout")
    except MowerError as e:
        # This will catch the converted error
        print(f"Caught error: {e}")


# Example 4: Safe function calls
def example_safe_call():
    """Example of using the safe_call function."""

    # Define a function that might raise an exception
    def might_fail(x: int) -> int:
        if x == 0:
            raise ValueError("Cannot process zero")
        return 100 // x

    # Call the function safely
    result = safe_call(
        might_fail,
        0,  # This will cause an error
        error_code=ErrorCode.SOFTWARE_ALGORITHM_ERROR,
        default_value=-1,
    )

    print(f"Result: {result}")  # Will print -1


# Example 5: Custom error handlers
def example_custom_error_handler():
    """Example of using custom error handlers."""

    # Define a custom error handler
    def custom_handler(error: MowerError):
        print(f"Custom handler received error: {error}")
        if error.error_code and error.error_code.is_critical:
            print("This is a critical error!")

    # Register the error handler
    reporter = get_error_reporter()
    reporter.register_error_handler("custom", custom_handler)

    # Raise an error that will be handled by the custom handler
    try:
        raise HardwareError(
            "Battery critically low",
            error_code=ErrorCode.HARDWARE_BATTERY_CRITICAL,
        )
    except MowerError as e:
        report_error(e)

    # Unregister the handler when done
    reporter.unregister_error_handler("custom")


# Example 6: Hardware component with error handling
class SensorComponent:
    """Example of a hardware component with error handling."""

    def __init__(self, sensor_id: str):
        """
        Initialize the sensor component.

        Args:
            sensor_id: ID of the sensor
        """
        self.sensor_id = sensor_id
        self.last_reading: Optional[float] = None
        self.error_count = 0
        self.max_errors = 3

    @with_error_handling(error_code=ErrorCode.HARDWARE_SENSOR_FAILURE)
    def initialize(self) -> bool:
        """
        Initialize the sensor.

        Returns:
            bool: True if initialization was successful
        """
        print(f"Initializing sensor {self.sensor_id}")
        # Simulate initialization
        if self.sensor_id == "broken":
            raise HardwareError(
                f"Failed to initialize sensor {self.sensor_id}",
                error_code=ErrorCode.HARDWARE_INITIALIZATION_FAILED,
            )
        return True

    def read(self) -> Optional[float]:
        """
        Read the sensor value.

        Returns:
            Optional[float]: Sensor reading or None if error
        """
        try:
            with error_context(
                error_code=ErrorCode.HARDWARE_SENSOR_FAILURE,
                context={"sensor_id": self.sensor_id},
            ):
                # Simulate reading
                if self.sensor_id == "broken":
                    self.error_count += 1
                    if self.error_count > self.max_errors:
                        raise HardwareError(
                            f"Sensor {self.sensor_id} failed too many times",
                            error_code=ErrorCode.HARDWARE_SENSOR_FAILURE,
                        )
                    raise ValueError("Sensor reading failed")

                # Simulate successful reading
                reading = 25.0 + (time.time() % 10)
                self.last_reading = reading
                return reading
        except MowerError:
            # Already handled by error_context
            return None

    def get_status(self) -> Dict[str, Any]:
        """
        Get the sensor status.

        Returns:
            Dict[str, Any]: Sensor status
        """
        return {
            "sensor_id": self.sensor_id,
            "last_reading": self.last_reading,
            "error_count": self.error_count,
            "status": "error" if self.error_count > 0 else "ok",
        }


# Example 7: Navigation component with error handling
class NavigationComponent:
    """Example of a navigation component with error handling."""

    def __init__(self):
        """Initialize the navigation component."""
        self.position = (0.0, 0.0)
        self.heading = 0.0
        self.waypoints: List[tuple] = []

    @with_error_handling(error_code=ErrorCode.NAVIGATION_GPS_SIGNAL_LOST)
    def get_position(self) -> tuple:
        """
        Get the current position.

        Returns:
            tuple: Current position (lat, lng)
        """
        # Simulate GPS reading
        if time.time() % 30 < 5:  # Simulate occasional GPS loss
            raise NavigationError(
                "GPS signal lost",
                error_code=ErrorCode.NAVIGATION_GPS_SIGNAL_LOST,
            )
        return self.position

    def navigate_to(self, target: tuple) -> bool:
        """
        Navigate to a target position.

        Args:
            target: Target position (lat, lng)

        Returns:
            bool: True if navigation was successful
        """
        try:
            with error_context(
                error_code=ErrorCode.NAVIGATION_PATH_BLOCKED,
                context={"target": target},
            ):
                # Get current position
                current = self.get_position()

                # Calculate path
                self.waypoints = [current, target]

                # Simulate navigation
                if target[0] < 0 or target[1] < 0:
                    raise NavigationError(
                        "Path blocked by obstacle",
                        error_code=ErrorCode.NAVIGATION_PATH_BLOCKED,
                    )

                # Update position
                self.position = target
                return True
        except MowerError as e:
            print(f"Navigation error: {e}")
            return False


# Run the examples
if __name__ == "__main__":
    print("Running error handling examples...")

    print("\nExample 1: Basic error handling")
    example_basic_error_handling()

    print("\nExample 2: Using decorators")
    try:
        temp = read_sensor("temperature")
        print(f"Temperature: {temp}°C")

        # This will raise an error
        unknown = read_sensor("unknown")
    except MowerError as e:
        print(f"Caught error: {e}")

    print("\nExample 3: Using context managers")
    example_context_manager()

    print("\nExample 4: Safe function calls")
    example_safe_call()

    print("\nExample 5: Custom error handlers")
    example_custom_error_handler()

    print("\nExample 6: Hardware component with error handling")
    sensor = SensorComponent("temperature")
    sensor.initialize()
    reading = sensor.read()
    print(f"Sensor reading: {reading}")
    print(f"Sensor status: {sensor.get_status()}")

    broken_sensor = SensorComponent("broken")
    try:
        broken_sensor.initialize()
    except MowerError as e:
        print(f"Caught error: {e}")

    print("\nExample 7: Navigation component with error handling")
    nav = NavigationComponent()
    success = nav.navigate_to((1.0, 1.0))
    print(f"Navigation success: {success}")

    # This will fail
    success = nav.navigate_to((-1.0, -1.0))
    print(f"Navigation success: {success}")

    print("\nDone!")
