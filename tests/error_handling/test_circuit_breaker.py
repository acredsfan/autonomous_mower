"""
Unit tests for circuit breaker implementation.
"""

import asyncio
import pytest
import time
from unittest.mock import Mock, patch

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
from mower.error_handling.exceptions import HardwareError


class TestCircuitBreaker:
    """Test cases for CircuitBreaker class."""
    
    def test_init_enhanced_values(self):
        """Test circuit breaker initialization with enhanced parameters."""
        cb = CircuitBreaker(
            "test_enhanced",
            failure_threshold=3,
            timeout=30.0,
            expected_exception=ValueError,
            fallback=lambda: "fallback",
            half_open_success_threshold=2,
            reset_timeout=120.0,
            failure_window=60.0
        )
        
        assert cb.name == "test_enhanced"
        assert cb.failure_threshold == 3
        assert cb.timeout == 30.0
        assert cb.expected_exception == ValueError
        assert cb.half_open_success_threshold == 2
        assert cb.reset_timeout == 120.0
        assert cb.failure_window == 60.0
        assert callable(cb.fallback)
    
    def test_init_default_values(self):
        """Test circuit breaker initialization with default values."""
        cb = CircuitBreaker("test")
        
        assert cb.name == "test"
        assert cb.failure_threshold == 5
        assert cb.timeout == 60.0
        assert cb.expected_exception == Exception
        assert cb.fallback is None
        assert cb.failure_count == 0
        assert cb.last_failure_time is None
        assert cb.state == CircuitState.CLOSED
        assert cb.success_count == 0
    
    def test_init_custom_values(self):
        """Test circuit breaker initialization with custom values."""
        fallback = Mock()
        cb = CircuitBreaker(
            "test",
            failure_threshold=3,
            timeout=30.0,
            expected_exception=ValueError,
            fallback=fallback
        )
        
        assert cb.name == "test"
        assert cb.failure_threshold == 3
        assert cb.timeout == 30.0
        assert cb.expected_exception == ValueError
        assert cb.fallback == fallback
    
    def test_successful_call(self):
        """Test successful function call through circuit breaker."""
        cb = CircuitBreaker("test")
        mock_func = Mock(return_value="success")
        
        result = cb.call(mock_func, "arg1", kwarg1="value1")
        
        assert result == "success"
        mock_func.assert_called_once_with("arg1", kwarg1="value1")
        assert cb.failure_count == 0
        assert cb.state == CircuitState.CLOSED
    
    def test_failure_below_threshold(self):
        """Test function failure below threshold."""
        cb = CircuitBreaker("test", failure_threshold=3)
        mock_func = Mock(side_effect=ValueError("test error"))
        
        # First failure
        with pytest.raises(ValueError):
            cb.call(mock_func)
        
        assert cb.failure_count == 1
        assert cb.state == CircuitState.CLOSED
        assert cb.last_failure_time is not None
        
        # Second failure
        with pytest.raises(ValueError):
            cb.call(mock_func)
        
        assert cb.failure_count == 2
        assert cb.state == CircuitState.CLOSED
    
    def test_circuit_opens_at_threshold(self):
        """Test circuit opens when failure threshold is reached."""
        cb = CircuitBreaker("test", failure_threshold=2)
        mock_func = Mock(side_effect=ValueError("test error"))
        
        # Reach threshold
        with pytest.raises(ValueError):
            cb.call(mock_func)
        with pytest.raises(ValueError):
            cb.call(mock_func)
        
        assert cb.failure_count == 2
        assert cb.state == CircuitState.OPEN
        
        # Next call should fail fast
        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            cb.call(mock_func)
        
        assert "Circuit breaker 'test' is open" in str(exc_info.value)
        assert exc_info.value.circuit_name == "test"
        assert exc_info.value.failure_count == 2
        # Function should not be called when circuit is open
        assert mock_func.call_count == 2
    
    def test_circuit_transitions_to_half_open(self):
        """Test circuit transitions to half-open after timeout."""
        cb = CircuitBreaker("test", failure_threshold=1, timeout=0.1)
        mock_func = Mock(side_effect=ValueError("test error"))
        
        # Open the circuit
        with pytest.raises(ValueError):
            cb.call(mock_func)
        
        assert cb.state == CircuitState.OPEN
        
        # Wait for timeout
        time.sleep(0.2)
        
        # Next call should transition to half-open
        mock_func.side_effect = None
        mock_func.return_value = "success"
        
        result = cb.call(mock_func)
        
        assert result == "success"
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
    
    def test_half_open_success_closes_circuit(self):
        """Test successful call in half-open state closes circuit."""
        cb = CircuitBreaker("test", failure_threshold=1, timeout=0.1)
        mock_func = Mock()
        
        # Open circuit
        mock_func.side_effect = ValueError("error")
        with pytest.raises(ValueError):
            cb.call(mock_func)
        
        # Wait and transition to half-open
        time.sleep(0.2)
        mock_func.side_effect = None
        mock_func.return_value = "success"
        
        result = cb.call(mock_func)
        
        assert result == "success"
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
    
    def test_half_open_failure_reopens_circuit(self):
        """Test failure in half-open state reopens circuit."""
        cb = CircuitBreaker("test", failure_threshold=1, timeout=0.1)
        mock_func = Mock(side_effect=ValueError("error"))
        
        # Open circuit
        with pytest.raises(ValueError):
            cb.call(mock_func)
        
        # Wait for timeout
        time.sleep(0.2)
        
        # Failure in half-open should reopen circuit
        with pytest.raises(ValueError):
            cb.call(mock_func)
        
        assert cb.state == CircuitState.OPEN
        
        # Next call should fail fast
        with pytest.raises(CircuitBreakerOpenError):
            cb.call(mock_func)
    
    def test_fallback_function(self):
        """Test fallback function is called when circuit is open."""
        fallback = Mock(return_value="fallback_result")
        cb = CircuitBreaker("test", failure_threshold=1, fallback=fallback)
        mock_func = Mock(side_effect=ValueError("error"))
        
        # Open circuit
        with pytest.raises(ValueError):
            cb.call(mock_func)
        
        # Call with open circuit should use fallback
        result = cb.call(mock_func, "arg1", kwarg1="value1")
        
        assert result == "fallback_result"
        fallback.assert_called_once_with("arg1", kwarg1="value1")
    
    def test_expected_exception_filtering(self):
        """Test that only expected exceptions trigger circuit opening."""
        cb = CircuitBreaker("test", failure_threshold=1, expected_exception=ValueError)
        mock_func = Mock()
        
        # Non-expected exception should not trigger circuit
        mock_func.side_effect = TypeError("not expected")
        with pytest.raises(TypeError):
            cb.call(mock_func)
        
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
        
        # Expected exception should trigger circuit
        mock_func.side_effect = ValueError("expected")
        with pytest.raises(ValueError):
            cb.call(mock_func)
        
        assert cb.state == CircuitState.OPEN
        assert cb.failure_count == 1
    
    def test_reset_circuit(self):
        """Test manual circuit reset."""
        cb = CircuitBreaker("test", failure_threshold=1)
        mock_func = Mock(side_effect=ValueError("error"))
        
        # Open circuit
        with pytest.raises(ValueError):
            cb.call(mock_func)
        
        assert cb.state == CircuitState.OPEN
        
        # Reset circuit
        cb.reset()
        
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
        assert cb.last_failure_time is None
    
    def test_get_state(self):
        """Test getting circuit breaker state."""
        cb = CircuitBreaker("test", failure_threshold=3, timeout=60.0)
        
        state = cb.get_state()
        
        assert state["name"] == "test"
        assert state["state"] == "closed"
        assert state["failure_count"] == 0
        assert state["failure_threshold"] == 3
        assert state["timeout"] == 60.0
        assert state["timeout_remaining"] == 0.0
        assert state["last_failure_time"] is None
        assert state["success_count"] == 0
    
    @pytest.mark.asyncio
    async def test_async_call_success(self):
        """Test successful async function call."""
        cb = CircuitBreaker("test")
        
        async def async_func(arg):
            return f"async_{arg}"
        
        result = await cb.call_async(async_func, "test")
        
        assert result == "async_test"
        assert cb.state == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_async_call_failure(self):
        """Test async function failure."""
        cb = CircuitBreaker("test", failure_threshold=1)
        
        async def async_func():
            raise ValueError("async error")
        
        with pytest.raises(ValueError):
            await cb.call_async(async_func)
        
        assert cb.state == CircuitState.OPEN
        
        # Next call should fail fast
        with pytest.raises(CircuitBreakerOpenError):
            await cb.call_async(async_func)


