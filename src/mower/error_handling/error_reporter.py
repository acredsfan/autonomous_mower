"""
Error reporting for the autonomous mower.

This module provides a centralized error reporting mechanism for the
autonomous mower project. It allows errors to be reported to various
destinations (logs, UI, etc.) and ensures consistent error reporting
throughout the codebase.
"""

import logging
import threading
import time
from typing import Dict, List, Optional, Any, Callable, Set

from mower.error_handling.exceptions import MowerError
from mower.error_handling.error_codes import ErrorCode, get_error_details


class ErrorReporter:
    """
    Centralized error reporting mechanism.

    This class provides methods to report errors to various destinations
    and maintains a history of recent errors.
    """

    def __init__(self, max_history: int = 100):
        """
        Initialize the error reporter.

        Args:
            max_history: Maximum number of errors to keep in history
        """
        self.logger = logging.getLogger("mower.error_reporter")
        self.max_history = max_history
        self.error_history: List[Dict[str, Any]] = []
        self.error_handlers: Dict[str, Callable[[MowerError], None]] = {}
        self.critical_errors: Set[ErrorCode] = set()
        self.lock = threading.RLock()

    def report_error(
        self,
        error: MowerError,
        log_level: int = logging.ERROR
    ) -> None:
        """
        Report an error.

        Args:
            error: The error to report
            log_level: The logging level to use
        """
        with self.lock:
            # Log the error
            self.logger.log(log_level, str(error))

            # Add to history
            error_entry = {
                "timestamp": time.time(),
                "error": error,
                "message": str(error),
                "error_code": error.error_code,
                "context": error.context,
                "traceback": error.traceback
            }

            self.error_history.append(error_entry)

            # Trim history if needed
            if len(self.error_history) > self.max_history:
                self.error_history = self.error_history[-self.max_history:]

            # Check if this is a critical error
            if error.error_code and error.error_code.is_critical:
                self.critical_errors.add(error.error_code)

            # Call error handlers
            for handler_name, handler_func in self.error_handlers.items():
                try:
                    handler_func(error)
                except Exception as e:
                    self.logger.error(
                        f"Error in error handler {handler_name}: {e}"
                    )

    def register_error_handler(
        self,
        name: str,
        handler: Callable[[MowerError], None]
    ) -> None:
        """
        Register an error handler.

        Args:
            name: Name of the handler
            handler: Handler function
        """
        with self.lock:
            self.error_handlers[name] = handler

    def unregister_error_handler(self, name: str) -> None:
        """
        Unregister an error handler.

        Args:
            name: Name of the handler to unregister
        """
        with self.lock:
            if name in self.error_handlers:
                del self.error_handlers[name]

    def get_error_history(self) -> List[Dict[str, Any]]:
        """
        Get the error history.

        Returns:
            List[Dict[str, Any]]: List of error entries
        """
        with self.lock:
            return list(self.error_history)

    def get_recent_errors(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        Get the most recent errors.

        Args:
            count: Number of errors to return

        Returns:
            List[Dict[str, Any]]: List of recent error entries
        """
        with self.lock:
            return list(self.error_history[-count:])

    def get_critical_errors(self) -> Set[ErrorCode]:
        """
        Get the set of critical errors that have occurred.

        Returns:
            Set[ErrorCode]: Set of critical error codes
        """
        with self.lock:
            return set(self.critical_errors)

    def clear_error_history(self) -> None:
        """Clear the error history."""
        with self.lock:
            self.error_history = []

    def clear_critical_errors(self) -> None:
        """Clear the set of critical errors."""
        with self.lock:
            self.critical_errors = set()


# Singleton instance of ErrorReporter
_error_reporter: Optional[ErrorReporter] = None
_reporter_lock = threading.RLock()


def get_error_reporter() -> ErrorReporter:
    """
    Get the singleton instance of ErrorReporter.

    Returns:
        ErrorReporter: The singleton instance
    """
    global _error_reporter

    with _reporter_lock:
        if _error_reporter is None:
            _error_reporter = ErrorReporter()

    return _error_reporter


def report_error(
    error: MowerError,
    log_level: int = logging.ERROR
) -> None:
    """
    Report an error using the singleton ErrorReporter.

    Args:
        error: The error to report
        log_level: The logging level to use
    """
    reporter = get_error_reporter()
    reporter.report_error(error, log_level)


# Register default error handlers
def _register_default_handlers():
    """Register default error handlers."""
    reporter = get_error_reporter()

    # Add default handlers here if needed
    # For example, a handler to send critical errors to the UI

    pass


# Initialize default handlers
_register_default_handlers()
