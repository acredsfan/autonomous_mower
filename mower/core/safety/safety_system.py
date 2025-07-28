"""
Safety System - Centralized safety monitoring and control.

This module provides the highest priority safety system that can override
all other operations to ensure safe operation of the autonomous mower.
"""

import time
import logging
import threading
from typing import Dict, Any, Optional, Callable, List
from enum import Enum
from dataclasses import dataclass
from threading import Lock, Event

from mower.config.settings import get_config, SystemConfig
from mower.core.hal.hardware_manager import get_hardware_manager, SafetyViolationError


logger = logging.getLogger(__name__)


class SafetyLevel(Enum):
    """Safety alert levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class SafetyState(Enum):
    """System safety states."""
    SAFE = "safe"
    WARNING = "warning"
    ERROR = "error"
    EMERGENCY_STOP = "emergency_stop"
    SYSTEM_SHUTDOWN = "system_shutdown"


@dataclass
class SafetyEvent:
    """Safety event data structure."""
    timestamp: float
    level: SafetyLevel
    source: str
    message: str
    data: Optional[Dict[str, Any]] = None


class SafetyMonitor:
    """Monitors system safety conditions and triggers responses."""
    
    def __init__(self, config: SystemConfig):
        """Initialize safety monitor.
        
        Args:
            config: System configuration
        """
        self.config = config
        self._lock = Lock()
        self._running = False
        self._safety_state = SafetyState.SAFE
        self._last_command_time = 0.0
        self._last_sensor_time = 0.0
        self._last_vision_time = 0.0
        
        # Safety event handling
        self._safety_events: List[SafetyEvent] = []
        self._event_handlers: Dict[SafetyLevel, List[Callable]] = {
            level: [] for level in SafetyLevel
        }
        
        # Emergency stop handling
        self._emergency_stop_event = Event()
        self._shutdown_event = Event()
        
        # Monitoring thread
        self._monitor_thread: Optional[threading.Thread] = None
        
        # Hardware manager reference
        self._hardware_manager = None
    
    def start(self) -> None:
        """Start safety monitoring."""
        with self._lock:
            if self._running:
                return
            
            # Don't get hardware manager here to avoid circular dependency
            self._running = True
            self._emergency_stop_event.clear()
            self._shutdown_event.clear()
            
            # Start monitoring thread
            self._monitor_thread = threading.Thread(
                target=self._monitor_loop,
                name="SafetyMonitor",
                daemon=True
            )
            self._monitor_thread.start()
            
            logger.info("Safety monitor started")
    
    def stop(self) -> None:
        """Stop safety monitoring."""
        with self._lock:
            if not self._running:
                return
            
            self._running = False
            self._shutdown_event.set()
            
            # Wait for monitor thread to finish
            if self._monitor_thread and self._monitor_thread.is_alive():
                self._monitor_thread.join(timeout=5.0)
            
            logger.info("Safety monitor stopped")
    
    def _monitor_loop(self) -> None:
        """Main safety monitoring loop."""
        logger.info("Safety monitor loop started")
        while self._running and not self._shutdown_event.is_set():
            try:
                self._check_emergency_stop()
                self._check_command_timeout()
                self._check_sensor_timeout()
                self._check_vision_timeout()
                self._check_hardware_health()
                
                # Sleep for monitoring interval with early exit on shutdown
                if self._shutdown_event.wait(0.1):  # 10Hz monitoring with early exit
                    break
                    
            except Exception as e:
                logger.error(f"Safety monitor error: {e}")
                self._trigger_safety_event(
                    SafetyLevel.ERROR,
                    "SafetyMonitor",
                    f"Monitor loop error: {e}"
                )
        
        logger.info("Safety monitor loop stopped")
    
    def _check_emergency_stop(self) -> None:
        """Check emergency stop status."""
        if not self._hardware_manager:
            # Lazy initialization to avoid circular dependency
            try:
                self._hardware_manager = get_hardware_manager()
            except:
                return
        
        try:
            if self._hardware_manager.safety_controller.is_emergency_stop_active():
                if self._safety_state != SafetyState.EMERGENCY_STOP:
                    self._trigger_emergency_stop("Hardware emergency stop activated")
        except Exception as e:
            logger.error(f"Error checking emergency stop: {e}")
    
    def _check_command_timeout(self) -> None:
        """Check for command timeout."""
        if self._last_command_time == 0:
            return
        
        timeout = self.config.safety.command_timeout
        if time.time() - self._last_command_time > timeout:
            self._trigger_safety_event(
                SafetyLevel.WARNING,
                "CommandTimeout",
                f"No commands received for {timeout} seconds"
            )
            # Stop motors on command timeout
            self._emergency_stop_motors()
    
    def _check_sensor_timeout(self) -> None:
        """Check for sensor data timeout."""
        if self._last_sensor_time == 0:
            return
        
        timeout = self.config.safety.sensor_watchdog
        if time.time() - self._last_sensor_time > timeout:
            self._trigger_safety_event(
                SafetyLevel.WARNING,
                "SensorTimeout",
                f"No sensor data for {timeout} seconds"
            )
    
    def _check_vision_timeout(self) -> None:
        """Check for vision system timeout."""
        if self._last_vision_time == 0:
            return
        
        timeout = self.config.safety.vision_watchdog
        if time.time() - self._last_vision_time > timeout:
            self._trigger_safety_event(
                SafetyLevel.WARNING,
                "VisionTimeout",
                f"No vision data for {timeout} seconds"
            )
    
    def _check_hardware_health(self) -> None:
        """Check hardware component health."""
        if not self._hardware_manager:
            return
        
        try:
            if not self._hardware_manager.is_system_healthy():
                self._trigger_safety_event(
                    SafetyLevel.ERROR,
                    "HardwareHealth",
                    "Hardware system unhealthy"
                )
        except Exception as e:
            logger.error(f"Error checking hardware health: {e}")
    
    def _trigger_safety_event(self, level: SafetyLevel, source: str, 
                             message: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Trigger a safety event."""
        event = SafetyEvent(
            timestamp=time.time(),
            level=level,
            source=source,
            message=message,
            data=data
        )
        
        with self._lock:
            self._safety_events.append(event)
            # Keep only last 1000 events
            if len(self._safety_events) > 1000:
                self._safety_events = self._safety_events[-1000:]
        
        # Log the event
        log_func = {
            SafetyLevel.INFO: logger.info,
            SafetyLevel.WARNING: logger.warning,
            SafetyLevel.ERROR: logger.error,
            SafetyLevel.CRITICAL: logger.critical,
            SafetyLevel.EMERGENCY: logger.critical
        }.get(level, logger.info)
        
        log_func(f"Safety event [{level.value}] {source}: {message}")
        
        # Call event handlers
        for handler in self._event_handlers.get(level, []):
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Safety event handler error: {e}")
        
        # Take automatic action based on level
        if level == SafetyLevel.EMERGENCY:
            self._trigger_emergency_stop(message)
        elif level == SafetyLevel.CRITICAL:
            self._emergency_stop_motors()
    
    def _trigger_emergency_stop(self, reason: str) -> None:
        """Trigger emergency stop."""
        with self._lock:
            self._safety_state = SafetyState.EMERGENCY_STOP
            self._emergency_stop_event.set()
        
        logger.critical(f"EMERGENCY STOP TRIGGERED: {reason}")
        
        # Stop all motors immediately
        self._emergency_stop_motors()
        
        # Trigger emergency stop event
        self._trigger_safety_event(
            SafetyLevel.EMERGENCY,
            "EmergencyStop",
            reason
        )
    
    def _emergency_stop_motors(self) -> None:
        """Emergency stop all motors."""
        if self._hardware_manager:
            try:
                self._hardware_manager.motor_controller.stop_all_motors()
                logger.info("Motors stopped for safety")
            except Exception as e:
                logger.error(f"Failed to stop motors: {e}")
    
    def update_command_time(self) -> None:
        """Update last command time."""
        self._last_command_time = time.time()
    
    def update_sensor_time(self) -> None:
        """Update last sensor data time."""
        self._last_sensor_time = time.time()
    
    def update_vision_time(self) -> None:
        """Update last vision data time."""
        self._last_vision_time = time.time()
    
    def get_safety_state(self) -> SafetyState:
        """Get current safety state."""
        with self._lock:
            return self._safety_state
    
    def is_emergency_stop_active(self) -> bool:
        """Check if emergency stop is active."""
        return self._emergency_stop_event.is_set()
    
    def clear_emergency_stop(self) -> bool:
        """Clear emergency stop if safe to do so."""
        with self._lock:
            # Check if it's safe to clear emergency stop
            if (self._hardware_manager and 
                not self._hardware_manager.safety_controller.is_emergency_stop_active()):
                
                self._emergency_stop_event.clear()
                self._safety_state = SafetyState.SAFE
                
                logger.info("Emergency stop cleared")
                return True
            
            return False
    
    def get_recent_events(self, count: int = 100) -> List[SafetyEvent]:
        """Get recent safety events."""
        with self._lock:
            return self._safety_events[-count:]
    
    def add_event_handler(self, level: SafetyLevel, handler: Callable[[SafetyEvent], None]) -> None:
        """Add safety event handler."""
        self._event_handlers[level].append(handler)
    
    def remove_event_handler(self, level: SafetyLevel, handler: Callable[[SafetyEvent], None]) -> None:
        """Remove safety event handler."""
        if handler in self._event_handlers[level]:
            self._event_handlers[level].remove(handler)


