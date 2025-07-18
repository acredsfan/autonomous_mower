"""
Integration tests for automatic recovery strategies.

Tests the recovery mechanism functionality including:
- Sensor recalibration procedures
- Hardware reset capabilities
- Connection recovery
- Service restart procedures
"""

import asyncio
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from mower.utilities.recovery_strategies import (
    RecoveryStrategyRegistry,
    SensorRecalibrationStrategy,
    HardwareResetStrategy,
    ConnectionRecoveryStrategy,
    ServiceRestartStrategy,
    RecoveryContext,
    RecoveryResult,
    attempt_component_recovery,
    get_recovery_registry
)


class MockComponent:
    """Mock component for testing recovery strategies"""
    
    def __init__(self, name: str, capabilities: list = None):
        self.name = name
        self.capabilities = capabilities or []
        self.calibrated = False
        self.connected = True
        self.running = True
        self.reset_count = 0
        self.calibration_count = 0
        self.restart_count = 0
        
        # Add methods based on capabilities
        if "calibrate" in self.capabilities:
            self.calibrate = MagicMock(return_value=True)
        if "reset_calibration" in self.capabilities:
            self.reset_calibration = MagicMock()
        if "is_calibrated" in self.capabilities:
            self.is_calibrated = MagicMock(return_value=True)
        if "soft_reset" in self.capabilities:
            self.soft_reset = MagicMock()
        if "hard_reset" in self.capabilities:
            self.hard_reset = MagicMock()
        if "health_check" in self.capabilities:
            self.health_check = MagicMock(return_value=True)
        if "reconnect" in self.capabilities:
            self.reconnect = MagicMock(return_value=True)
        if "disconnect" in self.capabilities:
            self.disconnect = MagicMock()
        if "connect" in self.capabilities:
            self.connect = MagicMock(return_value=True)
        if "restart" in self.capabilities:
            self.restart = MagicMock()
        if "stop" in self.capabilities:
            self.stop = MagicMock()
        if "start" in self.capabilities:
            self.start = MagicMock()
        if "initialize" in self.capabilities:
            self.initialize = MagicMock()
        
        # Always add initialize method for hard reset scenarios
        if not hasattr(self, 'initialize'):
            self.initialize = MagicMock()


class TestSensorRecalibrationStrategy:
    """Test cases for SensorRecalibrationStrategy"""
    
    @pytest.fixture
    def strategy(self):
        """Create a sensor recalibration strategy for testing"""
        return SensorRecalibrationStrategy()
    
    @pytest.fixture
    def calibration_context(self):
        """Create a context for calibration-related failures"""
        component = MockComponent("test_sensor", ["calibrate", "is_calibrated"])
        return RecoveryContext(
            component_name="test_sensor",
            error_info={"error": "calibration drift detected"},
            failure_count=1,
            last_failure_time=datetime.now(),
            component_instance=component
        )
    
    @pytest.mark.asyncio
    async def test_can_recover_calibration_error(self, strategy, calibration_context):
        """Test detection of calibration-related errors"""
        assert await strategy.can_recover(calibration_context)
    
    @pytest.mark.asyncio
    async def test_cannot_recover_non_calibration_error(self, strategy):
        """Test rejection of non-calibration errors"""
        component = MockComponent("test_sensor")
        context = RecoveryContext(
            component_name="test_sensor",
            error_info={"error": "network timeout"},
            failure_count=1,
            last_failure_time=datetime.now(),
            component_instance=component
        )
        
        assert not await strategy.can_recover(context)
    
    @pytest.mark.asyncio
    async def test_successful_calibration_recovery(self, strategy, calibration_context):
        """Test successful calibration recovery"""
        result = await strategy.execute_recovery(calibration_context)
        
        assert result == RecoveryResult.SUCCESS
        calibration_context.component_instance.calibrate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_reset_calibration_recovery(self, strategy):
        """Test recovery using reset calibration"""
        component = MockComponent("test_sensor", ["reset_calibration", "is_calibrated"])
        context = RecoveryContext(
            component_name="test_sensor",
            error_info={"error": "calibration offset error"},
            failure_count=1,
            last_failure_time=datetime.now(),
            component_instance=component
        )
        
        result = await strategy.execute_recovery(context)
        
        assert result == RecoveryResult.SUCCESS
        component.reset_calibration.assert_called_once()
        component.is_calibrated.assert_called_once()


