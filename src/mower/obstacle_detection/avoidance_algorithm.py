"""
Obstacle avoidance algorithm for the autonomous mower.

This module implements real-time obstacle detection and
avoidance functionality, allowing the mower to safely
navigate around obstacles in its path while continuing
to follow the planned mowing route.

The avoidance algorithm:
1. Continuously monitors sensor data for obstacles
2. Implements various avoidance strategies based on obstacle type
3. Coordinates with the path planner to adjust routes when obstacles are
   detected
4. Manages thread-safe interaction between sensors, motors, and navigation

Key features:
- Thread-safe operation with proper synchronization
- Multiple avoidance strategies (turn, backup, reroute)
- Dynamic path adjustment based on obstacle proximity
- Integration with machine learning-based obstacle detection
"""

import threading
import time
import random
import math
import os
from enum import Enum, auto
from typing import Optional, Tuple, Dict, Any, List
import numpy as np
from dataclasses import dataclass

from mower.utilities.logger_config import LoggerConfigInfo
from mower.constants import (
    AVOIDANCE_DELAY,
    MIN_DISTANCE_THRESHOLD
)
from mower.navigation.path_planner import (
    PathPlanner
)


# Initialize logger
logger = LoggerConfigInfo.get_logger(__name__)


class NavigationStatus(Enum):
    """
    Enum representing the different states of navigation.

    These states are used to track the progress of navigation maneuvers
    and determine when avoidance actions are complete.

    States:
        IDLE: No navigation in progress
        MOVING: Actively moving to target
        TARGET_REACHED: Successfully reached target
        ERROR: Error occurred during navigation
    """
    IDLE = 0
    MOVING = 1
    TARGET_REACHED = 2
    ERROR = 3


class AvoidanceState(Enum):
    """
    Enum representing the different states of the avoidance algorithm.

    These states define the current avoidance mode and dictate the
    behavior of the robot when encountering obstacles.

    States:
        NORMAL: Regular operation, no obstacle detected
        OBSTACLE_DETECTED: An obstacle has been detected, initiating avoidance
        AVOIDING: Currently executing an avoidance maneuver
        RECOVERY: Unable to avoid obstacle, attempting recovery procedure
    """
    NORMAL = auto()
    OBSTACLE_DETECTED = auto()
    AVOIDING = auto()
    RECOVERY = auto()


@dataclass
class Obstacle:
    """Data class for detected obstacles."""
    position: Tuple[float, float]
    size: float
    confidence: float


