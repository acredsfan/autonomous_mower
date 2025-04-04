"""
Obstacle avoidance algorithm for the autonomous mower.

This module implements real-time obstacle detection and avoidance
functionality, allowing the mower to safely navigate around obstacles
in its path while continuing to follow the planned mowing route.

The avoidance algorithm:
1. Continuously monitors sensor data for obstacles
2. Implements various avoidance strategies based on obstacle type
3. Coordinates with the path planner to adjust routes when obstacles
   are detected
4. Manages thread-safe interaction between sensors, motors, and
   navigation

Key features:
- Thread-safe operation with proper synchronization
- Multiple avoidance strategies (turn, backup, reroute)
- Dynamic path adjustment based on obstacle proximity
- Integration with machine learning-based obstacle detection
"""

import threading
import time
import logging
import random
import math
import os
from enum import Enum
from typing import Optional, Tuple, List, Dict, Any

from mower.utilities.logger_config import LoggerConfigInfo as LoggerConfig
from mower.constants import (
    AVOIDANCE_DELAY,
    CAMERA_OBSTACLE_THRESHOLD,
    MIN_DISTANCE_THRESHOLD
)
from mower.navigation.path_planning import PathPlanner
from mower.navigation.navigation import NavigationController
from mower.hardware.sensor_interface import SensorInterface

# Initialize logger
logger = LoggerConfig.get_logger(__name__)

