"""
Error codes for the autonomous mower.

This module defines error codes and categories for the autonomous mower project.
Error codes provide a structured way to identify and categorize errors.
"""

from enum import Enum, auto
from typing import Dict, Any


class ErrorCategory(Enum):
    """Categories of errors in the mower system."""

    # Hardware-related errors
    HARDWARE = auto()

    # Navigation-related errors
    NAVIGATION = auto()

    # Software-related errors
    SOFTWARE = auto()

    # Configuration-related errors
    CONFIGURATION = auto()

    # Communication-related errors
    COMMUNICATION = auto()

    # Security-related errors
    SECURITY = auto()

    # User-related errors
    USER = auto()


class ErrorCode(Enum):
    """
    Error codes for the mower system.

    Each error code consists of a category and a specific code within that category.
    The format is CATEGORY_SPECIFIC_ERROR.
    """

    # Hardware errors (1000-1999)
    HARDWARE_GENERIC = 1000
    HARDWARE_SENSOR_FAILURE = 1001
    HARDWARE_MOTOR_FAILURE = 1002
    HARDWARE_BLADE_FAILURE = 1003
    HARDWARE_BATTERY_LOW = 1004
    HARDWARE_BATTERY_CRITICAL = 1005
    HARDWARE_OVERHEATING = 1006
    HARDWARE_GPIO_ERROR = 1007
    HARDWARE_I2C_ERROR = 1008
    HARDWARE_SERIAL_ERROR = 1009
    HARDWARE_CAMERA_ERROR = 1010

    # Navigation errors (2000-2999)
    NAVIGATION_GENERIC = 2000
    NAVIGATION_GPS_SIGNAL_LOST = 2001
    NAVIGATION_POSITION_UNKNOWN = 2002
    NAVIGATION_PATH_BLOCKED = 2003
    NAVIGATION_BOUNDARY_VIOLATION = 2004
    NAVIGATION_NO_PATH_FOUND = 2005
    NAVIGATION_LOCALIZATION_ERROR = 2006
    NAVIGATION_IMU_ERROR = 2007

    # Software errors (3000-3999)
    SOFTWARE_GENERIC = 3000
    SOFTWARE_INITIALIZATION_FAILED = 3001
    SOFTWARE_THREAD_ERROR = 3002
    SOFTWARE_MEMORY_ERROR = 3003
    SOFTWARE_TIMEOUT = 3004
    SOFTWARE_ALGORITHM_ERROR = 3005
    SOFTWARE_STATE_ERROR = 3006

    # Configuration errors (4000-4999)
    CONFIGURATION_GENERIC = 4000
    CONFIGURATION_INVALID_PARAMETER = 4001
    CONFIGURATION_MISSING_PARAMETER = 4002
    CONFIGURATION_FILE_NOT_FOUND = 4003
    CONFIGURATION_PARSE_ERROR = 4004
    CONFIGURATION_VALIDATION_ERROR = 4005

    # Communication errors (5000-5999)
    COMMUNICATION_GENERIC = 5000
    COMMUNICATION_CONNECTION_LOST = 5001
    COMMUNICATION_TIMEOUT = 5002
    COMMUNICATION_PROTOCOL_ERROR = 5003
    COMMUNICATION_NETWORK_ERROR = 5004

    # Security errors (6000-6999)
    SECURITY_GENERIC = 6000
    SECURITY_AUTHENTICATION_FAILED = 6001
    SECURITY_AUTHORIZATION_FAILED = 6002
    SECURITY_ENCRYPTION_ERROR = 6003
    SECURITY_PERMISSION_DENIED = 6004

    # User errors (7000-7999)
    USER_GENERIC = 7000
    USER_INVALID_INPUT = 7001
    USER_OPERATION_CANCELED = 7002
    USER_COMMAND_REJECTED = 7003

    @property
    def category(self) -> ErrorCategory:
        """
        Get the category of this error code.

        Returns:
            ErrorCategory: The category of this error code
        """
        code_value = self.value

        if 1000 <= code_value < 2000:
            return ErrorCategory.HARDWARE
        elif 2000 <= code_value < 3000:
            return ErrorCategory.NAVIGATION
        elif 3000 <= code_value < 4000:
            return ErrorCategory.SOFTWARE
        elif 4000 <= code_value < 5000:
            return ErrorCategory.CONFIGURATION
        elif 5000 <= code_value < 6000:
            return ErrorCategory.COMMUNICATION
        elif 6000 <= code_value < 7000:
            return ErrorCategory.SECURITY
        elif 7000 <= code_value < 8000:
            return ErrorCategory.USER
        else:
            return (
                ErrorCategory.SOFTWARE
            )  # Default to SOFTWARE for unknown codes

    @property
    def is_critical(self) -> bool:
        """
        Check if this error code represents a critical error.

        Critical errors are those that require immediate attention and may
        prevent the mower from operating safely.

        Returns:
            bool: True if this is a critical error, False otherwise
        """
        critical_codes = {
            ErrorCode.HARDWARE_BATTERY_CRITICAL,
            ErrorCode.HARDWARE_OVERHEATING,
            ErrorCode.NAVIGATION_BOUNDARY_VIOLATION,
            ErrorCode.SECURITY_GENERIC,
            ErrorCode.SECURITY_AUTHENTICATION_FAILED,
            ErrorCode.SECURITY_AUTHORIZATION_FAILED,
        }

        return self in critical_codes

    @property
    def requires_human_intervention(self) -> bool:
        """
        Check if this error code requires human intervention.

        Some errors can be handled automatically by the system, while others
        require a human to intervene.

        Returns:
            bool: True if human intervention is required, False otherwise
        """
        intervention_codes = {
            ErrorCode.HARDWARE_SENSOR_FAILURE,
            ErrorCode.HARDWARE_MOTOR_FAILURE,
            ErrorCode.HARDWARE_BLADE_FAILURE,
            ErrorCode.HARDWARE_BATTERY_CRITICAL,
            ErrorCode.HARDWARE_OVERHEATING,
            ErrorCode.NAVIGATION_PATH_BLOCKED,
            ErrorCode.NAVIGATION_BOUNDARY_VIOLATION,
            ErrorCode.SECURITY_GENERIC,
            ErrorCode.SECURITY_AUTHENTICATION_FAILED,
            ErrorCode.SECURITY_AUTHORIZATION_FAILED,
        }

        return self in intervention_codes


# Map from error categories to their corresponding exception classes
CATEGORY_TO_EXCEPTION = {
    ErrorCategory.HARDWARE: "HardwareError",
    ErrorCategory.NAVIGATION: "NavigationError",
    ErrorCategory.SOFTWARE: "SoftwareError",
    ErrorCategory.CONFIGURATION: "ConfigurationError",
    ErrorCategory.COMMUNICATION: "CommunicationError",
    ErrorCategory.SECURITY: "SecurityError",
    ErrorCategory.USER: "UserError",
}


def get_error_details(error_code: ErrorCode) -> Dict[str, Any]:
    """
    Get detailed information about an error code.

    Args:
        error_code: The error code to get details for

    Returns:
        Dict[str, Any]: Dictionary with error details
    """
    return {
        "code": error_code.value,
        "name": error_code.name,
        "category": error_code.category.name,
        "is_critical": error_code.is_critical,
        "requires_human_intervention": error_code.requires_human_intervention,
        "exception_class": CATEGORY_TO_EXCEPTION.get(
            error_code.category, "MowerError"
        ),
    }
