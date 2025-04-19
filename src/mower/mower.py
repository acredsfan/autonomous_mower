# Updated 11.1.24
"""
Module to initialize and manage all resources used in the project.
Provides a centralized Mower class for resource management and control.
"""

import threading
import json
import time
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union

# Configuration management
from mower.config_management import (
    get_config_manager, get_config, set_config,
    CONFIG_DIR, HOME_LOCATION_PATH, PATTERN_PLANNER_PATH
)

# Hardware imports
from mower.hardware.blade_controller import BladeController
from mower.hardware.adapters.blade_controller_adapter import BladeControllerAdapter
from mower.hardware.bme280 import BME280Sensor
from mower.hardware.camera_instance import get_camera_instance
from mower.hardware.gpio_manager import GPIOManager
from mower.hardware.imu import BNO085Sensor
from mower.hardware.ina3221 import INA3221Sensor
from mower.hardware.robohat import RoboHATDriver
from mower.hardware.sensor_interface import get_sensor_interface, EnhancedSensorInterface
from mower.hardware.serial_port import SerialPort, GPS_BAUDRATE
from mower.hardware.tof import VL53L0XSensors

# Navigation imports
from mower.navigation.gps import (
    GpsNmeaPositions, GpsLatestPosition, GpsPosition
    )
from mower.navigation.localization import Localization
from mower.navigation.path_planning import PathPlanner  # type:ignore
from mower.navigation.navigation import NavigationController
from mower.navigation.path_planner import (
    PathPlanner as NewPathPlanner, PatternConfig, LearningConfig, PatternType
)

# Obstacle Detection imports
from mower.obstacle_detection.avoidance_algorithm import AvoidanceAlgorithm
from mower.obstacle_detection.local_obstacle_detection import (  # type:ignore
    detect_obstacle, detect_drop, stream_frame_with_overlays
    )

# UI and utilities imports
from mower.ui.web_ui.web_interface import WebInterface
from mower.utilities.logger_config import LoggerConfigInfo as LoggerConfig
from mower.utilities.text_writer import TextLogger, CsvLogger
from mower.utilities.utils import Utils

# Initialize logger
logger = LoggerConfig.get_logger(__name__)


