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
import os
import threading
import time
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from mower.hardware.gpio_manager import GPIOManager
from mower.hardware.imu import BNO085Sensor
from mower.hardware.ina3221 import INA3221Sensor
from mower.hardware.tof import VL53L0XSensors
from mower.hardware.robohat import RoboHATDriver
from mower.hardware.blade_controller import BladeController
from mower.hardware.camera_instance import get_camera_instance
from mower.hardware.serial_port import SerialPort, GPS_PORT, GPS_BAUDRATE
from mower.hardware.sensor_interface import get_sensor_interface
from mower.navigation.localization import Localization
from mower.navigation.path_planner import (
    PathPlanner,
    PatternConfig,
    LearningConfig,
    PatternType,
)
from mower.navigation.navigation import NavigationController, NavigationStatus
from mower.obstacle_detection.avoidance_algorithm import (
    AvoidanceAlgorithm,
    AvoidanceState,
)
from mower.obstacle_detection.obstacle_detector import ObstacleDetector
from mower.ui.web_ui import WebInterface
from mower.utilities.logger_config import LoggerConfigInfo
from mower.config_management.config_manager import get_config

# Initialize logging
logger = LoggerConfigInfo.get_logger(__name__)

# Base directory for consistent file referencing
BASE_DIR = Path(__file__).parent.parent.parent

