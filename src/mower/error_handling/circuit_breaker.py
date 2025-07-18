"""
Circuit breaker pattern implementation for hardware dependencies.

This module provides a circuit breaker pattern implementation to handle
failures in external dependencies like hardware components, network services,
and other unreliable resources.
"""

import asyncio
import functools
import logging
import time
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

from mower.error_handling.exceptions import HardwareError, MowerError

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, calls fail fast
    HALF_OPEN = "half_open"  # Testing if service is back


class CircuitBreakerOpenError(MowerError):
    """Exception raised when circuit breaker is open."""
    
    def __init__(self, circuit_name: str, failure_count: int, timeout_remaining: float):
        message = (
            f"Circuit breaker '{circuit_name}' is open. "
            f"Failures: {failure_count}, Timeout remaining: {timeout_remaining:.1f}s"
        )
        super().__init__(message)
        self.circuit_name = circuit_name
        self.failure_count = failure_count
        self.timeout_remaining = timeout_remaining


class CircuitBreaker:
    """
    Circuit breaker implementation for handling external dependency failures.
    
    The circuit breaker monitors failures and automatically opens when the
    failure threshold is reached, preventing further calls to the failing
    service. After a timeout period, it transitions to half-open to test
    if the service has recovered.
    
    Features:
    - Configurable failure thresholds and timeout periods
    - Support for both synchronous and asynchronous operations
    - Optional fallback function for graceful degradation
    - Automatic state transitions (closed -> open -> half-open -> closed)
    - Detailed state tracking and metrics
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        expected_exception: Union[type, tuple] = Exception,
        fallback: Optional[Callable] = None,
        half_open_success_threshold: int = 1,
        reset_timeout: Optional[float] = None,
        failure_window: Optional[float] = None
    ):
        """
        Initialize circuit breaker.
        
        Args:
            name: Name of the circuit breaker for logging/identification
            failure_threshold: Number of failures before opening circuit
            timeout: Time in seconds before attempting to close circuit
            expected_exception: Exception types that trigger circuit opening
            fallback: Optional fallback function to call when circuit is open
            half_open_success_threshold: Number of successful calls needed in half-open state
                                        before closing the circuit (default: 1)
            reset_timeout: Optional timeout to automatically reset failure count if no
                          failures occur within this period (in seconds)
            failure_window: Optional time window for counting failures (in seconds).
                           If specified, only failures within this window count toward threshold.
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception
        self.fallback = fallback
        self.half_open_success_threshold = half_open_success_threshold
        self.reset_timeout = reset_timeout
        self.failure_window = failure_window
        
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.last_success_time: Optional[float] = None
        self.state = CircuitState.CLOSED
        self.success_count = 0  # For half-open state
        self._lock = asyncio.Lock() if asyncio.iscoroutinefunction else None
        self._failure_timestamps: List[float] = []  # For tracking failures within window
        
        logger.info(
            f"Circuit breaker '{name}' initialized: "
            f"threshold={failure_threshold}, timeout={timeout}s"
        )
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.timeout
    
    def _on_success(self) -> None:
        """Handle successful call."""
        current_time = time.time()
        self.last_success_time = current_time
        
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            # Reset circuit after reaching success threshold in half-open state
            if self.success_count >= self.half_open_success_threshold:
                logger.info(f"Circuit breaker '{self.name}' reset to CLOSED after {self.success_count} successful calls")
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                self._failure_timestamps = []
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success if reset_timeout is configured
            if self.reset_timeout and self.failure_count > 0:
                if self.last_failure_time and (current_time - self.last_failure_time) >= self.reset_timeout:
                    logger.debug(f"Circuit breaker '{self.name}' failure count reset due to timeout")
                    self.failure_count = 0
                    self._failure_timestamps = []
    
    def _on_failure(self, exception: Exception) -> None:
        """Handle failed call."""
        current_time = time.time()
        self.last_failure_time = current_time
        
        # If using failure window, track timestamps and count only failures within window
        if self.failure_window:
            self._failure_timestamps.append(current_time)
            # Remove failures outside the window
            self._failure_timestamps = [ts for ts in self._failure_timestamps 
                                      if current_time - ts <= self.failure_window]
            self.failure_count = len(self._failure_timestamps)
        else:
            self.failure_count += 1
        
        if self.state == CircuitState.HALF_OPEN:
            # Failure in half-open state, go back to open
            logger.warning(
                f"Circuit breaker '{self.name}' failed in HALF_OPEN, "
                f"returning to OPEN state"
            )
            self.state = CircuitState.OPEN
            self.success_count = 0
        elif self.state == CircuitState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                logger.error(
                    f"Circuit breaker '{self.name}' opened after "
                    f"{self.failure_count} failures"
                )
                self.state = CircuitState.OPEN
    
    def _get_timeout_remaining(self) -> float:
        """Get remaining timeout in seconds."""
        if self.last_failure_time is None:
            return 0.0
        elapsed = time.time() - self.last_failure_time
        return max(0.0, self.timeout - elapsed)
    
    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """
        Call function with circuit breaker protection (async version).
        
        Args:
            func: Function to call
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Any: Function result
            
        Raises:
            CircuitBreakerOpenError: When circuit is open
            Exception: Original exception from function
        """
        async with self._lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    logger.info(f"Circuit breaker '{self.name}' transitioning to HALF_OPEN")
                    self.state = CircuitState.HALF_OPEN
                else:
                    timeout_remaining = self._get_timeout_remaining()
                    if self.fallback:
                        logger.debug(f"Circuit breaker '{self.name}' using fallback")
                        return await self.fallback(*args, **kwargs) if asyncio.iscoroutinefunction(self.fallback) else self.fallback(*args, **kwargs)
                    raise CircuitBreakerOpenError(self.name, self.failure_count, timeout_remaining)
        
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            async with self._lock:
                self._on_success()
            return result
            
        except self.expected_exception as e:
            async with self._lock:
                self._on_failure(e)
            raise
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Call function with circuit breaker protection (sync version).
        
        Args:
            func: Function to call
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Any: Function result
            
        Raises:
            CircuitBreakerOpenError: When circuit is open
            Exception: Original exception from function
        """
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                logger.info(f"Circuit breaker '{self.name}' transitioning to HALF_OPEN")
                self.state = CircuitState.HALF_OPEN
            else:
                timeout_remaining = self._get_timeout_remaining()
                if self.fallback:
                    logger.debug(f"Circuit breaker '{self.name}' using fallback")
                    return self.fallback(*args, **kwargs)
                raise CircuitBreakerOpenError(self.name, self.failure_count, timeout_remaining)
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
            
        except self.expected_exception as e:
            self._on_failure(e)
            raise
    
    def get_state(self) -> Dict[str, Any]:
        """
        Get current circuit breaker state.
        
        Returns:
            Dict containing state information
        """
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "timeout": self.timeout,
            "timeout_remaining": self._get_timeout_remaining(),
            "last_failure_time": self.last_failure_time,
            "success_count": self.success_count
        }
    
    def reset(self) -> None:
        """Manually reset the circuit breaker to closed state."""
        logger.info(f"Circuit breaker '{self.name}' manually reset")
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None


class CircuitBreakerManager:
    """
    Manager for multiple circuit breakers.
    
    Provides centralized management and configuration of circuit breakers
    throughout the application.
    """
    
    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._default_config = {
            "failure_threshold": 5,
            "timeout": 60.0,
            "expected_exception": Exception
        }
    
    def create_breaker(
        self,
        name: str,
        failure_threshold: Optional[int] = None,
        timeout: Optional[float] = None,
        expected_exception: Optional[Union[type, tuple]] = None,
        fallback: Optional[Callable] = None,
        half_open_success_threshold: Optional[int] = None,
        reset_timeout: Optional[float] = None,
        failure_window: Optional[float] = None
    ) -> CircuitBreaker:
        """
        Create or get existing circuit breaker.
        
        Args:
            name: Circuit breaker name
            failure_threshold: Number of failures before opening
            timeout: Timeout before attempting reset
            expected_exception: Exception types that trigger opening
            fallback: Fallback function
            half_open_success_threshold: Number of successful calls needed in half-open state
                                        before closing the circuit
            reset_timeout: Optional timeout to automatically reset failure count if no
                          failures occur within this period (in seconds)
            failure_window: Optional time window for counting failures (in seconds)
            
        Returns:
            CircuitBreaker instance
        """
        if name in self._breakers:
            return self._breakers[name]
        
        config = self._default_config.copy()
        if failure_threshold is not None:
            config["failure_threshold"] = failure_threshold
        if timeout is not None:
            config["timeout"] = timeout
        if expected_exception is not None:
            config["expected_exception"] = expected_exception
        
        breaker = CircuitBreaker(
            name=name,
            failure_threshold=config["failure_threshold"],
            timeout=config["timeout"],
            expected_exception=config["expected_exception"],
            fallback=fallback,
            half_open_success_threshold=half_open_success_threshold or 1,
            reset_timeout=reset_timeout,
            failure_window=failure_window
        )
        
        self._breakers[name] = breaker
        return breaker
    
    def get_breaker(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name."""
        return self._breakers.get(name)
    
    def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        """Get states of all circuit breakers."""
        return {name: breaker.get_state() for name, breaker in self._breakers.items()}
    
    def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for breaker in self._breakers.values():
            breaker.reset()
    
    def configure_defaults(
        self,
        failure_threshold: Optional[int] = None,
        timeout: Optional[float] = None,
        expected_exception: Optional[Union[type, tuple]] = None
    ) -> None:
        """Configure default settings for new circuit breakers."""
        if failure_threshold is not None:
            self._default_config["failure_threshold"] = failure_threshold
        if timeout is not None:
            self._default_config["timeout"] = timeout
        if expected_exception is not None:
            self._default_config["expected_exception"] = expected_exception


