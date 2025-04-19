# Error Handling System

This module provides a unified error handling and reporting system for the autonomous mower project. It includes custom exception classes, error codes, and a centralized error reporting mechanism.

## Features

- Custom exception classes with additional context
- Structured error codes and categories
- Centralized error reporting
- Consistent error handling patterns
- Thread-safe implementation
- Global exception handler

## Usage

### Basic Error Handling

```python
from mower.error_handling import MowerError, ErrorCode, report_error

try:
    # Some code that might raise an exception
    result = some_function()
except Exception as e:
    # Convert to a MowerError with an appropriate error code
    error = MowerError.from_exception(e, ErrorCode.HARDWARE_ERROR)
    # Report the error
    report_error(error)
    # Handle the error appropriately
    # ...
```

### Using Decorators

```python
from mower.error_handling import with_error_handling, ErrorCode

@with_error_handling(error_code=ErrorCode.HARDWARE_SENSOR_FAILURE)
def read_sensor():
    # This function will have consistent error handling
    # Any exceptions will be converted to MowerError and reported
    return sensor.read()
```

### Using Context Managers

```python
from mower.error_handling import error_context, ErrorCode

def some_function():
    with error_context(error_code=ErrorCode.NAVIGATION_GPS_SIGNAL_LOST):
        # Any exceptions in this block will be handled consistently
        gps_data = gps.get_position()
        # ...
```

### Safe Function Calls

```python
from mower.error_handling import safe_call, ErrorCode

# Call a function with error handling
result = safe_call(
    some_function,
    arg1, arg2,
    error_code=ErrorCode.SOFTWARE_TIMEOUT,
    default_value=None
)
```

### Custom Error Handlers

```python
from mower.error_handling import get_error_reporter, MowerError

def ui_error_handler(error: MowerError):
    # Send error to UI
    if error.error_code and error.error_code.is_critical:
        ui.show_critical_error(str(error))
    else:
        ui.show_error(str(error))

# Register the error handler
reporter = get_error_reporter()
reporter.register_error_handler("ui", ui_error_handler)
```

## Error Categories

The system defines the following error categories:

- `HARDWARE`: Hardware-related errors
- `NAVIGATION`: Navigation-related errors
- `SOFTWARE`: Software-related errors
- `CONFIGURATION`: Configuration-related errors
- `COMMUNICATION`: Communication-related errors
- `SECURITY`: Security-related errors
- `USER`: User-related errors

## Error Codes

Each error code belongs to a category and has a unique numeric value. For example:

- `HARDWARE_SENSOR_FAILURE`: 1001
- `NAVIGATION_GPS_SIGNAL_LOST`: 2001
- `SOFTWARE_INITIALIZATION_FAILED`: 3001

See `error_codes.py` for the complete list of error codes.

## Exception Classes

The system defines the following exception classes:

- `MowerError`: Base class for all mower-specific exceptions
- `HardwareError`: Exception raised for hardware-related errors
- `NavigationError`: Exception raised for navigation-related errors
- `SoftwareError`: Exception raised for software-related errors
- `ConfigurationError`: Exception raised for configuration-related errors
- `CommunicationError`: Exception raised for communication-related errors
- `SecurityError`: Exception raised for security-related errors
- `UserError`: Exception raised for user-related errors

## Error Reporting

Errors are reported to the centralized `ErrorReporter`, which:

- Logs the error
- Maintains a history of recent errors
- Tracks critical errors
- Notifies registered error handlers

## Best Practices

1. Use the provided decorators and context managers for consistent error handling
2. Always use appropriate error codes
3. Provide meaningful error messages
4. Include relevant context information
5. Handle critical errors appropriately
6. Register custom error handlers for specific needs