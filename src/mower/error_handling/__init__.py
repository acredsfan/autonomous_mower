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

from mower.error_handling.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerManager,
    CircuitBreakerOpenError,
    CircuitState,
    circuit_breaker,
    get_circuit_breaker_manager,
    hardware_circuit_breaker,
    i2c_circuit_breaker,
    motor_circuit_breaker,
    sensor_circuit_breaker,
)
from mower.error_handling.error_codes import ErrorCategory, ErrorCode
from mower.error_handling.error_handler import handle_error, with_error_handling
from mower.error_handling.error_reporter import get_error_reporter, report_error
from mower.error_handling.exceptions import HardwareError, MowerError, NavigationError, SoftwareError
from mower.error_handling.health_monitoring import (
    ComponentHealth,
    HealthCheckInterface,
    HealthCheckMixin,
    HealthIssue,
    HealthMonitor,
    HealthStatus,
    create_health_issue,
    get_health_monitor,
)
from mower.error_handling.retry_policy import (
    RetryPolicy,
    RetryPolicyEngine,
    RetryResult,
    RetryStrategy,
    get_retry_policy_engine,
    i2c_retry,
    network_retry,
    sensor_retry,
    with_retry,
)

__all__ = [
    "MowerError",
    "HardwareError",
    "NavigationError",
    "SoftwareError",
    "ErrorCode",
    "ErrorCategory",
    "report_error",
    "get_error_reporter",
    "handle_error",
    "with_error_handling",
    "CircuitBreaker",
    "CircuitBreakerManager",
    "CircuitBreakerOpenError",
    "CircuitState",
    "circuit_breaker",
    "get_circuit_breaker_manager",
    "hardware_circuit_breaker",
    "i2c_circuit_breaker",
    "motor_circuit_breaker",
    "sensor_circuit_breaker",
    "RetryPolicy",
    "RetryPolicyEngine",
    "RetryResult",
    "RetryStrategy",
    "get_retry_policy_engine",
    "with_retry",
    "network_retry",
    "sensor_retry",
    "i2c_retry",
    "ComponentHealth",
    "HealthCheckInterface",
    "HealthCheckMixin",
    "HealthIssue",
    "HealthMonitor",
    "HealthStatus",
    "create_health_issue",
    "get_health_monitor",
]