class TestCircuitBreakerManager:
    """Test cases for CircuitBreakerManager class."""
    
    def test_create_breaker(self):
        """Test creating circuit breaker through manager."""
        manager = CircuitBreakerManager()
        
        breaker = manager.create_breaker("test", failure_threshold=3)
        
        assert breaker.name == "test"
        assert breaker.failure_threshold == 3
        assert manager.get_breaker("test") == breaker
    
    def test_create_existing_breaker(self):
        """Test getting existing circuit breaker."""
        manager = CircuitBreakerManager()
        
        breaker1 = manager.create_breaker("test")
        breaker2 = manager.create_breaker("test")
        
        assert breaker1 is breaker2
    
    def test_configure_defaults(self):
        """Test configuring default settings."""
        manager = CircuitBreakerManager()
        manager.configure_defaults(failure_threshold=10, timeout=120.0)
        
        breaker = manager.create_breaker("test")
        
        assert breaker.failure_threshold == 10
        assert breaker.timeout == 120.0
    
    def test_get_all_states(self):
        """Test getting all circuit breaker states."""
        manager = CircuitBreakerManager()
        manager.create_breaker("test1")
        manager.create_breaker("test2")
        
        states = manager.get_all_states()
        
        assert "test1" in states
        assert "test2" in states
        assert states["test1"]["name"] == "test1"
        assert states["test2"]["name"] == "test2"
    
    def test_reset_all(self):
        """Test resetting all circuit breakers."""
        manager = CircuitBreakerManager()
        breaker1 = manager.create_breaker("test1", failure_threshold=1)
        breaker2 = manager.create_breaker("test2", failure_threshold=1)
        
        # Open both circuits
        mock_func = Mock(side_effect=ValueError("error"))
        with pytest.raises(ValueError):
            breaker1.call(mock_func)
        with pytest.raises(ValueError):
            breaker2.call(mock_func)
        
        assert breaker1.state == CircuitState.OPEN
        assert breaker2.state == CircuitState.OPEN
        
        # Reset all
        manager.reset_all()
        
        assert breaker1.state == CircuitState.CLOSED
        assert breaker2.state == CircuitState.CLOSED