class TestHardwareResetStrategy:
    """Test cases for HardwareResetStrategy"""
    
    @pytest.fixture
    def strategy(self):
        """Create a hardware reset strategy for testing"""
        return HardwareResetStrategy()
    
    @pytest.fixture
    def reset_context(self):
        """Create a context for hardware reset scenarios"""
        component = MockComponent("test_hardware", ["soft_reset", "hard_reset", "health_check"])
        return RecoveryContext(
            component_name="test_hardware",
            error_info={"error": "i2c communication timeout"},
            failure_count=1,
            last_failure_time=datetime.now(),
            component_instance=component
        )
    
    @pytest.mark.asyncio
    async def test_can_recover_communication_error(self, strategy, reset_context):
        """Test detection of communication-related errors"""
        assert await strategy.can_recover(reset_context)
    
    @pytest.mark.asyncio
    async def test_successful_soft_reset(self, strategy, reset_context):
        """Test successful soft reset recovery"""
        result = await strategy.execute_recovery(reset_context)
        
        assert result == RecoveryResult.SUCCESS
        reset_context.component_instance.soft_reset.assert_called_once()
        reset_context.component_instance.health_check.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fallback_to_hard_reset(self, strategy):
        """Test fallback to hard reset when soft reset fails"""
        component = MockComponent("test_hardware", ["soft_reset", "hard_reset", "health_check", "initialize"])
        component.health_check.side_effect = [False, True]  # Fail after soft reset, succeed after hard reset
        
        context = RecoveryContext(
            component_name="test_hardware",
            error_info={"error": "serial communication failure"},
            failure_count=1,
            last_failure_time=datetime.now(),
            component_instance=component
        )
        
        result = await strategy.execute_recovery(context)
        
        assert result == RecoveryResult.SUCCESS
        component.soft_reset.assert_called_once()
        component.hard_reset.assert_called_once()
        component.initialize.assert_called_once()


class TestConnectionRecoveryStrategy:
    """Test cases for ConnectionRecoveryStrategy"""
    
    @pytest.fixture
    def strategy(self):
        """Create a connection recovery strategy for testing"""
        return ConnectionRecoveryStrategy()
    
    @pytest.fixture
    def connection_context(self):
        """Create a context for connection recovery scenarios"""
        component = MockComponent("test_connection", ["reconnect", "disconnect", "connect"])
        return RecoveryContext(
            component_name="test_connection",
            error_info={"error": "connection timeout"},
            failure_count=1,
            last_failure_time=datetime.now(),
            component_instance=component
        )
    
    @pytest.mark.asyncio
    async def test_can_recover_connection_error(self, strategy, connection_context):
        """Test detection of connection-related errors"""
        assert await strategy.can_recover(connection_context)
    
    @pytest.mark.asyncio
    async def test_successful_reconnect(self, strategy, connection_context):
        """Test successful reconnection"""
        result = await strategy.execute_recovery(connection_context)
        
        assert result == RecoveryResult.SUCCESS
        connection_context.component_instance.reconnect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_disconnect_connect_sequence(self, strategy):
        """Test disconnect/connect sequence when reconnect fails"""
        component = MockComponent("test_connection", ["reconnect", "disconnect", "connect"])
        component.reconnect.return_value = False  # Reconnect fails
        
        context = RecoveryContext(
            component_name="test_connection",
            error_info={"error": "network unreachable"},
            failure_count=1,
            last_failure_time=datetime.now(),
            component_instance=component
        )
        
        result = await strategy.execute_recovery(context)
        
        assert result == RecoveryResult.SUCCESS
        component.reconnect.assert_called_once()
        component.disconnect.assert_called_once()
        component.connect.assert_called_once()


