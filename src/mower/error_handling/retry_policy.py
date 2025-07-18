"""
Retry policy engine with configurable strategies.

This module provides a flexible retry policy engine with various backoff strategies
for handling transient failures in external dependencies, network operations, and
hardware interactions.
"""

import functools
import logging
import random
import time
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union, cast

from mower.error_handling.exceptions import MowerError

logger = logging.getLogger(__name__)

# Type variable for function decorators
F = TypeVar("F", bound=Callable[..., Any])
R = TypeVar("R")  # Return type


class RetryStrategy(Enum):
    """Retry strategy types."""
    FIXED_DELAY = "fixed_delay"
    LINEAR_BACKOFF = "linear_backoff"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    FIBONACCI_BACKOFF = "fibonacci_backoff"
    RANDOM_BACKOFF = "random_backoff"


class RetryResult:
    """Result of a retry operation."""
    
    def __init__(
        self,
        success: bool,
        value: Any = None,
        exception: Optional[Exception] = None,
        attempts: int = 0,
        total_delay: float = 0.0
    ):
        """
        Initialize retry result.
        
        Args:
            success: Whether the operation eventually succeeded
            value: Return value of the successful operation
            exception: Last exception if operation failed
            attempts: Number of attempts made
            total_delay: Total delay time in seconds
        """
        self.success = success
        self.value = value
        self.exception = exception
        self.attempts = attempts
        self.total_delay = total_delay
    
    def __bool__(self) -> bool:
        """Return success status when used in boolean context."""
        return self.success


