"""
Unit tests for retry policy engine.
"""

import asyncio
import pytest
import time
from unittest.mock import Mock, patch

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


class TestRetryPolicy:
    """Test cases for RetryPolicy class."""
    
    def test_init_default_values(self):
        """Test retry policy initialization with default values."""
        policy = RetryPolicy()
        
        assert policy.max_attempts == 3
        assert policy.strategy == RetryStrategy.EXPONENTIAL_BACKOFF
        assert policy.base_delay == 1.0
        assert policy.max_delay == 60.0
        assert policy.expected_exceptions == Exception
        assert policy.jitter is True
        assert policy.jitter_factor == 0.1
        assert policy.on_retry is None
    
    def test_init_custom_values(self):
        """Test retry policy initialization with custom values."""
        on_retry = Mock()
        policy = RetryPolicy(
            max_attempts=5,
            strategy=RetryStrategy.LINEAR_BACKOFF,
            base_delay=0.5,
            max_delay=10.0,
            expected_exceptions=ValueError,
            jitter=False,
            jitter_factor=0.2,
            on_retry=on_retry
        )
        
        assert policy.max_attempts == 5
        assert policy.strategy == RetryStrategy.LINEAR_BACKOFF
        assert policy.base_delay == 0.5
        assert policy.max_delay == 10.0
        assert policy.expected_exceptions == ValueError
        assert policy.jitter is False
        assert policy.jitter_factor == 0.2
        assert policy.on_retry == on_retry
    
    def test_calculate_delay_fixed(self):
        """Test delay calculation for fixed delay strategy."""
        policy = RetryPolicy(
            strategy=RetryStrategy.FIXED_DELAY,
            base_delay=1.0,
            jitter=False
        )
        
        assert policy._calculate_delay(0) == 0.0
        assert policy._calculate_delay(1) == 1.0
        assert policy._calculate_delay(2) == 1.0
        assert policy._calculate_delay(3) == 1.0
    
    def test_calculate_delay_linear(self):
        """Test delay calculation for linear backoff strategy."""
        policy = RetryPolicy(
            strategy=RetryStrategy.LINEAR_BACKOFF,
            base_delay=1.0,
            jitter=False
        )
        
        assert policy._calculate_delay(0) == 0.0
        assert policy._calculate_delay(1) == 1.0
        assert policy._calculate_delay(2) == 2.0
        assert policy._calculate_delay(3) == 3.0
    
    def test_calculate_delay_exponential(self):
        """Test delay calculation for exponential backoff strategy."""
        policy = RetryPolicy(
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            base_delay=1.0,
            jitter=False
        )
        
        assert policy._calculate_delay(0) == 0.0
        assert policy._calculate_delay(1) == 1.0
        assert policy._calculate_delay(2) == 2.0
        assert policy._calculate_delay(3) == 4.0
        assert policy._calculate_delay(4) == 8.0
    
    def test_calculate_delay_fibonacci(self):
        """Test delay calculation for fibonacci backoff strategy."""
        policy = RetryPolicy(
            strategy=RetryStrategy.FIBONACCI_BACKOFF,
            base_delay=1.0,
            jitter=False
        )
        
        assert policy._calculate_delay(0) == 0.0
        assert policy._calculate_delay(1) == 1.0
        assert policy._calculate_delay(2) == 1.0
        assert policy._calculate_delay(3) == 2.0
        assert policy._calculate_delay(4) == 3.0
        assert policy._calculate_delay(5) == 5.0
    
    def test_calculate_delay_random(self):
        """Test delay calculation for random backoff strategy."""
        policy = RetryPolicy(
            strategy=RetryStrategy.RANDOM_BACKOFF,
            base_delay=1.0,
            jitter=False
        )
        
        # Random strategy should return a value between base_delay and base_delay * attempt
        assert policy._calculate_delay(0) == 0.0
        
        # Test multiple times to ensure values are within expected range
        for _ in range(10):
            delay1 = policy._calculate_delay(1)
            assert 1.0 <= delay1 <= 1.0
            
            delay2 = policy._calculate_delay(2)
            assert 1.0 <= delay2 <= 2.0
            
            delay3 = policy._calculate_delay(3)
            assert 1.0 <= delay3 <= 3.0
    
    def test_calculate_delay_with_jitter(self):
        """Test delay calculation with jitter."""
        policy = RetryPolicy(
            strategy=RetryStrategy.FIXED_DELAY,
            base_delay=1.0,
            jitter=True,
            jitter_factor=0.5
        )
        
        # With 50% jitter, delay should be between 0.5 and 1.5
        for _ in range(10):
            delay = policy._calculate_delay(1)
            assert 0.5 <= delay <= 1.5
    
    def test_calculate_delay_max_delay(self):
        """Test delay calculation respects max_delay."""
        policy = RetryPolicy(
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            base_delay=1.0,
            max_delay=5.0,
            jitter=False
        )
        
        assert policy._calculate_delay(4) == 5.0  # Would be 8.0 without max_delay
        assert policy._calculate_delay(5) == 5.0  # Would be 16.0 without max_delay
    
    def test_execute_success_first_attempt(self):
        """Test execute with success on first attempt."""
        policy = RetryPolicy()
        mock_func = Mock(return_value="success")
        
        result = policy.execute(mock_func, "arg1", kwarg1="value1")
        
        assert result.success is True
        assert result.value == "success"
        assert result.exception is None
        assert result.attempts == 1
        assert result.total_delay == 0.0
        mock_func.assert_called_once_with("arg1", kwarg1="value1")
    
    def test_execute_success_after_retries(self):
        """Test execute with success after retries."""
        policy = RetryPolicy(
            max_attempts=3,
            strategy=RetryStrategy.FIXED_DELAY,
            base_delay=0.01,  # Small delay for testing
            jitter=False
        )
        
        # Mock function that fails twice then succeeds
        mock_func = Mock(side_effect=[ValueError("error"), ValueError("error"), "success"])
        
        result = policy.execute(mock_func)
        
        assert result.success is True
        assert result.value == "success"
        assert result.exception is None
        assert result.attempts == 3
        assert result.total_delay > 0.0
        assert mock_func.call_count == 3
    
    def test_execute_all_attempts_fail(self):
        """Test execute when all attempts fail."""
        policy = RetryPolicy(
            max_attempts=2,
            strategy=RetryStrategy.FIXED_DELAY,
            base_delay=0.01,  # Small delay for testing
            jitter=False
        )
        
        # Mock function that always fails
        mock_func = Mock(side_effect=ValueError("error"))
        
        result = policy.execute(mock_func)
        
        assert result.success is False
        assert result.value is None
        assert isinstance(result.exception, ValueError)
        assert str(result.exception) == "error"
        assert result.attempts == 2
        assert result.total_delay > 0.0
        assert mock_func.call_count == 2
    
    def test_execute_unexpected_exception(self):
        """Test execute with unexpected exception type."""
        policy = RetryPolicy(
            expected_exceptions=ValueError
        )
        
        # Mock function that raises TypeError (not in expected_exceptions)
        mock_func = Mock(side_effect=TypeError("type error"))
        
        result = policy.execute(mock_func)
        
        assert result.success is False
        assert result.value is None
        assert isinstance(result.exception, TypeError)
        assert result.attempts == 1
        assert result.total_delay == 0.0
        mock_func.assert_called_once()
    
    def test_on_retry_callback(self):
        """Test on_retry callback is called."""
        on_retry = Mock()
        policy = RetryPolicy(
            max_attempts=2,
            strategy=RetryStrategy.FIXED_DELAY,
            base_delay=0.01,
            jitter=False,
            on_retry=on_retry
        )
        
        # Mock function that always fails
        mock_func = Mock(side_effect=ValueError("error"))
        
        policy.execute(mock_func)
        
        on_retry.assert_called_once()
        args = on_retry.call_args[0]
        assert args[0] == 1  # attempt number
        assert isinstance(args[1], ValueError)  # exception
        assert args[2] == 0.01  # delay
    
    @pytest.mark.asyncio
    async def test_execute_async_success(self):
        """Test execute_async with success."""
        policy = RetryPolicy()
        
        async def async_func():
            return "async success"
        
        result = await policy.execute_async(async_func)
        
        assert result.success is True
        assert result.value == "async success"
        assert result.attempts == 1
    
    @pytest.mark.asyncio
    async def test_execute_async_with_retries(self):
        """Test execute_async with retries."""
        policy = RetryPolicy(
            max_attempts=3,
            strategy=RetryStrategy.FIXED_DELAY,
            base_delay=0.01,
            jitter=False
        )
        
        # Counter to track calls
        call_count = 0
        
        async def async_func_with_failures():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError(f"error on attempt {call_count}")
            return "async success"
        
        result = await policy.execute_async(async_func_with_failures)
        
        assert result.success is True
        assert result.value == "async success"
        assert result.attempts == 3
        assert call_count == 3