class TestServiceRestartStrategy:
    """Test cases for ServiceRestartStrategy"""
    
    @pytest.fixture
    def strategy(self):
        """Create a service restart strategy for testing"""
        return ServiceRestartStrategy()
    
    @pytest.fixture
    def service_context(self):
        """Create a context for service restart scenarios"""
        component = MockComponent("test_service", ["restart", "stop", "start"])
        return RecoveryContext(
            component_name="test_service",
            error_info={"error": "service unresponsive"},
            failure_count=1,
            last_failure_time=datetime.now(),
            component_instance=component
        )
    
    @pytest.mark.asyncio
    async def test_can_recover_service_error(self, strategy, service_context):
        """Test detection of service-related errors"""
        assert await strategy.can_recover(service_context)
    
    @pytest.mark.asyncio
    async def test_successful_restart(self, strategy, service_context):
        """Test successful service restart"""
        result = await strategy.execute_recovery(service_context)
        
        assert result == RecoveryResult.SUCCESS
        service_context.component_instance.restart.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop_start_sequence(self, strategy):
        """Test stop/start sequence when restart fails"""
        component = MockComponent("test_service", ["restart", "stop", "start"])
        component.restart.side_effect = Exception("Restart failed")
        
        context = RecoveryContext(
            component_name="test_service",
            error_info={"error": "process deadlock"},
            failure_count=1,
            last_failure_time=datetime.now(),
            component_instance=component
        )
        
        result = await strategy.execute_recovery(context)
        
        assert result == RecoveryResult.SUCCESS
        component.restart.assert_called_once()
        component.stop.assert_called_once()
        component.start.assert_called_once()


class TestRecoveryStrategyRegistry:
    """Test cases for RecoveryStrategyRegistry"""
    
    @pytest.fixture
    def registry(self):
        """Create a fresh registry for testing"""
        return RecoveryStrategyRegistry()
    
    def test_default_strategies_registered(self, registry):
        """Test that default strategies are registered"""
        assert len(registry._strategies) > 0
        assert "sensor_recalibration" in registry._strategies
        assert "hardware_reset" in registry._strategies
        assert "connection_recovery" in registry._strategies
        assert "service_restart" in registry._strategies
    
    def test_register_custom_strategy(self, registry):
        """Test registering a custom strategy"""
        custom_strategy = SensorRecalibrationStrategy()
        custom_strategy.name = "custom_strategy"
        
        registry.register_strategy(custom_strategy)
        
        assert "custom_strategy" in registry._strategies
        assert registry._strategies["custom_strategy"] == custom_strategy
    
    def test_component_specific_strategies(self, registry):
        """Test component-specific strategy registration"""
        registry.register_component_strategies("gps_sensor", ["connection_recovery", "hardware_reset"])
        
        strategies = registry.get_strategies_for_component("gps_sensor")
        strategy_names = [s.name for s in strategies]
        
        assert len(strategies) == 2
        assert "connection_recovery" in strategy_names
        assert "hardware_reset" in strategy_names
    
    @pytest.mark.asyncio
    async def test_successful_recovery_attempt(self, registry):
        """Test successful recovery attempt"""
        component = MockComponent("test_component", ["calibrate"])
        context = RecoveryContext(
            component_name="test_component",
            error_info={"error": "calibration drift"},
            failure_count=1,
            last_failure_time=datetime.now(),
            component_instance=component
        )
        
        result = await registry.attempt_recovery(context)
        
        assert result == RecoveryResult.SUCCESS
        component.calibrate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_failed_recovery_attempt(self, registry):
        """Test failed recovery attempt"""
        component = MockComponent("test_component")  # No recovery capabilities
        context = RecoveryContext(
            component_name="test_component",
            error_info={"error": "unknown error"},
            failure_count=1,
            last_failure_time=datetime.now(),
            component_instance=component
        )
        
        result = await registry.attempt_recovery(context)
        
        assert result == RecoveryResult.FAILED
    
    def test_strategy_statistics(self, registry):
        """Test strategy statistics collection"""
        stats = registry.get_strategy_statistics()
        
        assert isinstance(stats, dict)
        assert len(stats) > 0
        
        for strategy_name, strategy_stats in stats.items():
            assert "total_attempts" in strategy_stats
            assert "recent_attempts" in strategy_stats
            assert "success_rate_24h" in strategy_stats
            assert "success_rate_1h" in strategy_stats
            assert "in_cooldown" in strategy_stats