# Global circuit breaker manager instance
_circuit_breaker_manager = CircuitBreakerManager()


def get_circuit_breaker_manager() -> CircuitBreakerManager:
    """Get the global circuit breaker manager instance."""
    return _circuit_breaker_manager


def circuit_breaker(
    name: Optional[str] = None,
    failure_threshold: int = 5,
    timeout: float = 60.0,
    expected_exception: Union[type, tuple] = Exception,
    fallback: Optional[Callable] = None,
    half_open_success_threshold: Optional[int] = None,
    reset_timeout: Optional[float] = None,
    failure_window: Optional[float] = None
) -> Callable[[F], F]:
    """
    Decorator to add circuit breaker protection to a function.
    
    Args:
        name: Circuit breaker name (defaults to function name)
        failure_threshold: Number of failures before opening
        timeout: Timeout before attempting reset
        expected_exception: Exception types that trigger opening
        fallback: Fallback function
        half_open_success_threshold: Number of successful calls needed in half-open state
                                    before closing the circuit
        reset_timeout: Optional timeout to automatically reset failure count if no
                      failures occur within this period (in seconds)
        failure_window: Optional time window for counting failures (in seconds)
        
    Returns:
        Decorated function
    """
    def decorator(func: F) -> F:
        breaker_name = name or f"{func.__module__}.{func.__name__}"
        breaker = _circuit_breaker_manager.create_breaker(
            name=breaker_name,
            failure_threshold=failure_threshold,
            timeout=timeout,
            expected_exception=expected_exception,
            fallback=fallback,
            half_open_success_threshold=half_open_success_threshold,
            reset_timeout=reset_timeout,
            failure_window=failure_window
        )
        
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await breaker.call_async(func, *args, **kwargs)
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                return breaker.call(func, *args, **kwargs)
            return sync_wrapper
    
    return decorator


