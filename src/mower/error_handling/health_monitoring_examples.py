"""
Examples of using health monitoring interfaces for system components.

This module demonstrates how to implement and use the health monitoring
interfaces for various system components.
"""

import logging
import random
import threading
import time
from typing import Any, Dict, List, Optional

from mower.error_handling.health_monitoring import (
    ComponentHealth,
    HealthCheckInterface,
    HealthCheckMixin,
    HealthIssue,
    HealthMonitor,
    HealthStatus,
    create_health_issue,
    get_health_monitor,
)

logger = logging.getLogger(__name__)


class ExampleSensor(HealthCheckInterface):
    """
    Example sensor implementing the HealthCheckInterface.
    
    This class demonstrates how to implement the HealthCheckInterface
    for a hardware component.
    """
    
    def __init__(self, sensor_id: str):
        """
        Initialize example sensor.
        
        Args:
            sensor_id: Sensor identifier
        """
        self.sensor_id = sensor_id
        self.is_initialized = False
        self.error_rate = 0.2  # 20% error rate
        self.value = 0.0
        self.read_count = 0
        self.error_count = 0
        self.last_read_time = time.time()
        self._health = ComponentHealth(component_name=f"sensor_{sensor_id}")
        self._health_callbacks = []
        
        # Register with health monitor
        get_health_monitor().register_component(f"sensor_{sensor_id}")
    
    def initialize(self) -> bool:
        """
        Initialize the sensor.
        
        Returns:
            bool: True if initialization successful
        """
        logger.info(f"Initializing sensor {self.sensor_id}")
        
        # Simulate initialization
        time.sleep(0.1)
        
        self.is_initialized = True
        self._health.update_status(HealthStatus.HEALTHY)
        
        # Update health monitor
        get_health_monitor().update_health(
            f"sensor_{self.sensor_id}",
            status=HealthStatus.HEALTHY
        )
        
        return True
    
    def read_value(self) -> float:
        """
        Read sensor value.
        
        Returns:
            float: Sensor value
            
        Raises:
            RuntimeError: If sensor not initialized or read fails
        """
        if not self.is_initialized:
            raise RuntimeError(f"Sensor {self.sensor_id} not initialized")
        
        self.read_count += 1
        self.last_read_time = time.time()
        
        # Simulate occasional read errors
        if random.random() < self.error_rate:
            self.error_count += 1
            
            # Create health issue
            issue = create_health_issue(
                component_name=f"sensor_{self.sensor_id}",
                issue_id=f"read_error_{self.sensor_id}_{self.error_count}",
                description=f"Failed to read from sensor {self.sensor_id}",
                severity="warning",
                details={"read_count": self.read_count, "error_count": self.error_count}
            )
            
            # Update health status if too many errors
            if self.error_count > 5:
                self._health.update_status(HealthStatus.DEGRADED)
                get_health_monitor().update_health(
                    f"sensor_{self.sensor_id}",
                    status=HealthStatus.DEGRADED
                )
            
            raise RuntimeError(f"Failed to read from sensor {self.sensor_id}")
        
        # Simulate successful read
        self.value = random.uniform(20.0, 30.0)
        
        # Update health metrics
        self._health.update_metric("value", self.value)
        self._health.update_metric("read_count", self.read_count)
        self._health.update_metric("error_rate", self.error_count / self.read_count if self.read_count > 0 else 0)
        
        # Update health monitor
        get_health_monitor().update_health(
            f"sensor_{self.sensor_id}",
            metrics={
                "value": self.value,
                "read_count": self.read_count,
                "error_rate": self.error_count / self.read_count if self.read_count > 0 else 0
            }
        )
        
        return self.value
    
    def check_health(self) -> ComponentHealth:
        """
        Check component health and return status.
        
        Returns:
            ComponentHealth: Current health status and metrics
        """
        # Update metrics
        self._health.update_metric("read_count", self.read_count)
        self._health.update_metric("error_count", self.error_count)
        self._health.update_metric("error_rate", self.error_count / self.read_count if self.read_count > 0 else 0)
        self._health.update_metric("last_read_time", self.last_read_time)
        self._health.update_metric("value", self.value)
        
        # Check if sensor is responsive
        time_since_last_read = time.time() - self.last_read_time
        if time_since_last_read > 60.0:  # 1 minute
            self._health.add_issue(HealthIssue(
                id=f"sensor_{self.sensor_id}_stale",
                description=f"Sensor {self.sensor_id} has not been read in {time_since_last_read:.1f} seconds",
                severity="warning"
            ))
        
        # Check error rate
        error_rate = self.error_count / self.read_count if self.read_count > 0 else 0
        if error_rate > 0.5:  # 50% error rate
            self._health.add_issue(HealthIssue(
                id=f"sensor_{self.sensor_id}_high_error_rate",
                description=f"Sensor {self.sensor_id} has high error rate: {error_rate:.1%}",
                severity="error"
            ))
            self._health.update_status(HealthStatus.DEGRADED)
        
        return self._health
    
    def get_health_metrics(self) -> Dict[str, Any]:
        """
        Get component health metrics.
        
        Returns:
            Dict[str, Any]: Current metrics
        """
        return self._health.metrics
    
    def register_health_callback(self, callback: callable) -> None:
        """
        Register callback for health status changes.
        
        Args:
            callback: Function to call when health status changes
        """
        self._health_callbacks.append(callback)