class RetryPolicy:
    """
    Configurable retry policy with various backoff strategies.
    
    This class provides a flexible retry mechanism with different backoff
    strategies for handling transient failures in external dependencies,
    network operations, and hardware interactions.
    """
    
    def __init__(
        self,
        max_attempts: int = 3,
        strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        expected_exceptions: Union[Type[Exception], tuple] = Exception,
        jitter: bool = True,
        jitter_factor: float = 0.1,
        on_retry: Optional[Callable[[int, Exception, float], None]] = None
    ):
        """
        Initialize retry policy.
        
        Args:
            max_attempts: Maximum number of attempts (including first attempt)
            strategy: Backoff strategy to use
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
            expected_exceptions: Exception types to retry on
            jitter: Whether to add random jitter to delay
            jitter_factor: Factor for jitter (0.0-1.0)
            on_retry: Optional callback function called before each retry
        """
        self.max_attempts = max_attempts
        self.strategy = strategy
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.expected_exceptions = expected_exceptions
        self.jitter = jitter
        self.jitter_factor = jitter_factor
        self.on_retry = on_retry
    
    def _calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for the current attempt based on strategy.
        
        Args:
            attempt: Current attempt number (0-based)
            
        Returns:
            float: Delay in seconds
        """
        if attempt <= 0:
            return 0.0
        
        if self.strategy == RetryStrategy.FIXED_DELAY:
            delay = self.base_delay
        
        elif self.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.base_delay * attempt
        
        elif self.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = self.base_delay * (2 ** (attempt - 1))
        
        elif self.strategy == RetryStrategy.FIBONACCI_BACKOFF:
            # Calculate Fibonacci number for attempt
            a, b = 1, 1
            for _ in range(attempt - 1):
                a, b = b, a + b
            delay = self.base_delay * a
        
        elif self.strategy == RetryStrategy.RANDOM_BACKOFF:
            # Random delay between base_delay and base_delay * attempt
            delay = random.uniform(self.base_delay, self.base_delay * attempt)
        
        else:
            # Default to exponential backoff
            delay = self.base_delay * (2 ** (attempt - 1))
        
        # Apply jitter if enabled
        if self.jitter:
            jitter_range = delay * self.jitter_factor
            delay += random.uniform(-jitter_range, jitter_range)
        
        # Ensure delay is within bounds
        return min(max(delay, 0.0), self.max_delay)
    
    def execute(self, func: Callable[..., R], *args: Any, **kwargs: Any) -> RetryResult:
        """
        Execute function with retry policy.
        
        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            RetryResult: Result of the operation
        """
        attempts = 0
        total_delay = 0.0
        last_exception = None
        
        while attempts < self.max_attempts:
            try:
                # Execute function
                result = func(*args, **kwargs)
                
                # Return successful result
                return RetryResult(
                    success=True,
                    value=result,
                    attempts=attempts + 1,
                    total_delay=total_delay
                )
            
            except self.expected_exceptions as e:
                attempts += 1
                last_exception = e
                
                # If this was the last attempt, don't delay
                if attempts >= self.max_attempts:
                    break
                
                # Calculate delay for next attempt
                delay = self._calculate_delay(attempts)
                total_delay += delay
                
                # Call on_retry callback if provided
                if self.on_retry:
                    try:
                        self.on_retry(attempts, e, delay)
                    except Exception as callback_error:
                        logger.warning(
                            f"Error in retry callback: {callback_error}"
                        )
                
                logger.debug(
                    f"Retry attempt {attempts}/{self.max_attempts} "
                    f"after {delay:.2f}s delay due to: {e}"
                )
                
                # Wait before next attempt
                time.sleep(delay)
        
        # All attempts failed
        return RetryResult(
            success=False,
            exception=last_exception,
            attempts=attempts,
            total_delay=total_delay
        )
    
    async def execute_async(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> RetryResult:
        """
        Execute async function with retry policy.
        
        Args:
            func: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            RetryResult: Result of the operation
        """
        import asyncio
        
        attempts = 0
        total_delay = 0.0
        last_exception = None
        
        while attempts < self.max_attempts:
            try:
                # Execute function
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                # Return successful result
                return RetryResult(
                    success=True,
                    value=result,
                    attempts=attempts + 1,
                    total_delay=total_delay
                )
            
            except self.expected_exceptions as e:
                attempts += 1
                last_exception = e
                
                # If this was the last attempt, don't delay
                if attempts >= self.max_attempts:
                    break
                
                # Calculate delay for next attempt
                delay = self._calculate_delay(attempts)
                total_delay += delay
                
                # Call on_retry callback if provided
                if self.on_retry:
                    try:
                        if asyncio.iscoroutinefunction(self.on_retry):
                            await self.on_retry(attempts, e, delay)
                        else:
                            self.on_retry(attempts, e, delay)
                    except Exception as callback_error:
                        logger.warning(
                            f"Error in retry callback: {callback_error}"
                        )
                
                logger.debug(
                    f"Async retry attempt {attempts}/{self.max_attempts} "
                    f"after {delay:.2f}s delay due to: {e}"
                )
                
                # Wait before next attempt
                await asyncio.sleep(delay)
        
        # All attempts failed
        return RetryResult(
            success=False,
            exception=last_exception,
            attempts=attempts,
            total_delay=total_delay
        )


class RetryPolicyEngine:
    """
    Engine for managing and applying retry policies.
    
    This class provides a centralized registry for retry policies and
    methods for applying them to functions.
    """
    
    def __init__(self):
        """Initialize retry policy engine."""
        self._policies: Dict[str, RetryPolicy] = {}
        self._default_policy = RetryPolicy()
    
    def register_policy(self, name: str, policy: RetryPolicy) -> None:
        """
        Register a named retry policy.
        
        Args:
            name: Policy name
            policy: RetryPolicy instance
        """
        self._policies[name] = policy
        logger.debug(f"Registered retry policy '{name}'")
    
    def get_policy(self, name: str) -> Optional[RetryPolicy]:
        """
        Get a registered retry policy by name.
        
        Args:
            name: Policy name
            
        Returns:
            RetryPolicy or None if not found
        """
        return self._policies.get(name)
    
    def set_default_policy(self, policy: RetryPolicy) -> None:
        """
        Set the default retry policy.
        
        Args:
            policy: RetryPolicy instance
        """
        self._default_policy = policy
        logger.debug("Set default retry policy")
    
    def execute(
        self,
        func: Callable[..., R],
        *args: Any,
        policy_name: Optional[str] = None,
        **kwargs: Any
    ) -> R:
        """
        Execute function with retry policy.
        
        Args:
            func: Function to execute
            *args: Positional arguments
            policy_name: Name of policy to use (uses default if None)
            **kwargs: Keyword arguments
            
        Returns:
            Any: Function result
            
        Raises:
            Exception: Last exception if all retries fail
        """
        policy = self._policies.get(policy_name, self._default_policy)
        result = policy.execute(func, *args, **kwargs)
        
        if result.success:
            return result.value
        
        # Raise the last exception
        if result.exception:
            raise result.exception
        
        # This should never happen, but just in case
        raise RuntimeError("Retry failed with no exception")
    
    async def execute_async(
        self,
        func: Callable[..., R],
        *args: Any,
        policy_name: Optional[str] = None,
        **kwargs: Any
    ) -> R:
        """
        Execute async function with retry policy.
        
        Args:
            func: Async function to execute
            *args: Positional arguments
            policy_name: Name of policy to use (uses default if None)
            **kwargs: Keyword arguments
            
        Returns:
            Any: Function result
            
        Raises:
            Exception: Last exception if all retries fail
        """
        policy = self._policies.get(policy_name, self._default_policy)
        result = await policy.execute_async(func, *args, **kwargs)
        
        if result.success:
            return result.value
        
        # Raise the last exception
        if result.exception:
            raise result.exception
        
        # This should never happen, but just in case
        raise RuntimeError("Retry failed with no exception")
    
    def load_from_config(self, config: Dict[str, Any]) -> None:
        """
        Load retry policies from configuration.
        
        Args:
            config: Configuration dictionary
        """
        if "retry_policies" not in config:
            logger.warning("No retry policies found in configuration")
            return
        
        policies_config = config["retry_policies"]
        
        # Load default policy if specified
        if "default" in policies_config:
            default_config = policies_config["default"]
            self._default_policy = self._create_policy_from_config(default_config)
            logger.info("Loaded default retry policy from configuration")
        
        # Load named policies
        for name, policy_config in policies_config.items():
            if name == "default":
                continue
            
            policy = self._create_policy_from_config(policy_config)
            self.register_policy(name, policy)
            logger.info(f"Loaded retry policy '{name}' from configuration")
    
    def _create_policy_from_config(self, config: Dict[str, Any]) -> RetryPolicy:
        """
        Create RetryPolicy from configuration dictionary.
        
        Args:
            config: Policy configuration
            
        Returns:
            RetryPolicy instance
        """
        strategy_name = config.get("strategy", "exponential_backoff")
        strategy = RetryStrategy(strategy_name)
        
        return RetryPolicy(
            max_attempts=config.get("max_attempts", 3),
            strategy=strategy,
            base_delay=config.get("base_delay", 1.0),
            max_delay=config.get("max_delay", 60.0),
            jitter=config.get("jitter", True),
            jitter_factor=config.get("jitter_factor", 0.1)
        )


# Global retry policy engine instance
_retry_policy_engine = RetryPolicyEngine()


def get_retry_policy_engine() -> RetryPolicyEngine:
    """Get the global retry policy engine instance."""
    return _retry_policy_engine


def with_retry(
    max_attempts: Optional[int] = None,
    strategy: Optional[RetryStrategy] = None,
    base_delay: Optional[float] = None,
    max_delay: Optional[float] = None,
    expected_exceptions: Optional[Union[Type[Exception], tuple]] = None,
    jitter: Optional[bool] = None,
    policy_name: Optional[str] = None,
) -> Callable[[F], F]:
    """
    Decorator to apply retry policy to a function.
    
    Args:
        max_attempts: Maximum number of attempts
        strategy: Backoff strategy
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        expected_exceptions: Exception types to retry on
        jitter: Whether to add random jitter to delay
        policy_name: Name of registered policy to use
        
    Returns:
        Decorated function
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Use named policy if specified
            if policy_name:
                return _retry_policy_engine.execute(
                    func, *args, policy_name=policy_name, **kwargs
                )
            
            # Create custom policy if parameters specified
            if any(param is not None for param in [
                max_attempts, strategy, base_delay, max_delay, expected_exceptions, jitter
            ]):
                policy = RetryPolicy(
                    max_attempts=max_attempts or 3,
                    strategy=strategy or RetryStrategy.EXPONENTIAL_BACKOFF,
                    base_delay=base_delay or 1.0,
                    max_delay=max_delay or 60.0,
                    expected_exceptions=expected_exceptions or Exception,
                    jitter=jitter if jitter is not None else True
               return policy.execute(func, *args, **kwargs).           # Use default policy
            return _retry_policy_engine.execute(func, *args, **kwargs)
        
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            import asyncio
            
            # Use named policy if specified
            if policy_name:
                return await _retry_policy_engine.execute_async(
                    func, *args, policy_name=policy_name, **kwargs
                )
            
            # Create custom policy if parameters specified
            if any(param is not None for param in [
                max_attempts, strategy, base_delay, max_delay, expected_exceptions, jitter
            ]):
                policy = RetryPolicy(
                    max_attempts=max_attempts or 3,
                    strategy=strategy or RetryStrategy.EXPONENTIAL_BACKOFF,
                    base_delay=base_delay or 1.0,
                    max_delay=max_delay or 60.0,
                    expected_exceptions=expected_exceptions or Exception,
                    jitter=jitter if jitter is not None else True
                )
                result = await policy.execute_async(func, *args, **kwargs)
                return result.value
            
            # Use default policy
            return await _retry_policy_engine.execute_async(func, *args, **kwargs)
        
        # Return appropriate wrapper based on whether function is async
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return cast(F, async_wrapper)
        return cast(F, wrapper)
    
    return decorator


def network_retry(
    max_attempts: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    policy_name: Optional[str] = None
) -> Callable[[F], F]:
    """
    Specialized retry decorator for network operations.
    
    Args:
        max_attempts: Maximum number of attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        policy_name: Name of registered policy to use
        
    Returns:
        Decorated function
    """
    network_exceptions = (
        ConnectionError,
        TimeoutError,
        OSError,
        IOError,
    )
    
    return with_retry(
        max_attempts=max_attempts,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        base_delay=base_delay,
        max_delay=max_delay,
        expected_exceptions=network_exceptions,
        jitter=True,
        policy_name=policy_name
    )


def sensor_retry(
    max_attempts: int = 3,
    base_delay: float = 0.1,
    max_delay: float = 1.0,
    policy_name: Optional[str] = None
) -> Callable[[F], F]:
    """
    Specialized retry decorator for sensor operations.
    
    Args:
        max_attempts: Maximum number of attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        policy_name: Name of registered policy to use
        
    Returns:
        Decorated function
    """
    from mower.error_handling.exceptions import HardwareError
    
    sensor_exceptions = (
        HardwareError,
        OSError,
        IOError,
        ValueError,
        TimeoutError
    )
    
    return with_retry(
        max_attempts=max_attempts,
        strategy=RetryStrategy.LINEAR_BACKOFF,
        base_delay=base_delay,
        max_delay=max_delay,
        expected_exceptions=sensor_exceptions,
        jitter=True,
        policy_name=policy_name
    )


def i2c_retry(
    max_attempts: int = 5,
    base_delay: float = 0.02,
    max_delay: float = 0.5,
    policy_name: Optional[str] = None
) -> Callable[[F], F]:
    """
    Specialized retry decorator for I2C operations.
    
    Args:
        max_attempts: Maximum number of attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        policy_name: Name of registered policy to use
        
    Returns:
        Decorated function
    """
    from mower.error_handling.exceptions import HardwareError
    
    i2c_exceptions = (
        HardwareError,
        OSError,
        IOError,
        ValueError,
        TimeoutError
    )
    
    return with_retry(
        max_attempts=max_attempts,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        base_delay=base_delay,
        max_delay=max_delay,
        expected_exceptions=i2c_exceptions,
        jitter=True,
        policy_name=policy_name
    )


# Default configuration schema for retry policies
DEFAULT_RETRY_CONFIG = {
    "retry_policies": {
        "default": {
            "max_attempts": 3,
            "strategy": "exponential_backoff",
            "base_delay": 1.0,
            "max_delay": 60.0,
            "jitter": True,
            "jitter_factor": 0.1
        },
        "network": {
            "max_attempts": 5,
            "strategy": "exponential_backoff",
            "base_delay": 1.0,
            "max_delay": 30.0,
            "jitter": True,
            "jitter_factor": 0.2
        },
        "sensor": {
            "max_attempts": 3,
            "strategy": "linear_backoff",
            "base_delay": 0.1,
            "max_delay": 1.0,
            "jitter": True,
            "jitter_factor": 0.1
        },
        "i2c": {
            "max_attempts": 5,
            "strategy": "exponential_backoff",
            "base_delay": 0.02,
            "max_delay": 0.5,
            "jitter": True,
            "jitter_factor": 0.05
        },
        "gps": {
            "max_attempts": 3,
            "strategy": "fixed_delay",
            "base_delay": 5.0,
            "max_delay": 5.0,
            "jitter": False
        }
    }
}