class TestCircuitBreakerDecorators:
    """Test cases for circuit breaker decorators."""
    
    def test_failure_window_functionality(self):
        """Test failure window functionality."""
        cb = CircuitBreaker("test_window", failure_threshold=3, failure_window=0.5)
        mock_func = Mock(side_effect=ValueError("error"))
        
        # First failure
        with pytest.raises(ValueError):
            cb.call(mock_func)
        
        assert cb.failure_count == 1
        assert cb.state == CircuitState.CLOSED
        
        # Second failure
        with pytest.raises(ValueError):
            cb.call(mock_func)
        
        assert cb.failure_count == 2
        assert cb.state == CircuitState.CLOSED
        
        # Wait for window to expire
        time.sleep(0.6)
        
        # This should reset the count since previous failures are outside the window
        with pytest.raises(ValueError):
            cb.call(mock_func)
        
        # Should be 1 again, not 3, because old failures expired
        assert cb.failure_count == 1
        assert cb.state == CircuitState.CLOSED
    
    def test_half_open_success_threshold(self):
        """Test half-open success threshold functionality."""
        cb = CircuitBreaker(
            "test_half_open", 
            failure_threshold=1, 
            timeout=0.1,
            half_open_success_threshold=2
        )
        mock_func = Mock()
        
        # Open circuit
        mock_func.side_effect = ValueError("error")
        with pytest.raises(ValueError):
            cb.call(mock_func)
        
        assert cb.state == CircuitState.OPEN
        
        # Wait for timeout
        time.sleep(0.2)
        
        # First success in half-open state
        mock_func.side_effect = None
        mock_func.return_value = "success"
        result = cb.call(mock_func)
        
        # Should still be in half-open state after first success
        assert result == "success"
        assert cb.state == CircuitState.HALF_OPEN
        assert cb.success_count == 1
        
        # Second success should close the circuit
        result = cb.call(mock_func)
        assert result == "success"
        assert cb.state == CircuitState.CLOSED
        assert cb.success_count == 0  # Reset after closing
    
    def test_reset_timeout_functionality(self):
        """Test reset timeout functionality."""
        cb = CircuitBreaker(
            "test_reset", 
            failure_threshold=3,
            reset_timeout=0.2
        )
        mock_func = Mock(side_effect=ValueError("error"))
        
        # First failure
        with pytest.raises(ValueError):
            cb.call(mock_func)
        
        assert cb.failure_count == 1
        
        # Wait for reset timeout
        time.sleep(0.3)
        
        # Success should reset failure count due to reset_timeout
        mock_func.side_effect = None
        mock_func.return_value = "success"
        result = cb.call(mock_func)
        
        assert result == "success"
        assert cb.failure_count == 0
    
    def test_circuit_breaker_decorator(self):
        """Test circuit breaker decorator."""
        @circuit_breaker("test_decorator", failure_threshold=1)
        def test_func():
            raise ValueError("error")
        
        # First call should fail and open circuit
        with pytest.raises(ValueError):
            test_func()
        
        # Second call should fail fast
        with pytest.raises(CircuitBreakerOpenError):
            test_func()
    
    def test_circuit_breaker_decorator_default_name(self):
        """Test circuit breaker decorator with default name."""
        @circuit_breaker(failure_threshold=1)
        def test_func():
            raise ValueError("error")
        
        with pytest.raises(ValueError):
            test_func()
        
        # Check that breaker was created with function name
        manager = get_circuit_breaker_manager()
        breaker_name = f"{test_func.__module__}.{test_func.__name__}"
        breaker = manager.get_breaker(breaker_name)
        assert breaker is not None
        assert breaker.state == CircuitState.OPEN
    
    def test_hardware_circuit_breaker_decorator(self):
        """Test hardware-specific circuit breaker decorator."""
        @hardware_circuit_breaker("hardware_test")
        def hardware_func():
            raise HardwareError("hardware failure")
        
        # Should have lower threshold and shorter timeout
        with pytest.raises(HardwareError):
            hardware_func()
        
        manager = get_circuit_breaker_manager()
        breaker = manager.get_breaker("hardware_test")
        assert breaker.failure_threshold == 3  # Lower than default
        assert breaker.timeout == 30.0  # Shorter than default
    
    @pytest.mark.asyncio
    async def test_async_circuit_breaker_decorator(self):
        """Test circuit breaker decorator with async function."""
        @circuit_breaker("async_test", failure_threshold=1)
        async def async_func():
            raise ValueError("async error")
        
        with pytest.raises(ValueError):
            await async_func()
        
        with pytest.raises(CircuitBreakerOpenError):
            await async_func()
    
    def test_circuit_breaker_with_fallback(self):
        """Test circuit breaker decorator with fallback."""
        def fallback_func():
            return "fallback"
        
        @circuit_breaker("fallback_test", failure_threshold=1, fallback=fallback_func)
        def test_func():
            raise ValueError("error")
        
        # Open circuit
        with pytest.raises(ValueError):
            test_func()
        
        # Should use fallback
        result = test_func()
        assert result == "fallback"


