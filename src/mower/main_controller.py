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
import platform
import signal  # Added for signal handling
import sys  # Added for sys.exit
import threading  # Added for threading.Lock
import time
import utm
from enum import Enum
from typing import Any, Optional
from pathlib import Path  # Added for Path()

from dotenv import load_dotenv

# ADDED: Import initialize_config_manager and CONFIG_DIR from constants
from mower.config_management import initialize_config_manager
from mower.config_management.config_manager import get_config

# Use an alias for clarity and to avoid conflict if CONFIG_DIR was defined
# locally
from mower.config_management.constants import CONFIG_DIR as APP_CONFIG_DIR
from mower.hardware.blade_controller import BladeController
from mower.hardware.camera_instance import get_camera_instance
from mower.hardware.gpio_manager import GPIOManager
from mower.hardware.imu import BNO085Sensor
from mower.hardware.ina3221 import INA3221Sensor
from mower.hardware.robohat import RoboHATDriver
from mower.hardware.sensor_interface import get_sensor_interface
from mower.hardware.serial_port import GPS_BAUDRATE, GPS_PORT, SerialPort
from mower.hardware.tof import VL53L0XSensors
from mower.navigation.localization import Localization
from mower.navigation.navigation import NavigationController
from mower.navigation.path_planner import LearningConfig, PathPlanner, PatternConfig, PatternType
from mower.navigation.gps import GpsPosition
from mower.obstacle_detection.avoidance_algorithm import AvoidanceAlgorithm
from mower.obstacle_detection.obstacle_detector import ObstacleDetector

# Always safe to import simulation modules and config
# mower.config_management.config_manager.get_config is used later,
# will benefit from early init
from mower.simulation import enable_simulation
from mower.ui.web_ui.web_interface import WebInterface
from mower.utilities.logger_config import LoggerConfigInfo

# Load environment variables from .env file
load_dotenv()

# ADDED: Define MAIN_CONFIG_FILE path using the imported APP_CONFIG_DIR
MAIN_CONFIG_FILE = APP_CONFIG_DIR / "main_config.json"

# ADDED: Ensure config directory and default main_config.json exist
if not APP_CONFIG_DIR.exists():
    APP_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