class ExampleMotorController(HealthCheckMixin):
    """
    Example motor controller using the HealthCheckMixin.
    
    This class demonstrates how to use the HealthCheckMixin to add
    health monitoring capabilities to a class.
    """
    
    def __init__(self, motor_id: str):
        """
        Initialize example motor controller.
        
        Args:
            motor_id: Motor identifier
        """
        # Initialize HealthCheckMixin with component name
        super().__init__(component_name=f"motor_{motor_id}")
        
        self.motor_id = motor_id
        self.is_enabled = False
        self.current_speed = 0.0
        self.target_speed = 0.0
        self.temperature = 25.0  # Celsius
        self.start_time = time.time()
        self.operation_time = 0.0  # seconds
    
    def enable(self) -> bool:
        """
        Enable the motor.
        
        Returns:
            bool: True if motor enabled successfully
        """
        logger.info(f"Enabling motor {self.motor_id}")
        
        # Simulate enable operation
        time.sleep(0.1)
        
        self.is_enabled = True
        self.update_health_status(HealthStatus.HEALTHY)
        
        return True
    
    def disable(self) -> bool:
        """
        Disable the motor.
        
        Returns:
            bool: True if motor disabled successfully
        """
        logger.info(f"Disabling motor {self.motor_id}")
        
        # Simulate disable operation
        time.sleep(0.1)
        
        self.is_enabled = False
        self.current_speed = 0.0
        self.update_health_status(HealthStatus.STOPPING)
        
        return True
    
    def set_speed(self, speed: float) -> bool:
        """
        Set motor speed.
        
        Args:
            speed: Motor speed (-1.0 to 1.0)
            
        Returns:
            bool: True if speed set successfully
            
        Raises:
            ValueError: If speed is out of range
            RuntimeError: If motor not enabled
        """
        if not self.is_enabled:
            raise RuntimeError(f"Motor {self.motor_id} not enabled")
        
        if abs(speed) > 1.0:
            raise ValueError("Speed must be between -1.0 and 1.0")
        
        logger.info(f"Setting motor {self.motor_id} speed to {speed}")
        
        # Simulate speed change
        self.target_speed = speed
        
        # Update health metrics
        self.update_health_metric("target_speed", speed)
        
        return True
    
    def update(self) -> None:
        """Update motor state."""
        if not self.is_enabled:
            return
        
        # Simulate motor physics
        speed_diff = self.target_speed - self.current_speed
        self.current_speed += speed_diff * 0.1  # Gradual change
        
        # Simulate temperature changes
        if abs(self.current_speed) > 0.5:
            self.temperature += 0.1  # Increase temperature when running fast
        else:
            self.temperature = max(25.0, self.temperature - 0.05)  # Cool down slowly
        
        # Update operation time
        if abs(self.current_speed) > 0.1:
            self.operation_time += 0.1  # 100ms update interval
        
        # Update health metrics
        self.update_health_metric("current_speed", self.current_speed)
        self.update_health_metric("temperature", self.temperature)
        self.update_health_metric("operation_time", self.operation_time)
        
        # Check for overheating
        if self.temperature > 60.0:  # Critical temperature
            self.add_health_issue(HealthIssue(
                id=f"motor_{self.motor_id}_overheating",
                description=f"Motor {self.motor_id} is overheating: {self.temperature:.1f}°C",
                severity="critical",
                resolution_steps=["Disable motor", "Allow to cool down", "Check for mechanical issues"]
            ))
            self.update_health_status(HealthStatus.FAILED)
        elif self.temperature > 50.0:  # Warning temperature
            self.add_health_issue(HealthIssue(
                id=f"motor_{self.motor_id}_hot",
                description=f"Motor {self.motor_id} is running hot: {self.temperature:.1f}°C",
                severity="warning",
                resolution_steps=["Reduce speed", "Monitor temperature"]
            ))
            self.update_health_status(HealthStatus.DEGRADED)
    
    def _collect_health_metrics(self) -> None:
        """Collect health metrics."""
        # Override HealthCheckMixin method to collect motor-specific metrics
        self.update_health_metric("is_enabled", self.is_enabled)
        self.update_health_metric("current_speed", self.current_speed)
        self.update_health_metric("target_speed", self.target_speed)
        self.update_health_metric("temperature", self.temperature)
        self.update_health_metric("operation_time", self.operation_time)