class TestSpecializedCircuitBreakers:
    """Test cases for specialized circuit breaker decorators."""
    
    def test_hardware_circuit_breaker(self):
        """Test hardware circuit breaker decorator."""
        @hardware_circuit_breaker("hardware_test_specialized")
        def hardware_func():
            raise HardwareError("hardware failure")
        
        # Should have hardware-specific settings
        with pytest.raises(HardwareError):
            hardware_func()
        
        manager = get_circuit_breaker_manager()
        breaker = manager.get_breaker("hardware_test_specialized")
        
        assert breaker.failure_threshold == 3
        assert breaker.timeout == 30.0
        assert breaker.half_open_success_threshold == 2
        assert breaker.reset_timeout == 300.0
        assert breaker.failure_window == 60.0
    
    def test_sensor_circuit_breaker(self):
        """Test sensor circuit breaker decorator."""
        @sensor_circuit_breaker("sensor_test")
        def sensor_func():
            raise HardwareError("sensor failure")
        
        # Should have sensor-specific settings
        with pytest.raises(HardwareError):
            sensor_func()
        
        manager = get_circuit_breaker_manager()
        breaker = manager.get_breaker("sensor_test")
        
        assert breaker.failure_threshold == 5  # Higher for sensors
        assert breaker.timeout == 15.0  # Shorter for sensors
        assert breaker.half_open_success_threshold == 1
        assert breaker.reset_timeout == 60.0
        assert breaker.failure_window == 30.0
    
    def test_motor_circuit_breaker(self):
        """Test motor circuit breaker decorator."""
        @motor_circuit_breaker("motor_test")
        def motor_func():
            raise HardwareError("motor failure")
        
        # Should have motor-specific settings
        with pytest.raises(HardwareError):
            motor_func()
        
        manager = get_circuit_breaker_manager()
        breaker = manager.get_breaker("motor_test")
        
        assert breaker.failure_threshold == 2  # Lower for motors
        assert breaker.timeout == 60.0  # Longer for motors
        assert breaker.half_open_success_threshold == 3  # More successes required
        assert breaker.reset_timeout == 600.0
        assert breaker.failure_window == 120.0
    
    def test_i2c_circuit_breaker(self):
        """Test I2C circuit breaker decorator."""
        @i2c_circuit_breaker("i2c_test")
        def i2c_func():
            raise HardwareError("i2c failure")
        
        # Should have I2C-specific settings
        with pytest.raises(HardwareError):
            i2c_func()
        
        manager = get_circuit_breaker_manager()
        breaker = manager.get_breaker("i2c_test")
        
        assert breaker.failure_threshold == 3
        assert breaker.timeout == 20.0
        assert breaker.half_open_success_threshold == 2
        assert breaker.reset_timeout == 120.0
        assert breaker.failure_window == 30.0


