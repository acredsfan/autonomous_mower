"""
Main controller module for autonomous mower.

This module implements the core control logic for the autonomous mower,
including state management, resource handling, and high-level control flow.
It coordinates between various subsystems (navigation, obstacle detection,
hardware control) to achieve autonomous operation.

Architecture:
    - State machine based control flow
    - Resource management for hardware and software components
    - Event-driven operation with safety checks
    - Modular design for easy subsystem integration

Usage:
    from mower.main_controller import MainController
    controller = MainController()
    controller.start()

Dependencies:
    - Hardware interfaces (GPIO, sensors, motors)
    - Navigation system
    - Obstacle detection
    - Web interface
    - Configuration management

Configuration:
    - Environment variables (.env)
    - User configuration files in config directory
    - Supports runtime updates
"""

import json
import threading
import time
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Union, Type

import logging
from dotenv import load_dotenv
import sys

# Suppress dotenv parse warnings
logging.getLogger('dotenv.main').setLevel(logging.ERROR)
load_dotenv()

from mower.hardware.gpio_manager import GPIOManager
from mower.hardware.imu import BNO085Sensor
from mower.hardware.bme280 import BME280Sensor
from mower.hardware.ina3221 import INA3221Sensor
from mower.hardware.tof import VL53L0XSensors
from mower.hardware.robohat import RoboHATDriver
from mower.hardware.blade_controller import BladeController
from mower.hardware.camera_instance import get_camera_instance
from mower.hardware.serial_port import SerialPort, GPS_BAUDRATE
from mower.navigation.localization import Localization
from mower.navigation.path_planner import (
    PathPlanner, PatternConfig, LearningConfig, PatternType
)
from mower.navigation.navigation import NavigationController, NavigationStatus
from mower.obstacle_detection.avoidance_algorithm import (
    AvoidanceAlgorithm, AvoidanceState
)
from mower.ui.web_ui import WebInterface
from mower.utilities.logger_config import LoggerConfigInfo
from mower.config_management import (
    get_config_manager, get_config, set_config,
    CONFIG_DIR, HOME_LOCATION_PATH, PATTERN_PLANNER_PATH
)
from mower.utilities import load_config, save_config, cleanup_resources

# Initialize logging
logger = LoggerConfigInfo.get_logger(__name__)


# System state enumeration
class SystemState(Enum):
    """Enumeration of possible system states."""
    IDLE = "idle"
    MOWING = "mowing"
    DOCKING = "docking"
    ERROR = "error"
    EMERGENCY_STOP = "emergency_stop"