class MowerMode(Enum):
    """Enumeration of possible mower operation modes."""
    IDLE = "idle"
    MOWING = "mowing"
    DOCKING = "docking"
    MANUAL = "manual"
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

        Args:
            config_path: Optional path to configuration file
        """
        self._initialized = False
        self._resources = {}
        self._lock = threading.Lock()
        self.user_polygon_path = CONFIG_DIR / "user_polygon.json"

        if config_path:
            self._load_config(config_path)

    def _load_config(self, filename):
        """
        Load a configuration file using the configuration manager.

        Args:
            filename: Name or path of the configuration file to load

        Returns:
            dict: Configuration data, or None if the file doesn't exist or there was an error
        """
        try:
            # Get the configuration manager
            config_manager = get_config_manager()

            # Get the full path to the configuration file
            if isinstance(filename, str) and not Path(filename).is_absolute():
                config_path = CONFIG_DIR / filename
            else:
                config_path = Path(filename)

            # Check if the file exists
            if not config_path.exists():
                logger.warning(f"Configuration file {filename} not found")
                return None

            # Load the configuration file
            config = config_manager.load(str(config_path))
            logger.info(f"Loaded configuration from {filename}")
            return config
        except Exception as e:
            logger.error(f"Error loading config file {filename}: {e}")
            return None

    def _save_config(self, filename, data):
        """
        Save configuration data to a file using the configuration manager.

        Args:
            filename: Name or path of the configuration file to save
            data: Configuration data to save

        Returns:
            bool: True if the configuration was saved successfully, False otherwise
        """
        try:
            # Get the configuration manager
            config_manager = get_config_manager()

            # Get the full path to the configuration file
            if isinstance(filename, str) and not Path(filename).is_absolute():
                config_path = CONFIG_DIR / filename
            else:
                config_path = Path(filename)

            # Save the configuration file
            config_manager.save(str(config_path), data)
            logger.info(f"Saved configuration to {filename}")
            return True
        except Exception as e:
            logger.error(f"Error saving config file {filename}: {e}")
            return False

    def _initialize_hardware(self):
        """Initialize all hardware components."""
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

            # Create blade controller with adapter for interface compatibility
            blade_controller = BladeController()
            blade_controller.__init__()
            self._resources["blade"] = BladeControllerAdapter(blade_controller)

            # Initialize camera
            self._resources["camera"] = get_camera_instance()
            self._resources["camera"].__init__()

            # Initialize serial ports
            self._resources["gps_serial"] = SerialPort(
                "/dev/ttyAMA0", GPS_BAUDRATE
            )
            self._resources["gps_serial"]._initialize()

            # Initialize sensor interface
            self._resources["sensor_interface"] = EnhancedSensorInterface()

            logger.info("All hardware components initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing hardware: {e}")
            raise

    def _initialize_software(self):
        """Initialize all software components."""
        try:
            # Initialize localization
            self._resources["localization"] = Localization()

            # Initialize pattern planner with learning capabilities
            pattern_config = PatternConfig(
                pattern_type=PatternType[get_config('path_planning.pattern_type', 'PARALLEL')],
                spacing=get_config('path_planning.spacing', 0.3),  # 30cm spacing between passes
                angle=get_config('path_planning.angle', 0.0),  # Start with parallel to x-axis
                overlap=get_config('path_planning.overlap', 0.1),  # 10% overlap between passes
                start_point=get_config('path_planning.start_point', (0.0, 0.0)),  # Will be updated with actual position
                boundary_points=get_config('path_planning.boundary_points', [])  # Will be loaded from config
            )

            learning_config = LearningConfig(
                learning_rate=get_config('path_planning.learning.learning_rate', 0.1),
                discount_factor=get_config('path_planning.learning.discount_factor', 0.9),
                exploration_rate=get_config('path_planning.learning.exploration_rate', 0.2),
                memory_size=get_config('path_planning.learning.memory_size', 1000),
                batch_size=get_config('path_planning.learning.batch_size', 32),
                update_frequency=get_config('path_planning.learning.update_frequency', 100),
                model_path=get_config('path_planning.learning.model_path', str(PATTERN_PLANNER_PATH))
            )

            self._resources["path_planner"] = NewPathPlanner(
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
                self._resources["path_planner"]
            )

            logger.info("All software components initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing software: {e}")
            raise

    def initialize(self):
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

    def cleanup(self):
        """Clean up all resources."""
        with self._lock:
            if not self._initialized:
                return

            try:
                # Clean up hardware in reverse order
                for name, resource in reversed(list(self._resources.items())):
                    try:
                        if hasattr(resource, 'cleanup'):
                            resource.cleanup()
                        elif hasattr(resource, 'shutdown'):
                            resource.shutdown()
                    except Exception as e:
                        logger.error(f"Error cleaning up {name}: {e}")

                self._resources.clear()
                self._initialized = False
                logger.info("All resources cleaned up successfully")
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")
                raise

    def get_resource(self, name):
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

    def get_path_planner(self):
        """Get the path planner instance."""
        return self._resources.get("path_planner")

    def get_navigation(self):
        """Get the navigation controller instance."""
        return self._resources.get("navigation")

    def get_obstacle_detection(self):
        """Get the obstacle detection instance."""
        return self._resources.get("obstacle_detection")

    def get_blade_controller(self):
        """Get the blade controller instance."""
        return self._resources.get("blade")

    def get_bme280_sensor(self):
        """Get the BME280 sensor instance."""
        return self._resources.get("bme280")

    def get_camera(self):
        """Get the camera instance."""
        return self._resources.get("camera")

    def get_robohat_driver(self):
        """Get the RoboHAT driver instance."""
        return self._resources.get("motor_driver")

    def get_gps_serial(self):
        """Get the GPS serial instance."""
        return self._resources.get("gps_serial")

    def get_imu_sensor(self):
        """Get the IMU sensor instance."""
        return self._resources.get("imu")

    def get_ina3221_sensor(self):
        """Get the INA3221 sensor instance."""
        return self._resources.get("ina3221")

    def get_tof_sensors(self):
        """Get the ToF sensors instance."""
        return self._resources.get("tof")

    def get_sensor_interface(self):
        """Get the sensor interface instance."""
        return self._resources.get("sensor_interface")


class Mower:
    """
    Main class for the autonomous mower.

    This class provides a centralized interface for controlling the mower
    and accessing its resources. It uses the ResourceManager class for
    resource management and provides methods for mowing, navigation,
    and other operations.
    """

    def __init__(self, config_path=None):
        """
        Initialize the mower.

        Args:
            config_path: Optional path to configuration file
        """
        self.resource_manager = ResourceManager(config_path)
        self.mode = MowerMode.IDLE
        self.error_condition = None
        self.home_location = None
        self.boundary = []
        self.no_go_zones = []
        self.mowing_schedule = []

        # Initialize logger
        self.logger = logger

        # Load home location from configuration
        try:
            home_config = self.resource_manager._load_config("home_location.json")
            if home_config and 'location' in home_config:
                self.home_location = home_config['location']
                self.logger.info(f"Loaded home location: {self.home_location}")
        except Exception as e:
            self.logger.error(f"Failed to load home location: {e}")

    def initialize(self):
        """Initialize all resources."""
        self.resource_manager.initialize()

        # Initialize web interface with self as the mower instance
        web_interface = WebInterface(mower=self)
        self.resource_manager._resources["web_interface"] = web_interface

        self.logger.info("Mower initialized successfully")

    def cleanup(self):
        """Clean up all resources."""
        self.resource_manager.cleanup()
        self.logger.info("Mower cleaned up successfully")

    def start(self):
        """Start the mowing operation."""
        if self.mode != MowerMode.IDLE:
            self.logger.warning(f"Cannot start mowing from mode {self.mode}")
            return False

        self.logger.info("Starting mowing operation")
        self.mode = MowerMode.MOWING

        # Start the blade
        blade_controller = self.resource_manager.get_blade_controller()
        if blade_controller:
            blade_controller.start_blade()

        # Start navigation
        path_planner = self.resource_manager.get_path_planner()
        if path_planner:
            path_planner.start()

        return True

    def stop(self):
        """Stop the mowing operation."""
        self.logger.info("Stopping mowing operation")

        # Stop the blade
        blade_controller = self.resource_manager.get_blade_controller()
        if blade_controller:
            blade_controller.stop_blade()

        # Stop navigation
        navigation = self.resource_manager.get_navigation()
        if navigation:
            navigation.stop()

        self.mode = MowerMode.IDLE
        return True

    def emergency_stop(self):
        """Perform an emergency stop."""
        self.logger.warning("Emergency stop activated")

        # Stop all motors immediately
        blade_controller = self.resource_manager.get_blade_controller()
        if blade_controller:
            blade_controller.stop_blade()

        robohat_driver = self.resource_manager.get_robohat_driver()
        if robohat_driver:
            robohat_driver.stop()

        self.mode = MowerMode.EMERGENCY_STOP
        return True

    def get_mode(self):
        """Get the current mode of the mower."""
        return self.mode.value

    def get_battery_level(self):
        """Get the current battery level."""
        try:
            ina3221 = self.resource_manager.get_ina3221_sensor()
            if ina3221:
                return ina3221.get_battery_voltage()
            return None
        except Exception as e:
            self.logger.error(f"Error getting battery level: {e}")
            return None

    def get_safety_status(self):
        """Get the current safety status."""
        try:
            # Check various safety conditions
            safety_status = {
                "emergency_stop_active": self.mode == MowerMode.EMERGENCY_STOP,
                "blade_running": False,
                "obstacles_detected": False,
                "battery_low": False
            }

            # Check blade status
            blade_controller = self.resource_manager.get_blade_controller()
            if blade_controller:
                safety_status["blade_running"] = blade_controller.is_running()

            # Check obstacle detection
            obstacle_detection = self.resource_manager.get_obstacle_detection()
            if obstacle_detection:
                safety_status["obstacles_detected"] = obstacle_detection.check_obstacles()

            # Check battery level
            battery_level = self.get_battery_level()
            if battery_level is not None:
                safety_status["battery_low"] = battery_level < 11.0  # Threshold for low battery

            return safety_status
        except Exception as e:
            self.logger.error(f"Error getting safety status: {e}")
            return {"error": str(e)}

    def get_status(self):
        """Get the current status of the mower."""
        try:
            status = {
                "mode": self.get_mode(),
                "battery": self.get_battery_level(),
                "safety": self.get_safety_status(),
                "error": self.error_condition
            }

            # Add position information if available
            navigation = self.resource_manager.get_navigation()
            if navigation:
                status["position"] = navigation.get_status()

            return status
        except Exception as e:
            self.logger.error(f"Error getting status: {e}")
            return {"error": str(e)}

    def get_sensor_data(self):
        """Get data from all sensors."""
        try:
            sensor_data = {}

            # Get IMU data
            imu = self.resource_manager.get_imu_sensor()
            if imu:
                sensor_data["imu"] = imu.get_data()

            # Get BME280 data
            bme280 = self.resource_manager.get_bme280_sensor()
            if bme280:
                sensor_data["bme280"] = bme280.get_data()

            # Get ToF data
            tof = self.resource_manager.get_tof_sensors()
            if tof:
                sensor_data["tof"] = tof.get_data()

            return sensor_data
        except Exception as e:
            self.logger.error(f"Error getting sensor data: {e}")
            return {"error": str(e)}

    def get_home_location(self):
        """Get the home location."""
        return self.home_location

    def set_home_location(self, location):
        """Set the home location."""
        self.home_location = location

        # Save to configuration file
        result = self.resource_manager._save_config("home_location.json", {"location": location})
        if result:
            self.logger.info(f"Saved home location: {location}")
        return result

    def get_boundary(self):
        """Get the yard boundary."""
        return self.boundary

    def get_no_go_zones(self):
        """Get the no-go zones."""
        return self.no_go_zones

    def save_boundary(self, boundary):
        """Save the yard boundary."""
        self.boundary = boundary

        # Update path planner
        path_planner = self.resource_manager.get_path_planner()
        if path_planner:
            path_planner.pattern_config.boundary_points = boundary

        # Save to configuration file
        result = self.resource_manager._save_config("boundary.json", {"boundary": boundary})
        if result:
            self.logger.info("Saved boundary configuration")
        return result

    def save_no_go_zones(self, zones):
        """Save no-go zones."""
        self.no_go_zones = zones

        # Save to configuration file
        result = self.resource_manager._save_config("no_go_zones.json", {"zones": zones})
        if result:
            self.logger.info("Saved no-go zones configuration")
        return result

    def get_mowing_schedule(self):
        """Get the mowing schedule."""
        return self.mowing_schedule

    def set_mowing_schedule(self, schedule):
        """Set the mowing schedule."""
        self.mowing_schedule = schedule

        # Save to configuration file
        result = self.resource_manager._save_config("schedule.json", {"schedule": schedule})
        if result:
            self.logger.info("Saved mowing schedule")
        return result

    def get_current_path(self):
        """Get the current planned path."""
        try:
            path_planner = self.resource_manager.get_path_planner()
            if path_planner:
                return path_planner.current_path
            return []
        except Exception as e:
            self.logger.error(f"Error getting current path: {e}")
            return []

    def _validate_command_params(self, command, params):
        """
        Validate command and parameters.

        Args:
            command: The command to validate
            params: Parameters to validate

        Returns:
            dict: Error response if validation fails, None if validation passes
        """
        # Validate command
        if not isinstance(command, str):
            return {"error": "Command must be a string"}

        # Validate params
        if not isinstance(params, dict):
            return {"error": "Parameters must be a dictionary"}

        return None

    def _execute_move_command(self, params):
        """
        Execute the 'move' command.

        Args:
            params: Command parameters

        Returns:
            dict: Result of the command execution
        """
        # Validate required parameters
        if "direction" not in params:
            return {"error": "Missing required parameter: direction"}

        direction = params.get("direction")

        # Validate direction
        if not isinstance(direction, str):
            return {"error": "Direction must be a string"}

        valid_directions = ["forward", "backward", "left", "right", "stop"]
        if direction not in valid_directions:
            return {"error": f"Invalid direction: {direction}. Valid directions are: {', '.join(valid_directions)}"}

        # Validate speed parameter
        speed = params.get("speed", 0.5)
        if not isinstance(speed, (int, float)):
            return {"error": "Speed must be a number"}

        if speed < 0.0 or speed > 1.0:
            return {"error": "Speed must be between 0.0 and 1.0"}

        # Validate no unexpected parameters
        unexpected_params = set(params.keys()) - {"direction", "speed"}
        if unexpected_params:
            return {"error": f"Unexpected parameters: {', '.join(unexpected_params)}"}

        # Get motor driver
        robohat_driver = self.resource_manager.get_robohat_driver()
        if not robohat_driver:
            return {"error": "Motor driver not available"}

        # Execute command
        if direction == "forward":
            robohat_driver.forward(speed)
        elif direction == "backward":
            robohat_driver.backward(speed)
        elif direction == "left":
            robohat_driver.left(speed)
        elif direction == "right":
            robohat_driver.right(speed)
        elif direction == "stop":
            robohat_driver.stop()

        return {"success": True}

    def _execute_blade_command(self, params):
        """
        Execute the 'blade' command.

        Args:
            params: Command parameters

        Returns:
            dict: Result of the command execution
        """
        # Validate required parameters
        if "action" not in params:
            return {"error": "Missing required parameter: action"}

        action = params.get("action")

        # Validate action
        if not isinstance(action, str):
            return {"error": "Action must be a string"}

        valid_actions = ["start", "stop"]
        if action not in valid_actions:
            return {"error": f"Invalid action: {action}. Valid actions are: {', '.join(valid_actions)}"}

        # Validate no unexpected parameters
        unexpected_params = set(params.keys()) - {"action"}
        if unexpected_params:
            return {"error": f"Unexpected parameters: {', '.join(unexpected_params)}"}

        # Get blade controller
        blade_controller = self.resource_manager.get_blade_controller()
        if not blade_controller:
            return {"error": "Blade controller not available"}

        # Execute command
        if action == "start":
            blade_controller.start_blade()
        elif action == "stop":
            blade_controller.stop_blade()

        return {"success": True}

    def execute_command(self, command, params=None):
        """
        Execute a command with the given parameters.

        Args:
            command: The command to execute
            params: Optional parameters for the command

        Returns:
            The result of the command execution
        """
        # Initialize params if None
        if params is None:
            params = {}

        # Validate command and parameters
        validation_error = self._validate_command_params(command, params)
        if validation_error:
            return validation_error

        self.logger.info(f"Executing command: {command} with params: {params}")

        try:
            # Dispatch command to appropriate handler
            if command == "move":
                return self._execute_move_command(params)
            elif command == "blade":
                return self._execute_blade_command(params)
            else:
                return {"error": f"Unknown command: {command}. Valid commands are: move, blade"}

        except Exception as e:
            self.logger.error(f"Error executing command {command}: {e}")
            return {"error": str(e)}


# Legacy functions for backward compatibility
# These functions use the new Mower class internally

# Singleton instance of the Mower class
_mower_instance = None


def get_mower_instance():
    """Get the singleton instance of the Mower class."""
    global _mower_instance
    if _mower_instance is None:
        _mower_instance = Mower()
        _mower_instance.initialize()
    return _mower_instance


def get_blade_controller():
    """Get the blade controller instance."""
    mower = get_mower_instance()
    return mower.resource_manager.get_blade_controller()


def get_bme280_sensor():
    """Get the BME280 sensor instance."""
    mower = get_mower_instance()
    return mower.resource_manager.get_bme280_sensor()


def get_camera():
    """Get the camera instance."""
    mower = get_mower_instance()
    return mower.resource_manager.get_camera()


def get_gpio_manager():
    """Get the GPIO manager instance."""
    mower = get_mower_instance()
    return mower.resource_manager.get_resource("gpio")


def get_imu_sensor():
    """Get the IMU sensor instance."""
    mower = get_mower_instance()
    return mower.resource_manager.get_imu_sensor()


def get_ina3221_sensor():
    """Get the INA3221 sensor instance."""
    mower = get_mower_instance()
    return mower.resource_manager.get_ina3221_sensor()


def get_robohat_driver():
    """Get the RoboHAT driver instance."""
    mower = get_mower_instance()
    return mower.resource_manager.get_robohat_driver()


def get_sensors():
    """Get the sensor interface instance."""
    mower = get_mower_instance()
    return mower.resource_manager.get_sensor_interface()


def get_serial_port():
    """Get the serial port instance."""
    mower = get_mower_instance()
    return mower.resource_manager.get_gps_serial()


def get_tof_sensors():
    """Get the ToF sensors instance."""
    mower = get_mower_instance()
    return mower.resource_manager.get_tof_sensors()


# Navigation initialization functions

def get_gps_nmea_positions():
    """Get the GPS NMEA positions instance."""
    mower = get_mower_instance()
    # This is a special case as we don't have a direct getter in ResourceManager
    # We'll use the GPS serial port instead
    return mower.resource_manager.get_gps_serial()


def get_gps_latest_position():
    """Get the GPS latest position instance."""
    mower = get_mower_instance()
    # This is a special case as we don't have a direct getter in ResourceManager
    # We'll use the navigation controller instead
    navigation = mower.resource_manager.get_navigation()
    if navigation:
        return navigation.gps_latest_position
    return None


def get_gps_position():
    """Get the GPS position instance."""
    # This is a special case as we don't have a direct getter in ResourceManager
    # We'll use the GPS serial port instead
    return get_gps_nmea_positions()


def get_localization():
    """Get the localization instance."""
    mower = get_mower_instance()
    return mower.resource_manager.get_resource("localization")


def get_path_planner():
    """Get the path planner instance."""
    mower = get_mower_instance()
    return mower.resource_manager.get_path_planner()


def get_navigation_controller():
    """Get the navigation controller instance."""
    mower = get_mower_instance()
    return mower.resource_manager.get_navigation()


# Obstacle Detection initialization functions

def get_avoidance_algorithm():
    """Get the avoidance algorithm instance."""
    mower = get_mower_instance()
    return mower.resource_manager.get_obstacle_detection()


def get_detect_obstacle():
    """Get the detect obstacle function."""
    return detect_obstacle


def get_detect_drop():
    """Get the detect drop function."""
    return detect_drop


def get_stream_frame_with_overlays():
    """Get the stream frame with overlays function."""
    return stream_frame_with_overlays


# UI and utilities initialization functions

def get_web_interface():
    """Get the web interface instance."""
    mower = get_mower_instance()
    return mower.resource_manager.get_resource("web_interface")


def get_logger_config():
    """Get the logger configuration instance."""
    return LoggerConfig()


def get_text_logger():
    """Get the text logger instance."""
    return TextLogger()


def get_csv_logger():
    """Get the CSV logger instance."""
    return CsvLogger()


def get_utils():
    """Get the utilities instance."""
    return Utils()


# Function to initialize all resources

def init_resources():
    """Initialize all resources."""
    mower = get_mower_instance()
    # The mower instance is already initialized in get_mower_instance()
    logger.info("All resources initialized")


# Function to cleanup all resources

def cleanup_resources():
    """Clean up all resources."""
    global _mower_instance
    if _mower_instance is not None:
        _mower_instance.cleanup()
        _mower_instance = None
    logger.info("All resources cleaned up")


# Function to start the web interface

def start_web_interface():
    """Start the web interface."""
    mower = get_mower_instance()
    web_interface = mower.resource_manager.get_resource("web_interface")
    if web_interface:
        web_interface.start()


# Function to start the robot logic

def start_robot_logic():
    """Start the robot logic."""
    # Import here to avoid circular import
    from mower.robot import run_robot
    robot_thread = threading.Thread(target=run_robot, daemon=True)
    robot_thread.start()


if __name__ == "__main__":
    try:
        init_resources()
        start_robot_logic()
        start_web_interface()
    except KeyboardInterrupt:
        logger.info("Exiting")
    finally:
        cleanup_resources()
