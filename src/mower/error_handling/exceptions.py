"""
Custom exception classes for the autonomous mower.

This module defines custom exception classes for the autonomous mower project.
These exceptions provide more context and structure than standard Python
exceptions, making it easier to handle errors in a consistent way.
"""

import traceback
from typing import Any, Dict, Optional, Type


class MowerError(Exception):
    """
    Base class for all mower-specific exceptions.

    This class provides additional context for errors, including an error code,
    a human-readable message, and the original exception if applicable.
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[Any] = None,
        original_exception: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a MowerError.

        Args:
            message: Human-readable error message
            error_code: Error code from ErrorCode enum
            original_exception: Original exception that caused this error
            context: Additional context information
        """
        self.message = message
        self.error_code = error_code
        self.original_exception = original_exception
        self.context = context or {}
        self.traceback = traceback.format_exc() if original_exception else None

        # Call the base class constructor with the message
        super().__init__(message)

    @classmethod
    def from_exception(
        cls,
        exception: Exception,
        error_code: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> "MowerError":
        """
        Create a MowerError from another exception.

        Args:
            exception: Original exception
            error_code: Error code from ErrorCode enum
            context: Additional context information

        Returns:
            MowerError: A new MowerError instance
        """
        return cls(
            message=str(exception),
            error_code=error_code,
            original_exception=exception,
            context=context,
        )

    def __str__(self) -> str:
        """
        Get a string representation of the error.

        Returns:
            str: String representation
        """
        parts = [self.message]

        if self.error_code:
            parts.append(f"Error code: {self.error_code}")

        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            parts.append(f"Context: {context_str}")

        return " | ".join(parts)


class HardwareError(MowerError):
    """Exception raised for hardware-related errors."""

    pass


class NavigationError(MowerError):
    """Exception raised for navigation-related errors."""

    pass


class SoftwareError(MowerError):
    """Exception raised for software-related errors."""

    pass


class ConfigurationError(MowerError):
    """Exception raised for configuration-related errors."""

    pass


class CommunicationError(MowerError):
    """Exception raised for communication-related errors."""

    pass


class SecurityError(MowerError):
    """Exception raised for security-related errors."""

    pass


class UserError(MowerError):
    """Exception raised for user-related errors."""

    pass


# Map of standard Python exceptions to MowerError subclasses
EXCEPTION_MAP: Dict[Type[Exception], Type[MowerError]] = {
    ValueError: ConfigurationError,
    TypeError: SoftwareError,
    KeyError: ConfigurationError,
    FileNotFoundError: ConfigurationError,
    PermissionError: SecurityError,
    ConnectionError: CommunicationError,
    TimeoutError: CommunicationError,
    RuntimeError: SoftwareError,
    NotImplementedError: SoftwareError,
}


def convert_exception(
    exception: Exception,
    error_code: Optional[Any] = None,
    context: Optional[Dict[str, Any]] = None,
) -> MowerError:
    """
    Convert a standard Python exception to a MowerError.

    Args:
        exception: Original exception
        error_code: Error code from ErrorCode enum
        context: Additional context information

    Returns:
        MowerError: A new MowerError instance
    """
    exception_type = type(exception)

    # Find the most specific matching exception type
    for exc_type, mower_error_class in EXCEPTION_MAP.items():
        if isinstance(exception, exc_type):
            return mower_error_class.from_exception(exception, error_code=error_code, context=context)

    # Default to base MowerError if no specific match
    return MowerError.from_exception(exception, error_code=error_code, context=context)