class SafetyValidator:
    """Validates motor commands and other operations for safety."""
    
    def __init__(self, config: SystemConfig):
        """Initialize safety validator.
        
        Args:
            config: System configuration
        """
        self.config = config
        self._lock = Lock()
    
    def validate_motor_command(self, steering: int, throttle: int, blade: int = 0) -> bool:
        """Validate motor command for safety.
        
        Args:
            steering: Steering PWM value
            throttle: Throttle PWM value
            blade: Blade PWM value
            
        Returns:
            True if command is safe, False otherwise.
            
        Raises:
            SafetyViolationError: If command violates safety limits
        """
        with self._lock:
            # Check steering range
            min_steer, max_steer = self.config.hardware.steering_range
            if not min_steer <= steering <= max_steer:
                raise SafetyViolationError(
                    f"Steering {steering} outside safe range [{min_steer}, {max_steer}]"
                )
            
            # Check throttle range
            min_throttle, max_throttle = self.config.hardware.throttle_range
            if not min_throttle <= throttle <= max_throttle:
                raise SafetyViolationError(
                    f"Throttle {throttle} outside safe range [{min_throttle}, {max_throttle}]"
                )
            
            # Check blade range
            min_blade, max_blade = self.config.hardware.blade_range
            if not min_blade <= blade <= max_blade:
                raise SafetyViolationError(
                    f"Blade {blade} outside safe range [{min_blade}, {max_blade}]"
                )
            
            # Check maximum speed
            if abs(throttle) > self.config.hardware.max_speed:
                raise SafetyViolationError(
                    f"Throttle {abs(throttle)} exceeds maximum speed {self.config.hardware.max_speed}"
                )
            
            return True
    
    def validate_boundary_position(self, x: float, y: float, boundary_points: List[tuple]) -> bool:
        """Validate position is within safe boundaries.
        
        Args:
            x: X coordinate
            y: Y coordinate
            boundary_points: List of boundary points
            
        Returns:
            True if position is safe, False otherwise.
        """
        # Implement point-in-polygon check with safety buffer
        # This is a simplified version - full implementation would use proper
        # geometric algorithms
        
        buffer = self.config.safety.boundary_buffer
        # Add boundary validation logic here
        
        return True  # Placeholder


