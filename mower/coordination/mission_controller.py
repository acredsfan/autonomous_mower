"""
Mission Controller

This service coordinates all other services and manages the overall
system state machine for the autonomous mower.
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass

from mower.core.communication.base_service import BaseService, ServiceMessage
from mower.core.safety.safety_system import get_safety_system, SafetySystem
from mower.config.settings import SystemConfig


logger = logging.getLogger(__name__)


class SystemState(Enum):
    """Overall system states."""
    INITIALIZING = "initializing"
    IDLE = "idle"
    MANUAL_CONTROL = "manual_control"
    AUTONOMOUS_MOWING = "autonomous_mowing"
    RETURNING_HOME = "returning_home"
    EMERGENCY_STOP = "emergency_stop"
    ERROR = "error"
    SHUTDOWN = "shutdown"


@dataclass
class SystemStatus:
    """Complete system status."""
    state: SystemState
    services_online: Dict[str, bool]
    safety_status: str
    mission_active: bool
    battery_level: float
    error_message: Optional[str] = None


class MissionController(BaseService):
    """Central mission coordination service."""
    
    def __init__(self, service_name: str = "mission_controller", config: Optional[SystemConfig] = None):
        """Initialize mission controller."""
        super().__init__(service_name, config)
        
        # System state
        self.system_state = SystemState.INITIALIZING
        self.system_status = SystemStatus(
            state=SystemState.INITIALIZING,
            services_online={},
            safety_status="unknown",
            mission_active=False,
            battery_level=0.0
        )
        
        # Safety system
        self.safety_system: Optional[SafetySystem] = None
        
        # Service monitoring
        self.required_services = ["motor_control", "sensor", "vision", "navigation", "web"]
        self.service_health = {}
        self.last_health_check = 0.0
        
        # State machine timing
        self.state_entry_time = time.time()
        self.last_state_update = 0.0
        
        # Emergency handling
        self.emergency_triggered = False
        self.last_emergency_check = 0.0
        
        # Register message handlers
        self.register_message_handler("system_command", self.handle_system_command)
        self.register_message_handler("service_notification", self.handle_service_notification)
    
    async def service_initialize(self) -> bool:
        """Initialize mission controller."""
        try:
            # Connect to safety system
            self.safety_system = get_safety_system(self.config)
            
            # Wait for other services to start
            await self._wait_for_services()
            
            # Initialize system state
            self.system_state = SystemState.IDLE
            self.state_entry_time = time.time()
            
            logger.info("Mission controller initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Mission controller initialization failed: {e}")
            return False
    
    async def service_loop(self) -> None:
        """Main mission controller loop."""
        try:
            while not self.shutdown_event.is_set():
                # Update service health
                await self._update_service_health()
                
                # Check safety conditions
                await self._check_safety_conditions()
                
                # Process state machine
                await self._process_state_machine()
                
                # Update system status
                await self._update_system_status()
                
                # Publish status
                await self._publish_system_status()
                
                await asyncio.sleep(0.5)  # 2Hz coordination loop
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Mission controller loop error: {e}")
    
    async def service_cleanup(self) -> None:
        """Cleanup mission controller."""
        try:
            # Ensure all services are stopped safely
            await self._shutdown_all_services()
            
            logger.info("Mission controller cleanup complete")
            
        except Exception as e:
            logger.error(f"Mission controller cleanup error: {e}")
    
    async def _wait_for_services(self) -> None:
        """Wait for required services to come online."""
        logger.info("Waiting for services to start...")
        
        start_time = time.time()
        timeout = self.config.services.service_startup_timeout
        
        while time.time() - start_time < timeout:
            online_services = 0
            
            for service_name in self.required_services:
                if await self.wait_for_service(service_name, timeout=1.0):
                    online_services += 1
            
            if online_services >= len(self.required_services) - 1:  # Allow one service to be offline
                logger.info(f"Services online: {online_services}/{len(self.required_services)}")
                return
            
            await asyncio.sleep(1.0)
        
        logger.warning("Not all services came online within timeout")
    
    async def _update_service_health(self) -> None:
        """Update health status of all services."""
        if time.time() - self.last_health_check < 5.0:  # Check every 5 seconds
            return
        
        self.service_health.clear()
        
        for service_name in self.required_services:
            health = await self.get_service_health(service_name)
            self.service_health[service_name] = health is not None and health.state.value == "running"
        
        self.last_health_check = time.time()
    
    async def _check_safety_conditions(self) -> None:
        """Check overall safety conditions."""
        if time.time() - self.last_emergency_check < 1.0:  # Check every second
            return
        
        try:
            safety_issues = []
            
            # Check safety system
            if self.safety_system:
                if self.safety_system.monitor.is_emergency_stop_active():
                    safety_issues.append("Emergency stop active")
                
                if not self.safety_system.is_safe_to_operate():
                    safety_issues.append("Safety system reports unsafe conditions")
            
            # Check service health
            critical_services = ["motor_control", "sensor"]
            for service in critical_services:
                if not self.service_health.get(service, False):
                    safety_issues.append(f"Critical service {service} offline")
            
            # Check battery level
            if self.system_status.battery_level < 20.0:
                safety_issues.append("Low battery")
            
            # Trigger emergency if needed
            if safety_issues and not self.emergency_triggered:
                await self._trigger_emergency("; ".join(safety_issues))
            elif not safety_issues and self.emergency_triggered:
                await self._clear_emergency()
            
            self.last_emergency_check = time.time()
            
        except Exception as e:
            logger.error(f"Safety check error: {e}")
    
    async def _process_state_machine(self) -> None:
        """Process the main system state machine."""
        if time.time() - self.last_state_update < 0.5:  # Update at 2Hz
            return
        
        previous_state = self.system_state
        
        try:
            if self.system_state == SystemState.INITIALIZING:
                await self._handle_initializing_state()
            
            elif self.system_state == SystemState.IDLE:
                await self._handle_idle_state()
            
            elif self.system_state == SystemState.MANUAL_CONTROL:
                await self._handle_manual_control_state()
            
            elif self.system_state == SystemState.AUTONOMOUS_MOWING:
                await self._handle_autonomous_mowing_state()
            
            elif self.system_state == SystemState.RETURNING_HOME:
                await self._handle_returning_home_state()
            
            elif self.system_state == SystemState.EMERGENCY_STOP:
                await self._handle_emergency_stop_state()
            
            elif self.system_state == SystemState.ERROR:
                await self._handle_error_state()
            
            # Log state changes
            if self.system_state != previous_state:
                logger.info(f"State transition: {previous_state.value} -> {self.system_state.value}")
                self.state_entry_time = time.time()
            
            self.last_state_update = time.time()
            
        except Exception as e:
            logger.error(f"State machine error: {e}")
            await self._transition_to_error(str(e))
    
    async def _handle_initializing_state(self) -> None:
        """Handle system initialization state."""
        # Check if all critical services are online
        critical_services_online = all(
            self.service_health.get(service, False)
            for service in ["motor_control", "sensor"]
        )
        
        if critical_services_online:
            self.system_state = SystemState.IDLE
    
    async def _handle_idle_state(self) -> None:
        """Handle idle state."""
        # Monitor for commands to transition to other states
        # This would be triggered by external commands
        pass
    
    async def _handle_manual_control_state(self) -> None:
        """Handle manual control state."""
        # Monitor manual control activity
        # Auto-transition back to idle if no activity
        pass
    
    async def _handle_autonomous_mowing_state(self) -> None:
        """Handle autonomous mowing state."""
        # Monitor mission progress
        # Check for completion or errors
        pass
    
    async def _handle_returning_home_state(self) -> None:
        """Handle returning home state."""
        # Monitor return progress
        # Transition to idle when home
        pass
    
    async def _handle_emergency_stop_state(self) -> None:
        """Handle emergency stop state."""
        # Ensure all motors are stopped
        await self.send_message("motor_control", "emergency_stop", {})
        
        # Can only exit emergency state by clearing the emergency condition
        if not self.emergency_triggered:
            self.system_state = SystemState.IDLE
    
    async def _handle_error_state(self) -> None:
        """Handle error state."""
        # Attempt recovery or wait for manual intervention
        state_duration = time.time() - self.state_entry_time
        
        if state_duration > 60.0:  # Auto-recover after 1 minute
            self.system_state = SystemState.IDLE
            self.system_status.error_message = None
    
    async def _trigger_emergency(self, reason: str) -> None:
        """Trigger emergency stop."""
        self.emergency_triggered = True
        self.system_state = SystemState.EMERGENCY_STOP
        self.system_status.error_message = f"Emergency: {reason}"
        
        logger.critical(f"Emergency triggered: {reason}")
        
        # Notify all services
        for service in self.required_services:
            await self.send_message(service, "emergency_stop", {"reason": reason})
    
    async def _clear_emergency(self) -> None:
        """Clear emergency condition."""
        self.emergency_triggered = False
        self.system_status.error_message = None
        
        logger.info("Emergency condition cleared")
    
    async def _transition_to_error(self, error_message: str) -> None:
        """Transition to error state."""
        self.system_state = SystemState.ERROR
        self.system_status.error_message = error_message
        
        logger.error(f"System error: {error_message}")
    
    async def _update_system_status(self) -> None:
        """Update overall system status."""
        try:
            # Update service status
            self.system_status.services_online = self.service_health.copy()
            
            # Update safety status
            if self.safety_system:
                if self.safety_system.is_safe_to_operate():
                    self.system_status.safety_status = "safe"
                else:
                    self.system_status.safety_status = "unsafe"
            else:
                self.system_status.safety_status = "unknown"
            
            # Update battery level from sensor data
            if self.redis_client:
                sensor_data_str = await self.redis_client.get("service:sensor:data")
                if sensor_data_str:
                    sensor_data = json.loads(sensor_data_str)
                    if "battery" in sensor_data:
                        self.system_status.battery_level = sensor_data["battery"].get("percentage", 0.0)
            
            # Update mission status
            navigation_status_str = await self.redis_client.get("service:navigation:status")
            if navigation_status_str:
                navigation_status = json.loads(navigation_status_str)
                self.system_status.mission_active = navigation_status.get("mission_active", False)
            
            # Update state
            self.system_status.state = self.system_state
            
        except Exception as e:
            logger.error(f"System status update error: {e}")
    
    async def _publish_system_status(self) -> None:
        """Publish system status to Redis."""
        try:
            if self.redis_client:
                status_dict = {
                    "state": self.system_status.state.value,
                    "services_online": self.system_status.services_online,
                    "safety_status": self.system_status.safety_status,
                    "mission_active": self.system_status.mission_active,
                    "battery_level": self.system_status.battery_level,
                    "error_message": self.system_status.error_message,
                    "timestamp": time.time()
                }
                
                await self.redis_client.setex(
                    f"service:{self.service_name}:status",
                    5,  # 5 second TTL
                    json.dumps(status_dict)
                )
                
                # Also publish to system status key
                await self.redis_client.setex(
                    "system:status",
                    5,  # 5 second TTL
                    json.dumps(status_dict)
                )
        
        except Exception as e:
            logger.error(f"Status publishing error: {e}")
    
    async def _shutdown_all_services(self) -> None:
        """Shutdown all services safely."""
        try:
            # Stop any active missions
            await self.send_message("navigation", "stop_mission", {})
            
            # Stop all motors
            await self.send_message("motor_control", "stop_motors", {})
            
            # Notify services of shutdown
            for service in self.required_services:
                await self.send_message(service, "shutdown", {})
            
            logger.info("Shutdown commands sent to all services")
            
        except Exception as e:
            logger.error(f"Service shutdown error: {e}")
    
    async def handle_system_command(self, message: ServiceMessage) -> None:
        """Handle system-level commands."""
        try:
            command = message.data.get("command")
            
            if command == "start_manual_control":
                self.system_state = SystemState.MANUAL_CONTROL
                
            elif command == "start_autonomous_mowing":
                if self.system_status.safety_status == "safe":
                    self.system_state = SystemState.AUTONOMOUS_MOWING
                else:
                    await self.send_message(
                        message.service,
                        "command_response",
                        {"success": False, "message": "System not safe for autonomous operation"},
                        message.correlation_id
                    )
                    return
            
            elif command == "return_home":
                self.system_state = SystemState.RETURNING_HOME
                
            elif command == "emergency_stop":
                await self._trigger_emergency("Manual emergency stop")
                
            elif command == "clear_emergency":
                await self._clear_emergency()
                
            elif command == "shutdown":
                self.system_state = SystemState.SHUTDOWN
                await self._shutdown_all_services()
            
            # Send response
            await self.send_message(
                message.service,
                "command_response",
                {"success": True, "new_state": self.system_state.value},
                message.correlation_id
            )
            
        except Exception as e:
            logger.error(f"System command handling error: {e}")
    
    async def handle_service_notification(self, message: ServiceMessage) -> None:
        """Handle notifications from other services."""
        try:
            notification_type = message.data.get("type")
            
            if notification_type == "mission_complete":
                if self.system_state == SystemState.AUTONOMOUS_MOWING:
                    self.system_state = SystemState.IDLE
                    
            elif notification_type == "low_battery":
                if self.system_state in [SystemState.AUTONOMOUS_MOWING, SystemState.MANUAL_CONTROL]:
                    self.system_state = SystemState.RETURNING_HOME
                    
            elif notification_type == "obstacle_detected":
                # Handle obstacle detection during autonomous operation
                if self.system_state == SystemState.AUTONOMOUS_MOWING:
                    # Pause mission temporarily
                    await self.send_message("navigation", "pause_mission", {})
            
        except Exception as e:
            logger.error(f"Service notification handling error: {e}")


# Service entry point
def main():
    """Main entry point for mission controller."""
    from mower.core.communication.base_service import run_service
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("Starting Mission Controller")
    run_service(MissionController, "mission_controller")


if __name__ == "__main__":
    main()
