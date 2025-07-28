"""
Navigation Service

This service handles path planning, navigation, and autonomous operation
of the mower using GPS coordinates and sensor data.
"""

import asyncio
import json
import logging
import math
import time
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from mower.core.communication.base_service import BaseService, ServiceMessage
from mower.config.settings import SystemConfig


logger = logging.getLogger(__name__)


class NavigationMode(Enum):
    """Navigation modes."""
    IDLE = "idle"
    MANUAL = "manual"
    AUTO_PATTERN = "auto_pattern"
    RETURN_TO_BASE = "return_to_base"
    BOUNDARY_FOLLOW = "boundary_follow"


@dataclass
class Waypoint:
    """GPS waypoint."""
    latitude: float
    longitude: float
    altitude: float = 0.0
    speed: float = 1.0  # m/s
    action: str = "move"  # move, stop, mow, etc.


@dataclass
class Mission:
    """Navigation mission."""
    name: str
    waypoints: List[Waypoint]
    boundary_points: List[Tuple[float, float]]
    created_time: float
    estimated_duration: float = 0.0


@dataclass
class NavigationState:
    """Current navigation state."""
    mode: NavigationMode
    current_position: Tuple[float, float]  # lat, lon
    target_position: Optional[Tuple[float, float]]
    heading: float  # degrees
    speed: float  # m/s
    distance_to_target: float  # meters
    progress_percent: float
    mission_active: bool
    waypoint_index: int


