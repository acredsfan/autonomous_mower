"""
Error handling utilities for the autonomous mower.

This module provides utilities for consistent error handling throughout the
autonomous mower project, including decorators and context managers.
"""

import functools
import logging
import sys
import traceback
from contextlib import contextmanager
from typing import Any, Callable, Dict, Optional, Type, TypeVar, cast

from mower.error_handling.exceptions import MowerError, convert_exception
from mower.error_handling.error_codes import ErrorCode
from mower.error_handling.error_reporter import report_error


# Type variables for function decorators
F = TypeVar('F', bound=Callable[..., Any])
T = TypeVar('T')


def handle_error(
    error_code: Optional[ErrorCode] = None,
    reraise: bool = True,
    log_level: int = logging.ERROR,
    context: Optional[Dict[str, Any]] = None
) -> Callable[[F], F]:
    """
    Decorator to handle exceptions in a consistent way.
    
    Args:
        error_code: Error code to use for the error
        reraise: Whether to reraise the exception after handling
        log_level: Logging level to use
        context: Additional context information
        
    Returns:
        Callable: Decorator function
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Skip if it's already a MowerError
                if isinstance(e, MowerError):
                    error = e
                else:
                    # Convert to MowerError
                    error = convert_exception(
                        e,
                        error_code=error_code,
                        context=context
                    )
                
                # Report the error
                report_error(error, log_level=log_level)
                
                # Reraise if requested
                if reraise:
                    raise error from e
                
                # Return None if not reraising
                return None
        
        return cast(F, wrapper)
    
    return decorator


@contextmanager
def error_context(
    error_code: Optional[ErrorCode] = None,
    reraise: bool = True,
    log_level: int = logging.ERROR,
    context: Optional[Dict[str, Any]] = None
):
    """
    Context manager for consistent error handling.
    
    Args:
        error_code: Error code to use for the error
        reraise: Whether to reraise the exception after handling
        log_level: Logging level to use
        context: Additional context information
        
    Yields:
        None
    """
    try:
        yield
    except Exception as e:
        # Skip if it's already a MowerError
        if isinstance(e, MowerError):
            error = e
        else:
            # Convert to MowerError
            error = convert_exception(
                e,
                error_code=error_code,
                context=context
            )
        
        # Report the error
        report_error(error, log_level=log_level)
        
        # Reraise if requested
        if reraise:
            raise error from e


def with_error_handling(
    func: Optional[F] = None,
    *,
    error_code: Optional[ErrorCode] = None,
    reraise: bool = True,
    log_level: int = logging.ERROR,
    context: Optional[Dict[str, Any]] = None
) -> Any:
    """
    Decorator to handle exceptions in a consistent way.
    
    This is a more flexible version of handle_error that can be used with
    or without arguments.
    
    Args:
        func: Function to decorate
        error_code: Error code to use for the error
        reraise: Whether to reraise the exception after handling
        log_level: Logging level to use
        context: Additional context information
        
    Returns:
        Any: Decorated function or decorator function
    """
    if func is None:
        return handle_error(
            error_code=error_code,
            reraise=reraise,
            log_level=log_level,
            context=context
        )
    
    return handle_error(
        error_code=error_code,
        reraise=reraise,
        log_level=log_level,
        context=context
    )(func)


def safe_call(
    func: Callable[..., T],
    *args: Any,
    error_code: Optional[ErrorCode] = None,
    default_value: Optional[T] = None,
    log_level: int = logging.ERROR,
    context: Optional[Dict[str, Any]] = None,
    **kwargs: Any
) -> Optional[T]:
    """
    Call a function with error handling.
    
    Args:
        func: Function to call
        *args: Arguments to pass to the function
        error_code: Error code to use for the error
        default_value: Default value to return if an error occurs
        log_level: Logging level to use
        context: Additional context information
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        Optional[T]: Result of the function call or default value
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        # Skip if it's already a MowerError
        if isinstance(e, MowerError):
            error = e
        else:
            # Convert to MowerError
            error = convert_exception(
                e,
                error_code=error_code,
                context=context
            )
        
        # Report the error
        report_error(error, log_level=log_level)
        
        # Return default value
        return default_value


def install_global_exception_handler():
    """
    Install a global exception handler to catch unhandled exceptions.
    
    This function installs a global exception handler that will report
    unhandled exceptions to the error reporter before the program exits.
    """
    def global_exception_handler(
        exc_type: Type[BaseException],
        exc_value: BaseException,
        exc_traceback: Optional[traceback.TracebackType]
    ):
        # Skip if it's a KeyboardInterrupt
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        # Convert to MowerError
        if isinstance(exc_value, Exception):
            error = convert_exception(
                exc_value,
                error_code=ErrorCode.SOFTWARE_GENERIC,
                context={"unhandled": True}
            )
            
            # Report the error
            report_error(error, log_level=logging.CRITICAL)
        
        # Call the original exception handler
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
    
    # Install the global exception handler
    sys.excepthook = global_exception_handler


# Install the global exception handler
install_global_exception_handler()