class TestRetryPolicyEngine:
    """Test cases for RetryPolicyEngine class."""
    
    def test_register_and_get_policy(self):
        """Test registering and retrieving policies."""
        engine = RetryPolicyEngine()
        policy = RetryPolicy(max_attempts=5)
        
        engine.register_policy("test_policy", policy)
        retrieved = engine.get_policy("test_policy")
        
        assert retrieved is policy
        assert retrieved.max_attempts == 5
        
        # Non-existent policy should return None
        assert engine.get_policy("non_existent") is None
    
    def test_set_default_policy(self):
        """Test setting default policy."""
        engine = RetryPolicyEngine()
        default_policy = RetryPolicy(max_attempts=10)
        
        engine.set_default_policy(default_policy)
        
        # Execute should use default policy
        mock_func = Mock(return_value="success")
        result = engine.execute(mock_func)
        
        assert result == "success"
        mock_func.assert_called_once()
    
    def test_execute_with_named_policy(self):
        """Test execute with named policy."""
        engine = RetryPolicyEngine()
        policy = RetryPolicy(max_attempts=5)
        engine.register_policy("test_policy", policy)
        
        mock_func = Mock(return_value="success")
        result = engine.execute(mock_func, policy_name="test_policy")
        
        assert result == "success"
        mock_func.assert_called_once()
    
    def test_execute_with_retries(self):
        """Test execute with retries."""
        engine = RetryPolicyEngine()
        policy = RetryPolicy(
            max_attempts=3,
            strategy=RetryStrategy.FIXED_DELAY,
            base_delay=0.01,
            jitter=False
        )
        engine.register_policy("retry_policy", policy)
        
        # Mock function that fails twice then succeeds
        mock_func = Mock(side_effect=[ValueError("error"), ValueError("error"), "success"])
        
        result = engine.execute(mock_func, policy_name="retry_policy")
        
        assert result == "success"
        assert mock_func.call_count == 3
    
    def test_execute_all_attempts_fail(self):
        """Test execute when all attempts fail."""
        engine = RetryPolicyEngine()
        policy = RetryPolicy(
            max_attempts=2,
            strategy=RetryStrategy.FIXED_DELAY,
            base_delay=0.01,
            jitter=False
        )
        engine.register_policy("fail_policy", policy)
        
        # Mock function that always fails
        mock_func = Mock(side_effect=ValueError("error"))
        
        with pytest.raises(ValueError):
            engine.execute(mock_func, policy_name="fail_policy")
        
        assert mock_func.call_count == 2
    
    @pytest.mark.asyncio
    async def test_execute_async(self):
        """Test execute_async with named policy."""
        engine = RetryPolicyEngine()
        policy = RetryPolicy(max_attempts=3)
        engine.register_policy("async_policy", policy)
        
        async def async_func():
            return "async success"
        
        result = await engine.execute_async(async_func, policy_name="async_policy")
        
        assert result == "async success"
    
    def test_load_from_config(self):
        """Test loading policies from configuration."""
        engine = RetryPolicyEngine()
        
        config = {
            "retry_policies": {
                "default": {
                    "max_attempts": 5,
                    "strategy": "exponential_backoff",
                    "base_delay": 2.0,
                    "max_delay": 30.0,
                    "jitter": True
                },
                "custom": {
                    "max_attempts": 3,
                    "strategy": "linear_backoff",
                    "base_delay": 0.5,
                    "max_delay": 5.0,
                    "jitter": False
                }
            }
        }
        
        engine.load_from_config(config)
        
        # Check default policy was updated
        assert engine._default_policy.max_attempts == 5
        assert engine._default_policy.base_delay == 2.0
        
        # Check custom policy was registered
        custom_policy = engine.get_policy("custom")
        assert custom_policy is not None
        assert custom_policy.max_attempts == 3
        assert custom_policy.strategy == RetryStrategy.LINEAR_BACKOFF
        assert custom_policy.jitter is False