def hardware_circuit_breaker(
    name: Optional[str] = None,
    failure_threshold: int = 3,
    timeout: float = 30.0,
    fallback: Optional[Callable] = None,
    half_open_success_threshold: int = 2,
    reset_timeout: Optional[float] = 300.0,
    failure_window: Optional[float] = 60.0
) -> Callable[[F], F]:
    """
    Specialized circuit breaker decorator for hardware operations.
    
    This decorator is optimized for hardware components with more conservative
    settings to prevent repeated hardware failures and provide better protection
    against hardware damage.
    
    Args:
        name: Circuit breaker name
        failure_threshold: Number of failures before opening (lower for hardware)
        timeout: Timeout before attempting reset (shorter for hardware)
        fallback: Fallback function
        half_open_success_threshold: Number of successful calls needed in half-open state
        reset_timeout: Timeout to reset failure count if no failures occur (5 minutes default)
        failure_window: Time window for counting failures (1 minute default)
        
    Returns:
        Decorated function
    """
    return circuit_breaker(
        name=name,
        failure_threshold=failure_threshold,
        timeout=timeout,
        expected_exception=(HardwareError, OSError, IOError, TimeoutError),
        fallback=fallback,
        half_open_success_threshold=half_open_success_threshold,
        reset_timeout=reset_timeout,
        failure_window=failure_window
    )