class TestRecoveryIntegration:
    """Integration tests for the complete recovery system"""
    
    @pytest.mark.asyncio
    async def test_attempt_component_recovery_function(self):
        """Test the convenience function for component recovery"""
        component = MockComponent("test_component", ["calibrate"])
        
        result = await attempt_component_recovery(
            component_name="test_component",
            component_instance=component,
            error_info={"error": "calibration accuracy low"},
            failure_count=1
        )
        
        assert result == RecoveryResult.SUCCESS
        component.calibrate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_multiple_strategy_fallback(self):
        """Test fallback through multiple strategies"""
        # Component that fails calibration but succeeds with reset
        component = MockComponent("test_component", ["calibrate", "soft_reset", "health_check"])
        component.calibrate.return_value = False  # Calibration fails
        
        registry = RecoveryStrategyRegistry()
        context = RecoveryContext(
            component_name="test_component",
            error_info={"error": "calibration drift"},  # Only matches calibration strategy
            failure_count=1,
            last_failure_time=datetime.now(),
            component_instance=component
        )
        
        result = await registry.attempt_recovery(context)
        
        # Should try calibration strategy and fail, then try other strategies
        assert result == RecoveryResult.FAILED  # All strategies should fail since calibrate returns False
        component.calibrate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cooldown_period_enforcement(self):
        """Test that cooldown periods are enforced"""
        component = MockComponent("test_component", ["calibrate"])
        strategy = SensorRecalibrationStrategy()
        strategy.cooldown_period = 1.0  # 1 second cooldown
        
        context = RecoveryContext(
            component_name="test_component",
            error_info={"error": "calibration drift"},
            failure_count=1,
            last_failure_time=datetime.now(),
            component_instance=component
        )
        
        # First attempt should succeed
        result1 = await strategy.attempt_recovery(context)
        assert result1 == RecoveryResult.SUCCESS
        
        # Second attempt immediately should be in cooldown
        result2 = await strategy.attempt_recovery(context)
        assert result2 == RecoveryResult.RETRY_LATER
        
        # After cooldown period, should work again
        await asyncio.sleep(1.1)
        result3 = await strategy.attempt_recovery(context)
        assert result3 == RecoveryResult.SUCCESS
    
    @pytest.mark.asyncio
    async def test_max_attempts_enforcement(self):
        """Test that maximum attempts are enforced"""
        component = MockComponent("test_component", ["calibrate"])
        component.calibrate.return_value = False  # Always fail
        
        strategy = SensorRecalibrationStrategy()
        strategy.max_attempts = 2
        strategy.cooldown_period = 0.1  # Short cooldown for testing
        
        context = RecoveryContext(
            component_name="test_component",
            error_info={"error": "calibration drift"},
            failure_count=1,
            last_failure_time=datetime.now(),
            component_instance=component
        )
        
        # First two attempts should return FAILED
        result1 = await strategy.attempt_recovery(context)
        assert result1 == RecoveryResult.FAILED
        
        await asyncio.sleep(0.2)  # Wait for cooldown
        result2 = await strategy.attempt_recovery(context)
        assert result2 == RecoveryResult.FAILED
        
        # Third attempt should be rejected due to max attempts
        await asyncio.sleep(0.2)  # Wait for cooldown
        result3 = await strategy.attempt_recovery(context)
        assert result3 == RecoveryResult.FAILED
        
        # Should have called calibrate twice (max_attempts)
        assert component.calibrate.call_count == 2


if __name__ == "__main__":
    pytest.main([__file__])