class TestRetryDecorators:
    """Test cases for retry decorators."""
    
    def test_with_retry_decorator(self):
        """Test with_retry decorator."""
        @with_retry(max_attempts=2, base_delay=0.01)
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("error")
            return "success"
        
        call_count = 0
        result = test_func()
        
        assert result == "success"
        assert call_count == 2
    
    def test_with_retry_all_attempts_fail(self):
        """Test with_retry when all attempts fail."""
        @with_retry(max_attempts=2, base_delay=0.01)
        def test_func():
            raise ValueError("error")
        
        with pytest.raises(ValueError):
            test_func()
    
    def test_with_retry_named_policy(self):
        """Test with_retry using named policy."""
        engine = get_retry_policy_engine()
        policy = RetryPolicy(max_attempts=2, base_delay=0.01)
        engine.register_policy("test_policy", policy)
        
        @with_retry(policy_name="test_policy")
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("error")
            return "success"
        
        call_count = 0
        result = test_func()
        
        assert result == "success"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_with_retry_async(self):
        """Test with_retry on async function."""
        @with_retry(max_attempts=2, base_delay=0.01)
        async def test_async_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("error")
            return "async success"
        
        call_count = 0
        result = await test_async_func()
        
        assert result == "async success"
        assert call_count == 2
    
    def test_network_retry_decorator(self):
        """Test network_retry decorator."""
        @network_retry(max_attempts=2, base_delay=0.01)
        def test_network_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("network error")
            return "connected"
        
        call_count = 0
        result = test_network_func()
        
        assert result == "connected"
        assert call_count == 2
    
    def test_sensor_retry_decorator(self):
        """Test sensor_retry decorator."""
        @sensor_retry(max_attempts=2, base_delay=0.01)
        def test_sensor_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise IOError("sensor error")
            return "sensor data"
        
        call_count = 0
        result = test_sensor_func()
        
        assert result == "sensor data"
        assert call_count == 2
    
    def test_i2c_retry_decorator(self):
        """Test i2c_retry decorator."""
        @i2c_retry(max_attempts=2, base_delay=0.01)
        def test_i2c_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise OSError("i2c error")
            return "i2c data"
        
        call_count = 0
        result = test_i2c_func()
        
        assert result == "i2c data"
        assert call_count == 2


class TestRetryIntegration:
    """Integration tests for retry functionality."""
    
    def test_global_engine_singleton(self):
        """Test that global engine is singleton."""
        engine1 = get_retry_policy_engine()
        engine2 = get_retry_policy_engine()
        
        assert engine1 is engine2
    
    def test_retry_result_boolean_context(self):
        """Test RetryResult in boolean context."""
        success_result = RetryResult(success=True, value="success")
        failure_result = RetryResult(success=False, exception=ValueError())
        
        assert bool(success_result) is True
        assert bool(failure_result) is False
        
        # Test in if statement
        if success_result:
            assert True
        else:
            assert False
        
        if failure_result:
            assert False
        else:
            assert True