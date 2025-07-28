"""
Motor Control Service

This service provides real-time motor control with safety integration.
It runs at the highest priority and integrates directly with the safety system.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from mower.core.communication.base_service import BaseService, ServiceMessage
from mower.core.hal.hardware_manager import get_hardware_manager, HardwareManager
from mower.core.safety.safety_system import get_safety_system, SafetySystem
from mower.config.settings import SystemConfig


logger = logging.getLogger(__name__)


class MotorCommand(Enum):
    """Motor control commands."""
    SET_MOTORS = "set_motors"
    STOP_MOTORS = "stop_motors"
    ENABLE_BLADE = "enable_blade"
    DISABLE_BLADE = "disable_blade"
    EMERGENCY_STOP = "emergency_stop"


@dataclass
class MotorCommandData:
    """Motor command data structure."""
    steering: int = 0
    throttle: int = 0
    blade: int = 0
    duration: Optional[float] = None  # Optional timeout


class MotorControlService(BaseService):
    """High-priority motor control service with safety integration."""
    
    def __init__(self, service_name: str = "motor_control", config: Optional[SystemConfig] = None):
        """Initialize motor control service."""
        super().__init__(service_name, config)
        
        # Hardware and safety systems
        self.hardware_manager: Optional[HardwareManager] = None
        self.safety_system: Optional[SafetySystem] = None
        
        # Motor state tracking
        self.current_steering = 0
        self.current_throttle = 0
        self.current_blade = 0
        self.motors_enabled = False
        self.last_command_time = 0.0
        
        # Command timeout tracking
        self.command_timeout = self.config.safety.motor_watchdog
        self.timeout_task: Optional[asyncio.Task] = None
        
        # Performance tracking
        self.commands_processed = 0
        self.command_latencies = []
        
        # Register message handlers
        self.register_message_handler(MotorCommand.SET_MOTORS.value, self.handle_set_motors)
        self.register_message_handler(MotorCommand.STOP_MOTORS.value, self.handle_stop_motors)
        self.register_message_handler(MotorCommand.ENABLE_BLADE.value, self.handle_enable_blade)
        self.register_message_handler(MotorCommand.DISABLE_BLADE.value, self.handle_disable_blade)
        self.register_message_handler(MotorCommand.EMERGENCY_STOP.value, self.handle_emergency_stop)
    
    async def service_initialize(self) -> bool:
        """Initialize motor control service components."""
        try:
            # Initialize hardware manager
            self.hardware_manager = get_hardware_manager(self.config, self.config.simulation_mode)
            if not self.hardware_manager.initialize_all():
                logger.error("Failed to initialize hardware manager")
                return False
            
            # Initialize safety system
            self.safety_system = get_safety_system(self.config)
            if not self.safety_system.initialize():
                logger.error("Failed to initialize safety system")
                return False
            
            # Wait for safety system to be ready
            await asyncio.sleep(0.5)
            
            if not self.safety_system.is_safe_to_operate():
                logger.warning("Safety system reports unsafe conditions")
                # Continue anyway in case it's just initial state
            
            logger.info("Motor control service initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Motor control service initialization failed: {e}")
            return False
    
    async def service_loop(self) -> None:
        """Main motor control service loop."""
        # Start command timeout monitoring
        self.timeout_task = asyncio.create_task(self._monitor_command_timeout())
        
        try:
            while not self.shutdown_event.is_set():
                # Publish motor status
                await self._publish_motor_status()
                
                # Check safety system
                if self.safety_system and self.safety_system.monitor.is_emergency_stop_active():
                    await self._emergency_stop_motors()
                
                # Update safety system with command time
                if self.safety_system and self.last_command_time > 0:
                    self.safety_system.monitor.update_command_time()
                
                await asyncio.sleep(0.1)  # 10Hz status updates
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Motor service loop error: {e}")
    
    async def service_cleanup(self) -> None:
        """Cleanup motor control service."""
        try:
            # Cancel timeout monitoring
            if self.timeout_task and not self.timeout_task.done():
                self.timeout_task.cancel()
            
            # Stop all motors
            await self._emergency_stop_motors()
            
            # Cleanup hardware
            if self.hardware_manager:
                self.hardware_manager.cleanup_all()
            
            # Shutdown safety system
            if self.safety_system:
                self.safety_system.shutdown()
            
            logger.info("Motor control service cleanup complete")
            
        except Exception as e:
            logger.error(f"Motor control service cleanup error: {e}")
    
    async def handle_set_motors(self, message: ServiceMessage) -> None:
        """Handle set motors command."""
        start_time = time.time()
        
        try:
            # Parse command data
            cmd_data = MotorCommandData(**message.data)
            
            # Safety checks
            if not self.safety_system or not self.safety_system.is_safe_to_operate():
                logger.warning("Rejecting motor command: system not safe to operate")
                await self._send_command_response(message, False, "System not safe")
                return
            
            # Validate command through safety system
            try:
                self.safety_system.validator.validate_motor_command(
                    cmd_data.steering, cmd_data.throttle, cmd_data.blade
                )
            except Exception as e:
                logger.warning(f"Motor command validation failed: {e}")
                await self._send_command_response(message, False, str(e))
                return
            
            # Execute motor command
            if self.hardware_manager:
                with self.hardware_manager.safe_operation():
                    success = self.hardware_manager.motor_controller.set_motors(
                        cmd_data.steering, cmd_data.throttle, cmd_data.blade
                    )
                    
                    if success:
                        self.current_steering = cmd_data.steering
                        self.current_throttle = cmd_data.throttle
                        self.current_blade = cmd_data.blade
                        self.motors_enabled = (cmd_data.steering != 0 or 
                                             cmd_data.throttle != 0 or 
                                             cmd_data.blade != 0)
                        self.last_command_time = time.time()
                        
                        # Track performance
                        latency = time.time() - start_time
                        self.command_latencies.append(latency)
                        if len(self.command_latencies) > 100:
                            self.command_latencies.pop(0)
                        
                        self.commands_processed += 1
                        
                        logger.debug(f"Motors set: S={cmd_data.steering}, T={cmd_data.throttle}, B={cmd_data.blade}")
                        await self._send_command_response(message, True, "Command executed")
                    else:
                        logger.error("Hardware failed to execute motor command")
                        await self._send_command_response(message, False, "Hardware error")
            else:
                logger.error("No hardware manager available")
                await self._send_command_response(message, False, "No hardware")
                
        except Exception as e:
            logger.error(f"Error handling set_motors command: {e}")
            await self._send_command_response(message, False, str(e))
    
    async def handle_stop_motors(self, message: ServiceMessage) -> None:
        """Handle stop motors command."""
        try:
            if self.hardware_manager:
                success = self.hardware_manager.motor_controller.stop_all_motors()
                
                if success:
                    self.current_steering = 0
                    self.current_throttle = 0
                    self.current_blade = 0
                    self.motors_enabled = False
                    self.last_command_time = time.time()
                    
                    logger.info("All motors stopped")
                    await self._send_command_response(message, True, "Motors stopped")
                else:
                    logger.error("Failed to stop motors")
                    await self._send_command_response(message, False, "Stop failed")
            else:
                await self._send_command_response(message, False, "No hardware")
                
        except Exception as e:
            logger.error(f"Error handling stop_motors command: {e}")
            await self._send_command_response(message, False, str(e))
    
    async def handle_enable_blade(self, message: ServiceMessage) -> None:
        """Handle enable blade command."""
        try:
            speed = message.data.get("speed", 50)
            
            if self.hardware_manager:
                success = self.hardware_manager.motor_controller.enable_blade(speed)
                
                if success:
                    self.current_blade = speed
                    self.last_command_time = time.time()
                    
                    logger.info(f"Blade enabled at speed {speed}")
                    await self._send_command_response(message, True, f"Blade enabled at {speed}")
                else:
                    await self._send_command_response(message, False, "Blade enable failed")
            else:
                await self._send_command_response(message, False, "No hardware")
                
        except Exception as e:
            logger.error(f"Error handling enable_blade command: {e}")
            await self._send_command_response(message, False, str(e))
    
    async def handle_disable_blade(self, message: ServiceMessage) -> None:
        """Handle disable blade command."""
        try:
            if self.hardware_manager:
                success = self.hardware_manager.motor_controller.disable_blade()
                
                if success:
                    self.current_blade = 0
                    self.last_command_time = time.time()
                    
                    logger.info("Blade disabled")
                    await self._send_command_response(message, True, "Blade disabled")
                else:
                    await self._send_command_response(message, False, "Blade disable failed")
            else:
                await self._send_command_response(message, False, "No hardware")
                
        except Exception as e:
            logger.error(f"Error handling disable_blade command: {e}")
            await self._send_command_response(message, False, str(e))
    
    async def handle_emergency_stop(self, message: ServiceMessage) -> None:
        """Handle emergency stop command."""
        try:
            await self._emergency_stop_motors()
            
            if self.safety_system:
                self.safety_system.emergency_stop("Motor service emergency stop command")
            
            logger.critical("Emergency stop executed")
            await self._send_command_response(message, True, "Emergency stop executed")
            
        except Exception as e:
            logger.error(f"Error handling emergency_stop command: {e}")
            await self._send_command_response(message, False, str(e))
    
    async def _emergency_stop_motors(self) -> None:
        """Emergency stop all motors immediately."""
        try:
            if self.hardware_manager:
                self.hardware_manager.motor_controller.stop_all_motors()
                
                self.current_steering = 0
                self.current_throttle = 0
                self.current_blade = 0
                self.motors_enabled = False
                
                logger.warning("Emergency motor stop executed")
        except Exception as e:
            logger.error(f"Emergency stop error: {e}")
    
    async def _monitor_command_timeout(self) -> None:
        """Monitor for command timeouts and stop motors if needed."""
        while not self.shutdown_event.is_set():
            try:
                if (self.last_command_time > 0 and 
                    self.motors_enabled and 
                    time.time() - self.last_command_time > self.command_timeout):
                    
                    logger.warning("Motor command timeout - stopping motors")
                    await self._emergency_stop_motors()
                
                await asyncio.sleep(0.5)  # Check every 500ms
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Command timeout monitor error: {e}")
                await asyncio.sleep(1)
    
    async def _publish_motor_status(self) -> None:
        """Publish current motor status."""
        try:
            status = {
                "steering": self.current_steering,
                "throttle": self.current_throttle,
                "blade": self.current_blade,
                "motors_enabled": self.motors_enabled,
                "last_command_time": self.last_command_time,
                "commands_processed": self.commands_processed,
                "average_latency": sum(self.command_latencies) / len(self.command_latencies) if self.command_latencies else 0,
                "hardware_healthy": self.hardware_manager.is_system_healthy() if self.hardware_manager else False,
                "safe_to_operate": self.safety_system.is_safe_to_operate() if self.safety_system else False
            }
            
            if self.redis_client:
                await self.redis_client.setex(
                    f"service:{self.service_name}:status",
                    5,  # 5 second TTL
                    json.dumps(status)
                )
        except Exception as e:
            logger.error(f"Error publishing motor status: {e}")
    
    async def _send_command_response(self, original_message: ServiceMessage, 
                                   success: bool, message: str) -> None:
        """Send response to command."""
        if original_message.correlation_id:
            response_data = {
                "success": success,
                "message": message,
                "timestamp": time.time()
            }
            
            await self.send_message(
                original_message.service,
                "command_response",
                response_data,
                original_message.correlation_id
            )


# Service entry point
def main():
    """Main entry point for motor control service."""
    import json
    from mower.core.communication.base_service import run_service
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("Starting Motor Control Service")
    run_service(MotorControlService, "motor_control")


if __name__ == "__main__":
    main()