class SafetySystem:
    """Main safety system coordinating all safety components."""
    
    def __init__(self, config: Optional[SystemConfig] = None):
        """Initialize safety system.
        
        Args:
            config: System configuration
        """
        self.config = config or get_config()
        self.monitor = SafetyMonitor(self.config)
        self.validator = SafetyValidator(self.config)
        self._initialized = False
    
    def initialize(self) -> bool:
        """Initialize safety system."""
        try:
            self.monitor.start()
            self._initialized = True
            logger.info("Safety system initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize safety system: {e}")
            return False
    
    def shutdown(self) -> None:
        """Shutdown safety system."""
        try:
            self.monitor.stop()
            self._initialized = False
            logger.info("Safety system shutdown")
        except Exception as e:
            logger.error(f"Error shutting down safety system: {e}")
    
    def is_safe_to_operate(self) -> bool:
        """Check if it's safe to operate the mower."""
        if not self._initialized:
            return False
        
        return (self.monitor.get_safety_state() in [SafetyState.SAFE, SafetyState.WARNING] and
                not self.monitor.is_emergency_stop_active())
    
    def emergency_stop(self, reason: str = "Manual emergency stop") -> None:
        """Trigger emergency stop."""
        self.monitor._trigger_emergency_stop(reason)
    
    def clear_emergency_stop(self) -> bool:
        """Clear emergency stop if safe."""
        return self.monitor.clear_emergency_stop()
    
    def get_status(self) -> Dict[str, Any]:
        """Get safety system status."""
        return {
            "initialized": self._initialized,
            "safety_state": self.monitor.get_safety_state().value,
            "emergency_stop_active": self.monitor.is_emergency_stop_active(),
            "safe_to_operate": self.is_safe_to_operate(),
            "recent_events": [
                {
                    "timestamp": event.timestamp,
                    "level": event.level.value,
                    "source": event.source,
                    "message": event.message
                }
                for event in self.monitor.get_recent_events(10)
            ]
        }


# Global safety system instance
_safety_system: Optional[SafetySystem] = None

def get_safety_system(config: Optional[SystemConfig] = None) -> SafetySystem:
    """Get global safety system instance."""
    global _safety_system
    if _safety_system is None:
        _safety_system = SafetySystem(config)
    return _safety_system

def initialize_safety(config: Optional[SystemConfig] = None) -> bool:
    """Initialize safety system."""
    safety_system = get_safety_system(config)
    return safety_system.initialize()

def shutdown_safety() -> None:
    """Shutdown safety system."""
    global _safety_system
    if _safety_system:
        _safety_system.shutdown()
        _safety_system = None