class SystemHealthMonitor:
    """
    Example system health monitor.
    
    This class demonstrates how to use the HealthMonitor to track
    the health of multiple system components.
    """
    
    def __init__(self):
        """Initialize system health monitor."""
        self.monitor = get_health_monitor()
        self.components = {}
        self.running = False
        self.check_interval = 1.0  # seconds
        self._thread = None
    
    def register_component(self, name: str, component: HealthCheckInterface) -> None:
        """
        Register a component for health monitoring.
        
        Args:
            name: Component name
            component: Component to monitor
        """
        self.components[name] = component
        
        # Register callback to update health monitor
        component.register_health_callback(
            lambda health: self.monitor.update_health(
                name,
                status=health.status,
                metrics=health.metrics,
                issues=health.issues
            )
        )
        
        logger.info(f"Registered component '{name}' for health monitoring")
    
    def start(self) -> None:
        """Start health monitoring."""
        if self.running:
            return
        
        self.running = True
        self._thread = threading.Thread(target=self._monitor_loop)
        self._thread.daemon = True
        self._thread.start()
        
        logger.info("Started system health monitoring")
    
    def stop(self) -> None:
        """Stop health monitoring."""
        self.running = False
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None
        
        logger.info("Stopped system health monitoring")
    
    def _monitor_loop(self) -> None:
        """Health monitoring loop."""
        while self.running:
            try:
                # Check all components
                for name, component in self.components.items():
                    try:
                        health = component.check_health()
                        logger.debug(f"Health check for '{name}': {health.status.value}")
                    except Exception as e:
                        logger.error(f"Error checking health of '{name}': {e}")
                
                # Get system health summary
                summary = self.monitor.get_health_summary()
                logger.debug(f"System health: {summary['overall_status']}")
                
                # Log critical issues
                for issue in summary.get("critical_issues", []):
                    logger.critical(
                        f"Critical issue: {issue['description']} "
                        f"(component: {issue['related_component']})"
                    )
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
            
            # Wait for next check
            time.sleep(self.check_interval)
    
    def get_health_summary(self) -> Dict[str, Any]:
        """
        Get system health summary.
        
        Returns:
            Dict[str, Any]: Health summary
        """
        return self.monitor.get_health_summary()
    
    def get_component_health(self, name: str) -> Optional[ComponentHealth]:
        """
        Get health status for a component.
        
        Args:
            name: Component name
            
        Returns:
            ComponentHealth or None if component not found
        """
        return self.monitor.get_component_health(name)