# Configuration directory
CONFIG_DIR = BASE_DIR / "config"


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

    def __init__(self, config_path=None):
        """
        Initialize the resource manager.
        """
        self._initialized = False
        self._resources = {}
        self._lock = threading.Lock()
        # Path to user polygon config
        self.user_polygon_path = CONFIG_DIR / "user_polygon.json"
        # allow web UI to access resource manager
        self.resource_manager = self

        if config_path:
            self._load_config(config_path)

    def _load_config(self, filename):
        """Load a configuration file from the standard config location."""
        config_path = self.user_polygon_path.parent / filename
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading config file {filename}: {e}")
        return None

    def _initialize_hardware(self):
        """Initialize all hardware components."""
        try:
            # Initialize all hardware resources
            self._resources["gpio"] = GPIOManager()
            self._resources["imu"] = BNO085Sensor()

            # Initialize INA3221 sensor
            try:
                self._resources["ina3221"] = INA3221Sensor()
                logger.info("INA3221 power monitor initialized successfully")
            except Exception as e:
                logger.warning(f"Error initializing INA3221 sensor: {e}")
                self._resources["ina3221"] = None

            # Initialize ToF (VL53L0X) sensors
            try:
                self._resources["tof"] = VL53L0XSensors()
                logger.info(
                    "VL53L0X time-of-flight sensors initialized successfully"
                )
            except Exception as e:
                logger.warning(f"Error initializing VL53L0X sensors: {e}")
                self._resources["tof"] = None

            # Initialize motor controller
            try:
                self._resources["motor_driver"] = RoboHATDriver()
                logger.info("RoboHAT motor driver initialized successfully")
            except Exception as e:
                logger.error(f"Error initializing motor driver: {e}")
                self._resources["motor_driver"] = None

            # Initialize blade controller
            try:
                self._resources["blade"] = BladeController()
                logger.info("Blade controller initialized successfully")
            except Exception as e:
                logger.warning(f"Error initializing blade controller: {e}")
                self._resources["blade"] = None

            # Initialize camera
            try:
                self._resources["camera"] = get_camera_instance()
                logger.info("Camera initialized successfully")
            except Exception as e:
                logger.warning(f"Error initializing camera: {e}")
                self._resources["camera"] = None

            # Initialize GPS serial port
            try:
                self._resources["gps_serial"] = SerialPort(
                    GPS_PORT, GPS_BAUDRATE
                )
                logger.info(
                    f"GPS serial port initialized on {GPS_PORT} at "
                    f"{GPS_BAUDRATE} baud"
                )
            except Exception as e:
                logger.warning(f"Error initializing GPS serial port: {e}")
                self._resources["gps_serial"] = None

            # Initialize each resource if possible
            for name, res in list(self._resources.items()):
                if res is None:
                    continue

                if hasattr(res, "initialize"):
                    try:
                        res.initialize()
                    except Exception as e:
                        logger.error(f"Error initializing {name}: {e}")
                        self._resources[name] = None
                elif hasattr(res, "_initialize"):
                    try:
                        res._initialize()
                    except Exception as e:
                        logger.error(f"Error initializing {name}: {e}")
                        self._resources[name] = None

            logger.info(
                "Hardware components initialized with fallbacks for any "
                "failures"
            )
        except Exception as e:
            logger.error(f"Critical error in hardware initialization: {e}")
            raise

    def _initialize_software(self):
        """Initialize all software components."""
        try:
            # Initialize localization
            try:
                self._resources["localization"] = Localization()
                logger.info("Localization system initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize localization: {e}")
                self._resources["localization"] = None

            # Initialize pattern planner with learning capabilities
            pattern_cfg = get_config("pattern_config", {})
            pattern_config = PatternConfig(
                pattern_type=PatternType.PARALLEL,
                spacing=0.5,
                angle=0.0,
                overlap=0.1,
                start_point=(
                    0.0,
                    0.0,
                ),  # Will be updated with actual position
                boundary_points=[],  # Will be loaded from config
                **pattern_cfg
            )

            learning_config = LearningConfig(
                learning_rate=0.1,
                discount_factor=0.9,
                exploration_rate=0.2,
                memory_size=1000,
                batch_size=32,
                update_frequency=100,
                model_path=str(
                    CONFIG_DIR / "models" / "pattern_planner.json"
                ),
            )

            try:
                self._resources["path_planner"] = PathPlanner(
                    pattern_config, learning_config
                )
                logger.info("Path planner initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize path planner: {e}")
                self._resources["path_planner"] = None

            # Initialize frame-based obstacle detector (camera)
            try:
                self._resources["obstacle_detector"] = ObstacleDetector(self)
                logger.info("Obstacle detector initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize obstacle detector: {e}")
                self._resources["obstacle_detector"] = None

            # Obtain sensor interface singleton
            try:
                sensor_interface = get_sensor_interface()
                self._resources["sensor_interface"] = sensor_interface
                logger.info("Sensor interface initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize sensor interface: {e}")
                sensor_interface = None
                self._resources["sensor_interface"] = None

            # Initialize NavigationController
            try:
                # Get dependencies, providing fallbacks if they're not
                # available
                localization = self._resources.get("localization")
                motor_driver = self._resources.get("motor_driver")

                if localization and motor_driver and sensor_interface:
                    self._resources["navigation"] = NavigationController(
                        localization, motor_driver, sensor_interface
                    )
                    logger.info(
                        "Navigation controller initialized successfully"
                    )
                else:
                    missing = []
                    if not localization:
                        missing.append("localization")
                    if not motor_driver:
                        missing.append("motor_driver")
                    if not sensor_interface:
                        missing.append("sensor_interface")
                    logger.error(
                        f"Cannot initialize navigation controller - "
                        f"missing dependencies: {missing}"
                    )
                    self._resources["navigation"] = None
            except Exception as e:
                logger.error(
                    f"Failed to initialize navigation controller: {e}"
                )
                self._resources["navigation"] = None

            # Initialize the avoidance algorithm
            try:
                # Initialize with resource manager for dependency resolution
                self._resources["avoidance_algorithm"] = AvoidanceAlgorithm(
                    self
                )
                logger.info("Avoidance algorithm initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize avoidance algorithm: {e}")
                self._resources["avoidance_algorithm"] = None

            # Initialize web interface
            try:
                # No direct dependency on main controller to avoid circular
                # imports
                from mower.ui.web_ui import WebInterface

                # Create web interface with access to resource manager
                self._resources["web_interface"] = WebInterface(self)
                logger.info("Web interface initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize web interface: {e}")
                self._resources["web_interface"] = None

            logger.info(
                "Software components initialized with fallbacks for any "
                "failures"
            )
        except Exception as e:
            logger.error(f"Critical error in software initialization: {e}")
            # Don't re-raise here to allow partial initialization

    def initialize(self):
        """Initialize all resources."""
        if self._initialized:
            logger.warning("Resources already initialized")
            return

        try:
            # Set up configuration paths
            os.makedirs(CONFIG_DIR, exist_ok=True)
            if not os.path.exists(self.user_polygon_path):
                logger.warning(
                    f"User polygon file not found at {self.user_polygon_path} "
                    "creating default"
                )
                with open(self.user_polygon_path, "w") as f:
                    json.dump(
                        {
                            "boundary": [[0, 0], [10, 0], [10, 10], [0, 10]],
                            "home": [5, 5],
                        },
                        f,
                    )

            # Initialize hardware and software components with robust error
            # handling
            self._initialize_hardware()
            self._initialize_software()

            self._initialized = True
            logger.info(
                "All resources initialized with fallbacks for any failures"
            )
        except Exception as e:
            logger.error(f"Failed to initialize resources: {e}")
            self._initialized = False

    def init_all_resources(self) -> bool:
        """
        Initialize all resources; return True if successful,
        False otherwise.
        """
        try:
            self.initialize()
            return True
        except Exception as e:
            logger.error(f"ResourceManager init_all_resources failed: {e}")
            return False

    def cleanup(self):
        """Clean up all resources."""
        with self._lock:
            if not self._initialized:
                return

            try:
                # Clean up hardware in reverse order
                for name, resource in reversed(self._resources.items()):
                    try:
                        resource.cleanup()
                    except Exception as e:
                        logger.error(f"Error cleaning up {name}: {e}")

                self._resources.clear()
                self._initialized = False
                logger.info("All resources cleaned up successfully")
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")
                raise

    def cleanup_all_resources(self):
        """Clean up all initialized resources."""
        for name, res in self._resources.items():
            try:
                if hasattr(res, "disconnect"):
                    res.disconnect()
                elif hasattr(res, "cleanup"):
                    res.cleanup()
                elif hasattr(res, "stop"):
                    res.stop()
                else:
                    logger.debug(
                        f"No cleanup method for resource '{name}'",
                    )
            except Exception as e:
                logger.error(f"Error cleaning up resource '{name}': {e}")
        self._resources.clear()
        self._initialized = False

    def get_resource(self, name: str) -> Any:
        """
        Get a resource by name.

        Args:
            name (str): Name of the resource to get.

        Returns:
            object: The requested resource.

        Raises:
            KeyError: If the resource is not found.
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

    def get_obstacle_detection(self) -> Optional[ObstacleDetector]:
        """Get the obstacle detection instance."""
        return self._resources.get("obstacle_detection")

    def get_web_interface(self) -> Optional[WebInterface]:
        """Get the web interface instance."""
        return self._resources.get("web_interface")

    def get_camera(self) -> Optional[Any]:
        """Get the camera instance."""
        return self._resources.get("camera")

    def get_obstacle_detector(self) -> Optional[ObstacleDetector]:
        """Get the vision-based obstacle detector instance."""
        return self._resources.get("obstacle_detector")

    def get_sensor_interface(self) -> Optional[Any]:
        """Get the sensor interface instance."""
        if (
            "sensor_interface" not in self._resources
            or self._resources["sensor_interface"] is None
        ):
            try:
                from mower.hardware.sensor_interface import (
                    get_sensor_interface,
                )

                self._resources["sensor_interface"] = get_sensor_interface()
                logger.info("Sensor interface initialized on demand")
            except Exception as e:
                logger.error(
                    f"Failed to initialize sensor interface on demand: {e}"
                )
                return None
        return self._resources.get("sensor_interface")

    def get_gps(self) -> Optional[SerialPort]:
        """Get the GPS serial port instance."""
        if (
            "gps_serial" not in self._resources
            or self._resources["gps_serial"] is None
        ):
            try:
                from mower.hardware.serial_port import (
                    SerialPort,
                    GPS_PORT,
                    GPS_BAUDRATE,
                )

                self._resources["gps_serial"] = SerialPort(
                    GPS_PORT, GPS_BAUDRATE
                )
                logger.info(
                    f"GPS serial port initialized on demand on {GPS_PORT}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to initialize GPS serial port on demand: {e}"
                )
                return None
        return self._resources.get("gps_serial")

    def get_navigation_controller(self) -> Optional[NavigationController]:
        """Get the navigation controller instance."""
        if (
            "navigation" not in self._resources
            or self._resources["navigation"] is None
        ):
            try:
                # Try to initialize navigation controller with dependencies
                localization = self.get_resource("localization")
                motor_driver = self.get_robohat_driver()
                sensor_interface = self.get_sensor_interface()

                if localization and motor_driver and sensor_interface:
                    from mower.navigation.navigation import (
                        NavigationController,
                    )

                    self._resources["navigation"] = NavigationController(
                        localization, motor_driver, sensor_interface
                    )
                    logger.info("Navigation controller initialized on demand")
                else:
                    logger.error(
                        "Cannot initialize navigation controller - missing "
                        "dependencies"
                    )
                    return None
            except Exception as e:
                logger.error(
                    f"Failed to initialize navigation controller on "
                    f"demand: {e}"
                )
                return None
        return self._resources.get("navigation")

    def start_web_interface(self):
        """Start the web interface."""
        web = self._resources.get("web_interface")
        if web:
            web.start()
        else:
            logger.warning("Web interface resource not available")

    # Interpreter stubs for camera obstacle detection
    def get_inference_interpreter(self):
        """Stub for TFLite interpreter dependency."""
        return None

    def get_interpreter_type(self):
        return None

    def get_model_input_details(self):
        return None

    def get_model_output_details(self):
        return None

    def get_model_input_size(self):
        return (0, 0)

    # Expose hardware interfaces for run_robot and web UI
    def get_blade_controller(self) -> Optional[BladeController]:
        """Return blade controller instance."""
        return self._resources.get("blade")

    def get_robohat_driver(self) -> Optional[RoboHATDriver]:
        """Return motor driver instance."""
        return self._resources.get("motor_driver")

    def get_imu_sensor(self) -> Optional[BNO085Sensor]:
        """Return IMU sensor instance."""
        return self._resources.get("imu")

    def get_avoidance_algorithm(self) -> Optional[AvoidanceAlgorithm]:
        """Return avoidance algorithm instance."""
        if (
            "avoidance_algorithm" not in self._resources
            or self._resources["avoidance_algorithm"] is None
        ):
            try:
                from mower.obstacle_detection.avoidance_algorithm import (
                    AvoidanceAlgorithm,
                )

                self._resources["avoidance_algorithm"] = AvoidanceAlgorithm(
                    self
                )
                logger.info("Avoidance algorithm initialized on demand")
            except Exception as e:
                logger.error(
                    f"Failed to initialize avoidance algorithm on demand: {e}"
                )
                return None
        return self._resources.get("avoidance_algorithm")

    def get_navigation_controller(self) -> Optional[NavigationController]:
        """Return navigation controller instance."""
        return self._resources.get("navigation")

    def get_ina3221_sensor(self) -> Optional[INA3221Sensor]:
        """Return INA3221 power monitoring sensor instance."""
        # Initialize on first call if needed
        if (
            "ina3221" not in self._resources
            or self._resources["ina3221"] is None
        ):
            try:
                from mower.hardware.ina3221 import INA3221Sensor

                self._resources["ina3221"] = INA3221Sensor(address=0x40)
                logger.info("INA3221 sensor initialized on demand")
            except Exception as e:
                logger.error(f"Failed to initialize INA3221 sensor: {e}")
                return None
        return self._resources.get("ina3221")

    def get_gps_latest_position(self) -> Optional[Any]:
        """Return the latest GPS position."""
        # Initialize on first call if needed
        if (
            "gps_latest_position" not in self._resources
            or self._resources["gps_latest_position"] is None
        ):
            try:
                from mower.interfaces.gps import GpsLatestPosition

                # Get GPS device from resources or initialize
                gps_device = (
                    self.get_resource("gps")
                    if "gps" in self._resources
                    else None
                )
                if not gps_device:
                    # Initialize GPS device if needed
                    from mower.hardware.serial_port import (
                        SerialPort,
                        GPS_PORT,
                        GPS_BAUDRATE,
                    )

                    gps_device = SerialPort(GPS_PORT, GPS_BAUDRATE)
                    self._resources["gps"] = gps_device

                self._resources["gps_latest_position"] = GpsLatestPosition(
                    gps_device
                )
                logger.info(
                    "GPS latest position tracker initialized on demand"
                )
            except Exception as e:
                logger.error(
                    f"Failed to initialize GPS position tracker: {e}"
                )
                return None
        return self._resources.get("gps_latest_position")

    def get_home_location(self) -> dict:
        """Load home location polygon from config."""
        try:
            with open(self.user_polygon_path, "r") as f:
                data = json.load(f)
            return data
        except Exception as e:
            logger.error(f"Failed to load home location: {e}")
            return {}

    # Stub methods for web UI
    def get_status(self) -> dict:
        """Return current status for web UI."""
        return {}

    def get_safety_status(self) -> dict:
        return {}

    def get_sensor_data(self) -> dict:
        return {}

    def get_current_path(self) -> list:
        """Return current planned path."""
        planner = self.get_path_planner()
        return getattr(planner, "current_path", [])

    def emergency_stop(self) -> bool:
        """Perform emergency stop."""
        # attempt to stop operations
        if "navigation" in self._resources:
            try:
                self._resources["navigation"].stop()
            except Exception:
                pass
        return True

    def set_mowing_schedule(self, schedule: dict) -> bool:
        """Store mowing schedule."""
        self._resources["schedule"] = schedule
        return True


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

    def __init__(self, resource_manager: ResourceManager):
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
            home_config = self._load_config("home_location.json")
            if home_config and "location" in home_config:
                self.home_location = home_config["location"]
                logger.info(f"Loaded home location: {self.home_location}")
        except Exception as e:
            logger.error(f"Failed to load home location: {e}")

        logger.info("Robot controller initialized")

    def _load_config(self, filename: str) -> dict:
        """Load a configuration file from the standard config location."""
        config_path = (
            self.resource_manager.user_polygon_path.parent / filename
        )
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading config file {filename}: {e}")
        return None

    def run_robot(self):
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
            self.resource_manager.init_all_resources()

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
            if hasattr(self, "avoidance_algorithm") and self.avoidance_algorithm:
                self.avoidance_algorithm.stop()
            self.resource_manager.cleanup_all_resources()

    def _main_control_loop(self):
        """
        Main control loop that handles state transitions and monitoring.

        This loop continuously checks system status, handles state
        transitions, and performs appropriate actions based on the current
        state.
        """
        try:
            while self.current_state != SystemState.ERROR:
                # Check for emergency stop conditions (battery,
                # temperature, etc.)
                if self._check_emergency_conditions():
                    self.current_state = SystemState.EMERGENCY_STOP
                    logger.warning("Emergency stop condition detected")

                # State-specific actions
                if self.current_state == SystemState.IDLE:
                    # In IDLE state, just check for commands from UI
                    time.sleep(0.5)

                elif self.current_state == SystemState.MOWING:
                    # Check if avoidance is active and handle it
                    avoidance_state = self.avoidance_algorithm.current_state
                    if avoidance_state != AvoidanceState.NORMAL:
                        if not self.avoidance_active:
                            logger.info("Avoidance activated, pausing mowing")
                            self.avoidance_active = True
                            self.current_state = SystemState.AVOIDING

                elif self.current_state == SystemState.AVOIDING:
                    # Check if avoidance has completed
                    avoidance_state = self.avoidance_algorithm.current_state
                    if avoidance_state == AvoidanceState.NORMAL:
                        if self.avoidance_active:
                            logger.info(
                                "Avoidance completed, resuming mowing"
                            )
                            self.avoidance_active = False
                            self.current_state = SystemState.MOWING
                    # Check for recovery failures
                    elif avoidance_state == AvoidanceState.RECOVERY:
                        recovery_attempts = (
                            self.avoidance_algorithm.recovery_attempts
                        )
                        if (
                            recovery_attempts
                            >= self.avoidance_algorithm.max_recovery_attempts
                        ):
                            logger.error(
                                "Failed to recover from obstacle after "
                                "multiple attempts"
                            )
                            self.error_condition = (
                                "Failed to recover from obstacle"
                            )
                            self.current_state = SystemState.ERROR

                elif self.current_state == SystemState.RETURNING_HOME:
                    # Check if we've reached home
                    if self._check_at_home():
                        logger.info("Reached home location")
                        self.navigation_controller.stop()
                        self.current_state = SystemState.DOCKED

                elif self.current_state == SystemState.EMERGENCY_STOP:
                    # Handle emergency stop - ensure all motors are stopped
                    self.navigation_controller.stop()
                    self.blade_controller.stop_blade()
                    logger.critical("Emergency stop - all motors stopped")

                    # Check if emergency condition is cleared
                    if not self._check_emergency_conditions():
                        logger.info("Emergency condition cleared")
                        self.current_state = SystemState.IDLE

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
            current_lat, current_lng = (
                current_position[1],
                current_position[2],
            )

            # Simple Euclidean distance (for more accurate distance, use
            # haversine formula)
            distance = (
                (home_lat - current_lat) ** 2 + (home_lng - current_lng) ** 2
            ) ** 0.5

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
            current_pos = (
                self.resource_manager.get_navigation().get_position()
            )
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

    def _navigate_to_waypoint(self, waypoint) -> bool:
        """Navigate to a specific waypoint."""
        try:
            navigation = self.resource_manager.get_navigation()
            obstacle_detection = (
                self.resource_manager.get_obstacle_detection()
            )

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
            SystemState.EMERGENCY_STOP,
        ]:
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
                SystemState.RETURNING_HOME,
            ]:
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
                SystemState.ERROR,
                SystemState.EMERGENCY_STOP,
            ]:
                self.current_state = SystemState.IDLE

            logger.info("All operations stopped")
            return True
        except Exception as e:
            logger.error(f"Error stopping operations: {e}")
            return False


def main():
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
        if not resource_manager.init_all_resources():
            logger.error("Failed to initialize resources. Exiting.")
            return

        # Create the robot controller
        robot_controller = RobotController(resource_manager)

        # Start the robot logic in a separate thread
        # Using daemon=True ensures thread terminates when main thread
        # exits
        robot_thread = threading.Thread(
            target=robot_controller.run_robot, daemon=True
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
        resource_manager.cleanup_all_resources()
        logger.info("Main controller exited.")


if __name__ == "__main__":
    main()