# Define navigation status enum for internal use
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
    NORMAL = 0
    OBSTACLE_DETECTED = 1
    AVOIDING = 2
    RECOVERY = 3

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

    def __init__(self, resource_manager=None):
        """
        Initialize the avoidance algorithm.
        
        Args:
            resource_manager: Optional ResourceManager instance to access system resources
        """
        self.logger = logger.getLogger('mower.avoidance')
        
        # Get resource manager if not provided
        if resource_manager is None:
            from mower.main_controller import ResourceManager
            resource_manager = ResourceManager()
            
        # Store resource manager reference
        self._resource_manager = resource_manager
        
        # Camera-related settings
        self.use_camera = bool(os.environ.get('USE_CAMERA', 'True').lower() == 'true')
        self.camera = None
        self.obstacle_detector = None
        
        if self.use_camera:
            try:
                # Get camera instance through resource manager
                self.camera = self._resource_manager.get_camera()
                
                # Get obstacle detector through resource manager
                self.obstacle_detector = self._resource_manager.get_obstacle_detector()
                self.logger.info("Initialized camera and obstacle detector for visual detection")
            except Exception as e:
                self.logger.error(f"Failed to initialize camera components: {e}")
                self.use_camera = False
        
        # Initialize algorithm state
        self.reset_state()

    def reset_state(self):
        """
        Reset the state of the avoidance algorithm.
        
        This method initializes all necessary attributes to start a new
        avoidance session.
        """
        self.path_planner = None
        self.motor_controller = None
        self.sensor_interface = None
        self.current_state = AvoidanceState.NORMAL
        self.obstacle_data = None
        self.obstacle_left = False
        self.obstacle_right = False
        self.camera_obstacle_detected = False
        self.dropoff_detected = False
        
        # Thread management
        self.thread_lock = threading.RLock()
        self.running = False
        self.stop_thread = False
        self.avoidance_thread = None
        
        # Configuration parameters
        self.obstacle_threshold = 30.0  # cm
        self.safe_distance = 50.0  # cm
        self.recovery_attempts = 0
        self.max_recovery_attempts = 3
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
        if not self.use_camera or self.camera is None or self.obstacle_detector is None:
            return False, False
            
        has_obstacle = False
        has_dropoff = False
        
        try:
            # Use the obstacle detector to check for obstacles
            # This now handles capturing the frame from the camera
            detected_objects = self.obstacle_detector.detect_obstacles()
            
            if detected_objects:
                # Check if any detected objects require avoidance
                for obj in detected_objects:
                    if obj['class_name'] in self._objects_to_avoid():
                        score = obj['score']
                        box = obj['box']  # Format is [ymin, xmin, ymax, xmax]
                        
                        # If object is large enough and confidence is high
                        # Call it an obstacle
                        box_area = (box[2] - box[0]) * (box[3] - box[1])
                        if score > 0.5 and box_area > 0.1:
                            has_obstacle = True
                            self.logger.info(f"Camera detected obstacle: {obj['class_name']} "
                                             f"(confidence: {score:.2f})")
                            break
            
            # TODO: Implement drop-off detection using depth analysis or edge detection
            # Currently not implemented
            
        except Exception as e:
            self.logger.error(f"Error during camera obstacle detection: {e}")
            
        return has_obstacle, has_dropoff
    
    def _objects_to_avoid(self):
        """
        Return list of object classes that should be treated as obstacles.
        
        Returns:
            list: Object class names to avoid
        """
        # Objects the mower should recognize and avoid
        return [
            'person', 'bicycle', 'car', 'motorcycle', 'bus', 'truck', 
            'dog', 'cat', 'horse', 'sheep', 'cow', 'animal',
            'bench', 'potted plant', 'fence', 'rock', 'stone'
        ]

    def start(self) -> None:
        """
        Start the avoidance algorithm background monitoring.
        
        This initializes and starts the background thread that continuously
        monitors sensor data for obstacles and manages the avoidance state machine.
        
        The thread runs until explicitly stopped by calling stop().
        """
        if self.running:
            logger.warning("Avoidance algorithm already running")
            return
            
        with self.thread_lock:
            self.running = True
            self.stop_thread = False
            self.current_state = AvoidanceState.NORMAL
            
        # Start the avoidance monitoring thread
        self.avoidance_thread = threading.Thread(
            target=self._avoidance_loop,
            daemon=True
        )
        self.avoidance_thread.start()
        logger.info("Avoidance algorithm started")

    def stop(self) -> None:
        """
        Stop the avoidance algorithm background monitoring.
        
        This signals the monitoring thread to terminate and waits for it
        to complete before returning. This ensures a clean shutdown.
        """
        if not self.running:
            return
            
        logger.info("Stopping avoidance algorithm...")
        
        with self.thread_lock:
            self.stop_thread = True
            self.running = False
        
        # Wait for thread to terminate
        if self.avoidance_thread and self.avoidance_thread.is_alive():
            try:
                self.avoidance_thread.join(timeout=5.0)
                if self.avoidance_thread.is_alive():
                    logger.warning("Avoidance thread did not terminate within timeout")
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
                'left_distance', float('inf'))
            right_distance = self.sensor_interface._read_vl53l0x(
                'right_distance', float('inf'))

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
        """
        Main loop for obstacle detection and avoidance.
        
        This method runs in a separate thread and continuously:
        1. Checks sensors for obstacles
        2. Updates the internal state based on sensor readings
        3. Executes appropriate avoidance actions based on the state
        4. Transitions between states as obstacles are detected and avoided
        
        The loop handles state transitions and execution logic using the
        avoidance state machine.
        """
        logger.info("Avoidance monitoring loop started")
        
        try:
            while not self.stop_thread and self.running:
                # Read updated sensor data
                self._update_sensor_obstacle_status()
                
                # Check camera if available
                if self.camera:
                    self.check_camera_obstacles_and_dropoffs()
                
                # Get current state (thread-safe)
                current_state = None
                with self.thread_lock:
                    current_state = self.current_state
                
                # State machine logic
                if current_state == AvoidanceState.NORMAL:
                    # Check for obstacles
                    obstacle_detected, obstacle_data = self._detect_obstacle()
                    if obstacle_detected:
                        logger.info("Obstacle detected, initiating avoidance")
                        with self.thread_lock:
                            self.current_state = AvoidanceState.OBSTACLE_DETECTED
                            self.obstacle_data = obstacle_data
                
                elif current_state == AvoidanceState.OBSTACLE_DETECTED:
                    # Start avoidance procedure
                    success = self._start_avoidance()
                    with self.thread_lock:
                        if success:
                            self.current_state = AvoidanceState.AVOIDING
                        else:
                            # Failed to start avoidance, try recovery
                            self.current_state = AvoidanceState.RECOVERY
                            self.recovery_attempts = 0
                
                elif current_state == AvoidanceState.AVOIDING:
                    # Continue avoidance procedure
                    avoidance_complete = self._continue_avoidance()
                    
                    if avoidance_complete:
                        logger.info("Avoidance complete, returning to normal operation")
                        with self.thread_lock:
                            self.current_state = AvoidanceState.NORMAL
                            self.obstacle_data = None
                    
                    # Check if we still detect obstacles after avoidance maneuver
                    still_detected, _ = self._detect_obstacle()
                    if still_detected:
                        logger.warning("Obstacle still detected after avoidance maneuver")
                        with self.thread_lock:
                            self.current_state = AvoidanceState.RECOVERY
                            self.recovery_attempts = 0
                
                elif current_state == AvoidanceState.RECOVERY:
                    # Execute recovery strategy
                    recovery_success = self._execute_recovery()
                    
                    with self.thread_lock:
                        if recovery_success:
                            # Check if obstacle is still present
                            still_detected, _ = self._detect_obstacle()
                            if not still_detected:
                                logger.info("Recovery successful, returning to normal operation")
                                self.current_state = AvoidanceState.NORMAL
                                self.obstacle_data = None
                            else:
                                logger.warning("Obstacle still present after recovery, trying again")
                                self.recovery_attempts += 1
                                if self.recovery_attempts >= self.max_recovery_attempts:
                                    logger.error("Max recovery attempts reached, cannot avoid obstacle")
                                    # Keep in RECOVERY state, main controller will handle this
                        else:
                            logger.error("Recovery strategy failed")
                            self.recovery_attempts += 1
                
                # Brief pause to avoid CPU spinning
                time.sleep(AVOIDANCE_DELAY)
                
        except Exception as e:
            logger.error(f"Error in avoidance loop: {e}")
            with self.thread_lock:
                self.running = False
        
        logger.info("Avoidance monitoring loop ended")

    def _detect_obstacle(self) -> Tuple[bool, Optional[dict]]:
        """
        Check all sensors to detect obstacles.
        
        This method combines data from distance sensors and camera (if available)
        to determine if an obstacle is present and its characteristics.
        
        Returns:
            Tuple[bool, Optional[dict]]: 
                - bool: True if an obstacle is detected, False otherwise
                - dict: Data about the detected obstacle, or None if no obstacle
        """
        with self.thread_lock:
            # Check distance sensors
            obstacle_left = self.obstacle_left
            obstacle_right = self.obstacle_right
            
            # Check camera obstacles
            camera_obstacle = self.camera_obstacle_detected
            dropoff = self.dropoff_detected
            
            # Determine if any obstacle is detected
            obstacle_detected = obstacle_left or obstacle_right or camera_obstacle or dropoff
            
            if not obstacle_detected:
                return False, None
            
            # Collect data about the obstacle for avoidance strategy
            obstacle_data = {
                "left_sensor": obstacle_left,
                "right_sensor": obstacle_right,
                "camera_detected": camera_obstacle,
                "dropoff_detected": dropoff,
                "timestamp": time.time()
            }
            
            # Add position estimation if we can determine it
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
            # Stop current movement
            self.motor_controller.stop()
            
            # Get the obstacle data
            obstacle_data = None
            with self.thread_lock:
                obstacle_data = self.obstacle_data
            
            if not obstacle_data:
                logger.error("No obstacle data available to start avoidance")
                return False
            
            # Determine avoidance strategy based on sensor data
            if obstacle_data.get("dropoff_detected", False):
                # Always back up from dropoffs
                logger.info("Dropoff detected, backing up")
                return self._backup_strategy(distance=50.0)
                
            # If obstacle is only on one side, turn away from it
            elif obstacle_data.get("left_sensor", False) and not obstacle_data.get("right_sensor", False):
                logger.info("Obstacle on left side, turning right")
                return self._turn_right_strategy(angle=45.0)
                
            elif obstacle_data.get("right_sensor", False) and not obstacle_data.get("left_sensor", False):
                logger.info("Obstacle on right side, turning left")
                return self._turn_left_strategy(angle=45.0)
                
            # If obstacles detected on both sides or by camera, back up then try alternative route
            elif obstacle_data.get("camera_detected", False) or (
                    obstacle_data.get("left_sensor", False) and 
                    obstacle_data.get("right_sensor", False)):
                logger.info("Obstacle detected ahead, backing up")
                backup_success = self._backup_strategy(distance=40.0)
                if not backup_success:
                    return False
                
                # After backing up, try to find an alternative route
                return self._select_random_strategy()
            
            # If no specific strategy determined, use a random one
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
        2. Returns True if the avoidance is complete, False if still in progress
        3. Updates obstacle data if needed during avoidance
        
        Returns:
            bool: True if avoidance is complete, False if still in progress
        """
        # Check navigation status
        nav_status = self.motor_controller.get_status()
        
        # Determine if the current maneuver is complete
        if nav_status == NavigationStatus.TARGET_REACHED:
            # We've completed the avoidance maneuver
            logger.info("Avoidance maneuver completed")
            return True
            
        elif nav_status == NavigationStatus.MOVING:
            # Still executing the avoidance maneuver
            logger.debug("Continuing avoidance maneuver")
            return False
            
        elif nav_status == NavigationStatus.ERROR:
            # Something went wrong with the maneuver
            logger.error("Error during avoidance maneuver")
            return False
            
        else:
            # Check how long we've been trying to avoid
            obstacle_data = None
            with self.thread_lock:
                obstacle_data = self.obstacle_data
                
            if not obstacle_data:
                logger.warning("No obstacle data available during avoidance")
                return True  # Assume complete if no data
                
            # Check if we've been trying to avoid for too long
            start_time = obstacle_data.get("timestamp", 0)
            current_time = time.time()
            
            # If we've been in avoidance for more than 30 seconds, consider it complete
            # and let the recovery process take over if needed
            if current_time - start_time > 30.0:
                logger.warning("Avoidance timeout, considering maneuver complete")
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
        logger.info(f"Executing recovery (attempt {self.recovery_attempts + 1})")
        
        try:
            # Get current recovery attempt
            attempt = 0
            with self.thread_lock:
                attempt = self.recovery_attempts
            
            # Choose strategy based on attempt number
            if attempt == 0:
                # First recovery: more aggressive turn
                turn_angle = 90.0  # Larger angle for first recovery
                
                # Choose turn direction based on obstacle position
                obstacle_data = None
                with self.thread_lock:
                    obstacle_data = self.obstacle_data
                
                if obstacle_data and obstacle_data.get("left_sensor", False):
                    # Obstacle on left, turn right
                    logger.info(f"Recovery attempt {attempt+1}: aggressive right turn")
                    return self._turn_right_strategy(angle=turn_angle)
                else:
                    # Default or obstacle on right, turn left
                    logger.info(f"Recovery attempt {attempt+1}: aggressive left turn")
                    return self._turn_left_strategy(angle=turn_angle)
                    
            elif attempt == 1:
                # Second recovery: longer backup
                logger.info(f"Recovery attempt {attempt+1}: extended backup")
                return self._backup_strategy(distance=80.0)  # Longer distance
                
            else:
                # Third recovery: try alternative route calculation
                logger.info(f"Recovery attempt {attempt+1}: alternative route")
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
            # Pick a random strategy from the list, excluding alternative route
            # because it's more complex and should be used as a last resort
            strategies = [
                self._turn_right_strategy,
                self._turn_left_strategy,
                self._backup_strategy
            ]
            
            strategy = random.choice(strategies)
            strategy_name = strategy.__name__
            
            logger.info(f"Selected random strategy: {strategy_name}")
            
            # Execute the selected strategy
            if strategy == self._turn_right_strategy or strategy == self._turn_left_strategy:
                # For turning, use random angle between 30 and 60 degrees
                angle = random.uniform(30.0, 60.0)
                return strategy(angle=angle)
            elif strategy == self._backup_strategy:
                # For backup, use random distance between 20 and 40 cm
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
            
            # Get current orientation
            current_heading = self.motor_controller.get_current_heading()
            
            # Calculate new heading (add angle for right turn)
            new_heading = current_heading + angle
            # Normalize to 0-360 range
            new_heading = new_heading % 360
            
            # Execute the turn
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
            
            # Get current orientation
            current_heading = self.motor_controller.get_current_heading()
            
            # Calculate new heading (subtract angle for left turn)
            new_heading = current_heading - angle
            # Normalize to 0-360 range
            new_heading = new_heading % 360
            
            # Execute the turn
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
            
            # Get current heading
            current_heading = self.motor_controller.get_current_heading()
            
            # Calculate reverse heading (180° from current)
            reverse_heading = (current_heading + 180) % 360
            
            # First rotate to face backward
            self.motor_controller.rotate_to_heading(reverse_heading)
            
            # Wait for rotation to complete
            time.sleep(2.0)  # Adjust based on rotation speed
            
            # Then move forward (which is backward relative to original direction)
            # Convert cm to appropriate distance unit used by the navigation controller
            self.motor_controller.move_distance(distance / 100.0)  # Convert cm to meters
            
            return True
        except Exception as e:
            logger.error(f"Error executing backup: {e}")
            return False
    
    def _alternative_route_strategy(self) -> bool:
        """
        Calculate and follow an alternative route to avoid an obstacle.
        
        This strategy:
        1. Identifies the obstacle location
        2. Updates the path planner's obstacle map
        3. Requests a new path that avoids the obstacle
        4. Begins following the new path
        
        Returns:
            bool: True if alternative route initiated successfully, False otherwise
        """
        try:
            logger.info("Calculating alternative route")
            
            # Get current position and orientation
            current_position = self.motor_controller.get_current_position()
            if not current_position:
                logger.error("Unable to get current position for alternative route")
                return False
            
            # Estimate obstacle position
            obstacle_position = self._estimate_obstacle_position()
            if not obstacle_position or not obstacle_position.get('position'):
                logger.error("Unable to estimate obstacle position")
                return False
            
            # Extract obstacle coordinates
            obstacle_coords = obstacle_position['position']
            
            # Update path planner with obstacle
            logger.info(f"Adding obstacle at position {obstacle_coords}")
            self.path_planner.update_obstacle_map([obstacle_coords])
            
            # Get navigation goal
            goal = self.path_planner.get_current_goal()
            if not goal:
                logger.error("No goal available for alternative route")
                return False
            
            # Calculate new path
            logger.info("Requesting new path to avoid obstacle")
            start_point = self.path_planner.coord_to_grid(current_position[0], current_position[1])
            goal_point = self.path_planner.coord_to_grid(goal[0], goal[1])
            
            new_path = self.path_planner.get_path(start_point, goal_point)
            if not new_path or len(new_path) == 0:
                logger.error("Failed to calculate alternative route")
                return False
            
            logger.info(f"Found alternative route with {len(new_path)} waypoints")
            
            # Begin following new path
            # Just navigate to the first waypoint of the new path for now
            # The main navigation system will handle the rest
            first_waypoint = new_path[0]
            self.motor_controller.navigate_to_location((first_waypoint['lat'], first_waypoint['lng']))
            
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
                - 'type': String identifier of obstacle type ('static', 'moving', etc.)
                - 'confidence': Confidence level of the detection (0.0-1.0)
                - 'sensor': Which sensor detected the obstacle
        """
        try:
            # Get the current robot position
            current_position = self.motor_controller.get_current_position()
            if not current_position:
                logger.warning("Couldn't get current position for obstacle estimation")
                return {}
                
            current_lat, current_lng = current_position[0], current_position[1]
            
            # Get robot heading
            heading = self.motor_controller.get_current_heading()
            if heading is None:
                logger.warning("Couldn't get current heading for obstacle estimation")
                return {}
                
            # Convert heading from degrees to radians for calculations
            heading_rad = math.radians(heading)
            
            # Get obstacle data
            obstacle_data = None
            with self.thread_lock:
                obstacle_data = self.obstacle_data
                
            if not obstacle_data:
                logger.warning("No obstacle data available for position estimation")
                return {}
                
            # Initialize results with default values
            result = {
                'position': None,
                'type': 'static',
                'confidence': 0.8,
                'sensor': 'unknown'
            }
            
            # Determine distance and direction to obstacle based on which sensors detected it
            distance = 0.0
            obstacle_angle = 0.0
            
            if obstacle_data.get('left_sensor', False) and obstacle_data.get('right_sensor', False):
                # Both sensors detected - obstacle is directly ahead
                distance = self.obstacle_threshold  # Use configured threshold
                obstacle_angle = 0.0  # Straight ahead
                result['sensor'] = 'tof_both'
                
            elif obstacle_data.get('left_sensor', False):
                # Left sensor detected - obstacle is to the left
                distance = self.obstacle_threshold
                obstacle_angle = math.radians(30.0)  # 30 degrees to the left
                result['sensor'] = 'tof_left'
                
            elif obstacle_data.get('right_sensor', False):
                # Right sensor detected - obstacle is to the right
                distance = self.obstacle_threshold
                obstacle_angle = math.radians(-30.0)  # 30 degrees to the right
                result['sensor'] = 'tof_right'
                
            elif obstacle_data.get('camera_detected', False):
                # Camera detected obstacle - assume it's directly ahead
                distance = self.obstacle_threshold * 1.5  # Camera usually detects at greater distance
                obstacle_angle = 0.0
                result['sensor'] = 'camera'
                result['confidence'] = 0.9  # Higher confidence for camera detection
                
            else:
                # No specific sensor data available
                logger.warning("Cannot determine obstacle direction from sensor data")
                return {}
                
            # Calculate obstacle position in world coordinates
            # Using simplified lat/lng calculation without accounting for Earth curvature
            # For high precision, Haversine formula or similar should be used
            
            # Calculate heading to obstacle
            obstacle_heading = (heading_rad + obstacle_angle) % (2 * math.pi)
            
            # Convert meters to approximate lat/lng offsets
            # These are simple approximations that work for small distances
            # 1 meter is roughly 0.0000089 degrees latitude
            # 1 meter longitude depends on latitude, approx 0.0000089 / cos(lat)
            meters_to_lat = 0.0000089
            meters_to_lng = 0.0000089 / math.cos(math.radians(current_lat))
            
            # Calculate obstacle position
            obstacle_lat = current_lat + (distance * math.cos(obstacle_heading) * meters_to_lat)
            obstacle_lng = current_lng + (distance * math.sin(obstacle_heading) * meters_to_lng)
            
            # Update result with calculated position
            result['position'] = (obstacle_lat, obstacle_lng)
            
            logger.debug(f"Estimated obstacle position: {result['position']}")
            
            return result
                
        except Exception as e:
            logger.error(f"Error estimating obstacle position: {e}")
            return {}