def demonstrate_health_monitoring():
    """
    Demonstrate health monitoring functionality.
    
    This function shows how to use the health monitoring interfaces
    and classes to monitor system components.
    """
    logger.info("Starting health monitoring demonstration")
    
    # Create system health monitor
    system_monitor = SystemHealthMonitor()
    
    # Create example components
    sensor1 = ExampleSensor("temp1")
    sensor2 = ExampleSensor("temp2")
    motor1 = ExampleMotorController("left")
    motor2 = ExampleMotorController("right")
    
    # Register components with system monitor
    system_monitor.register_component("sensor_temp1", sensor1)
    system_monitor.register_component("sensor_temp2", sensor2)
    system_monitor.register_component("motor_left", motor1)
    system_monitor.register_component("motor_right", motor2)
    
    # Initialize components
    sensor1.initialize()
    sensor2.initialize()
    motor1.enable()
    motor2.enable()
    
    # Start health monitoring
    system_monitor.start()
    
    try:
        # Simulate system operation
        logger.info("\n=== Normal Operation ===")
        for i in range(10):
            # Read sensors
            try:
                temp1 = sensor1.read_value()
                logger.info(f"Sensor 1 reading: {temp1:.1f}°C")
            except Exception as e:
                logger.error(f"Failed to read sensor 1: {e}")
            
            try:
                temp2 = sensor2.read_value()
                logger.info(f"Sensor 2 reading: {temp2:.1f}°C")
            except Exception as e:
                logger.error(f"Failed to read sensor 2: {e}")
            
            # Update motors
            motor1.set_speed(0.5)
            motor2.set_speed(0.5)
            motor1.update()
            motor2.update()
            
            # Wait
            time.sleep(0.5)
        
        # Print health summary
        summary = system_monitor.get_health_summary()
        logger.info(f"\nSystem health: {summary['overall_status']}")
        logger.info(f"Components: {summary['component_count']}")
        logger.info(f"Status counts: {summary['status_counts']}")
        logger.info(f"Issue counts: {summary['issue_counts']}")
        
        # Simulate degraded operation
        logger.info("\n=== Degraded Operation ===")
        
        # Increase sensor error rate
        sensor1.error_rate = 0.8  # 80% error rate
        
        # Run motor at high speed to increase temperature
        motor1.set_speed(1.0)
        
        for i in range(20):
            # Read sensors
            try:
                temp1 = sensor1.read_value()
                logger.info(f"Sensor 1 reading: {temp1:.1f}°C")
            except Exception as e:
                logger.error(f"Failed to read sensor 1: {e}")
            
            # Update motors
            motor1.update()
            motor2.update()
            
            # Wait
            time.sleep(0.5)
        
        # Print health summary
        summary = system_monitor.get_health_summary()
        logger.info(f"\nSystem health: {summary['overall_status']}")
        logger.info(f"Components: {summary['component_count']}")
        logger.info(f"Status counts: {summary['status_counts']}")
        logger.info(f"Issue counts: {summary['issue_counts']}")
        
        # Print component health details
        logger.info("\n=== Component Health Details ===")
        for name in ["sensor_temp1", "motor_left"]:
            health = system_monitor.get_component_health(name)
            if health:
                logger.info(f"{name}: {health.status.value}")
                logger.info(f"  Metrics: {health.metrics}")
                logger.info(f"  Issues: {len(health.issues)}")
                for issue in health.issues:
                    logger.info(f"    - {issue.severity}: {issue.description}")
    
    finally:
        # Stop health monitoring
        system_monitor.stop()
        
        # Disable motors
        motor1.disable()
        motor2.disable()
    
    logger.info("\nHealth monitoring demonstration completed")


if __name__ == "__main__":
    # Configure logging for demonstration
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)8s] %(message)s (%(filename)s:%(lineno)d)'
    )
    
    demonstrate_health_monitoring()