class AvoidanceAlgorithm:
    """
    Implements obstacle detection and avoidance for the autonomous mower.

    This class coordinates between sensors, path planning, and motor control
    to ensure the mower can safely navigate around obstacles while maintaining
    its mowing path as much as possible.

    The algorithm uses a state machine approach to manage different phases
    of obstacle detection and avoidance, with thread-safe operation to handle
    concurrent sensing and motion control.

    Attributes:
        path_planner: Interface to the path planning system
        motor_controller: Interface to the motor control system
        sensor_interface: Interface to all onboard sensors
        camera: Optional camera instance for visual obstacle detection
        current_state: Current state of the avoidance algorithm
        obstacle_data: Information about detected obstacles
        thread_lock: Lock for thread-safe operation
        avoidance_thread: Background thread for continuous monitoring
        pattern_planner: Interface to the pattern planner
        obstacles: List of detected obstacles
        recovery_attempts: Number of recovery attempts
        max_recovery_attempts: Maximum number of recovery attempts

    Troubleshooting:
        - If the robot frequently stops for non-existent obstacles, check
          sensor calibration and detection thresholds
        - If avoidance maneuvers are too aggressive, adjust turning and
          speed parameters
        - If the robot gets stuck in avoidance loops, check the recovery
          strategy parameters
        - For issues with thread synchronization, inspect lock acquisition
          patterns in the logs
    """

    def __init__(
            self, resource_manager=None,
            pattern_planner: PathPlanner = None):
        """
        Initialize the avoidance algorithm.

        Args:
            resource_manager: Optional ResourceManager instance for system
                resources
            pattern_planner: Optional PathPlanner instance for
                path planning
        """
        self.logger = logger

        if resource_manager is None:
            from mower.main_controller import ResourceManager
            resource_manager = ResourceManager()

        self._resource_manager = resource_manager

        # Camera-related settings
        self.use_camera = bool(
            os.environ.get('USE_CAMERA', 'True').lower() == 'true'
        )
        self.camera = None
        self.obstacle_detector = None

        if self.use_camera:
            try:
                self.camera = self._resource_manager.get_camera()
                self.obstacle_detector = (
                    self._resource_manager.get_obstacle_detector()
                )
                self.logger.info("Camera and obstacle detector initialized")
            except Exception as e:
                self.logger.error(
                    "Failed to initialize camera components: "
                    f"{e}")
                self.use_camera = False

        self.reset_state()
        if pattern_planner is None:
            from mower.navigation.path_planner import (
                PathPlanner, PatternConfig, PatternType
            )
            pattern_config = PatternConfig(
                pattern_type=PatternType.PARALLEL,
                spacing=0.3,  # Default spacing in meters
                angle=0.0,  # Default angle in degrees
                overlap=0.1,  # Default overlap (10%)
                start_point=(0.0, 0.0),  # Default start point
                boundary_points=[]  # Default empty boundary
            )
            pattern_planner = PathPlanner(pattern_config)

        self.pattern_planner = pattern_planner
        self.obstacles = []
        self.recovery_attempts = 0
        self.max_recovery_attempts = 3

    def reset_state(self):
        """Reset the state of the avoidance algorithm."""
        self.path_planner = None
        self.motor_controller = None
        self.sensor_interface = None
        self.current_state = AvoidanceState.NORMAL
        self.obstacle_data = None
        self.obstacle_left = False
        self.obstacle_right = False
        self.camera_obstacle_detected = False
        self.dropoff_detected = False

        self.thread_lock = threading.RLock()
        self.running = False
        self.stop_thread = False
        self.avoidance_thread = None

        # Configuration parameters
        self.obstacle_threshold = 30.0  # cm
        self.safe_distance = 50.0  # cm
        self.avoidance_strategies = [
            self._turn_right_strategy,
            self._turn_left_strategy,
            self._backup_strategy,
            self._alternative_route_strategy
        ]

        logger.info("Avoidance algorithm initialized")

    def check_camera_obstacles_and_dropoffs(self):
        """
        Check for obstacles and drop-offs using camera.

        Returns:
            tuple: (has_obstacle, has_dropoff)
        """
        if not self.use_camera or self.camera is None:
            return False, False

        if self.obstacle_detector is None:
            return False, False

        has_obstacle = False
        has_dropoff = False

        try:
            detected_objects = self.obstacle_detector.detect_obstacles()

            if detected_objects:
                for obj in detected_objects:
                    if obj['class_name'] in self._objects_to_avoid():
                        score = obj['score']
                        # Format is [ymin, xmin, ymax, xmax]
                        box = obj['box']

                        box_area = (box[2] - box[0]) * (box[3] - box[1])
                        if score > 0.5 and box_area > 0.1:
                            has_obstacle = True
                            class_name = obj['class_name']
                            msg = (
                                f"Camera detected obstacle: {class_name} "
                                f"(conf: {score:.2f})"
                            )
                            self.logger.info(msg)
                            break

            # TODO: Implement drop-off detection using depth analysis

        except Exception as e:
            self.logger.error(f"Error during camera obstacle detection: {e}")

        return has_obstacle, has_dropoff

    def _objects_to_avoid(self):
        """Return list of object classes to treat as obstacles."""
        return [
            'person', 'animal', 'vehicle', 'obstacle', 'fence',
            'wall', 'tree', 'bush'
        ]

    def start(self) -> None:
        """Start the avoidance algorithm background monitoring."""
        if self.running:
            logger.warning("Avoidance algorithm already running")
            return

        with self.thread_lock:
            self.running = True
            self.stop_thread = False
            self.current_state = AvoidanceState.NORMAL

        self.avoidance_thread = threading.Thread(
            target=self._avoidance_loop,
            daemon=True
        )
        self.avoidance_thread.start()
        logger.info("Avoidance algorithm started")

    def stop(self) -> None:
        """Stop the avoidance algorithm background monitoring."""
        if not self.running:
            return

        logger.info("Stopping avoidance algorithm...")

        with self.thread_lock:
            self.stop_thread = True
            self.running = False

        if self.avoidance_thread and self.avoidance_thread.is_alive():
            try:
                self.avoidance_thread.join(timeout=5.0)
                if self.avoidance_thread.is_alive():
                    logger.warning(
                        "Avoidance thread did not terminate within timeout"
                    )
            except Exception as e:
                logger.error(f"Error stopping avoidance thread: {e}")

        self.avoidance_thread = None
        logger.info("Avoidance algorithm stopped")

    def _update_sensor_obstacle_status(self):
        """
        Update obstacle status based on distance sensor readings.

        This method checks the VL53L0X distance sensors and updates
        the obstacle_left and obstacle_right flags accordingly.
        """
        try:
            left_distance = self.sensor_interface._read_vl53l0x(
                'left_distance', float('inf')
            )
            right_distance = self.sensor_interface._read_vl53l0x(
                'right_distance', float('inf')
            )

            with self.thread_lock:
                self.obstacle_left = left_distance < MIN_DISTANCE_THRESHOLD
                self.obstacle_right = right_distance < MIN_DISTANCE_THRESHOLD

            if self.obstacle_left:
                logger.debug(f"Left obstacle detected: {left_distance}cm")
            if self.obstacle_right:
                logger.debug(f"Right obstacle detected: {right_distance}cm")

        except Exception as e:
            logger.error(f"Error updating sensor obstacle status: {e}")

    def _avoidance_loop(self) -> None:
        """Main loop for obstacle detection and avoidance."""
        logger.info("Avoidance monitoring loop started")

        try:
            while not self.stop_thread and self.running:
                self._update_sensor_obstacle_status()

                if self.camera:
                    self.check_camera_obstacles_and_dropoffs()

                current_state = None
                with self.thread_lock:
                    current_state = self.current_state

                if current_state == AvoidanceState.NORMAL:
                    obstacle_detected, obstacle_data = self._detect_obstacle()
                    if obstacle_detected:
                        logger.info("Obstacle detected, initiating avoidance")
                        with self.thread_lock:
                            self.current_state = (
                                AvoidanceState.OBSTACLE_DETECTED)
                            self.obstacle_data = obstacle_data

                elif current_state == AvoidanceState.OBSTACLE_DETECTED:
                    success = self._start_avoidance()
                    with self.thread_lock:
                        if success:
                            self.current_state = AvoidanceState.AVOIDING
                        else:
                            self.current_state = AvoidanceState.RECOVERY
                            self.recovery_attempts = 0

                elif current_state == AvoidanceState.AVOIDING:
                    avoidance_complete = self._continue_avoidance()

                    if avoidance_complete:
                        logger.info(
                            "Avoidance complete, returning to normal operation"
                        )
                        with self.thread_lock:
                            self.current_state = AvoidanceState.NORMAL
                            self.obstacle_data = None

                    still_detected, _ = self._detect_obstacle()
                    if still_detected:
                        logger.warning(
                            "Obstacle still detected after avoidance maneuver"
                        )
                        with self.thread_lock:
                            self.current_state = AvoidanceState.RECOVERY
                            self.recovery_attempts = 0

                elif current_state == AvoidanceState.RECOVERY:
                    recovery_success = self._execute_recovery()

                    with self.thread_lock:
                        if recovery_success:
                            still_detected, _ = self._detect_obstacle()
                            if not still_detected:
                                logger.info(
                                    "Recovery successful, returning to normal "
                                    "operation"
                                )
                                self.current_state = AvoidanceState.NORMAL
                                self.obstacle_data = None
                            else:
                                logger.warning(
                                    "Obstacle still present after recovery, "
                                    "trying again"
                                )
                                self.recovery_attempts += 1
                                if (self.recovery_attempts >=
                                        self.max_recovery_attempts):
                                    logger.error(
                                        "Max recovery attempts reached, "
                                        "cannot avoid obstacle"
                                    )
                        else:
                            logger.error("Recovery strategy failed")
                            self.recovery_attempts += 1

                time.sleep(AVOIDANCE_DELAY)

        except Exception as e:
            logger.error(f"Error in avoidance loop: {e}")
            with self.thread_lock:
                self.running = False

        logger.info("Avoidance monitoring loop ended")

    def _detect_obstacle(self) -> Tuple[bool, Optional[dict]]:
        """
        Check all sensors to detect obstacles.
        This method combines data from distance sensors and
        camera (if available) to determine if
        an obstacle is present and its characteristics.

        Returns:
            Tuple[bool, Optional[dict]]:
                - bool: True if an obstacle is detected, False otherwise
                - dict: Data about the detected obstacle, or None if no
                  obstacle detected
        """
        with self.thread_lock:
            obstacle_left = self.obstacle_left
            obstacle_right = self.obstacle_right

            camera_obstacle = self.camera_obstacle_detected
            dropoff = self.dropoff_detected

            obstacle_detected = (
                obstacle_left or obstacle_right or
                camera_obstacle or dropoff
            )

            if not obstacle_detected:
                return False, None

            obstacle_data = {
                "left_sensor": obstacle_left,
                "right_sensor": obstacle_right,
                "camera_detected": camera_obstacle,
                "dropoff_detected": dropoff,
                "timestamp": time.time()
            }

            obstacle_position = self._estimate_obstacle_position()
            if obstacle_position:
                obstacle_data.update(obstacle_position)

            return True, obstacle_data

    def _start_avoidance(self) -> bool:
        """
        Initiate the obstacle avoidance procedure.

        This method:
        1. Stops the robot's current movement
        2. Analyzes the obstacle data to determine the best avoidance strategy
        3. Begins executing the selected avoidance maneuver

        Returns:
            bool: True if avoidance initiated successfully, False otherwise
        """
        logger.info("Starting obstacle avoidance")

        try:
            self.motor_controller.stop()

            obstacle_data = None
            with self.thread_lock:
                obstacle_data = self.obstacle_data

            if not obstacle_data:
                logger.error("No obstacle data available to start avoidance")
                return False

            if obstacle_data.get("dropoff_detected", False):
                logger.info("Dropoff detected, backing up")
                return self._backup_strategy(distance=50.0)

            elif (obstacle_data.get("left_sensor", False) and
                  not obstacle_data.get("right_sensor", False)):
                logger.info("Obstacle on left side, turning right")
                return self._turn_right_strategy(angle=45.0)

            elif (obstacle_data.get("right_sensor", False) and
                  not obstacle_data.get("left_sensor", False)):
                logger.info("Obstacle on right side, turning left")
                return self._turn_left_strategy(angle=45.0)

            elif (obstacle_data.get("camera_detected", False) or
                  (obstacle_data.get("left_sensor", False) and
                   obstacle_data.get("right_sensor", False))):
                logger.info("Obstacle detected ahead, backing up")
                backup_success = self._backup_strategy(distance=40.0)
                if not backup_success:
                    return False

                return self._select_random_strategy()

            else:
                logger.info("Using random avoidance strategy")
                return self._select_random_strategy()

        except Exception as e:
            logger.error(f"Error starting avoidance: {e}")
            return False

    def _continue_avoidance(self) -> bool:
        """
        Continue the current avoidance maneuver.

        This method:
        1. Checks if the current avoidance maneuver is complete
        2. Returns True if avoidance is complete, False if still avoiding
        3. Updates obstacle data if needed during avoidance

        Returns:
            bool: True if avoidance is complete, False if still in progress
        """
        nav_status = self.motor_controller.get_status()

        if nav_status == NavigationStatus.TARGET_REACHED:
            logger.info("Avoidance maneuver completed")
            return True

        elif nav_status == NavigationStatus.MOVING:
            logger.debug("Continuing avoidance maneuver")
            return False

        elif nav_status == NavigationStatus.ERROR:
            logger.error("Error during avoidance maneuver")
            return False

        else:
            obstacle_data = None
            with self.thread_lock:
                obstacle_data = self.obstacle_data

            if not obstacle_data:
                logger.warning("No obstacle data available during avoidance")
                return True

            start_time = obstacle_data.get("timestamp", 0)
            current_time = time.time()

            if current_time - start_time > 30.0:
                logger.warning(
                    "Avoidance timeout, considering maneuver complete"
                )
                return True

            return False

    def _execute_recovery(self) -> bool:
        """
        Execute a recovery strategy when normal avoidance fails.

        This method is called when the robot cannot avoid an obstacle using
        standard strategies. It implements more aggressive recovery maneuvers
        to get the robot out of difficult situations.

        Recovery strategies increase in aggressiveness with each attempt:
        1. First attempt: larger turn angle
        2. Second attempt: longer backup distance
        3. Third attempt: combination of backup and turn

        Returns:
            bool: True if recovery initiated successfully, False otherwise
        """
        logger.info(
            f"Executing recovery (attempt {self.recovery_attempts + 1})"
        )

        try:
            attempt = 0
            with self.thread_lock:
                attempt = self.recovery_attempts

            if attempt == 0:
                turn_angle = 90.0

                obstacle_data = None
                with self.thread_lock:
                    obstacle_data = self.obstacle_data

                if obstacle_data and obstacle_data.get("left_sensor", False):
                    logger.info(
                        f"Recovery attempt {attempt + 1}: "
                        "aggressive right turn"
                    )
                    return self._turn_right_strategy(angle=turn_angle)
                else:
                    logger.info(
                        f"Recovery attempt {attempt + 1}: aggressive left turn"
                    )
                    return self._turn_left_strategy(angle=turn_angle)

            elif attempt == 1:
                logger.info(f"Recovery attempt {attempt + 1}: extended backup")
                return self._backup_strategy(distance=80.0)

            else:
                logger.info(
                    f"Recovery attempt {attempt + 1}: alternative route"
                )
                return self._alternative_route_strategy()

        except Exception as e:
            logger.error(f"Error executing recovery: {e}")
            return False

    def _select_random_strategy(self) -> bool:
        """
        Select and execute a random avoidance strategy.

        This method chooses a random strategy from the available
        avoidance strategies when no specific strategy is indicated
        by the sensor data.

        Returns:
            bool: True if strategy executed successfully, False otherwise
        """
        try:
            strategies = [
                self._turn_right_strategy,
                self._turn_left_strategy,
                self._backup_strategy
            ]

            strategy = random.choice(strategies)
            strategy_name = strategy.__name__

            logger.info(f"Selected random strategy: {strategy_name}")
            # Check if strategy is a turn strategy
            if strategy in (
                    self._turn_right_strategy,
                    self._turn_left_strategy
            ):
                angle = random.uniform(30.0, 60.0)
                return strategy(angle=angle)
            elif strategy == self._backup_strategy:
                distance = random.uniform(20.0, 40.0)
                return strategy(distance=distance)
            else:
                return strategy()

        except Exception as e:
            logger.error(f"Error selecting random strategy: {e}")
            return False

    def _turn_right_strategy(self, angle: float = 45.0) -> bool:
        """
        Execute a right turn to avoid an obstacle.

        Args:
            angle: Turn angle in degrees (default: 45.0)

        Returns:
            bool: True if turn initiated successfully, False otherwise
        """
        try:
            logger.info(f"Executing right turn avoidance ({angle}°)")

            current_heading = self.motor_controller.get_current_heading()

            new_heading = current_heading + angle
            new_heading = new_heading % 360

            self.motor_controller.rotate_to_heading(new_heading)

            return True
        except Exception as e:
            logger.error(f"Error executing right turn: {e}")
            return False

    def _turn_left_strategy(self, angle: float = 45.0) -> bool:
        """
        Execute a left turn to avoid an obstacle.

        Args:
            angle: Turn angle in degrees (default: 45.0)

        Returns:
            bool: True if turn initiated successfully, False otherwise
        """
        try:
            logger.info(f"Executing left turn avoidance ({angle}°)")

            current_heading = self.motor_controller.get_current_heading()

            new_heading = current_heading - angle
            new_heading = new_heading % 360

            self.motor_controller.rotate_to_heading(new_heading)

            return True
        except Exception as e:
            logger.error(f"Error executing left turn: {e}")
            return False

    def _backup_strategy(self, distance: float = 30.0) -> bool:
        """
        Execute a backward movement to avoid an obstacle.

        Args:
            distance: Backup distance in cm (default: 30.0)

        Returns:
            bool: True if backup initiated successfully, False otherwise
        """
        try:
            logger.info(f"Executing backup avoidance ({distance} cm)")

            current_heading = self.motor_controller.get_current_heading()

            reverse_heading = (current_heading + 180) % 360

            self.motor_controller.rotate_to_heading(reverse_heading)

            time.sleep(2.0)

            self.motor_controller.move_distance(distance / 100.0)

            return True
        except Exception as e:
            logger.error(f"Error executing backup: {e}")
            return False

    def _alternative_route_strategy(self) -> bool:
        """
        Calculate and follow an alternative route to avoid an obstacle.

        This method:
        1. Identifies the obstacle location
        2. Updates the path planner's obstacle map
        3. Requests a new path that avoids the obstacle
        4. Begins following the new path

        Returns:
            bool: True if alternative route initiated successfully,
                False otherwise
        """
        try:
            logger.info("Calculating alternative route")

            current_position = self.motor_controller.get_current_position()
            if not current_position:
                logger.error(
                    "Unable to get current position for alternative route"
                )
                return False

            obstacle_position = self._estimate_obstacle_position()
            if not obstacle_position or not obstacle_position.get('position'):
                logger.error("Unable to estimate obstacle position")
                return False

            obstacle_coords = obstacle_position['position']

            logger.info(f"Adding obstacle at position {obstacle_coords}")
            self.pattern_planner.update_obstacle_map([obstacle_coords])

            goal = self.pattern_planner.get_current_goal()
            if not goal:
                logger.error("No goal available for alternative route")
                return False

            logger.info("Requesting new path to avoid obstacle")
            start_point = self.pattern_planner.coord_to_grid(
                current_position[0], current_position[1]
            )
            goal_point = self.pattern_planner.coord_to_grid(goal[0], goal[1])

            new_path = self.pattern_planner.get_path(start_point, goal_point)
            if not new_path or len(new_path) == 0:
                logger.error("Failed to calculate alternative route")
                return False

            logger.info(
                f"Found alternative route with {len(new_path)} waypoints"
            )

            first_waypoint = new_path[0]
            self.motor_controller.navigate_to_location(
                (first_waypoint['lat'], first_waypoint['lng'])
            )

            return True

        except Exception as e:
            logger.error(f"Error calculating alternative route: {e}")
            return False

    def _estimate_obstacle_position(self) -> Dict[str, Any]:
        """
        Estimate the position of detected obstacles in world coordinates.

        This method combines sensor data with the robot's current position
        and orientation to estimate where obstacles are located in the
        world coordinate system. This information is used to update the
        path planning obstacle map.

        Returns:
            Dict: Information about the obstacle position and type, including:
                - 'position': (lat, lng) tuple of obstacle coordinates
                - 'type': String identifier of obstacle type ('static',
                  'moving', etc.)
                - 'confidence': Confidence level of the detection (0.0-1.0)
                - 'sensor': Which sensor detected the obstacle
        """
        try:
            current_position = self.motor_controller.get_current_position()
            if not current_position:
                logger.warning(
                    "Couldn't get current position for obstacle estimation"
                )
                return {}

            current_lat, current_lng = current_position[0], current_position[1]

            heading = self.motor_controller.get_current_heading()
            if heading is None:
                logger.warning(
                    "Couldn't get current heading for obstacle estimation"
                )
                return {}

            heading_rad = math.radians(heading)

            obstacle_data = None
            with self.thread_lock:
                obstacle_data = self.obstacle_data

            if not obstacle_data:
                logger.warning(
                    "No obstacle data available for position estimation"
                )
                return {}

            result = {
                'position': None,
                'type': 'static',
                'confidence': 0.8,
                'sensor': 'unknown'
            }

            distance = 0.0
            obstacle_angle = 0.0

            if (obstacle_data.get('left_sensor', False) and
                    obstacle_data.get('right_sensor', False)):
                distance = self.obstacle_threshold
                obstacle_angle = 0.0
                result['sensor'] = 'tof_both'

            elif obstacle_data.get('left_sensor', False):
                distance = self.obstacle_threshold
                obstacle_angle = math.radians(30.0)
                result['sensor'] = 'tof_left'

            elif obstacle_data.get('right_sensor', False):
                distance = self.obstacle_threshold
                obstacle_angle = math.radians(-30.0)
                result['sensor'] = 'tof_right'

            elif obstacle_data.get('camera_detected', False):
                distance = self.obstacle_threshold * 1.5
                obstacle_angle = 0.0
                result['sensor'] = 'camera'
                result['confidence'] = 0.9

            else:
                logger.warning(
                    "Cannot determine obstacle direction from sensor data"
                )
                return {}

            obstacle_heading = (heading_rad + obstacle_angle) % (2 * math.pi)

            meters_to_lat = 0.0000089
            meters_to_lng = (
                0.0000089 / math.cos(math.radians(current_lat))
            )

            obstacle_lat = current_lat + (
                distance * math.cos(obstacle_heading) * meters_to_lat
            )
            obstacle_lng = current_lng + (
                distance * math.sin(obstacle_heading) * meters_to_lng
            )

            result['position'] = (obstacle_lat, obstacle_lng)

            logger.debug(f"Estimated obstacle position: {result['position']}")

            return result

        except Exception as e:
            logger.error(f"Error estimating obstacle position: {e}")
            return {}

    def _handle_obstacle_detected(self, obstacle_data):
        """
        Handle detected obstacle by choosing and executing avoidance strategy.

        Args:
            obstacle_data: Dict containing obstacle detection info
        """
        if self.current_state != AvoidanceState.NORMAL:
            return

        self.current_state = AvoidanceState.OBSTACLE_DETECTED
        self.obstacle_data = obstacle_data

        # Try each strategy in order until one succeeds
        for strategy in self.avoidance_strategies:
            if strategy():
                self.current_state = AvoidanceState.AVOIDING
                break
        else:
            # No strategy worked, enter recovery mode
            self.current_state = AvoidanceState.RECOVERY
            self._handle_recovery()

    def _handle_recovery(self):
        """
        Handle recovery when normal avoidance strategies fail.

        Implements increasingly aggressive recovery attempts when the mower
        gets stuck or cannot find a valid path around an obstacle.
        """
        if self.recovery_attempts >= self.max_recovery_attempts:
            msg = (
                "Max recovery attempts reached. "
                "Stopping and waiting for manual intervention."
            )
            self.logger.error(msg)
            self.stop()
            return

        self.recovery_attempts += 1

        # Try more aggressive avoidance maneuvers
        backup_dist = 50 + (self.recovery_attempts * 25)  # cm
        turn_angle = 45 + (self.recovery_attempts * 15)  # degrees

        msg = (
            f"Recovery attempt {self.recovery_attempts}: "
            f"Backup {backup_dist}cm, turn {turn_angle} degrees"
        )
        self.logger.info(msg)

    def check_obstacles(self) -> bool:
        """Check for obstacles in the current path."""
        try:
            # Get sensor data
            sensor_data = self._get_sensor_data()

            # Process sensor data to detect obstacles
            self.obstacles = self._process_sensor_data(sensor_data)

            # Check if any obstacles are in the path
            if self.obstacles:
                logger.info(f"Detected {len(self.obstacles)} obstacles")
                return True

            return False

        except Exception as e:
            logger.error(f"Error checking for obstacles: {e}")
            return False

    def avoid_obstacle(self) -> bool:
        """Modify path to avoid detected obstacles."""
        try:
            if not self.obstacles:
                return True

            # Transition to AVOIDING state
            self.current_state = AvoidanceState.AVOIDING

            # Get current path
            current_path = self.pattern_planner.current_path

            # Find obstacle positions in path
            obstacle_indices = self._find_obstacle_positions(
                current_path, self.obstacles
            )

            if not obstacle_indices:
                logger.warning("No obstacles found in current path")
                return True

            # Modify path to avoid obstacles
            new_path = self._modify_path(current_path, obstacle_indices)

            if not new_path:
                logger.error("Failed to generate obstacle avoidance path")
                return False

            # Update pattern planner with new path
            self.pattern_planner.current_path = new_path

            # Transition back to NORMAL state
            self.current_state = AvoidanceState.NORMAL
            return True

        except Exception as e:
            logger.error(f"Error avoiding obstacle: {e}")
            return False

    def _get_sensor_data(self) -> List[float]:
        """Get sensor data from hardware interface."""
        try:
            # This would interface with actual sensors
            # For now, return dummy data
            return [0.0] * 8
        except Exception as e:
            logger.error(f"Error getting sensor data: {e}")
            return []

    def _process_sensor_data(
        self,
        sensor_data: List[float]
    ) -> List[Obstacle]:
        """Process sensor data to detect obstacles."""
        try:
            obstacles = []

            # Process each sensor reading
            for i, reading in enumerate(sensor_data):
                if reading > 0.5:  # Threshold for obstacle detection
                    # Calculate obstacle position based on sensor position
                    angle = i * (2 * np.pi / len(sensor_data))
                    distance = reading

                    position = (
                        distance * np.cos(angle),
                        distance * np.sin(angle)
                    )

                    # Create obstacle object
                    obstacle = Obstacle(
                        position=position,
                        size=0.2,  # Default size in meters
                        confidence=min(1.0, reading)
                    )

                    obstacles.append(obstacle)

            return obstacles

        except Exception as e:
            logger.error(f"Error processing sensor data: {e}")
            return []

    def _find_obstacle_positions(
        self,
        path: List[Tuple[float, float]],
        obstacles: List[Obstacle]
    ) -> List[int]:
        """Find indices of path points near obstacles."""
        try:
            obstacle_indices = []

            for i, point in enumerate(path):
                for obstacle in obstacles:
                    distance = np.linalg.norm(
                        np.array(point) - np.array(obstacle.position)
                    )

                    if distance < obstacle.size + 0.1:  # Safety margin
                        obstacle_indices.append(i)
                        break

            return obstacle_indices

        except Exception as e:
            logger.error(f"Error finding obstacle positions: {e}")
            return []

    def _modify_path(
        self,
        path: List[Tuple[float, float]],
        obstacle_indices: List[int]
    ) -> List[Tuple[float, float]]:
        """Modify path to avoid obstacles."""
        try:
            if not obstacle_indices:
                return path

            # Create new path by removing points near obstacles
            new_path = [
                point for i, point in enumerate(path)
                if i not in obstacle_indices
            ]

            # Add intermediate points to smooth the path
            smoothed_path = self._smooth_path(new_path)

            return smoothed_path

        except Exception as e:
            logger.error(f"Error modifying path: {e}")
            return []

    def _smooth_path(
        self,
        path: List[Tuple[float, float]]
    ) -> List[Tuple[float, float]]:
        """Smooth the path by adding intermediate points."""
        try:
            if len(path) < 3:
                return path

            smoothed_path = []

            # Add first point
            smoothed_path.append(path[0])

            # Add intermediate points
            for i in range(len(path) - 1):
                p1 = np.array(path[i])
                p2 = np.array(path[i + 1])

                # Calculate midpoint
                midpoint = (p1 + p2) / 2

                # Add midpoint if it's not too close to existing points
                if np.linalg.norm(midpoint - p1) > 0.1:
                    smoothed_path.append(tuple(midpoint))

                # Add next point
                smoothed_path.append(path[i + 1])

            return smoothed_path

        except Exception as e:
            logger.error(f"Error smoothing path: {e}")
            return path

    def cleanup(self):
        """Clean up resources used by the avoidance algorithm."""
        try:
            # Add any specific cleanup logic here
            logger.info("Avoidance algorithm cleaned up successfully.")
        except Exception as e:
            logger.error(f"Error cleaning up avoidance algorithm: {e}")