class ResourceManager:
    """
    Manages hardware and software resources for the autonomous mower.

    This class handles initialization, access, and cleanup of all hardware
    components and software modules. It provides a centralized interface for
    accessing resources and ensures proper initialization order and cleanup.
    """

    def __init__(self, config_path: Optional[str] = None) -> None:
        """
        Initialize the resource manager.

        Args:
            config_path: Optional path to configuration file
        """
        self._initialized: bool = False
        self._resources: Dict[str, Any] = {}
        self._lock: threading.Lock = threading.Lock()

        if config_path:
            self._load_config(config_path)

    def _initialize_hardware(self) -> None:
        """Initialize all hardware components."""
        # Skip hardware init on non-Linux (e.g., Windows) to allow testing without Pi
        if sys.platform != "linux":
            logger.warning("Non-Linux platform detected. Skipping hardware initialization.")
            return
        try:
            # Initialize GPIO first
            self._resources["gpio"] = GPIOManager()
            self._resources["gpio"]._initialize()

            # Initialize I2C bus
            from busio import I2C  # type:ignore
            import board  # type:ignore
            i2c = I2C(board.SCL, board.SDA)

            # Initialize sensors
            self._resources["imu"] = BNO085Sensor()
            self._resources["imu"]._initialize()

            self._resources["bme280"] = BME280Sensor()
            self._resources["bme280"]._initialize(i2c)

            self._resources["ina3221"] = INA3221Sensor()
            self._resources["ina3221"]._initialize()

            self._resources["tof"] = VL53L0XSensors()
            self._resources["tof"]._initialize()

            # Initialize motors and blade
            self._resources["motor_driver"] = RoboHATDriver()
            self._resources["motor_driver"].__init__()

            self._resources["blade"] = BladeController()
            self._resources["blade"].__init__()

            # Initialize camera
            self._resources["camera"] = get_camera_instance()
            self._resources["camera"].__init__()

            # Initialize serial ports
            self._resources["gps_serial"] = SerialPort(
                "/dev/ttyAMA0", GPS_BAUDRATE
            )
            self._resources["gps_serial"]._initialize()

            # Initialize sensor interface
            from mower.hardware.sensor_interface import EnhancedSensorInterface
            self._resources["sensor_interface"] = EnhancedSensorInterface()

            logger.info("All hardware components initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing hardware: {e}")
            raise

    def _initialize_software(self) -> None:
        """Initialize all software components."""
        try:
            # Initialize localization
            self._resources["localization"] = Localization()

            # Initialize pattern planner with learning capabilities
            # Get pattern configuration from the configuration manager
            pattern_config = PatternConfig(
                pattern_type=PatternType[get_config('path_planning.pattern_type', 'PARALLEL')],
                spacing=get_config('path_planning.spacing', 0.3),  # 30cm spacing between passes
                angle=get_config('path_planning.angle', 0.0),  # Start with parallel to x-axis
                overlap=get_config('path_planning.overlap', 0.1),  # 10% overlap between passes
                start_point=(0.0, 0.0),  # Will be updated with actual position
                boundary_points=[]  # Will be loaded from config
            )

            # Get learning configuration from the configuration manager
            learning_config = LearningConfig(
                learning_rate=get_config('path_planning.learning_rate', 0.1),
                discount_factor=get_config('path_planning.discount_factor', 0.9),
                exploration_rate=get_config('path_planning.exploration_rate', 0.2),
                memory_size=get_config('path_planning.memory_size', 1000),
                batch_size=get_config('path_planning.batch_size', 32),
                update_frequency=get_config('path_planning.update_frequency', 100),
                model_path=str(PATTERN_PLANNER_PATH)
            )

            self._resources["path_planner"] = PathPlanner(
                pattern_config, learning_config
            )

            # Initialize navigation controller
            self._resources["navigation"] = NavigationController(
                self._resources["gps_serial"],
                self._resources["motor_driver"],
                self._resources["sensor_interface"]
            )

            # Initialize obstacle detection
            self._resources["obstacle_detection"] = AvoidanceAlgorithm(
                resource_manager=self,
                pattern_planner=self._resources["path_planner"]
            )

            # Initialize web interface
            self._resources["web_interface"] = WebInterface(mower=self)

            logger.info("All software components initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing software: {e}")
            raise

    def initialize(self) -> None:
        """Initialize all resources."""
        with self._lock:
            if self._initialized:
                return

            try:
                self._initialize_hardware()
                self._initialize_software()
                self._initialized = True
                logger.info("All resources initialized successfully")
            except Exception as e:
                logger.error(f"Error during initialization: {e}")
                self.cleanup()
                raise

    def cleanup(self) -> None:
        """Clean up all resources."""
        result = cleanup_resources(self._resources, self._initialized, self._lock)
        if result:
            self._initialized = False
        return result

    def get_resource(self, name: str) -> Any:
        """
        Get a resource by name.

        Args:
            name (str): Name of the resource to get.

        Returns:
            object: The requested resource.

        Raises:
            KeyError: If the resource is not found.
            RuntimeError: If resources are not initialized.
        """
        with self._lock:
            if not self._initialized:
                raise RuntimeError("Resources not initialized")
            return self._resources[name]

    def get_path_planner(self) -> Optional[PathPlanner]:
        """Get the path planner instance."""
        return self._resources.get("path_planner")

    def get_navigation(self) -> Optional[NavigationController]:
        """Get the navigation controller instance."""
        return self._resources.get("navigation")

    def get_obstacle_detection(self) -> Optional[Any]:
        """Get the obstacle detection instance."""
        return self._resources.get("obstacle_detection")

    def get_web_interface(self) -> Optional[WebInterface]:
        """Get the web interface instance."""
        return self._resources.get("web_interface")

    def get_blade_controller(self) -> Optional[BladeController]:
        """Get the blade controller instance."""
        return self._resources.get("blade")

    def get_bme280_sensor(self) -> Optional[BME280Sensor]:
        """Get the BME280 sensor instance."""
        return self._resources.get("bme280")

    def get_camera(self) -> Optional[Any]:
        """Get the camera instance."""
        return self._resources.get("camera")

    def get_robohat_driver(self) -> Optional[RoboHATDriver]:
        """Get the RoboHAT driver instance."""
        return self._resources.get("motor_driver")

    def get_gps_position(self) -> Optional[SerialPort]:
        """Get the GPS position instance."""
        return self._resources.get("gps_serial")

    def get_imu_sensor(self) -> Optional[BNO085Sensor]:
        """Get the IMU sensor instance."""
        return self._resources.get("imu")

    def get_ina3221_sensor(self) -> Optional[INA3221Sensor]:
        """Get the INA3221 sensor instance."""
        return self._resources.get("ina3221")

    def get_tof_sensors(self) -> Optional[VL53L0XSensors]:
        """Get the ToF sensors instance."""
        return self._resources.get("tof")

    def get_navigation_controller(self) -> Optional[NavigationController]:
        """Alias for get_navigation."""
        return self.get_navigation()

    def get_avoidance_algorithm(self) -> Optional[AvoidanceAlgorithm]:
        """Alias for get_obstacle_detection."""
        return self.get_obstacle_detection()

    def get_obstacle_detector(self) -> Any:
        """Return the obstacle detector resource."""
        return self._resources.get("obstacle_detector")

    def get_camera(self) -> Any:
        """Return the camera resource."""
        return self._resources.get("camera")

    def start_web_interface(self) -> None:
        """Start the web interface from resources."""
        web_ui = self.get_web_interface()
        if web_ui:
            web_ui.start()