class NavigationService(BaseService):
    """Navigation and path planning service."""
    
    def __init__(self, service_name: str = "navigation", config: Optional[SystemConfig] = None):
        """Initialize navigation service."""
        super().__init__(service_name, config)
        
        # Navigation state
        self.mode = NavigationMode.IDLE
        self.current_mission: Optional[Mission] = None
        self.current_waypoint_index = 0
        self.navigation_state = NavigationState(
            mode=NavigationMode.IDLE,
            current_position=(0.0, 0.0),
            target_position=None,
            heading=0.0,
            speed=0.0,
            distance_to_target=0.0,
            progress_percent=0.0,
            mission_active=False,
            waypoint_index=0
        )
        
        # Path planning parameters
        self.waypoint_tolerance = 2.0  # meters
        self.max_speed = 2.0  # m/s
        self.default_speed = 1.0  # m/s
        
        # Safety parameters
        self.min_obstacle_distance = 1.0  # meters
        self.boundary_buffer = 1.0  # meters
        
        # Performance tracking
        self.navigation_cycles = 0
        self.total_distance_traveled = 0.0
        self.mission_start_time = 0.0
        
        # Register message handlers
        self.register_message_handler("start_mission", self.handle_start_mission)
        self.register_message_handler("stop_mission", self.handle_stop_mission)
        self.register_message_handler("set_waypoint", self.handle_set_waypoint)
        self.register_message_handler("get_navigation_state", self.handle_get_navigation_state)
        self.register_message_handler("generate_pattern", self.handle_generate_pattern)
    
    async def service_initialize(self) -> bool:
        """Initialize navigation service components."""
        try:
            logger.info("Navigation service initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Navigation service initialization failed: {e}")
            return False
    
    async def service_loop(self) -> None:
        """Main navigation service loop."""
        try:
            while not self.shutdown_event.is_set():
                # Update navigation state
                await self._update_navigation_state()
                
                # Process navigation if in auto mode
                if self.mode != NavigationMode.IDLE and self.mode != NavigationMode.MANUAL:
                    await self._process_navigation()
                
                # Publish navigation status
                await self._publish_navigation_status()
                
                self.navigation_cycles += 1
                await asyncio.sleep(0.5)  # 2Hz navigation updates
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Navigation service loop error: {e}")
    
    async def service_cleanup(self) -> None:
        """Cleanup navigation service."""
        try:
            # Stop any active mission
            await self._stop_mission()
            
            logger.info("Navigation service cleanup complete")
            
        except Exception as e:
            logger.error(f"Navigation service cleanup error: {e}")
    
    async def _update_navigation_state(self) -> None:
        """Update current navigation state from sensor data."""
        try:
            # Get latest sensor data
            if self.redis_client:
                sensor_data_str = await self.redis_client.get("service:sensor:data")
                if sensor_data_str:
                    sensor_data = json.loads(sensor_data_str)
                    
                    # Update position from GPS
                    if "fusion" in sensor_data:
                        fusion = sensor_data["fusion"]
                        self.navigation_state.current_position = (
                            fusion.get("position_lat", 0.0),
                            fusion.get("position_lon", 0.0)
                        )
                        self.navigation_state.heading = fusion.get("heading_degrees", 0.0)
                        self.navigation_state.speed = fusion.get("speed_mps", 0.0)
            
            # Update target distance if we have a target
            if self.navigation_state.target_position:
                self.navigation_state.distance_to_target = self._calculate_distance(
                    self.navigation_state.current_position,
                    self.navigation_state.target_position
                )
            
            # Update mission progress
            if self.current_mission and self.current_mission.waypoints:
                total_waypoints = len(self.current_mission.waypoints)
                self.navigation_state.progress_percent = (
                    self.current_waypoint_index / total_waypoints * 100.0
                )
                self.navigation_state.waypoint_index = self.current_waypoint_index
            
        except Exception as e:
            logger.error(f"Navigation state update error: {e}")
    
    async def _process_navigation(self) -> None:
        """Process navigation logic."""
        try:
            if self.mode == NavigationMode.AUTO_PATTERN:
                await self._process_auto_pattern()
            elif self.mode == NavigationMode.RETURN_TO_BASE:
                await self._process_return_to_base()
            elif self.mode == NavigationMode.BOUNDARY_FOLLOW:
                await self._process_boundary_follow()
            
        except Exception as e:
            logger.error(f"Navigation processing error: {e}")
    
    async def _process_auto_pattern(self) -> None:
        """Process automatic pattern mowing."""
        try:
            if not self.current_mission or not self.current_mission.waypoints:
                return
            
            # Check if we've reached the current waypoint
            if self.current_waypoint_index < len(self.current_mission.waypoints):
                current_waypoint = self.current_mission.waypoints[self.current_waypoint_index]
                target_pos = (current_waypoint.latitude, current_waypoint.longitude)
                
                distance = self._calculate_distance(
                    self.navigation_state.current_position,
                    target_pos
                )
                
                if distance <= self.waypoint_tolerance:
                    # Reached waypoint, move to next
                    self.current_waypoint_index += 1
                    logger.info(f"Reached waypoint {self.current_waypoint_index}/{len(self.current_mission.waypoints)}")
                    
                    if self.current_waypoint_index >= len(self.current_mission.waypoints):
                        # Mission complete
                        await self._complete_mission()
                        return
                
                # Navigate to current waypoint
                await self._navigate_to_waypoint(current_waypoint)
            
        except Exception as e:
            logger.error(f"Auto pattern processing error: {e}")
    
    async def _process_return_to_base(self) -> None:
        """Process return to base navigation."""
        try:
            # Create a simple return to base waypoint (origin for now)
            base_waypoint = Waypoint(
                latitude=0.0,  # Would be set to actual base coordinates
                longitude=0.0,
                speed=self.default_speed
            )
            
            await self._navigate_to_waypoint(base_waypoint)
            
            # Check if we've reached base
            distance = self._calculate_distance(
                self.navigation_state.current_position,
                (base_waypoint.latitude, base_waypoint.longitude)
            )
            
            if distance <= self.waypoint_tolerance:
                logger.info("Returned to base")
                self.mode = NavigationMode.IDLE
            
        except Exception as e:
            logger.error(f"Return to base processing error: {e}")
    
    async def _process_boundary_follow(self) -> None:
        """Process boundary following navigation."""
        try:
            # Simplified boundary following - would be more complex in practice
            logger.debug("Processing boundary follow mode")
            
        except Exception as e:
            logger.error(f"Boundary follow processing error: {e}")
    
    async def _navigate_to_waypoint(self, waypoint: Waypoint) -> None:
        """Navigate to a specific waypoint."""
        try:
            target_pos = (waypoint.latitude, waypoint.longitude)
            self.navigation_state.target_position = target_pos
            
            # Calculate bearing to target
            bearing = self._calculate_bearing(
                self.navigation_state.current_position,
                target_pos
            )
            
            # Simple navigation command - send to motor service
            # This would be more sophisticated with obstacle avoidance
            steering, throttle = self._calculate_motor_commands(bearing, waypoint.speed)
            
            # Check for obstacles
            if await self._check_obstacles():
                # Stop if obstacle detected
                steering, throttle = 0, 0
                logger.warning("Obstacle detected, stopping")
            
            # Send motor command
            await self.send_message(
                "motor_control",
                "set_motors",
                {
                    "steering": steering,
                    "throttle": throttle,
                    "blade": 50 if waypoint.action == "mow" else 0
                }
            )
            
        except Exception as e:
            logger.error(f"Waypoint navigation error: {e}")
    
    def _calculate_distance(self, pos1: Tuple[float, float], pos2: Tuple[float, float]) -> float:
        """Calculate distance between two GPS coordinates in meters."""
        lat1, lon1 = pos1
        lat2, lon2 = pos2
        
        # Haversine formula
        R = 6371000  # Earth's radius in meters
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def _calculate_bearing(self, pos1: Tuple[float, float], pos2: Tuple[float, float]) -> float:
        """Calculate bearing from pos1 to pos2 in degrees."""
        lat1, lon1 = pos1
        lat2, lon2 = pos2
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lon = math.radians(lon2 - lon1)
        
        y = math.sin(delta_lon) * math.cos(lat2_rad)
        x = (math.cos(lat1_rad) * math.sin(lat2_rad) -
             math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lon))
        
        bearing = math.degrees(math.atan2(y, x))
        return (bearing + 360) % 360
    
    def _calculate_motor_commands(self, target_bearing: float, target_speed: float) -> Tuple[int, int]:
        """Calculate motor commands from navigation requirements."""
        # Simplified motor command calculation
        current_heading = self.navigation_state.heading
        
        # Calculate heading error
        heading_error = target_bearing - current_heading
        if heading_error > 180:
            heading_error -= 360
        elif heading_error < -180:
            heading_error += 360
        
        # Simple proportional control
        steering = max(-100, min(100, int(heading_error * 2)))  # Simple P controller
        throttle = max(-100, min(100, int(target_speed / self.max_speed * 50)))  # Speed control
        
        return steering, throttle
    
    async def _check_obstacles(self) -> bool:
        """Check for obstacles from vision service."""
        try:
            if self.redis_client:
                vision_status_str = await self.redis_client.get("service:vision:status")
                if vision_status_str:
                    vision_status = json.loads(vision_status_str)
                    return not vision_status.get("path_clear", True)
            
            return False
            
        except Exception as e:
            logger.error(f"Obstacle check error: {e}")
            return True  # Assume obstacle if error
    
    async def _stop_mission(self) -> None:
        """Stop current mission."""
        try:
            self.mode = NavigationMode.IDLE
            self.current_mission = None
            self.current_waypoint_index = 0
            self.navigation_state.mission_active = False
            self.navigation_state.target_position = None
            
            # Stop motors
            await self.send_message(
                "motor_control",
                "stop_motors",
                {}
            )
            
            logger.info("Mission stopped")
            
        except Exception as e:
            logger.error(f"Mission stop error: {e}")
    
    async def _complete_mission(self) -> None:
        """Complete current mission."""
        try:
            mission_duration = time.time() - self.mission_start_time
            logger.info(f"Mission completed in {mission_duration:.1f} seconds")
            
            await self._stop_mission()
            
        except Exception as e:
            logger.error(f"Mission completion error: {e}")
    
    # Message handlers
    
    async def handle_start_mission(self, message: ServiceMessage) -> None:
        """Handle start mission command."""
        try:
            mission_data = message.data
            
            # Create mission from data
            waypoints = [Waypoint(**wp) for wp in mission_data.get("waypoints", [])]
            
            self.current_mission = Mission(
                name=mission_data.get("name", "Auto Mission"),
                waypoints=waypoints,
                boundary_points=mission_data.get("boundary_points", []),
                created_time=time.time()
            )
            
            self.current_waypoint_index = 0
            self.mode = NavigationMode.AUTO_PATTERN
            self.navigation_state.mission_active = True
            self.mission_start_time = time.time()
            
            logger.info(f"Started mission: {self.current_mission.name} with {len(waypoints)} waypoints")
            
            await self.send_message(
                message.service,
                "mission_response",
                {"success": True, "message": "Mission started"},
                message.correlation_id
            )
            
        except Exception as e:
            logger.error(f"Start mission error: {e}")
            await self.send_message(
                message.service,
                "mission_response",
                {"success": False, "message": str(e)},
                message.correlation_id
            )
    
    async def handle_stop_mission(self, message: ServiceMessage) -> None:
        """Handle stop mission command."""
        try:
            await self._stop_mission()
            
            await self.send_message(
                message.service,
                "mission_response",
                {"success": True, "message": "Mission stopped"},
                message.correlation_id
            )
            
        except Exception as e:
            logger.error(f"Stop mission error: {e}")
    
    async def handle_set_waypoint(self, message: ServiceMessage) -> None:
        """Handle set waypoint command."""
        try:
            waypoint_data = message.data
            waypoint = Waypoint(**waypoint_data)
            
            # Create simple mission with single waypoint
            self.current_mission = Mission(
                name="Single Waypoint",
                waypoints=[waypoint],
                boundary_points=[],
                created_time=time.time()
            )
            
            self.current_waypoint_index = 0
            self.mode = NavigationMode.AUTO_PATTERN
            self.navigation_state.mission_active = True
            
            logger.info(f"Set waypoint: {waypoint.latitude}, {waypoint.longitude}")
            
        except Exception as e:
            logger.error(f"Set waypoint error: {e}")
    
    async def handle_get_navigation_state(self, message: ServiceMessage) -> None:
        """Handle get navigation state request."""
        try:
            response_data = {
                "success": True,
                "navigation_state": asdict(self.navigation_state),
                "mission": asdict(self.current_mission) if self.current_mission else None
            }
            
            await self.send_message(
                message.service,
                "navigation_state_response",
                response_data,
                message.correlation_id
            )
            
        except Exception as e:
            logger.error(f"Get navigation state error: {e}")
    
    async def handle_generate_pattern(self, message: ServiceMessage) -> None:
        """Handle generate mowing pattern request."""
        try:
            pattern_data = message.data
            boundary_points = pattern_data.get("boundary_points", [])
            pattern_type = pattern_data.get("pattern_type", "lines")
            
            # Generate simple line pattern
            waypoints = self._generate_line_pattern(boundary_points)
            
            response_data = {
                "success": True,
                "waypoints": [asdict(wp) for wp in waypoints],
                "estimated_duration": len(waypoints) * 10.0  # Rough estimate
            }
            
            await self.send_message(
                message.service,
                "pattern_response",
                response_data,
                message.correlation_id
            )
            
        except Exception as e:
            logger.error(f"Generate pattern error: {e}")
            await self.send_message(
                message.service,
                "pattern_response",
                {"success": False, "message": str(e)},
                message.correlation_id
            )
    
    def _generate_line_pattern(self, boundary_points: List[Tuple[float, float]]) -> List[Waypoint]:
        """Generate simple line mowing pattern."""
        waypoints = []
        
        if len(boundary_points) < 3:
            return waypoints
        
        # Simple rectangular pattern for now
        # In practice, this would be much more sophisticated
        min_lat = min(p[0] for p in boundary_points)
        max_lat = max(p[0] for p in boundary_points)
        min_lon = min(p[1] for p in boundary_points)
        max_lon = max(p[1] for p in boundary_points)
        
        # Create parallel lines
        num_lines = 10
        lat_step = (max_lat - min_lat) / num_lines
        
        for i in range(num_lines):
            lat = min_lat + i * lat_step
            
            if i % 2 == 0:
                # Left to right
                waypoints.append(Waypoint(lat, min_lon, speed=1.0, action="mow"))
                waypoints.append(Waypoint(lat, max_lon, speed=1.0, action="mow"))
            else:
                # Right to left
                waypoints.append(Waypoint(lat, max_lon, speed=1.0, action="mow"))
                waypoints.append(Waypoint(lat, min_lon, speed=1.0, action="mow"))
        
        return waypoints
    
    async def _publish_navigation_status(self) -> None:
        """Publish navigation service status."""
        try:
            status = {
                "mode": self.mode.value,
                "navigation_cycles": self.navigation_cycles,
                "mission_active": self.navigation_state.mission_active,
                "waypoint_index": self.current_waypoint_index,
                "total_waypoints": len(self.current_mission.waypoints) if self.current_mission else 0,
                "distance_to_target": self.navigation_state.distance_to_target,
                "progress_percent": self.navigation_state.progress_percent,
                "current_position": self.navigation_state.current_position,
                "current_heading": self.navigation_state.heading
            }
            
            if self.redis_client:
                await self.redis_client.setex(
                    f"service:{self.service_name}:status",
                    5,  # 5 second TTL
                    json.dumps(status)
                )
                
                # Publish detailed state
                await self.redis_client.setex(
                    f"service:{self.service_name}:state",
                    2,  # 2 second TTL
                    json.dumps(asdict(self.navigation_state))
                )
        
        except Exception as e:
            logger.error(f"Error publishing navigation status: {e}")


# Service entry point
def main():
    """Main entry point for navigation service."""
    from mower.core.communication.base_service import run_service
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("Starting Navigation Service")
    run_service(NavigationService, "navigation")


if __name__ == "__main__":
    main()