def sensor_circuit_breaker(
    name: Optional[str] = None,
    failure_threshold: int = 5,
    timeout: float = 15.0,
    fallback: Optional[Callable] = None
) -> Callable[[F], F]:
    """
    Specialized circuit breaker decorator for sensor operations.
    
    Optimized for sensor readings which may have frequent but transient failures.
    Uses a shorter timeout but higher failure threshold than other hardware components.
    
    Args:
        name: Circuit breaker name
        failure_threshold: Number of failures before opening (higher for sensors)
        timeout: Timeout before attempting reset (shorter for sensors)
        fallback: Fallback function
        
    Returns:
        Decorated function
    """
    return hardware_circuit_breaker(
        name=name,
        failure_threshold=failure_threshold,
        timeout=timeout,
        fallback=fallback,
        half_open_success_threshold=1,
        reset_timeout=60.0,
        failure_window=30.0
    )


def motor_circuit_breaker(
    name: Optional[str] = None,
    failure_threshold: int = 2,
    timeout: float = 60.0,
    fallback: Optional[Callable] = None
) -> Callable[[F], F]:
    """
    Specialized circuit breaker decorator for motor controller operations.
    
    Optimized for motor operations which require more conservative protection
    to prevent damage to motors and mechanical components.
    
    Args:
        name: Circuit breaker name
        failure_threshold: Number of failures before opening (lower for motors)
        timeout: Timeout before attempting reset (longer for motors)
        fallback: Fallback function
        
    Returns:
        Decorated function
    """
    return hardware_circuit_breaker(
        name=name,
        failure_threshold=failure_threshold,
        timeout=timeout,
        fallback=fallback,
        half_open_success_threshold=3,  # Require more successes before closing
        reset_timeout=600.0,  # 10 minutes
        failure_window=120.0   # 2 minutes
    )


def i2c_circuit_breaker(
    name: Optional[str] = None,
    failure_threshold: int = 3,
    timeout: float = 20.0,
    fallback: Optional[Callable] = None
) -> Callable[[F], F]:
    """
    Specialized circuit breaker decorator for I2C bus operations.
    
    Optimized for I2C communications which may experience bus contention
    and timing-related failures.
    
    Args:
        name: Circuit breaker name
        failure_threshold: Number of failures before opening
        timeout: Timeout before attempting reset
        fallback: Fallback function
        
    Returns:
        Decorated function
    """
    return hardware_circuit_breaker(
        name=name,
        failure_threshold=failure_threshold,
        timeout=timeout,
        fallback=fallback,
        half_open_success_threshold=2,
        reset_timeout=120.0,
        failure_window=30.0
    )