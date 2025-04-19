"""
Error handling package for the autonomous mower.

This package provides a unified error handling and reporting system for the
autonomous mower project. It includes custom exception classes, error codes,
and a centralized error reporting mechanism.

Usage:
    from mower.error_handling import MowerError, ErrorCode, report_error

    try:
        # Some code that might raise an exception
        pass
    except Exception as e:
        # Convert to a MowerError with an appropriate error code
        error = MowerError.from_exception(e, ErrorCode.HARDWARE_ERROR)
        # Report the error
        report_error(error)
        # Handle the error appropriately
        # ...
"""

from mower.error_handling.exceptions import MowerError, HardwareError, NavigationError, SoftwareError
from mower.error_handling.error_codes import ErrorCode, ErrorCategory
from mower.error_handling.error_reporter import report_error, get_error_reporter
from mower.error_handling.error_handler import handle_error, with_error_handling

__all__ = [
    'MowerError',
    'HardwareError',
    'NavigationError',
    'SoftwareError',
    'ErrorCode',
    'ErrorCategory',
    'report_error',
    'get_error_reporter',
    'handle_error',
    'with_error_handling',
]