class TestCircuitBreakerIntegration:
    """Integration tests for circuit breaker functionality."""
    
    def test_global_manager_singleton(self):
        """Test that global manager is singleton."""
        manager1 = get_circuit_breaker_manager()
        manager2 = get_circuit_breaker_manager()
        
        assert manager1 is manager2
    
    def test_circuit_breaker_state_persistence(self):
        """Test that circuit breaker state persists across calls."""
        manager = get_circuit_breaker_manager()
        breaker = manager.create_breaker("persistent_test", failure_threshold=2)
        
        mock_func = Mock(side_effect=ValueError("error"))
        
        # First failure
        with pytest.raises(ValueError):
            breaker.call(mock_func)
        
        assert breaker.failure_count == 1
        
        # Get same breaker instance
        same_breaker = manager.get_breaker("persistent_test")
        assert same_breaker is breaker
        assert same_breaker.failure_count == 1
    
    def test_multiple_circuit_breakers_independence(self):
        """Test that multiple circuit breakers operate independently."""
        manager = get_circuit_breaker_manager()
        breaker1 = manager.create_breaker("independent1", failure_threshold=1)
        breaker2 = manager.create_breaker("independent2", failure_threshold=1)
        
        mock_func = Mock(side_effect=ValueError("error"))
        
        # Open first circuit
        with pytest.raises(ValueError):
            breaker1.call(mock_func)
        
        assert breaker1.state == CircuitState.OPEN
        assert breaker2.state == CircuitState.CLOSED
        
        # Second circuit should still work
        mock_func.side_effect = None
        mock_func.return_value = "success"
        
        result = breaker2.call(mock_func)
        assert result == "success"
        assert breaker2.state == CircuitState.CLOSED