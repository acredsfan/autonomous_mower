"""
Graceful Degradation Controller for the autonomous mower.

This module implements graceful degradation strategies for sensor failures,
allowing the system to continue operating with reduced functionality when
sensors fail or become unavailable.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Set, Union

from mower.utilities.logger_config import LoggerConfigInfo

logger = LoggerConfigInfo.get_logger(__name__)


class DegradationLevel(Enum):
    """Levels of system degradation"""
    NORMAL = "normal"
    MINOR = "minor"
    MODERATE = "moderate"
    SEVERE = "severe"
    CRITICAL = "critical"


class SensorType(Enum):
    """Types of sensors in the system"""
    GPS = "gps"
    IMU = "imu"
    CAMERA = "camera"
    TOF = "tof"
    ENVIRONMENT = "environment"
    POWER = "power"
    EMERGENCY_STOP = "emergency_stop"


@dataclass
class FallbackStrategy:
    """Configuration for a fallback strategy"""
    name: str
    sensor_types: List[SensorType]
    fallback_sensors: List[SensorType]
    degradation_level: DegradationLevel
    enabled_functions: List[str]
    disabled_functions: List[str]
    max_duration: Optional[timedelta] = None
    confidence_threshold: float = 0.5
    
    def is_applicable(self, failed_sensors: Set[SensorType]) -> bool:
        """Check if this strategy applies to the given failed sensors"""
        return any(sensor in failed_sensors for sensor in self.sensor_types)


@dataclass
class DegradationState:
    """Current degradation state of the system"""
    level: DegradationLevel = DegradationLevel.NORMAL
    active_strategies: List[str] = field(default_factory=list)
    failed_sensors: Set[SensorType] = field(default_factory=set)
    fallback_sensors: Set[SensorType] = field(default_factory=set)
    start_time: Optional[datetime] = None
    last_update: Optional[datetime] = None
    confidence_score: float = 1.0
    
    def get_duration(self) -> Optional[timedelta]:
        """Get duration of current degradation state"""
        if self.start_time:
            return datetime.now() - self.start_time
        return None


class SensorFusion:
    """Sensor fusion logic for combining multiple sensor inputs"""
    
    def __init__(self):
        self.logger = LoggerConfigInfo.get_logger(__name__)
    
    async def fuse_gps_imu(self, gps_data: Optional[Dict], imu_data: Optional[Dict]) -> Dict[str, Any]:
        """Fuse GPS and IMU data for navigation"""
        result = {
            "position": None,
            "heading": None,
            "confidence": 0.0,
            "source": "unknown"
        }
        
        if gps_data and gps_data.get("fix_quality", 0) > 0:
            # GPS available - primary source
            result.update({
                "position": {
                    "latitude": gps_data.get("latitude"),
                    "longitude": gps_data.get("longitude"),
                    "altitude": gps_data.get("altitude")
                },
                "heading": gps_data.get("course"),
                "confidence": min(gps_data.get("fix_quality", 0) / 4.0, 1.0),
                "source": "gps"
            })
        elif imu_data and imu_data.get("heading") is not None:
            # GPS unavailable - use IMU dead reckoning
            result.update({
                "heading": imu_data.get("heading"),
                "confidence": 0.6,  # Lower confidence for IMU-only
                "source": "imu_dead_reckoning"
            })
            
            # Estimate position using last known GPS + IMU integration
            last_position = await self._get_last_known_position()
            if last_position:
                estimated_position = await self._dead_reckon_position(
                    last_position, imu_data
                )
                result["position"] = estimated_position
                result["confidence"] = min(result["confidence"], 0.4)
        
        return result
    
    async def fuse_camera_tof(self, camera_data: Optional[Dict], tof_data: Optional[Dict]) -> Dict[str, Any]:
        """Fuse camera and ToF data for obstacle detection"""
        result = {
            "obstacles": [],
            "safe_distance": None,
            "confidence": 0.0,
            "source": "unknown"
        }
        
        if camera_data and tof_data:
            # Both sensors available - high confidence
            obstacles = self._merge_obstacle_data(
                camera_data.get("obstacles", []),
                tof_data.get("distances", {})
            )
            result.update({
                "obstacles": obstacles,
                "safe_distance": min(
                    camera_data.get("min_distance", float('inf')),
                    min(tof_data.get("distances", {}).values(), default=float('inf'))
                ),
                "confidence": 0.9,
                "source": "camera_tof_fusion"
            })
        elif camera_data:
            # Camera only
            result.update({
                "obstacles": camera_data.get("obstacles", []),
                "safe_distance": camera_data.get("min_distance"),
                "confidence": 0.7,
                "source": "camera_only"
            })
        elif tof_data:
            # ToF only
            distances = tof_data.get("distances", {})
            obstacles = [
                {"type": "unknown", "distance": dist, "direction": direction}
                for direction, dist in distances.items()
                if dist < 1.0  # Less than 1 meter
            ]
            result.update({
                "obstacles": obstacles,
                "safe_distance": min(distances.values(), default=None),
                "confidence": 0.6,
                "source": "tof_only"
            })
        
        return result
    
    async def _get_last_known_position(self) -> Optional[Dict]:
        """Get the last known GPS position"""
        # This would integrate with the GPS service to get last known position
        # For now, return None - would be implemented with actual GPS service
        return None
    
    async def _dead_reckon_position(self, last_position: Dict, imu_data: Dict) -> Dict:
        """Estimate position using dead reckoning"""
        # Simplified dead reckoning - would need more sophisticated implementation
        return {
            "latitude": last_position.get("latitude"),
            "longitude": last_position.get("longitude"),
            "estimated": True,
            "accuracy": "low"
        }
    
    def _merge_obstacle_data(self, camera_obstacles: List, tof_distances: Dict) -> List[Dict]:
        """Merge obstacle data from camera and ToF sensors"""
        merged = []
        
        # Add camera obstacles with ToF distance validation
        for obstacle in camera_obstacles:
            obstacle_copy = obstacle.copy()
            # Try to correlate with ToF data based on direction
            direction = obstacle.get("direction", "front")
            if direction in tof_distances:
                obstacle_copy["tof_distance"] = tof_distances[direction]
                obstacle_copy["validated"] = True
            merged.append(obstacle_copy)
        
        # Add ToF-only obstacles not detected by camera
        for direction, distance in tof_distances.items():
            if distance < 1.0:  # Close obstacle
                # Check if already covered by camera
                camera_covered = any(
                    obs.get("direction") == direction for obs in camera_obstacles
                )
                if not camera_covered:
                    merged.append({
                        "type": "unknown",
                        "distance": distance,
                        "direction": direction,
                        "source": "tof_only"
                    })
        
        return merged


class GracefulDegradationController:
    """
    Controller for managing graceful degradation strategies.
    
    This class monitors sensor health and automatically switches to
    fallback strategies when sensors fail, allowing the system to
    continue operating with reduced functionality.
    """
    
    def __init__(self):
        self.logger = LoggerConfigInfo.get_logger(__name__)
        self._state = DegradationState()
        self._strategies: Dict[str, FallbackStrategy] = {}
        self._sensor_fusion = SensorFusion()
        self._callbacks: Dict[str, List[Callable]] = {}
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Initialize default strategies
        self._initialize_default_strategies()
    
    def _initialize_default_strategies(self):
        """Initialize default fallback strategies"""
        
        # GPS failure - use IMU dead reckoning
        self.register_strategy(FallbackStrategy(
            name="gps_to_imu_fallback",
            sensor_types=[SensorType.GPS],
            fallback_sensors=[SensorType.IMU],
            degradation_level=DegradationLevel.MODERATE,
            enabled_functions=["basic_navigation", "return_to_base"],
            disabled_functions=["precision_mowing", "boundary_following"],
            max_duration=timedelta(minutes=30),
            confidence_threshold=0.4
        ))
        
        # Camera failure - rely on ToF sensors
        self.register_strategy(FallbackStrategy(
            name="camera_to_tof_fallback",
            sensor_types=[SensorType.CAMERA],
            fallback_sensors=[SensorType.TOF],
            degradation_level=DegradationLevel.MODERATE,
            enabled_functions=["basic_obstacle_avoidance", "slow_movement"],
            disabled_functions=["object_recognition", "advanced_navigation"],
            max_duration=timedelta(hours=2),
            confidence_threshold=0.6
        ))
        
        # ToF failure - camera only with reduced speed
        self.register_strategy(FallbackStrategy(
            name="tof_to_camera_fallback",
            sensor_types=[SensorType.TOF],
            fallback_sensors=[SensorType.CAMERA],
            degradation_level=DegradationLevel.MINOR,
            enabled_functions=["visual_obstacle_avoidance", "reduced_speed"],
            disabled_functions=["close_proximity_detection"],
            max_duration=timedelta(hours=4),
            confidence_threshold=0.7
        ))
        
        # Both GPS and IMU failure - emergency mode
        self.register_strategy(FallbackStrategy(
            name="navigation_failure_emergency",
            sensor_types=[SensorType.GPS, SensorType.IMU],
            fallback_sensors=[],
            degradation_level=DegradationLevel.CRITICAL,
            enabled_functions=["emergency_stop", "manual_control"],
            disabled_functions=["autonomous_operation"],
            max_duration=timedelta(minutes=5),
            confidence_threshold=0.1
        ))
        
        # Both camera and ToF failure - stop operation
        self.register_strategy(FallbackStrategy(
            name="vision_failure_emergency",
            sensor_types=[SensorType.CAMERA, SensorType.TOF],
            fallback_sensors=[],
            degradation_level=DegradationLevel.CRITICAL,
            enabled_functions=["emergency_stop", "return_to_base_blind"],
            disabled_functions=["mowing", "autonomous_navigation"],
            max_duration=timedelta(minutes=10),
            confidence_threshold=0.1
        ))
    
    def register_strategy(self, strategy: FallbackStrategy):
        """Register a fallback strategy"""
        self._strategies[strategy.name] = strategy
        self.logger.info(f"Registered fallback strategy: {strategy.name}")
    
    async def start_monitoring(self):
        """Start the degradation monitoring task"""
        if self._running:
            return
        
        self._running = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self.logger.info("Graceful degradation monitoring started")
    
    async def stop_monitoring(self):
        """Stop the degradation monitoring task"""
        if not self._running:
            return
        
        self._running = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Graceful degradation monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self._running:
            try:
                await self._check_sensor_health()
                await asyncio.sleep(5.0)  # Check every 5 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in degradation monitoring loop: {e}")
                await asyncio.sleep(10.0)  # Back off on error
    
    async def _check_sensor_health(self):
        """Check health of all sensors and update degradation state"""
        # This would integrate with the actual sensor health monitoring
        # For now, we'll simulate the interface
        pass
    
    async def handle_sensor_failure(self, sensor_type: SensorType, error_info: Dict[str, Any]):
        """Handle a sensor failure event"""
        self.logger.warning(f"Sensor failure detected: {sensor_type.value} - {error_info}")
        
        # Add to failed sensors
        self._state.failed_sensors.add(sensor_type)
        self._state.last_update = datetime.now()
        
        # Find applicable strategies
        applicable_strategies = [
            strategy for strategy in self._strategies.values()
            if strategy.is_applicable(self._state.failed_sensors)
        ]
        
        if not applicable_strategies:
            self.logger.error(f"No fallback strategy available for failed sensor: {sensor_type.value}")
            return
        
        # Select best strategy - prioritize by severity first, then confidence
        def strategy_priority(strategy):
            severity_order = {
                DegradationLevel.CRITICAL: 4,
                DegradationLevel.SEVERE: 3,
                DegradationLevel.MODERATE: 2,
                DegradationLevel.MINOR: 1,
                DegradationLevel.NORMAL: 0
            }
            # Check if strategy covers all failed sensors (exact match gets priority)
            exact_match = set(strategy.sensor_types) == self._state.failed_sensors
            return (severity_order[strategy.degradation_level], exact_match, strategy.confidence_threshold)
        
        best_strategy = max(applicable_strategies, key=strategy_priority)
        
        await self._activate_strategy(best_strategy)
    
    async def handle_sensor_recovery(self, sensor_type: SensorType):
        """Handle a sensor recovery event"""
        self.logger.info(f"Sensor recovery detected: {sensor_type.value}")
        
        if sensor_type in self._state.failed_sensors:
            self._state.failed_sensors.remove(sensor_type)
            self._state.last_update = datetime.now()
            
            # Re-evaluate degradation state
            await self._reevaluate_degradation()
    
    async def _activate_strategy(self, strategy: FallbackStrategy):
        """Activate a fallback strategy"""
        self.logger.info(f"Activating fallback strategy: {strategy.name}")
        
        # Deactivate conflicting strategies first
        conflicting_strategies = []
        for active_strategy_name in self._state.active_strategies:
            active_strategy = self._strategies.get(active_strategy_name)
            if active_strategy and set(active_strategy.sensor_types) & set(strategy.sensor_types):
                conflicting_strategies.append(active_strategy_name)
        
        for conflicting_strategy in conflicting_strategies:
            await self._deactivate_strategy(conflicting_strategy)
        
        # Update state
        if strategy.name not in self._state.active_strategies:
            self._state.active_strategies.append(strategy.name)
        
        # Use the most severe degradation level
        if strategy.degradation_level.value == "critical" or self._state.level.value != "critical":
            self._state.level = strategy.degradation_level
        
        self._state.fallback_sensors.update(strategy.fallback_sensors)
        self._state.confidence_score = min(self._state.confidence_score, strategy.confidence_threshold)
        
        if not self._state.start_time:
            self._state.start_time = datetime.now()
        
        # Notify callbacks
        await self._notify_callbacks("strategy_activated", {
            "strategy": strategy.name,
            "level": strategy.degradation_level.value,
            "enabled_functions": strategy.enabled_functions,
            "disabled_functions": strategy.disabled_functions
        })
    
    async def _reevaluate_degradation(self):
        """Re-evaluate the current degradation state"""
        if not self._state.failed_sensors:
            # No failed sensors - return to normal
            await self._return_to_normal()
            return
        
        # Find applicable strategies for remaining failed sensors
        applicable_strategies = [
            strategy for strategy in self._strategies.values()
            if strategy.is_applicable(self._state.failed_sensors)
        ]
        
        if not applicable_strategies:
            # No strategies needed - return to normal
            await self._return_to_normal()
            return
        
        # Select best strategy
        best_strategy = max(applicable_strategies, key=lambda s: s.confidence_threshold)
        
        # Check if we need to change strategy
        if best_strategy.name not in self._state.active_strategies:
            # Deactivate old strategies
            for strategy_name in self._state.active_strategies.copy():
                await self._deactivate_strategy(strategy_name)
            
            # Activate new strategy
            await self._activate_strategy(best_strategy)
    
    async def _return_to_normal(self):
        """Return system to normal operation"""
        if self._state.level == DegradationLevel.NORMAL:
            return
        
        self.logger.info("Returning to normal operation")
        
        # Deactivate all strategies
        for strategy_name in self._state.active_strategies.copy():
            await self._deactivate_strategy(strategy_name)
        
        # Reset state
        self._state = DegradationState()
        
        # Notify callbacks
        await self._notify_callbacks("normal_operation_restored", {})
    
    async def _deactivate_strategy(self, strategy_name: str):
        """Deactivate a fallback strategy"""
        self.logger.info(f"Deactivating fallback strategy: {strategy_name}")
        
        if strategy_name in self._state.active_strategies:
            self._state.active_strategies.remove(strategy_name)
        
        # Notify callbacks
        await self._notify_callbacks("strategy_deactivated", {
            "strategy": strategy_name
        })
    
    def register_callback(self, event_type: str, callback: Callable):
        """Register a callback for degradation events"""
        if event_type not in self._callbacks:
            self._callbacks[event_type] = []
        self._callbacks[event_type].append(callback)
    
    async def _notify_callbacks(self, event_type: str, data: Dict[str, Any]):
        """Notify registered callbacks of an event"""
        callbacks = self._callbacks.get(event_type, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                self.logger.error(f"Error in callback for {event_type}: {e}")
    
    async def get_fused_navigation_data(self, gps_data: Optional[Dict], imu_data: Optional[Dict]) -> Dict[str, Any]:
        """Get fused navigation data based on current degradation state"""
        return await self._sensor_fusion.fuse_gps_imu(gps_data, imu_data)
    
    async def get_fused_obstacle_data(self, camera_data: Optional[Dict], tof_data: Optional[Dict]) -> Dict[str, Any]:
        """Get fused obstacle detection data based on current degradation state"""
        return await self._sensor_fusion.fuse_camera_tof(camera_data, tof_data)
    
    def get_current_state(self) -> DegradationState:
        """Get the current degradation state"""
        return self._state
    
    def get_enabled_functions(self) -> List[str]:
        """Get list of currently enabled functions"""
        if not self._state.active_strategies:
            return ["all"]  # Normal operation
        
        enabled = set()
        for strategy_name in self._state.active_strategies:
            strategy = self._strategies.get(strategy_name)
            if strategy:
                enabled.update(strategy.enabled_functions)
        
        return list(enabled)
    
    def get_disabled_functions(self) -> List[str]:
        """Get list of currently disabled functions"""
        if not self._state.active_strategies:
            return []  # Normal operation
        
        disabled = set()
        for strategy_name in self._state.active_strategies:
            strategy = self._strategies.get(strategy_name)
            if strategy:
                disabled.update(strategy.disabled_functions)
        
        return list(disabled)
    
    def is_function_enabled(self, function_name: str) -> bool:
        """Check if a specific function is currently enabled"""
        if not self._state.active_strategies:
            return True  # Normal operation - all functions enabled
        
        enabled_functions = self.get_enabled_functions()
        disabled_functions = self.get_disabled_functions()
        
        # If explicitly disabled, return False
        if function_name in disabled_functions:
            return False
        
        # If explicitly enabled, return True
        if function_name in enabled_functions:
            return True
        
        # Default to disabled in degraded mode if not explicitly enabled
        return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status of the degradation controller"""
        return {
            "degradation_level": self._state.level.value,
            "active_strategies": self._state.active_strategies,
            "failed_sensors": [sensor.value for sensor in self._state.failed_sensors],
            "fallback_sensors": [sensor.value for sensor in self._state.fallback_sensors],
            "confidence_score": self._state.confidence_score,
            "duration": str(self._state.get_duration()) if self._state.get_duration() else None,
            "enabled_functions": self.get_enabled_functions(),
            "disabled_functions": self.get_disabled_functions(),
            "monitoring_active": self._running
        }