if not MAIN_CONFIG_FILE.exists():
    default_main_config = {
        "mower": {"name": "DefaultMowerName", "log_level": "INFO"},
        "hardware": {"use_simulation": False},
        "safety": {"use_physical_emergency_stop": True, "emergency_stop_pin": 7, "watchdog_timeout": 15},
        # Add other essential default sections and keys as needed
    }
    with open(MAIN_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(default_main_config, f, indent=2)
    # Logger not initialized yet, so print to stdout
    print(f"Created default configuration file: {MAIN_CONFIG_FILE}")


# ADDED: Initialize the configuration manager early
# This loads .env by default (if EnvironmentConfigurationSource finds it)
# and then main_config.json.
# Priority: main_config.json > .env > programmatic defaults.
initialize_config_manager(config_file=str(MAIN_CONFIG_FILE))

# Initialize logging (now uses config from initialize_config_manager)
logger = LoggerConfigInfo.get_logger(__name__)

# Enable simulation on Windows or when explicitly requested via config or .env
# get_config will now use the initialized config_manager
use_simulation_env = os.environ.get("USE_SIMULATION", "").lower()
use_simulation_config = get_config("hardware.use_simulation", False)

# CORRECTED: Multi-line if condition syntax
if platform.system() == "Windows" or use_simulation_env in ("true", "1", "yes") or use_simulation_config:
    enable_simulation()
    logger.info("Simulation mode enabled (Windows, USE_SIMULATION env, or config)")

# REMOVED/COMMENTED OUT: Local BASE_DIR and CONFIG_DIR definition,
# will use APP_CONFIG_DIR from constants
# BASE_DIR = Path(__file__).resolve().parent.parent.parent
# CONFIG_DIR = BASE_DIR / "config"

# Placeholder for watchdog interval, ensure this is appropriately defined
# WATCHDOG_INTERVAL_S = 10  # seconds, example value. Adjust as needed.
# Moved WATCHDOG_INTERVAL_S to be configurable via main_config.json or .env
# Defaulting here if not found in config.
WATCHDOG_INTERVAL_S = get_config("safety.watchdog_timeout", 15)


# System state enumeration
class SystemState(Enum):
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
        self.logger = LoggerConfigInfo.get_logger(__name__)
        """
        Initialize the resource manager.
        """
        self._initialized = False
        self._resources = {}
        self._lock = threading.Lock()
        self.current_state = SystemState.IDLE  # Initialize current_state
        # Path to user polygon config - UPDATED to use APP_CONFIG_DIR
        self.user_polygon_path = APP_CONFIG_DIR / "user_polygon.json"

        # Watchdog attributes
        self._watchdog_thread: Optional[threading.Thread] = None
        self._watchdog_stop_event: Optional[threading.Event] = None

        # Web interface thread
        self._web_interface_thread: Optional[threading.Thread] = None

        # Initialize safety status tracking variables
        self._safety_status_vars = {
            "warning_logged": False,
            "last_warning_time": 0,
            "warning_interval": 30,  # seconds, configurable
        }

        # This argument is for a specific additional config file, not the main
        # one.
        if config_path:
            self._load_config(config_path)

    def _load_config(self, filename):
        """Load a specific configuration file from the standard config location."""
        # UPDATED to use APP_CONFIG_DIR
        config_file_path = APP_CONFIG_DIR / filename
        if config_file_path.exists():
            try:
                with open(config_file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading config file {filename}: {e}")
        return None

    def _initialize_sensors(self):
        """Consolidate sensor initialization logic."""
        try:
            # Use the static method to initialize INA3221 sensor
            logger.debug("Calling INA3221Sensor.init_ina3221()")
            ina3221_sensor = INA3221Sensor.init_ina3221()
            logger.debug(f"INA3221Sensor.init_ina3221() returned: {ina3221_sensor} (type: {type(ina3221_sensor)})")
            self._resources["ina3221"] = ina3221_sensor
            logger.info("INA3221 power monitor initialized successfully")
        except Exception as e:
            logger.warning(f"Error initializing INA3221 sensor: {e}")
            self._resources["ina3221"] = None

        try:
            self._resources["tof"] = VL53L0XSensors()
            logger.info("VL53L0X time-of-flight sensors initialized successfully")
        except Exception as e:
            logger.warning(f"Error initializing VL53L0X sensors: {e}")
            self._resources["tof"] = None

        try:
            self._resources["imu"] = BNO085Sensor()
            logger.info("IMU sensor initialized successfully")
        except Exception as e:
            logger.warning(f"Error initializing IMU sensor: {e}")
            self._resources["imu"] = None

    def _initialize_hardware(self):
        """Initialize all hardware components."""
        self._resources["gpio"] = GPIOManager()
        self._initialize_sensors()

        try:
            self._resources["blade"] = BladeController()
            logger.info("Blade controller initialized successfully.")
        except Exception as e:
            logger.warning(f"Error initializing blade controller: {e}")
            self._resources["blade"] = None

        try:
            self._resources["motor_driver"] = RoboHATDriver()
            logger.info("RoboHAT motor driver initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing motor driver: {e}")
            self._resources["motor_driver"] = None

        try:
            self._resources["camera"] = get_camera_instance()
            logger.info("Camera initialized successfully")
        except Exception as e:
            logger.warning(f"Error initializing camera: {e}")
            self._resources["camera"] = None

        try:
            # Default for Pi; ensure GPS_PORT is defined in constants or .env
            gps_port_val = GPS_PORT if GPS_PORT is not None else "/dev/ttyACM0"
            self._resources["gps_serial"] = SerialPort(gps_port_val, GPS_BAUDRATE)
            logger.info(f"GPS serial port initialized on {gps_port_val} " f"at {GPS_BAUDRATE} baud")
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
            elif hasattr(res, "_initialize"):  # Some components might use _initialize
                try:
                    res._initialize()
                except Exception as e:
                    logger.error(f"Error _initializing {name}: {e}")
                    self._resources[name] = None

        logger.info("Hardware components initialized with fallbacks for any " "failures")

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
            # get_config will use the globally initialized manager
            pattern_cfg = get_config("pattern_config", {})
            pattern_config = PatternConfig(
                pattern_type=PatternType.PARALLEL,
                spacing=0.5,
                angle=0.0,
                overlap=0.1,
                start_point=(0.0, 0.0),
                boundary_points=[],  # Will be loaded from config
                **pattern_cfg,
            )

            learning_config = LearningConfig(
                learning_rate=0.1,
                discount_factor=0.9,
                exploration_rate=0.2,
                memory_size=1000,
                batch_size=32,
                update_frequency=100,
                # UPDATED to use APP_CONFIG_DIR
                model_path=str(APP_CONFIG_DIR / "models" / "pattern_planner.json"),
            )

            try:
                self._resources["path_planner"] = PathPlanner(pattern_config, learning_config, self)
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
                sensor_interface = None  # Ensure it's None if init fails
                self._resources["sensor_interface"] = None

            # Initialize NavigationController
            try:
                localization = self._resources.get("localization")
                motor_driver = self._resources.get("motor_driver")
                # sensor_interface is already fetched or None
                sensor_if = self._resources.get("sensor_interface")
                if localization and motor_driver and sensor_if:
                    self._resources["navigation"] = NavigationController(localization, motor_driver, sensor_if)
                    logger.info("Navigation controller initialized successfully")
                else:
                    missing_items = []
                    if not localization:
                        missing_items.append("localization")
                    if not motor_driver:
                        missing_items.append("motor_driver")
                    if not sensor_if:
                        missing_items.append("sensor_interface")
                    logger.error("Cannot initialize navigation controller - " f"missing dependencies: {missing_items}")
                    self._resources["navigation"] = None
            except Exception as e:
                logger.error(f"Failed to initialize navigation controller: {e}")
                self._resources["navigation"] = None

            # Initialize the avoidance algorithm
            try:
                self._resources["avoidance_algorithm"] = AvoidanceAlgorithm(self)
                logger.info("Avoidance algorithm initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize avoidance algorithm: {e}")
                self._resources["avoidance_algorithm"] = None

            # Initialize web interface
            self.web_interface = None # Ensure attribute exists even if init fails
            try:
                # Pass self (ResourceManager instance) to WebInterface
                # WebInterface constructor likely expects the main controller/resource manager
                web_interface_instance = WebInterface(self)
                self._resources["web_interface"] = web_interface_instance
                self.web_interface = web_interface_instance # Assign to direct attribute
                logger.info("Web interface initialized successfully and stored in _resources.")
            except Exception as e:
                logger.error(f"Failed to initialize web interface: {e}", exc_info=True)
                self._resources["web_interface"] = None
                self.web_interface = None # Ensure direct attribute is also None on failure

            logger.info("Software components initialized with fallbacks for any " "failures")
        except Exception as e:
            logger.error(f"Critical error in software initialization: {e}")
            # Don't re-raise here to allow partial initialization

        try:
            gps_serial_port = self.get_resource("gps_serial")
            if gps_serial_port:
                # Create and start the continuous GPS reader
                gps_position_reader = GpsPosition(gps_serial_port, debug=True)
                gps_position_reader.start() # Start the background thread
                self._resources["gps_position_reader"] = gps_position_reader
                logger.info("GpsPosition reader thread started.")
            else:
                logger.warning("GPS serial port not available, cannot start GpsPosition reader.")
                self._resources["gps_position_reader"] = None
        except Exception as e:
            logger.error(f"Failed to initialize and start GpsPosition reader: {e}", exc_info=True)
            self._resources["gps_position_reader"] = None

    def initialize(self):
        """Initialize all resources."""
        if self._initialized:
            logger.warning("Resources already initialized")
            return

        try:
            # Set up configuration paths - UPDATED to use APP_CONFIG_DIR
            # APP_CONFIG_DIR existence is ensured before config manager init.
            # self.user_polygon_path already uses APP_CONFIG_DIR from __init__
            if not self.user_polygon_path.exists():
                logger.warning(f"User polygon file not found at " f"{self.user_polygon_path}. Creating default.")
                with open(self.user_polygon_path, "w", encoding="utf-8") as f:
                    json.dump(
                        {
                            "boundary": [[0, 0], [10, 0], [10, 10], [0, 10]],
                            "home": [5, 5],
                        },
                        f,
                    )

            self._initialize_hardware()
            logger.info("Hardware components initialization attempt complete.")

            # Mark ResourceManager as initialized here, so that software components
            # initialized in _initialize_software() can successfully use get_resource().
            # If _initialize_hardware had critical failures, individual resources might be None,
            # but the ResourceManager itself is ready for software components to query them.
            self._initialized = True
            logger.info("ResourceManager marked as initialized (hardware phase complete). Software initialization will now proceed.")

            self._initialize_software()
            logger.info("Software components initialization attempt complete.")

            # If we reached here, both hardware and software initialization phases were attempted.
            # self._initialized is True.
            logger.info("All resource initialization phases complete with fallbacks for any individual failures.")
        except Exception as e:
            logger.error(f"Critical error during resource initialization process: {e}", exc_info=True)
            self._initialized = False  # Ensure this is set on any overriding failure

    def init_all_resources(self) -> bool:
        """
        Initialize all resources; return True if successful,
        False otherwise.
        """
        try:
            self.initialize()
            return self._initialized  # Return the actual status
        except Exception as e:
            logger.error(f"ResourceManager init_all_resources failed: {e}", exc_info=True)
            self._initialized = False  # Ensure this is set on failure
            return False

    def cleanup_all_resources(self):
        """Clean up all initialized resources."""
        logger.info("Starting cleanup of all resources...")
        with self._lock:
            if not self._initialized:
                logger.info("Resources not initialized or already cleaned up.")
                return

            # Stop watchdog first
            self._stop_watchdog()

            # Stop web interface
            web_interface = self._resources.get("web_interface")
            if web_interface and hasattr(web_interface, "stop"):
                try:
                    logger.info("Stopping web interface...")
                    web_interface.stop()  # This now handles socketio.stop() internally
                    # Ensure the thread is properly managed by WebInterface's stop method
                    # The join should happen after web_interface.stop() has signaled the server
                    if self._web_interface_thread and self._web_interface_thread.is_alive():
                        logger.info("Waiting for web interface thread to join...")
                        self._web_interface_thread.join(timeout=10) # Increased timeout slightly
                        if self._web_interface_thread.is_alive():
                            logger.warning("Web interface thread did not join in time.")
                except Exception as e:
                    logger.error(f"Error stopping web interface: {e}", exc_info=True)

            # Cleanup other resources in reverse order of initialization if necessary
            # For now, iterating through all and calling cleanup if available
            for name, resource in reversed(list(self._resources.items())):
                if resource is None or name == "web_interface":  # Web interface already handled
                    continue

                cleanup_method = getattr(resource, "cleanup", None)
                if cleanup_method is None:
                    cleanup_method = getattr(resource, "close", None)  # Common for file-like objects or connections
                if cleanup_method is None and name == "gpio": # GPIOManager specific
                    cleanup_method = getattr(resource, "cleanup_gpio", None)


                if callable(cleanup_method):
                    try:
                        logger.info(f"Cleaning up {name}...")
                        cleanup_method()
                    except Exception as e:
                        logger.error(f"Error cleaning up {name}: {e}", exc_info=True)
                else:
                    logger.debug(f"No standard cleanup/close method found for {name}.")

            # Special handling for GPIO if not covered by a generic 'cleanup'
            gpio_manager = self._resources.get("gpio")
            if gpio_manager and hasattr(gpio_manager, "cleanup_gpio") and "gpio" not in ["web_interface"]: # ensure it wasn't called if gpio had a cleanup method
                try:
                    logger.info("Performing final GPIO cleanup...")
                    gpio_manager.cleanup_gpio()
                except Exception as e:
                    logger.error(f"Error during final GPIO cleanup: {e}", exc_info=True)


            self._resources.clear()
            self._initialized = False
            logger.info("All resources have been cleaned up.")

    def get_resource(self, name: str) -> Any:
        """
        Get a resource by name.

        Args:
            name (str): Name of the resource to get.

        Returns:
            object: The requested resource, or None if not found or not initialized.
        """
        with self._lock:
            if not self._initialized:
                logger.warning(f"Attempted to get resource '{name}' " "but resources not initialized.")
                return None
            return self._resources.get(name)

    def get_path_planner(self) -> Optional[PathPlanner]:
        """Get the path planner instance."""
        return self.get_resource("path_planner")

    def get_navigation(self) -> Optional[NavigationController]:
        """Get the navigation controller instance."""
        return self.get_resource("navigation")

    def get_obstacle_detection(self) -> Optional[ObstacleDetector]:
        """Get the obstacle detection instance."""
        return self.get_resource("obstacle_detector")

    def get_web_interface(self) -> Optional[WebInterface]:
        """Get the web interface instance."""
        return self.get_resource("web_interface")

    # Replace Any with actual camera type
    def get_camera(self) -> Optional[Any]:
        """Get the camera instance."""
        return self.get_resource("camera")

    # Replace Any with actual type
    def get_sensor_interface(self) -> Optional[Any]:
        """Get the sensor interface instance."""
        si = self.get_resource("sensor_interface")
        if si is None and self._initialized:  # Try to init on demand if not present
            logger.info("Sensor interface not found, attempting on-demand initialization.")
            try:
                self._resources["sensor_interface"] = get_sensor_interface()
                logger.info("Sensor interface initialized on demand.")
                return self._resources["sensor_interface"]
            except Exception as e:
                logger.error(f"Failed to initialize sensor interface on demand: {e}")
                return None
        return si

    def get_gps(self) -> Optional[SerialPort]:
        """Get the GPS serial port instance."""
        gps = self.get_resource("gps_serial")
        if gps is None and self._initialized:  # Try to init on demand
            logger.info("GPS serial port not found, attempting on-demand initialization.")
            try:
                gps_port_val = GPS_PORT if GPS_PORT is not None else "/dev/ttyACM0"
                self._resources["gps_serial"] = SerialPort(gps_port_val, GPS_BAUDRATE)
                logger.info(f"GPS serial port initialized on demand on {gps_port_val}")
                return self._resources["gps_serial"]
            except Exception as e:
                logger.error(f"Failed to initialize GPS serial on demand: {e}")
                return None
        return gps

    def start_web_interface(self):
        """Starts the web interface if it has been initialized."""
        print("DEBUG: ResourceManager.start_web_interface() - Entered method")
        self.logger.info("ResourceManager: Attempting to start web interface...")
        web_iface = self.get_resource("web_interface") # Use get_resource
        if web_iface:
            print("DEBUG: ResourceManager.start_web_interface() - web_iface (from get_resource) is not None")
            self.logger.info("ResourceManager: Web interface instance retrieved from resources.")
            try:
                print("DEBUG: ResourceManager.start_web_interface() - Entering try block to call web_iface.start()")
                self.logger.info("ResourceManager: Calling web_iface.start()...")
                web_iface.start() # Call start on the retrieved instance
                self.logger.info("ResourceManager: web_iface.start() returned.")
                print("DEBUG: ResourceManager.start_web_interface() - web_iface.start() returned")
            except Exception as e:
                print(f"DEBUG: ResourceManager.start_web_interface() - Exception caught: {e}")
                self.logger.error(f"ResourceManager: Failed to start web interface: {e}", exc_info=True)
        else:
            print("DEBUG: ResourceManager.start_web_interface() - web_iface (from get_resource) is None")
            self.logger.warning("ResourceManager: Web interface not initialized or not found in resources, cannot start.")
        print("DEBUG: ResourceManager.start_web_interface() - Exiting method")

    def get_home_location(self):
        """
        Get the home location from the user polygon configuration file.

        Returns:
            list: A list representing the home coordinates [lat, lon],
                  or a default if not found.
        """
        default_home = [0.0, 0.0]  # Default if not found or error
        try:
            if self.user_polygon_path.exists():
                with open(self.user_polygon_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                home_location = data.get("home", default_home)
                if (
                    isinstance(home_location, list)
                    and len(home_location) == 2
                    and all(isinstance(coord, (int, float)) for coord in home_location)
                ):
                    return home_location
                else:
                    logger.warning(
                        f"Invalid home location format in "
                        f"{self.user_polygon_path}: {home_location}. "
                        f"Using default: {default_home}"
                    )
                    return default_home
            else:
                logger.warning(
                    f"User polygon file not found: {self.user_polygon_path}. " f"Using default home: {default_home}"
                )
                return default_home
        except Exception as e:
            logger.error(f"Error reading home location: {e}. Using default.")
            return default_home

    def get_boundary_points(self):
        """
        Get boundary points from the path planner or configuration file.

        Returns:
            list: A list of boundary points, or an empty list if not found.
        """
        default_boundary = []
        try:
            path_planner = self.get_path_planner()
            # MODIFIED: Access boundary_points directly from
            # path_planner.pattern_config
            if (
                path_planner
                and hasattr(path_planner, "pattern_config")
                and hasattr(path_planner.pattern_config, "boundary_points")
            ):
                boundary = path_planner.pattern_config.boundary_points
                if boundary:
                    return boundary

            # Fallback to reading from the config file
            if self.user_polygon_path.exists():
                with open(self.user_polygon_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                boundary = data.get("boundary", default_boundary)
                # Add validation for boundary points format if necessary
                return boundary
            else:
                logger.warning(f"User polygon file not found: {self.user_polygon_path}. " "Returning empty boundary.")
                return default_boundary
        except Exception as e:
            logger.error(f"Error reading boundary points: {e}. Returning empty boundary.")
            return default_boundary

    def get_safety_status(self):
        """Retrieve safety status from the sensor interface.

        Returns:
            dict: A dictionary containing safety status information,
                  e.g., {"emergency_stop": False, "obstacle_detected": True}.
                  Returns a default safe status if the sensor interface is unavailable.
        """
        default_status = {
            "emergency_stop_active": False,
            "obstacle_detected_nearby": False,
            "low_battery_warning": False,
            "system_error": False,
            "status_message": "Safety status nominal or sensor interface unavailable.",
        }
        sensor_interface = self.get_sensor_interface()
        if sensor_interface and hasattr(sensor_interface, "get_safety_status"):
            try:
                return sensor_interface.get_safety_status()
            except Exception as e:
                logger.error(f"Error getting safety status from interface: {e}")
                default_status["status_message"] = "Error retrieving status from sensor interface."
                default_status["system_error"] = True
                return default_status
        else:
            # Log a warning if the sensor interface is unavailable, but not too
            # frequently
            current_time = time.time()
            if not self._safety_status_vars["warning_logged"] or (
                current_time - self._safety_status_vars["last_warning_time"]
                > self._safety_status_vars["warning_interval"]
            ):
                logger.warning("Sensor interface unavailable for safety status. " "Returning default safe status.")
                self._safety_status_vars["warning_logged"] = True
                self._safety_status_vars["last_warning_time"] = current_time
            return default_status

    def get_status(self):
        """Get the overall system status."""
        # This can be expanded to include more detailed status information
        return {
            "state": self.current_state.value,
            "initialized": self._initialized,
            "resources_available": list(self._resources.keys()),
        }

    def get_battery_status(self):
        """Get the battery status information.

        Returns:
            dict: Battery voltage, current, percentage, or None if unavailable.
        """
        ina_sensor = self.get_resource("ina3221")
        logger.debug(f"get_battery_status: ina_sensor = {ina_sensor} (type: {type(ina_sensor)})")
        if ina_sensor:  # ina_sensor is the adafruit_ina3221.INA3221 object
            try:
                # Use the static method to read channel data
                # Try all channels to find one with power readings
                channel_data = None
                active_channel = None
                
                for channel in [1, 2, 3]:
                    logger.debug(f"Attempting to read INA3221 channel {channel} data")
                    test_data = INA3221Sensor.read_ina3221(ina_sensor, channel)
                    logger.debug(f"INA3221 channel {channel} data: {test_data}")
                    
                    if test_data and test_data.get("bus_voltage", 0) > 0.1:  # Found a channel with actual power
                        channel_data = test_data
                        active_channel = channel
                        break
                
                if channel_data and active_channel:
                    # Found active power on a channel
                    voltage = channel_data.get("bus_voltage")
                    current = channel_data.get("current")
                    power = voltage * current if voltage and current else None

                    # Calculate battery percentage based on voltage
                    # Example for 12V lead-acid battery (adjust for actual battery type)
                    percentage = None
                    if voltage is not None:
                        min_volt = 10.5  # Empty battery voltage
                        max_volt = 12.7  # Full battery voltage
                        if voltage <= min_volt:
                            percentage = 0.0
                        elif voltage >= max_volt:
                            percentage = 100.0
                        else:
                            percentage = ((voltage - min_volt) / (max_volt - min_volt)) * 100
                        percentage = round(percentage, 1)

                    result = {
                        "voltage": voltage,
                        "current": current,
                        "power": power,
                        "percentage": percentage,
                        "status": f"Channel {active_channel} active",
                        "channel": active_channel,
                    }
                    logger.debug(f"Returning battery status from channel {active_channel}: {result}")
                    return result
                else:
                    # INA3221 is connected but no power detected on any channel
                    logger.warning("INA3221 sensor connected but no power detected on any channel - check wiring")
                    return {
                        "voltage": 0.0,
                        "current": 0.0,
                        "power": 0.0,
                        "percentage": 0.0,
                        "status": "No power detected - check wiring",
                        "channel": None,
                    }
            except Exception as e:
                logger.warning(f"Could not retrieve battery info from INA3221: {e}")
                return {
                    "voltage": None,
                    "current": None,
                    "power": None,
                    "percentage": None,
                    "status": f"Sensor error: {e}",
                }
        else:
            logger.debug("ina_sensor is None in get_battery_status")
        return {
            "voltage": None,
            "current": None,
            "power": None,
            "percentage": None,
            "status": "Battery sensor unavailable or error.",
        }

    def get_gps_location(self):
        """Get the current GPS location and satellite count from the running GpsPosition thread."""
        gps_reader = self.get_resource("gps_position_reader")
        if gps_reader:
            try:
                # The position format from gps.py is (timestamp, easting, northing, zone_number, zone_letter)
                position_data = gps_reader.get_latest_position()
                metadata = gps_reader.get_latest_metadata() if hasattr(gps_reader, "get_latest_metadata") else None
                if position_data:
                    _, easting, northing, zone_number, zone_letter = position_data
                    # Convert UTM back to lat/lon for the UI
                    lat, lon = utm.to_latlon(easting, northing, zone_number, zone_letter)
                    satellites = metadata.get("satellites") if metadata else None
                    hdop = metadata.get("hdop") if metadata else None
                    return {
                        "status": "Fix acquired",
                        "latitude": lat,
                        "longitude": lon,
                        "satellites": satellites,
                        "hdop": hdop,
                    }
                else:
                    return {"status": "Waiting for GPS fix", "latitude": None, "longitude": None, "satellites": 0}
            except Exception as e:
                logger.warning(f"Error getting or converting data from GpsPosition reader: {e}", exc_info=True)
                return {"status": "Error processing GPS data", "latitude": None, "longitude": None, "satellites": 0}

        return {"status": "GPS unavailable", "latitude": None, "longitude": None, "satellites": 0}

    def get_sensor_data(self):
        """
        Collects and returns data from all available sensors.

        Returns:
            dict: A dictionary containing data from various sensors.
                  Keys are sensor names (e.g., 'imu', 'tof', 'power'),
                  and values are their respective readings.
        """
        # Hardened: Always return a complete sensor_data dict, with mock/simulated values if hardware is missing.
        sensor_data = {}

        # IMU Data
        try:
            imu = self.get_resource("imu")
            if imu:
                heading = imu.get_heading() if hasattr(imu, "get_heading") else 0.0
                roll = imu.get_roll() if hasattr(imu, "get_roll") else 0.0
                pitch = imu.get_pitch() if hasattr(imu, "get_pitch") else 0.0
                sensor_data["imu"] = {
                    "heading": heading,
                    "roll": roll,
                    "pitch": pitch,
                    "acceleration": (imu.get_acceleration() if hasattr(imu, "get_acceleration") else [0, 0, 0]),
                    "gyroscope": (imu.get_gyroscope() if hasattr(imu, "get_gyroscope") else [0, 0, 0]),
                    "quaternion": (imu.get_quaternion() if hasattr(imu, "get_quaternion") else [1, 0, 0, 0]),
                    "temperature": (imu.get_temperature() if hasattr(imu, "get_temperature") else 0.0),
                }
            else:
                # Simulated IMU data
                sensor_data["imu"] = {
                    "heading": 0.0,
                    "roll": 0.0,
                    "pitch": 0.0,
                    "acceleration": [0, 0, 0],
                    "gyroscope": [0, 0, 0],
                    "quaternion": [1, 0, 0, 0],
                    "temperature": 25.0,
                }
        except Exception as e:
            logger.warning(f"Failed to get IMU data: {e}")
            sensor_data["imu"] = {
                "heading": 0.0,
                "roll": 0.0,
                "pitch": 0.0,
                "acceleration": [0, 0, 0],
                "gyroscope": [0, 0, 0],
                "quaternion": [1, 0, 0, 0],
                "temperature": 25.0,
                "error": str(e),
            }

        # ToF Data
        try:
            tof_sensors = self.get_resource("tof")
            if tof_sensors and hasattr(tof_sensors, "get_distances"):
                sensor_data["tof"] = tof_sensors.get_distances()
            else:
                # Simulated ToF data
                sensor_data["tof"] = {"left": 100.0, "right": 100.0, "front": 100.0}
        except Exception as e:
            logger.warning(f"Failed to get ToF data: {e}")
            sensor_data["tof"] = {"left": 100.0, "right": 100.0, "front": 100.0, "error": str(e)}

        # Power/Battery Data
        try:
            power_monitor = self.get_resource("ina3221")
            logger.debug(f"Power monitor resource: {power_monitor} (type: {type(power_monitor)})")
            if power_monitor:
                battery_info = self.get_battery_status()
                logger.debug(f"Battery info from get_battery_status(): {battery_info}")
                
                # Check if we got real data from INA3221
                if battery_info and battery_info.get("status") not in [None, "Battery sensor unavailable or error."]:
                    sensor_data["power"] = battery_info
                else:
                    # INA3221 is available but returned no useful data
                    logger.debug("INA3221 available but no useful power data, using simulated data")
                    sensor_data["power"] = {
                        "voltage": 12.0,
                        "current": 1.0,
                        "power": 12.0,
                        "percentage": 80.0,
                        "status": "Simulated - INA3221 connected but no power detected",
                    }
            else:
                # Simulated battery info
                logger.debug("Power monitor resource is None, using simulated data")
                sensor_data["power"] = {
                    "voltage": 12.0,
                    "current": 1.0,
                    "power": 12.0,
                    "percentage": 80.0,
                    "status": "Simulated - INA3221 not available",
                }
        except Exception as e:
            logger.warning(f"Failed to get power monitor data: {e}")
            sensor_data["power"] = {
                "voltage": 12.0,
                "current": 1.0,
                "power": 12.0,
                "percentage": 80.0,
                "status": "Simulated - Error accessing INA3221",
                "error": str(e),
            }

        # GPS Data
        try:
            gps_data = self.get_gps_location()
            if gps_data and gps_data.get("latitude") is not None and gps_data.get("longitude") is not None:
                sensor_data["gps"] = gps_data
            else:
                # Simulated GPS data
                sensor_data["gps"] = {
                    "status": "Simulated",
                    "latitude": 37.7749,
                    "longitude": -122.4194,
                    "raw": "",
                }
        except Exception as e:
            logger.warning(f"Failed to get GPS data: {e}")
            sensor_data["gps"] = {
                "status": "Simulated",
                "latitude": 37.7749,
                "longitude": -122.4194,
                "raw": "",
                "error": str(e),
            }

        # GPIO Inputs
        try:
            gpio_manager = self.get_resource("gpio")
            if gpio_manager and hasattr(gpio_manager, "get_all_input_states"):
                sensor_data["gpio_inputs"] = gpio_manager.get_all_input_states()
            else:
                sensor_data["gpio_inputs"] = {"simulated": True}
        except Exception as e:
            logger.warning(f"Failed to get GPIO input states: {e}")
            sensor_data["gpio_inputs"] = {"simulated": True, "error": str(e)}

        # Blade Controller Status
        try:
            blade_controller = self.get_resource("blade")
            if blade_controller and hasattr(blade_controller, "get_state"):
                sensor_data["blade_status"] = blade_controller.get_state()
            else:
                sensor_data["blade_status"] = {"status": "Simulated"}
        except Exception as e:
            logger.warning(f"Failed to get blade status: {e}")
            sensor_data["blade_status"] = {"status": "Simulated", "error": str(e)}

        # Motor Driver Status
        try:
            motor_driver = self.get_resource("motor_driver")
            if motor_driver and hasattr(motor_driver, "get_status"):
                sensor_data["motor_driver_status"] = motor_driver.get_status()
            else:
                sensor_data["motor_driver_status"] = {"status": "Simulated"}
        except Exception as e:
            logger.warning(f"Failed to get motor driver status: {e}")
            sensor_data["motor_driver_status"] = {"status": "Simulated", "error": str(e)}

        # Camera Status
        try:
            camera = self.get_resource("camera")
            if camera and hasattr(camera, "is_operational"):
                sensor_data["camera_status"] = {"operational": camera.is_operational()}
            else:
                sensor_data["camera_status"] = {"operational": True, "simulated": True}
        except Exception as e:
            logger.warning(f"Failed to get camera status: {e}")
            sensor_data["camera_status"] = {"operational": True, "simulated": True, "error": str(e)}

        return sensor_data

    def get_avoidance_algorithm(self) -> Optional[AvoidanceAlgorithm]:
        """Get the avoidance algorithm instance."""
        aa = self.get_resource("avoidance_algorithm")
        if aa is None and self._initialized:
            logger.info("Avoidance algorithm not found, attempting on-demand initialization.")
            try:
                self._resources["avoidance_algorithm"] = AvoidanceAlgorithm(self)
                logger.info("Avoidance algorithm initialized on demand.")
                return self._resources["avoidance_algorithm"]
            except Exception as e:
                logger.error(f"Failed to initialize avoidance algorithm on demand: {e}")
                return None
        return aa

    def _watchdog_loop(self, stop_event: threading.Event):
        """Internal watchdog loop to monitor critical components."""
        logger.info("Watchdog loop started.")
        try:
            while not stop_event.wait(timeout=WATCHDOG_INTERVAL_S):
                logger.debug("Watchdog check...")
                # Example checks:
                if self.current_state == SystemState.ERROR:
                    logger.warning("Watchdog: System is in ERROR state.")
                # Check if critical threads are alive (if applicable)
                # Check sensor responsiveness (e.g., last update time)
        except Exception as e:
            logger.error(f"Exception in watchdog loop: {e}", exc_info=True)
        finally:
            logger.info("Watchdog loop finishing.")

    def _stop_watchdog(self):
        """Stop the watchdog thread."""
        logger.info("Stopping system watchdog thread...")
        if self._watchdog_stop_event:
            logger.debug("Setting watchdog stop event.")
            self._watchdog_stop_event.set()
        else:
            logger.debug("Watchdog stop event not found (already stopped or never started?).")

        thread_to_join = self._watchdog_thread # Capture before potentially nullifying
        if thread_to_join and thread_to_join.is_alive():
            logger.debug(f"Watchdog thread '{thread_to_join.name}' is alive. Attempting to join with 5s timeout.")
            thread_to_join.join(timeout=5.0)
            if thread_to_join.is_alive():
                logger.warning(f"System watchdog thread '{thread_to_join.name}' did not join in time.")
            else:
                logger.info(f"System watchdog thread '{thread_to_join.name}' stopped successfully.")
        elif thread_to_join: # Thread object exists but not alive
            logger.info(f"System watchdog thread '{thread_to_join.name}' was found but not alive.")
        else: # No thread object
            logger.info("System watchdog thread was not running or reference already cleared.")

        self._watchdog_thread = None
        self._watchdog_stop_event = None

    def _start_watchdog(self):
        """Start a watchdog thread to monitor system health."""
        if self._watchdog_thread and self._watchdog_thread.is_alive():
            logger.warning("Watchdog thread already running.")
            return

        self._watchdog_stop_event = threading.Event()
        self._watchdog_thread = threading.Thread(
            target=self._watchdog_loop,
            args=(self._watchdog_stop_event,),
            daemon=True,  # Daemon threads exit when the main program exits
            name="SystemWatchdogThread",
        )
        self._watchdog_thread.start()
        logger.info("System watchdog thread started.")

    def start(self):
        """Start the main controller operations (placeholder)."""
        logger.info("Main controller 'start' method called (currently a placeholder).")
        # This is where you would typically start the main operational logic,
        # perhaps by starting a state machine or main control loop in a thread.
        # For now, it does nothing beyond logging.
        # Example:
        # if not self._main_loop_thread or not self._main_loop_thread.is_alive():
        #     self._main_loop_stop_event = threading.Event()
        #     self._main_loop_thread = threading.Thread(
        #         target=self._run_main_loop,
        #         args=(self._main_loop_stop_event,)
        #     )
        #     self._main_loop_thread.start()
        #     logger.info("Main operational loop started.")
        # else:
        #     logger.warning("Main operational loop already running.")
        pass

    def start_manual_control(self) -> bool:
        """
        Start manual control mode. (Placeholder)
        Actual implementation involves setting state and enabling manual input.
        """
        logger.info("Attempting to start manual control mode...")
        nav_controller = self.get_navigation()
        if nav_controller and hasattr(nav_controller, "enable_manual_control"):
            try:
                nav_controller.enable_manual_control(True)  # MODIFIED: Pass True
                # Consider a dedicated MANUAL_CONTROL state
                self.current_state = SystemState.IDLE
                logger.info("Manual control enabled.")
                return True
            except Exception as e:
                logger.error(f"Failed to enable manual control: {e}")
                return False
        else:
            logger.warning("Nav controller unavailable or no manual control support.")
            return False

    def stop_all_operations(self) -> bool:
        """
        Stop all mower operations (motors, blades, etc.). (Placeholder)
        This should bring the mower to a safe, stationary state.
        """
        logger.info("Stopping all mower operations...")
        success = True
        try:
            # Stop motors
            motor_driver = self.get_resource("motor_driver")
            if motor_driver and hasattr(motor_driver, "stop_motors"):
                motor_driver.stop_motors()
                logger.info("Motors stopped.")
            elif motor_driver:
                logger.warning("Motor driver present but 'stop_motors' method missing.")
            else:
                logger.warning("Motor driver not available to stop motors.")
                success = False

            # Stop blades
            blade_controller = self.get_resource("blade")
            if blade_controller and hasattr(blade_controller, "stop_blade"):
                blade_controller.stop_blade()
                logger.info("Blades stopped.")
            elif blade_controller:
                logger.warning("Blade controller present but 'stop_blade' method missing.")
            else:
                logger.warning("Blade controller not available to stop blades.")
                success = False

            self.current_state = SystemState.IDLE  # Or EMERGENCY_STOP if appropriate
            logger.info("All operations commanded to stop.")
            return success
        except Exception as e:
            logger.error(f"Error during stop_all_operations: {e}")
            self.current_state = SystemState.ERROR
            return False

    def emergency_stop(self):
        """Trigger an emergency stop."""
        logger.critical("EMERGENCY STOP ACTIVATED!")
        self.stop_all_operations()  # Utilize the common stop logic
        self.current_state = SystemState.EMERGENCY_STOP
        # Potentially log to a specific emergency log file or send alert
        # For now, relies on stop_all_operations and state change.

    def get_gps_coordinates(self):
        """Get GPS coordinates, simple wrapper around get_gps_location."""
        gps_info = self.get_gps_location()
        if gps_info and gps_info.get("latitude") is not None and gps_info.get("longitude") is not None:
            return {"lat": gps_info["latitude"], "lng": gps_info["longitude"]}
        return None

    def set_home_location(self, location):
        """
        Set the home location in the user polygon configuration file.

        Args:
            location (list or dict): Home location as [lat, lon]
                                     or {"lat": lat, "lng": lon}.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Normalize location format
            if isinstance(location, dict) and "lat" in location and "lng" in location:
                normalized_location = [location["lat"], location["lng"]]
            elif isinstance(location, (list, tuple)) and len(location) == 2:
                # Ensure it's a list for JSON
                normalized_location = list(location)
            else:
                logger.error(f"Invalid location format for set_home_location: {location}")
                return False

            # Load existing data or create new if file doesn't exist
            data = {}
            if self.user_polygon_path.exists():
                try:
                    with open(self.user_polygon_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except json.JSONDecodeError:
                    logger.warning(
                        f"Error decoding JSON from {self.user_polygon_path}. " "Will overwrite with new data."
                    )
                except Exception as e:
                    logger.warning(
                        f"Error reading config file {self.user_polygon_path}, " f"will create/overwrite: {e}"
                    )
            else:
                logger.info(f"Config file " f"{self.user_polygon_path} not found. Creating new.")

            # Update home location
            data["home"] = normalized_location

            # Save to configuration file
            try:
                with open(self.user_polygon_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)  # Add indent for readability
                logger.info(f"Home location saved to {self.user_polygon_path}" f": {normalized_location}")
                return True
            except Exception as e:
                logger.error(f"Failed to save home location to " f"{self.user_polygon_path}: {e}")
                return False
        except Exception as e:
            logger.error(f"Error setting home location: {e}", exc_info=True)
            return False

    def initialize_resources(self):
        """Initialize all resources."""
        if self._initialized:
            logger.warning("Resources already initialized")
            return

        try:
            # Set up configuration paths - UPDATED to use APP_CONFIG_DIR
            # APP_CONFIG_DIR existence is ensured before config manager init.
            # self.user_polygon_path already uses APP_CONFIG_DIR from __init__
            if not self.user_polygon_path.exists():
                logger.warning(f"User polygon file not found at " f"{self.user_polygon_path}. Creating default.")
                with open(self.user_polygon_path, "w", encoding="utf-8") as f:
                    json.dump(
                        {
                            "boundary": [[0, 0], [10, 0], [10, 10], [0, 10]],
                            "home": [5, 5],
                        },
                        f,
                    )

            self._initialize_hardware()
            logger.info("Hardware components initialization attempt complete.")

            # Mark ResourceManager as initialized here, so that software components
            # initialized in _initialize_software() can successfully use get_resource().
            # If _initialize_hardware had critical failures, individual resources might be None,
            # but the ResourceManager itself is ready for software components to query them.
            self._initialized = True
            logger.info("ResourceManager marked as initialized (hardware phase complete). Software initialization will now proceed.")

            # Initialize obstacle detector separately to manage dependencies
            try:
                self.obstacle_detector = get_obstacle_detector(resource_manager=self)
                logger.info("Obstacle detector initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize obstacle detector: {e}", exc_info=True)
                self.obstacle_detector = None # Ensure it's None on failure

            self._initialize_software()
            logger.info("Software components initialization attempt complete.")

            # If we reached here, both hardware and software initialization phases were attempted.
            # self._initialized is True.
            logger.info("All resource initialization phases complete with fallbacks for any individual failures.")
        except Exception as e:
            logger.error(f"Critical error during resource initialization process: {e}", exc_info=True)
            self._initialized = False  # Ensure this is set on any overriding failure

    def get_obstacle_detector(self) -> Optional[ObstacleDetector]:
        return self.get_resource("obstacle_detector")


def main():
    """
    Main function to initialize and run the autonomous mower application.
    """
    logger.info("Starting Autonomous Mower Application...")

    # Global stop event for all threads
    stop_event = threading.Event()
    resource_manager = None  # Ensure resource_manager is defined in this scope

    def signal_handler(signum, frame):
        logger.info(f"Signal {signum} received. Initiating shutdown...")
        stop_event.set()
        if resource_manager:
            logger.info("Cleaning up resources...")
            resource_manager.cleanup_all_resources()
            logger.info("Resources cleaned up.")
        logger.info("Exiting application.")
        sys.exit(0)

    # Register signal handlers for SIGINT (Ctrl+C) and SIGTERM
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        resource_manager = ResourceManager(config_path=str(MAIN_CONFIG_FILE))
        if not resource_manager.init_all_resources():
            logger.error("Failed to initialize critical resources. Exiting.")
            if resource_manager: # Check if resource_manager was instantiated
                resource_manager.cleanup_all_resources()
            sys.exit(1)

        # Start the web interface
        try:
            print("DEBUG: main() - Before calling resource_manager.start_web_interface()") # ADDED
            logger.info("MAIN: Attempting to start the web interface...")
            resource_manager.start_web_interface()
            logger.info("MAIN: Web interface start process initiated.")
            print("DEBUG: main() - After calling resource_manager.start_web_interface()") # ADDED
        except Exception as e:
            print(f"DEBUG: main() - Exception caught while starting web interface: {e}") # ADDED
            logger.error(f"MAIN: Failed to start web interface: {e}", exc_info=True)
            # Decide if this is critical enough to exit. For now, log and continue.

        # Start the watchdog timer
        # Ensure watchdog is started only if resource_manager is valid
        if resource_manager:
             resource_manager._start_watchdog()


        logger.info("Application started. Waiting for shutdown signal...")
        stop_event.wait()  # Wait indefinitely until stop_event is set

    except Exception as e:
        logger.critical(f"Unhandled exception in main: {e}", exc_info=True)
        if resource_manager:
            resource_manager.cleanup_all_resources()
        sys.exit(1)
    finally:
        logger.info("Application main loop ended or error occurred.")
        if resource_manager and not stop_event.is_set(): # If not already shutting down via signal
            logger.info("Performing final cleanup from main finally block...")
            resource_manager.cleanup_all_resources()
            logger.info("Final cleanup complete.")

if __name__ == "__main__":
    # This allows running the main_controller.py directly for testing/debugging
    # In production, it's run via the 'mower' entry point defined in setup.py
    main()