class RobotController:
    """
    Manages the core mowing operation logic of the autonomous mower.

    This class coordinates all the robot's subsystems to achieve autonomous
    mowing operation. It implements a state machine to manage different
    operational modes and transitions between them based on sensor data,
    user commands, and internal state.

    The controller handles:
    - State transitions between idle, mowing, avoiding, returning home
    - Coordination between navigation, obstacle avoidance, and motor control
    - Error detection and recovery procedures
    - Scheduled operations based on configured mowing times

    Attributes:
        resource_manager: Reference to the ResourceManager for accessing
            components
        current_state: Current state of the robot (from RobotState enum)
        error_condition: Description of current error (if in ERROR state)
        mowing_paused: Flag indicating if mowing is temporarily paused
        home_location: Coordinates of the home/charging location

    Troubleshooting:
        - If robot won't start mowing, check error_condition and logs
        - If robot gets stuck in a state, check the state transition
            conditions
        - For navigation issues, verify the path planning and GPS signal
            quality
        - For unexpected stops, check sensor readings and obstacle detection
    """

    def __init__(self, resource_manager: ResourceManager) -> None:
        """
        Initialize the robot controller with resource manager and default
        state.

        Args:
            resource_manager: ResourceManager instance for accessing
                components

        The controller starts in the IDLE state and needs to be explicitly
        started via run_robot().
        """
        self.resource_manager = resource_manager
        self.current_state = SystemState.IDLE
        self.error_condition = None
        self.mowing_paused = False
        self.home_location = None

        # Load home location from configuration
        try:
            # Get the home location from the configuration manager
            home_location = get_config('home.location')
            if not home_location:
                # Try to load from the home location file
                home_config = self._load_config('home_location.json')
                if home_config and 'location' in home_config:
                    home_location = home_config['location']
                    # Save to the configuration manager for future use
                    set_config('home.location', home_location)

            if home_location:
                self.home_location = home_location
                logger.info(f"Loaded home location: {self.home_location}")
        except Exception as e:
            logger.error(f"Failed to load home location: {e}")

        logger.info("Robot controller initialized")

    def _load_config(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        Load a configuration file using the configuration manager.

        Args:
            filename: Name of the configuration file to load

        Returns:
            dict: Configuration data, or None if the file doesn't exist or there was an error
        """
        return load_config(filename)

    def run_robot(self) -> None:
        """
        Main entry point to start the robot operation.

        This method initializes all required resources, starts the web
        interface, and transitions to the IDLE state, ready to receive
        commands.

        The robot remains in operation until shutdown is requested,
        handling state transitions and commands from the web interface.
        """
        logger.info("Starting robot...")

        try:
            # Initialize robot in INITIALIZING state
            self.current_state = SystemState.IDLE

            # Initialize all resources
            self.resource_manager.initialize()

            # Initialize key components for quick access
            self.blade_controller = (
                self.resource_manager.get_blade_controller()
            )
            self.imu_sensor = self.resource_manager.get_imu_sensor()
            self.avoidance_algorithm = (
                self.resource_manager.get_avoidance_algorithm()
            )
            self.path_planner = self.resource_manager.get_path_planner()
            self.navigation_controller = (
                self.resource_manager.get_navigation_controller()
            )

            # Start the web interface
            self.resource_manager.start_web_interface()

            # Start primary systems
            self.avoidance_algorithm.start()

            # Transition to IDLE state
            self.current_state = SystemState.IDLE
            logger.info("Robot ready and in IDLE state")

            # Start the main control loop
            self._main_control_loop()

        except Exception as e:
            logger.error(f"Error in run_robot: {e}")
            self.current_state = SystemState.ERROR
            self.error_condition = str(e)
        finally:
            # Clean up resources when shutting down
            logger.info("Shutting down robot...")
            if hasattr(self, 'avoidance_algorithm'):
                self.avoidance_algorithm.stop()
            self.resource_manager.cleanup()

    def _handle_idle_state(self) -> None:
        """
        Handle the IDLE state.

        In IDLE state, the robot is waiting for commands from the UI.
        """
        # In IDLE state, just check for commands from UI
        time.sleep(0.5)

    def _handle_mowing_state(self) -> None:
        """
        Handle the MOWING state.

        In MOWING state, the robot is actively mowing and monitoring for obstacles.
        """
        # Check if avoidance is active and handle it
        avoidance_state = self.avoidance_algorithm.current_state
        if avoidance_state != AvoidanceState.NORMAL:
            if not self.avoidance_active:
                logger.info("Avoidance activated, pausing mowing")
                self.avoidance_active = True
                self.current_state = SystemState.AVOIDING

    def _handle_avoiding_state(self) -> None:
        """
        Handle the AVOIDING state.

        In AVOIDING state, the robot is actively avoiding an obstacle.
        """
        # Check if avoidance has completed
        avoidance_state = self.avoidance_algorithm.current_state
        if avoidance_state == AvoidanceState.NORMAL:
            if self.avoidance_active:
                logger.info("Avoidance completed, resuming mowing")
                self.avoidance_active = False
                self.current_state = SystemState.MOWING
        # Check for recovery failures
        elif avoidance_state == AvoidanceState.RECOVERY:
            recovery_attempts = self.avoidance_algorithm.recovery_attempts
            if recovery_attempts >= self.avoidance_algorithm.max_recovery_attempts:
                logger.error("Failed to recover from obstacle after multiple attempts")
                self.error_condition = "Failed to recover from obstacle"
                self.current_state = SystemState.ERROR

    def _handle_returning_home_state(self) -> None:
        """
        Handle the RETURNING_HOME state.

        In RETURNING_HOME state, the robot is navigating back to its home/charging location.
        """
        # Check if we've reached home
        if self._check_at_home():
            logger.info("Reached home location")
            self.navigation_controller.stop()
            self.current_state = SystemState.DOCKED

    def _handle_emergency_stop_state(self) -> None:
        """
        Handle the EMERGENCY_STOP state.

        In EMERGENCY_STOP state, the robot has detected an emergency condition
        and has stopped all motors.
        """
        # Handle emergency stop - ensure all motors are stopped
        self.navigation_controller.stop()
        self.blade_controller.stop_blade()
        logger.critical("Emergency stop - all motors stopped")

        # Check if emergency condition is cleared
        if not self._check_emergency_conditions():
            logger.info("Emergency condition cleared")
            self.current_state = SystemState.IDLE

    def _main_control_loop(self) -> None:
        """
        Main control loop that handles state transitions and monitoring.

        This loop continuously checks system status, handles state
        transitions, and performs appropriate actions based on the current
        state.
        """
        try:
            while self.current_state != SystemState.ERROR:
                # Check for emergency stop conditions (battery, temperature, etc.)
                if self._check_emergency_conditions():
                    self.current_state = SystemState.EMERGENCY_STOP
                    logger.warning("Emergency stop condition detected")

                # Handle state-specific actions
                if self.current_state == SystemState.IDLE:
                    self._handle_idle_state()
                elif self.current_state == SystemState.MOWING:
                    self._handle_mowing_state()
                elif self.current_state == SystemState.AVOIDING:
                    self._handle_avoiding_state()
                elif self.current_state == SystemState.RETURNING_HOME:
                    self._handle_returning_home_state()
                elif self.current_state == SystemState.EMERGENCY_STOP:
                    self._handle_emergency_stop_state()

                # Brief pause to avoid CPU spinning
                time.sleep(0.1)

        except Exception as e:
            logger.error(f"Error in main control loop: {e}")
            self.current_state = SystemState.ERROR
            self.error_condition = str(e)

    def _check_emergency_conditions(self) -> bool:
        """
        Check for conditions that would trigger an emergency stop.

        Returns:
            bool: True if emergency stop is needed, False otherwise
        """
        try:
            # Check battery voltage
            power_monitor = self.resource_manager.get_ina3221_sensor()
            battery_voltage = power_monitor.get_battery_voltage()

            # Critical battery threshold (customize based on your battery)
            if battery_voltage < 10.5:  # Critical voltage for LiFePO4
                logger.warning(
                    f"Emergency: Battery voltage critical at "
                    f"{battery_voltage}V"
                )
                return True

            # Check for other emergency conditions like:
            # - Extreme IMU readings (tilt beyond safe limits)
            # - Motor overcurrent conditions
            # - Temperature exceeding safe limits

            return False
        except Exception as e:
            logger.error(f"Error checking emergency conditions: {e}")
            # Default to emergency stop on error to be safe
            return True

    def _check_at_home(self) -> bool:
        """
        Check if the robot has reached the home location.

        Returns:
            bool: True if at home location, False otherwise
        """
        if not self.home_location:
            logger.warning(
                "Home location not set, can't determine if at home"
            )
            return False

        try:
            # Get current position
            gps = self.resource_manager.get_gps_latest_position()
            current_position = gps.run()

            if not current_position:
                logger.warning("Unable to get current position")
                return False

            # Calculate distance to home
            home_lat, home_lng = self.home_location
            current_lat, current_lng = current_position[1], current_position[2]

            # Simple Euclidean distance (for more accurate distance, use
            # haversine formula)
            distance = ((home_lat - current_lat) ** 2 +
                        (home_lng - current_lng) ** 2) ** 0.5

            # Threshold distance to consider "at home" (in coordinate units)
            # This should be converted to meters and set appropriately
            threshold = 0.0001  # approximately 10 meters

            return distance < threshold
        except Exception as e:
            logger.error(f"Error checking home position: {e}")
            return False

    def mow_yard(self) -> bool:
        """
        Main mowing operation logic for autonomous mowing.

        This method:
        1. Retrieves the mowing path from the path planner
        2. Initiates blade rotation
        3. Navigates through the path while monitoring for obstacles
        4. Handles path completion and returns home when finished

        The mowing operation can be interrupted by:
        - Obstacle detection (handled via state transition to AVOIDING)
        - User commands from the web interface
        - Emergency conditions (low battery, errors, etc.)

        Returns:
            bool: True if mowing completed successfully, False otherwise
        """
        if self.current_state != SystemState.IDLE:
            logger.warning(
                f"Cannot start mowing from state {self.current_state}"
            )
            return False

        logger.info("Starting mowing operation")

        try:
            # Transition to MOWING state
            self.current_state = SystemState.MOWING

            # Get path planner
            path_planner = self.resource_manager.get_path_planner()

            # Update path planner with current position
            current_pos = self.resource_manager.get_navigation().get_position()
            path_planner.pattern_config.start_point = current_pos

            # Generate mowing path
            mowing_path = path_planner.generate_path()
            if not mowing_path or len(mowing_path) == 0:
                logger.error("Failed to generate mowing path")
                self.error_condition = "Failed to generate mowing path"
                self.current_state = SystemState.ERROR
                return False

            logger.info(
                f"Generated mowing path with {len(mowing_path)} waypoints"
            )

            # Start the blade motor
            self.blade_controller.start_blade()

            # Navigate through each waypoint
            for waypoint_idx, waypoint in enumerate(mowing_path):
                # Check if we're still in MOWING state (might have changed
                # due to obstacle avoidance or user commands)
                if self.current_state != SystemState.MOWING:
                    logger.info(
                        f"Mowing interrupted: state changed to "
                        f"{self.current_state}"
                    )
                    break

                # Navigate to waypoint
                success = self._navigate_to_waypoint(waypoint)
                if not success:
                    logger.warning(
                        f"Failed to reach waypoint {waypoint_idx + 1}/"
                        f"{len(mowing_path)}"
                    )
                    break

            # Path completed successfully
            logger.info("Mowing path completed")

            # Stop the blade motor
            self.blade_controller.stop_blade()

            # Return home
            self._return_home()

            return True

        except Exception as e:
            logger.error(f"Error during mowing operation: {e}")
            self.error_condition = f"Mowing error: {str(e)}"
            self.current_state = SystemState.ERROR

            # Safety: ensure blade is stopped
            try:
                self.blade_controller.stop_blade()
            except BaseException:
                pass

            return False

    def _navigate_to_waypoint(self, waypoint: Tuple[float, float]) -> bool:
        """Navigate to a specific waypoint."""
        try:
            navigation = self.resource_manager.get_navigation()
            obstacle_detection = self.resource_manager.get_obstacle_detection()

            # Set target waypoint
            navigation.set_target(waypoint)

            # Navigate until reached or interrupted
            while True:
                # Check for obstacles
                if obstacle_detection.check_obstacles():
                    logger.info("Obstacle detected, avoiding...")
                    if not obstacle_detection.avoid_obstacle():
                        return False

                # Update navigation
                status = navigation.update()

                # Check if waypoint reached
                if status == NavigationStatus.REACHED:
                    return True

                # Check for navigation errors
                if status == NavigationStatus.ERROR:
                    return False

                # Small delay to prevent CPU overload
                time.sleep(0.1)

        except Exception as e:
            logger.error(f"Error navigating to waypoint: {e}")
            return False

    def _return_home(self) -> bool:
        """
        Navigate back to the home/charging location.

        Returns:
            bool: True if successfully started returning home, False otherwise
        """
        if not self.home_location:
            logger.error("Home location not set, cannot return home")
            return False

        try:
            logger.info("Initiating return to home")
            self.current_state = SystemState.RETURNING_HOME

            # Extract home coordinates
            home_lat, home_lng = self.home_location

            # Command navigation to home
            self.navigation_controller.navigate_to_location(
                (home_lat, home_lng)
            )

            return True
        except Exception as e:
            logger.error(f"Error initiating return to home: {e}")
            return False

    def start_manual_control(self) -> bool:
        """
        Switch to manual control mode.

        Returns:
            bool: True if successfully switched to manual mode, False otherwise
        """
        if self.current_state in [
                SystemState.ERROR,
                SystemState.EMERGENCY_STOP]:
            logger.warning(
                f"Cannot start manual control from state "
                f"{self.current_state}"
            )
            return False

        try:
            # Stop any active autonomous operations
            if self.current_state in [
                    SystemState.MOWING,
                    SystemState.AVOIDING,
                    SystemState.RETURNING_HOME]:
                self.navigation_controller.stop()

            self.current_state = SystemState.MANUAL_CONTROL
            logger.info("Switched to manual control mode")
            return True
        except Exception as e:
            logger.error(f"Error switching to manual control: {e}")
            return False

    def stop_all_operations(self) -> bool:
        """
        Stop all operations and return to IDLE state.

        Returns:
            bool: True if successfully stopped, False otherwise
        """
        try:
            # Stop navigation and blade
            self.navigation_controller.stop()
            self.blade_controller.stop_blade()

            # Return to IDLE state if not in ERROR or EMERGENCY_STOP
            if self.current_state not in [
                    SystemState.ERROR, SystemState.EMERGENCY_STOP]:
                self.current_state = SystemState.IDLE

            logger.info("All operations stopped")
            return True
        except Exception as e:
            logger.error(f"Error stopping operations: {e}")
            return False


def main() -> None:
    """
    Main entry point for the autonomous mower application.

    This function:
    1. Initializes the resource manager
    2. Sets up all hardware and software components
    3. Starts the robot controller in a separate thread
    4. Launches the web interface for control
    5. Maintains the main application loop
    6. Handles cleanup on shutdown

    Troubleshooting:
        - For startup failures, check resource initialization logs
        - For thread issues, verify daemon thread setup
        - For keyboard interrupt issues, check signal handling
        - For cleanup failures, review individual component logs
    """
    # Initialize the resource manager
    resource_manager = ResourceManager()

    try:
        # Initialize all resources
        resource_manager.initialize()

        # Create the robot controller
        robot_controller = RobotController(resource_manager)

        # Start the robot logic in a separate thread
        # Using daemon=True ensures thread terminates when main thread
        # exits
        robot_thread = threading.Thread(
            target=robot_controller.run_robot,
            daemon=True
        )
        robot_thread.start()
        logger.info("Robot logic thread started.")

        # Start the web interface for user control
        resource_manager.start_web_interface()
        logger.info("Web interface started.")

        # Keep the main thread running
        # This loop keeps the application alive and responsive to keyboard
        # interrupts
        while True:
            try:
                # Sleep to avoid high CPU usage while waiting
                threading.Event().wait(1)
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received. Exiting.")
                break

    except Exception as e:
        logger.exception(f"An error occurred in the main function: {e}")
    finally:
        # Ensure all resources are properly cleaned up
        resource_manager.cleanup()
        logger.info("Main controller exited.")


if __name__ == "__main__":
    main()
