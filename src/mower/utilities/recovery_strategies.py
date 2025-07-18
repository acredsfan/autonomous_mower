"""
Automatic Resource Recovery Strategies for the autonomous mower.

This module implements automatic recovery mechanisms for various hardware
and software components, including sensor recalibration, hardware resets,
and component-specific recovery procedures.
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Type, Union

from mower.utilities.logger_config import LoggerConfigInfo

logger = LoggerConfigInfo.get_logger(__name__)


class RecoveryResult(Enum):
    """Results of recovery attempts"""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    RETRY_LATER = "retry_later"
    NOT_APPLICABLE = "not_applicable"


@dataclass
class RecoveryContext:
    """Context information for recovery operations"""
    component_name: str
    error_info: Dict[str, Any]
    failure_count: int
    last_failure_time: datetime
    component_instance: Any
    additional_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryAttempt:
    """Record of a recovery attempt"""
    timestamp: datetime
    strategy_name: str
    result: RecoveryResult
    duration: timedelta
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


class RecoveryStrategy(ABC):
    """Abstract base class for recovery strategies"""
    
    def __init__(self, name: str, max_attempts: int = 3, cooldown_period: float = 60.0):
        self.name = name
        self.max_attempts = max_attempts
        self.cooldown_period = cooldown_period
        self.logger = LoggerConfigInfo.get_logger(f"{__name__}.{name}")
        self._attempt_history: List[RecoveryAttempt] = []
    
    @abstractmethod
    async def can_recover(self, context: RecoveryContext) -> bool:
        """Check if this strategy can handle the given failure"""
        pass
    
    @abstractmethod
    async def execute_recovery(self, context: RecoveryContext) -> RecoveryResult:
        """Execute the recovery procedure"""
        pass
    
    async def attempt_recovery(self, context: RecoveryContext) -> RecoveryResult:
        """Attempt recovery with logging and error handling"""
        if not await self.can_recover(context):
            return RecoveryResult.NOT_APPLICABLE
        
        # Check cooldown period
        if self._is_in_cooldown():
            self.logger.info(f"Recovery strategy {self.name} is in cooldown period")
            return RecoveryResult.RETRY_LATER
        
        # Check max attempts
        recent_attempts = self._get_recent_attempts()
        if len(recent_attempts) >= self.max_attempts:
            self.logger.warning(f"Max recovery attempts ({self.max_attempts}) reached for {self.name}")
            return RecoveryResult.FAILED
        
        start_time = datetime.now()
        self.logger.info(f"Attempting recovery with strategy: {self.name}")
        
        try:
            result = await self.execute_recovery(context)
            duration = datetime.now() - start_time
            
            # Record attempt
            attempt = RecoveryAttempt(
                timestamp=start_time,
                strategy_name=self.name,
                result=result,
                duration=duration
            )
            self._attempt_history.append(attempt)
            
            self.logger.info(f"Recovery attempt completed: {result.value} (took {duration.total_seconds():.2f}s)")
            return result
            
        except Exception as e:
            duration = datetime.now() - start_time
            error_msg = str(e)
            
            # Record failed attempt
            attempt = RecoveryAttempt(
                timestamp=start_time,
                strategy_name=self.name,
                result=RecoveryResult.FAILED,
                duration=duration,
                error_message=error_msg
            )
            self._attempt_history.append(attempt)
            
            self.logger.error(f"Recovery attempt failed: {error_msg}")
            return RecoveryResult.FAILED
    
    def _is_in_cooldown(self) -> bool:
        """Check if strategy is in cooldown period"""
        if not self._attempt_history:
            return False
        
        last_attempt = self._attempt_history[-1]
        time_since_last = (datetime.now() - last_attempt.timestamp).total_seconds()
        return time_since_last < self.cooldown_period
    
    def _get_recent_attempts(self, window_hours: int = 1) -> List[RecoveryAttempt]:
        """Get recent recovery attempts within the time window"""
        cutoff_time = datetime.now() - timedelta(hours=window_hours)
        return [attempt for attempt in self._attempt_history if attempt.timestamp > cutoff_time]
    
    def get_success_rate(self, window_hours: int = 24) -> float:
        """Get success rate over the specified time window"""
        recent_attempts = self._get_recent_attempts(window_hours)
        if not recent_attempts:
            return 0.0
        
        successful = sum(1 for attempt in recent_attempts if attempt.result == RecoveryResult.SUCCESS)
        return successful / len(recent_attempts)


class SensorRecalibrationStrategy(RecoveryStrategy):
    """Recovery strategy for sensor calibration issues"""
    
    def __init__(self):
        super().__init__("sensor_recalibration", max_attempts=2, cooldown_period=300.0)
    
    async def can_recover(self, context: RecoveryContext) -> bool:
        """Check if this is a calibration-related failure"""
        error_keywords = ["calibration", "drift", "offset", "accuracy", "precision"]
        error_info = str(context.error_info).lower()
        return any(keyword in error_info for keyword in error_keywords)
    
    async def execute_recovery(self, context: RecoveryContext) -> RecoveryResult:
        """Execute sensor recalibration"""
        component = context.component_instance
        
        # Try different calibration methods based on component type
        if hasattr(component, 'calibrate'):
            self.logger.info(f"Performing calibration for {context.component_name}")
            success = await self._run_in_executor(component.calibrate)
            return RecoveryResult.SUCCESS if success else RecoveryResult.FAILED
        
        elif hasattr(component, 'reset_calibration'):
            self.logger.info(f"Resetting calibration for {context.component_name}")
            await self._run_in_executor(component.reset_calibration)
            
            # Wait for stabilization
            await asyncio.sleep(5.0)
            
            # Verify calibration
            if hasattr(component, 'is_calibrated'):
                is_calibrated = await self._run_in_executor(component.is_calibrated)
                return RecoveryResult.SUCCESS if is_calibrated else RecoveryResult.PARTIAL
            
            return RecoveryResult.SUCCESS
        
        return RecoveryResult.NOT_APPLICABLE
    
    async def _run_in_executor(self, func, *args):
        """Run blocking function in executor"""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, func, *args)


class HardwareResetStrategy(RecoveryStrategy):
    """Recovery strategy for hardware reset operations"""
    
    def __init__(self):
        super().__init__("hardware_reset", max_attempts=1, cooldown_period=600.0)
    
    async def can_recover(self, context: RecoveryContext) -> bool:
        """Check if hardware reset is applicable"""
        # Hardware reset is a last resort for communication failures
        error_keywords = ["communication", "timeout", "no_response", "i2c", "serial", "connection"]
        error_info = str(context.error_info).lower()
        return any(keyword in error_info for keyword in error_keywords)
    
    async def execute_recovery(self, context: RecoveryContext) -> RecoveryResult:
        """Execute hardware reset"""
        component = context.component_instance
        
        # Try soft reset first
        if hasattr(component, 'soft_reset'):
            self.logger.info(f"Performing soft reset for {context.component_name}")
            try:
                await self._run_in_executor(component.soft_reset)
                await asyncio.sleep(2.0)  # Wait for reset to complete
                
                # Verify component is responsive
                if await self._verify_component_health(component):
                    return RecoveryResult.SUCCESS
            except Exception as e:
                self.logger.warning(f"Soft reset failed: {e}")
        
        # Try hard reset if available
        if hasattr(component, 'hard_reset'):
            self.logger.info(f"Performing hard reset for {context.component_name}")
            try:
                await self._run_in_executor(component.hard_reset)
                await asyncio.sleep(5.0)  # Wait longer for hard reset
                
                # Re-initialize component after hard reset
                if hasattr(component, 'initialize'):
                    await self._run_in_executor(component.initialize)
                
                # Verify component is responsive
                if await self._verify_component_health(component):
                    return RecoveryResult.SUCCESS
            except Exception as e:
                self.logger.error(f"Hard reset failed: {e}")
        
        return RecoveryResult.FAILED
    
    async def _verify_component_health(self, component) -> bool:
        """Verify component is healthy after reset"""
        try:
            if hasattr(component, 'health_check'):
                return await self._run_in_executor(component.health_check)
            elif hasattr(component, 'is_connected'):
                return await self._run_in_executor(component.is_connected)
            elif hasattr(component, 'test_communication'):
                return await self._run_in_executor(component.test_communication)
            else:
                # Basic test - try to read some data
                if hasattr(component, 'read_data'):
                    await self._run_in_executor(component.read_data)
                    return True
        except Exception:
            return False
        
        return True  # Assume healthy if no test methods available
    
    async def _run_in_executor(self, func, *args):
        """Run blocking function in executor"""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, func, *args)


class ConnectionRecoveryStrategy(RecoveryStrategy):
    """Recovery strategy for connection-related issues"""
    
    def __init__(self):
        super().__init__("connection_recovery", max_attempts=3, cooldown_period=120.0)
    
    async def can_recover(self, context: RecoveryContext) -> bool:
        """Check if this is a connection-related failure"""
        error_keywords = ["connection", "disconnect", "timeout", "unreachable", "network"]
        error_info = str(context.error_info).lower()
        return any(keyword in error_info for keyword in error_keywords)
    
    async def execute_recovery(self, context: RecoveryContext) -> RecoveryResult:
        """Execute connection recovery"""
        component = context.component_instance
        
        # Try to reconnect
        if hasattr(component, 'reconnect'):
            self.logger.info(f"Attempting to reconnect {context.component_name}")
            try:
                success = await self._run_in_executor(component.reconnect)
                if success:
                    return RecoveryResult.SUCCESS
            except Exception as e:
                self.logger.warning(f"Reconnect failed: {e}")
        
        # Try disconnect and connect sequence
        if hasattr(component, 'disconnect') and hasattr(component, 'connect'):
            self.logger.info(f"Attempting disconnect/connect sequence for {context.component_name}")
            try:
                await self._run_in_executor(component.disconnect)
                await asyncio.sleep(1.0)
                success = await self._run_in_executor(component.connect)
                if success:
                    return RecoveryResult.SUCCESS
            except Exception as e:
                self.logger.warning(f"Disconnect/connect sequence failed: {e}")
        
        # Try to reinitialize connection
        if hasattr(component, 'initialize_connection'):
            self.logger.info(f"Attempting to reinitialize connection for {context.component_name}")
            try:
                await self._run_in_executor(component.initialize_connection)
                return RecoveryResult.SUCCESS
            except Exception as e:
                self.logger.warning(f"Connection reinitialization failed: {e}")
        
        return RecoveryResult.FAILED
    
    async def _run_in_executor(self, func, *args):
        """Run blocking function in executor"""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, func, *args)


class ServiceRestartStrategy(RecoveryStrategy):
    """Recovery strategy for restarting services"""
    
    def __init__(self):
        super().__init__("service_restart", max_attempts=2, cooldown_period=300.0)
    
    async def can_recover(self, context: RecoveryContext) -> bool:
        """Check if service restart is applicable"""
        # Service restart for software components
        error_keywords = ["service", "process", "thread", "deadlock", "hang", "unresponsive"]
        error_info = str(context.error_info).lower()
        return any(keyword in error_info for keyword in error_keywords)
    
    async def execute_recovery(self, context: RecoveryContext) -> RecoveryResult:
        """Execute service restart"""
        component = context.component_instance
        
        # Try graceful restart
        if hasattr(component, 'restart'):
            self.logger.info(f"Performing graceful restart for {context.component_name}")
            try:
                await self._run_in_executor(component.restart)
                await asyncio.sleep(3.0)  # Wait for restart
                return RecoveryResult.SUCCESS
            except Exception as e:
                self.logger.warning(f"Graceful restart failed: {e}")
        
        # Try stop and start sequence
        if hasattr(component, 'stop') and hasattr(component, 'start'):
            self.logger.info(f"Performing stop/start sequence for {context.component_name}")
            try:
                await self._run_in_executor(component.stop)
                await asyncio.sleep(2.0)
                await self._run_in_executor(component.start)
                await asyncio.sleep(3.0)
                return RecoveryResult.SUCCESS
            except Exception as e:
                self.logger.warning(f"Stop/start sequence failed: {e}")
        
        return RecoveryResult.FAILED
    
    async def _run_in_executor(self, func, *args):
        """Run blocking function in executor"""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, func, *args)


class RecoveryStrategyRegistry:
    """Registry for managing recovery strategies"""
    
    def __init__(self):
        self.logger = LoggerConfigInfo.get_logger(__name__)
        self._strategies: Dict[str, RecoveryStrategy] = {}
        self._component_strategies: Dict[str, List[str]] = {}
        
        # Register default strategies
        self._register_default_strategies()
    
    def _register_default_strategies(self):
        """Register default recovery strategies"""
        default_strategies = [
            SensorRecalibrationStrategy(),
            ConnectionRecoveryStrategy(),
            ServiceRestartStrategy(),
            HardwareResetStrategy(),  # Last resort
        ]
        
        for strategy in default_strategies:
            self.register_strategy(strategy)
    
    def register_strategy(self, strategy: RecoveryStrategy):
        """Register a recovery strategy"""
        self._strategies[strategy.name] = strategy
        self.logger.info(f"Registered recovery strategy: {strategy.name}")
    
    def register_component_strategies(self, component_name: str, strategy_names: List[str]):
        """Register specific strategies for a component"""
        self._component_strategies[component_name] = strategy_names
        self.logger.info(f"Registered strategies for {component_name}: {strategy_names}")
    
    def get_strategies_for_component(self, component_name: str) -> List[RecoveryStrategy]:
        """Get applicable strategies for a component"""
        # Get component-specific strategies if defined
        if component_name in self._component_strategies:
            strategy_names = self._component_strategies[component_name]
            return [self._strategies[name] for name in strategy_names if name in self._strategies]
        
        # Return all strategies if no specific ones defined
        return list(self._strategies.values())
    
    async def attempt_recovery(self, context: RecoveryContext) -> RecoveryResult:
        """Attempt recovery using applicable strategies"""
        strategies = self.get_strategies_for_component(context.component_name)
        
        # Sort strategies by priority (based on success rate and type)
        strategies.sort(key=lambda s: (s.get_success_rate(), self._get_strategy_priority(s)), reverse=True)
        
        self.logger.info(f"Attempting recovery for {context.component_name} using {len(strategies)} strategies")
        
        for strategy in strategies:
            try:
                result = await strategy.attempt_recovery(context)
                
                if result == RecoveryResult.SUCCESS:
                    self.logger.info(f"Recovery successful using strategy: {strategy.name}")
                    return result
                elif result == RecoveryResult.PARTIAL:
                    self.logger.info(f"Partial recovery achieved using strategy: {strategy.name}")
                    # Continue with other strategies to see if we can achieve full recovery
                elif result == RecoveryResult.RETRY_LATER:
                    self.logger.info(f"Strategy {strategy.name} suggests retry later")
                    continue
                elif result == RecoveryResult.NOT_APPLICABLE:
                    continue
                else:
                    self.logger.warning(f"Strategy {strategy.name} failed")
                    
            except Exception as e:
                self.logger.error(f"Error executing recovery strategy {strategy.name}: {e}")
                continue
        
        self.logger.error(f"All recovery strategies failed for {context.component_name}")
        return RecoveryResult.FAILED
    
    def _get_strategy_priority(self, strategy: RecoveryStrategy) -> int:
        """Get priority score for strategy ordering"""
        # Lower numbers = higher priority
        priority_map = {
            "connection_recovery": 1,
            "sensor_recalibration": 2,
            "service_restart": 3,
            "hardware_reset": 4,  # Last resort
        }
        return priority_map.get(strategy.name, 5)
    
    def get_strategy_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all strategies"""
        stats = {}
        for name, strategy in self._strategies.items():
            recent_attempts = strategy._get_recent_attempts(24)
            stats[name] = {
                "total_attempts": len(strategy._attempt_history),
                "recent_attempts": len(recent_attempts),
                "success_rate_24h": strategy.get_success_rate(24),
                "success_rate_1h": strategy.get_success_rate(1),
                "last_attempt": strategy._attempt_history[-1].timestamp.isoformat() if strategy._attempt_history else None,
                "in_cooldown": strategy._is_in_cooldown()
            }
        return stats


# Global registry instance
_recovery_registry = RecoveryStrategyRegistry()


def get_recovery_registry() -> RecoveryStrategyRegistry:
    """Get the global recovery strategy registry"""
    return _recovery_registry


async def attempt_component_recovery(
    component_name: str,
    component_instance: Any,
    error_info: Dict[str, Any],
    failure_count: int = 1
) -> RecoveryResult:
    """Convenience function to attempt recovery for a component"""
    context = RecoveryContext(
        component_name=component_name,
        error_info=error_info,
        failure_count=failure_count,
        last_failure_time=datetime.now(),
        component_instance=component_instance
    )
    
    registry = get_recovery_registry()
    return await registry.attempt_recovery(context)