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
import threading
import time
import signal  # Added for signal handling
import sys  # Added for sys.exit
from enum import Enum
from pathlib import Path
from typing import Any, Optional
from dotenv import load_dotenv

# Always safe to import simulation modules and config
from mower.simulation import enable_simulation
from mower.utilities.logger_config import LoggerConfigInfo
from mower.config_management.config_manager import get_config
from mower.navigation.path_planner import (
    PathPlanner,
    PatternConfig,
    PatternType,
    LearningConfig,
)
from mower.navigation.navigation import NavigationController
from mower.navigation.localization import Localization
from mower.obstacle_detection.obstacle_detector import ObstacleDetector
from mower.obstacle_detection.avoidance_algorithm import AvoidanceAlgorithm
from mower.ui.web_ui.web_interface import WebInterface
from mower.hardware.serial_port import SerialPort, GPS_PORT, GPS_BAUDRATE
from mower.hardware.ina3221 import INA3221Sensor
from mower.hardware.tof import VL53L0XSensors
from mower.hardware.imu import BNO085Sensor
from mower.hardware.gpio_manager import GPIOManager
from mower.hardware.blade_controller import BladeController
from mower.hardware.robohat import RoboHATDriver
from mower.hardware.camera_instance import get_camera_instance
from mower.hardware.sensor_interface import get_sensor_interface

# Load environment variables
load_dotenv()

# Initialize logging
logger = LoggerConfigInfo.get_logger(__name__)

# Enable simulation on Windows or when explicitly requested
if (platform.system() == "Windows" or
        os.environ.get("USE_SIMULATION", "").lower() in ("true", "1", "yes")):
    enable_simulation()
    logger.info(
        "Simulation mode enabled (running on Windows or USE_SIMULATION=true)")

# Base directory for consistent file referencing
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Configuration directory
CONFIG_DIR = BASE_DIR / "config"

# Placeholder for watchdog interval, ensure this is appropriately defined
WATCHDOG_INTERVAL_S = 10  # seconds, example value. Adjust as needed.


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
        self.current_state = SystemState.IDLE  # Initialize current_state
        # Path to user polygon config
        self.user_polygon_path = CONFIG_DIR / "user_polygon.json"
        # allow web UI to access resource manager
        self.resource_manager = self

        # Watchdog attributes
        self._watchdog_thread: Optional[threading.Thread] = None
        self._watchdog_stop_event: Optional[threading.Event] = None

        # Initialize safety status tracking variables
        self._safety_status_vars = {
            "warning_logged": False,
            "last_warning_time": 0,
            "warning_interval": 30,  # seconds, configurable
        }

        if config_path:
            self._load_config(config_path)

    def _load_config(self, filename):
        """Load a configuration file from the standard config location."""
        config_path = self.user_polygon_path.parent / filename
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading config file {filename}: {e}")
        return None

    def _initialize_sensors(self):
        """Consolidate sensor initialization logic."""
        try:
            self._resources["ina3221"] = INA3221Sensor.init_ina3221()
            logger.info("INA3221 power monitor initialized successfully")
        except Exception as e:
            logger.warning(f"Error initializing INA3221 sensor: {e}")
            self._resources["ina3221"] = None

        try:
            self._resources["tof"] = VL53L0XSensors()
            logger.info(
                "VL53L0X time-of-flight sensors initialized successfully")
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
            logger.info(
                "Blade controller initialized successfully."
            )
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
            gps_port_val = GPS_PORT if GPS_PORT is not None else "/dev/ttyS0"
            self._resources["gps_serial"] = SerialPort(
                gps_port_val, GPS_BAUDRATE
            )
            logger.info(
                f"GPS serial port initialized on {gps_port_val} "
                f"at {GPS_BAUDRATE} baud"
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
            elif hasattr(res, "_initialize"):  # Some components might use _initialize
                try:
                    res._initialize()
                except Exception as e:
                    logger.error(f"Error _initializing {name}: {e}")
                    self._resources[name] = None

        logger.info(
            "Hardware components initialized with fallbacks for any "
            "failures")

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
                model_path=str(CONFIG_DIR / "models" / "pattern_planner.json"),
            )

            try:
                self._resources["path_planner"] = PathPlanner(
                    pattern_config, learning_config, self
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
                sensor_interface = None  # Ensure it's None if init fails
                self._resources["sensor_interface"] = None

            # Initialize NavigationController
            try:
                localization = self._resources.get("localization")
                motor_driver = self._resources.get("motor_driver")
                # sensor_interface is already fetched or None
                sensor_if = self._resources.get("sensor_interface")
                if localization and motor_driver and sensor_if:
                    self._resources["navigation"] = NavigationController(
                        localization, motor_driver, sensor_if
                    )
                    logger.info(
                        "Navigation controller initialized successfully")
                else:
                    missing_items = []
                    if not localization:
                        missing_items.append("localization")
                    if not motor_driver:
                        missing_items.append("motor_driver")
                    if not sensor_if:
                        missing_items.append("sensor_interface")
                    logger.error(
                        "Cannot initialize navigation controller - "
                        f"missing dependencies: {missing_items}"
                    )
                    self._resources["navigation"] = None
            except Exception as e:
                logger.error(
                    f"Failed to initialize navigation controller: {e}")
                self._resources["navigation"] = None

            # Initialize the avoidance algorithm
            try:
                self._resources["avoidance_algorithm"] = AvoidanceAlgorithm(
                    self)
                logger.info("Avoidance algorithm initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize avoidance algorithm: {e}")
                self._resources["avoidance_algorithm"] = None

            # Initialize web interface
            try:
                self._resources["web_interface"] = WebInterface(self)
                logger.info("Web interface initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize web interface: {e}")
                self._resources["web_interface"] = None

            logger.info(
                "Software components initialized with fallbacks for any "
                "failures")
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
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            if not self.user_polygon_path.exists():
                logger.warning(
                    f"User polygon file not found at "
                    f"{self.user_polygon_path} "
                    "creating default"
                )
                with open(self.user_polygon_path, "w", encoding="utf-8") as f:
                    json.dump(
                        {
                            "boundary": [[0, 0], [10, 0], [10, 10], [0, 10]],
                            "home": [5, 5],
                        },
                        f,
                    )

            self._initialize_hardware()
            self._initialize_software()

            self._initialized = True
            logger.info(
                "All resources initialized with fallbacks for any failures")
        except Exception as e:
            logger.error(f"Failed to initialize resources: {e}", exc_info=True)
            self._initialized = False  # Ensure this is set on failure

    def init_all_resources(self) -> bool:
        """
        Initialize all resources; return True if successful,
        False otherwise.
        """
        try:
            self.initialize()
            return self._initialized  # Return the actual status
        except Exception as e:
            logger.error(
                f"ResourceManager init_all_resources failed: {e}",
                exc_info=True)
            self._initialized = False  # Ensure this is set on failure
            return False

    def cleanup_all_resources(self):
        """Clean up all initialized resources, including the watchdog."""
        logger.info("Starting cleanup of all resources...")

        # Stop watchdog thread first if it exists and is running
        if self._watchdog_thread and self._watchdog_thread.is_alive():
            if self._watchdog_stop_event:
                logger.info("Stopping watchdog thread...")
                self._watchdog_stop_event.set()
                self._watchdog_thread.join(timeout=WATCHDOG_INTERVAL_S + 2)
                if self._watchdog_thread.is_alive():
                    logger.warning("Watchdog thread did not stop in time.")
                else:
                    logger.info("Watchdog thread stopped.")
            else:
                logger.warning(
                    "Watchdog thread exists but _watchdog_stop_event is missing."
                )
        elif self._watchdog_thread:  # Check if it exists even if not alive
            logger.info("Watchdog thread was found but not alive.")

        # Cleanup other resources
        for name, res in reversed(
                list(self._resources.items())):  # Iterate in reverse
            if res is None:
                continue
            logger.debug(f"Cleaning up resource: {name}")
            try:
                if hasattr(res, "disconnect"):
                    logger.debug(f"Calling disconnect() on {name}")
                    res.disconnect()
                elif hasattr(res, "cleanup"):
                    logger.debug(f"Calling cleanup() on {name}")
                    res.cleanup()
                elif hasattr(res, "stop"):  # Common for threads/processes
                    logger.debug(f"Calling stop() on {name}")
                    res.stop()
                # Add other common cleanup methods if necessary
            except Exception as e:
                logger.error(
                    f"Error cleaning up resource '{name}': {e}",
                    exc_info=True)

        self._resources.clear()
        self._initialized = False  # Mark as not initialized after cleanup
        logger.info("All resources have been processed for cleanup.")

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
                logger.warning(
                    f"Attempted to get resource '{name}' "
                    "but resources not initialized."
                )
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
            logger.info(
                "Sensor interface not found, attempting on-demand initialization.")
            try:
                self._resources["sensor_interface"] = get_sensor_interface()
                logger.info("Sensor interface initialized on demand.")
                return self._resources["sensor_interface"]
            except Exception as e:
                logger.error(
                    f"Failed to initialize sensor interface on demand: {e}")
                return None
        return si

    def get_gps(self) -> Optional[SerialPort]:
        """Get the GPS serial port instance."""
        gps = self.get_resource("gps_serial")
        if gps is None and self._initialized:  # Try to init on demand
            logger.info(
                "GPS serial port not found, attempting on-demand initialization.")
            try:
                gps_port_val = GPS_PORT if GPS_PORT is not None else "/dev/ttyS0"
                self._resources["gps_serial"] = SerialPort(
                    gps_port_val, GPS_BAUDRATE)
                logger.info(
                    f"GPS serial port initialized on demand on {gps_port_val}"
                )
                return self._resources["gps_serial"]
            except Exception as e:
                logger.error(f"Failed to initialize GPS serial on demand: {e}")
                return None
        return gps

    def start_web_interface(self):
        """Start the web interface if available."""
        web_if = self.get_web_interface()
        if web_if:
            try:
                web_if.start()  # Assumed to be non-blocking
                logger.info("Web interface started via ResourceManager.")
            except Exception as e:
                logger.error(
                    f"Failed to start web interface via ResourceManager: {e}")
        else:
            logger.warning("Web interface not available to start.")

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
                if (isinstance(home_location, list) and len(home_location) == 2 and all(
                        isinstance(coord, (int, float)) for coord in home_location)):
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
                    f"User polygon file not found: {self.user_polygon_path}. "
                    f"Using default home: {default_home}"
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
            if path_planner and hasattr(path_planner, "get_boundary_points"):
                # Prefer getting from path_planner if it's initialized and has
                # them
                boundary = path_planner.get_boundary_points()
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
                logger.warning(
                    f"User polygon file not found: {self.user_polygon_path}. "
                    "Returning empty boundary."
                )
                return default_boundary
        except Exception as e:
            logger.error(
                f"Error reading boundary points: {e}. Returning empty boundary.")
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
                logger.error(
                    f"Error getting safety status from interface: {e}")
                default_status["status_message"] = (
                    "Error retrieving status from sensor interface."
                )
                default_status["system_error"] = True
                return default_status
        else:
            # Log a warning if the sensor interface is unavailable, but not too
            # frequently
            current_time = time.time()
            if not self._safety_status_vars["warning_logged"] or \
               (current_time - self._safety_status_vars["last_warning_time"] >
                    self._safety_status_vars["warning_interval"]):
                logger.warning(
                    "Sensor interface unavailable for safety status. "
                    "Returning default safe status."
                )
                self._safety_status_vars["warning_logged"] = True
                self._safety_status_vars["last_warning_time"] = current_time
            return default_status

    def get_status(self):
        """Get the overall system status."""
        # This can be expanded to include more detailed status information
        return {
            "state": self.current_state.value,
            "initialized": self._initialized,
            "resources_available": list(self._resources.keys())
        }

    def get_battery_status(self):
        """Get the battery status information.

        Returns:
            dict: Battery voltage, current, percentage, or None if unavailable.
        """
        ina_sensor = self.get_resource("ina3221")
        if ina_sensor and hasattr(ina_sensor, "get_battery_info"):
            try:
                return ina_sensor.get_battery_info()
            except Exception as e:
                logger.warning(
                    f"Could not retrieve battery info from INA3221: {e}")
        elif ina_sensor:  # If sensor exists but no get_battery_info
            logger.warning(
                "INA3221 sensor present but get_battery_info method is missing.")
        return {
            "voltage": None,
            "current": None,
            "power": None,
            "percentage": None,  # Placeholder
            "status": "Battery sensor unavailable or error.",
        }

    def get_gps_location(self):
        """Get the current GPS location.

        Returns:
            dict: GPS latitude, longitude, altitude, satellites, fix_quality or None.
        """
        gps_device = self.get_gps()  # Uses the on-demand init if needed
        if gps_device and hasattr(
                gps_device, "read_data"):  # Assuming read_data gives parsed output
            try:
                # GPS parsing depends heavily on SerialPort and GPS module capabilities.
                # Assume get_parsed_data if available, otherwise handle raw.
                if hasattr(gps_device, "get_parsed_data"):
                    data = gps_device.get_parsed_data()
                    if data and "latitude" in data and "longitude" in data:
                        return data
                # Fallback for raw NMEA data
                raw_data = gps_device.read_line()
                if raw_data:
                    # Robust NMEA parsing should be in a dedicated GPS class/library.
                    # This is a simplified placeholder.
                    logger.debug(f"Raw GPS data: {raw_data}")
                    if "$GPGGA" in raw_data:  # Example check for GGA sentence
                        return {
                            "status": "Fix acquired (raw data)",
                            "raw": raw_data}
                return {
                    "status": "No GPS data or fix",
                    "latitude": None,
                    "longitude": None}
            except Exception as e:
                logger.warning(f"Error reading from GPS: {e}")
        return {
            "status": "GPS unavailable",
            "latitude": None,
            "longitude": None}

    def get_sensor_data(self):
        """
        Collects and returns data from all available sensors.

        Returns:
            dict: A dictionary containing data from various sensors.
                  Keys are sensor names (e.g., 'imu', 'tof', 'power'),
                  and values are their respective readings.
        """
        sensor_data = {}
        try:
            # IMU Data
            imu = self.get_resource("imu")
            if imu:
                try:
                    # Reformatting to fix line length
                    heading = imu.get_heading() if hasattr(imu, "get_heading") else 0.0
                    roll = imu.get_roll() if hasattr(imu, "get_roll") else 0.0
                    pitch = imu.get_pitch() if hasattr(imu, "get_pitch") else 0.0
                    sensor_data["imu"] = {
                        "heading": heading,
                        "roll": roll,
                        "pitch": pitch,
                        "acceleration": (
                            imu.get_acceleration()
                            if hasattr(imu, "get_acceleration") else [0, 0, 0]
                        ),
                        "gyroscope": (
                            imu.get_gyroscope()
                            if hasattr(imu, "get_gyroscope") else [0, 0, 0]
                        ),
                        "quaternion": (
                            imu.get_quaternion()
                            if hasattr(imu, "get_quaternion") else [1, 0, 0, 0]
                        ),
                        "temperature": (
                            imu.get_temperature()
                            if hasattr(imu, "get_temperature") else 0.0
                        ),
                    }
                except Exception as e:
                    logger.warning(f"Failed to get IMU data: {e}")
                    sensor_data["imu"] = {"error": str(e)}

            # Time-of-Flight (ToF) Data
            tof_sensors = self.get_resource("tof")
            if tof_sensors and hasattr(tof_sensors, 'get_distances'):
                try:
                    # Use get_distances()
                    sensor_data["tof"] = tof_sensors.get_distances()
                except Exception as e:
                    logger.warning(f"Failed to get ToF data: {e}")
                    sensor_data["tof"] = {"error": str(e)}
            elif tof_sensors:
                logger.warning(
                    "ToF sensors object present but 'get_distances' method missing."
                )
                sensor_data["tof"] = {"error": "get_distances method missing"}

            # Power Monitor (INA3221) Data
            power_monitor = self.get_resource("ina3221")
            if power_monitor:
                try:
                    # Assuming get_battery_info provides a dict
                    battery_info = self.get_battery_status()
                    # Use the structured battery info
                    sensor_data["power"] = battery_info
                except Exception as e:
                    logger.warning(f"Failed to get power monitor data: {e}")
                    sensor_data["power"] = {"error": str(e)}

            # GPS Data
            gps_data = self.get_gps_location()  # Already handles errors internally
            sensor_data["gps"] = gps_data

            # GPIO Status (Example - if relevant)
            gpio_manager = self.get_resource("gpio")
            if gpio_manager and hasattr(gpio_manager, "get_all_input_states"):
                try:
                    sensor_data["gpio_inputs"] = gpio_manager.get_all_input_states()
                except Exception as e:
                    logger.warning(f"Failed to get GPIO input states: {e}")
                    sensor_data["gpio_inputs"] = {"error": str(e)}

            # Blade Controller Status
            blade_controller = self.get_resource("blade")
            # Use get_state()
            if blade_controller and hasattr(blade_controller, "get_state"):
                try:
                    sensor_data["blade_status"] = blade_controller.get_state()
                except Exception as e:
                    logger.warning(f"Failed to get blade status: {e}")
                    sensor_data["blade_status"] = {"error": str(e)}
            elif blade_controller:
                logger.warning(
                    "Blade controller object present but 'get_state' method missing."
                )
                sensor_data["blade_status"] = {
                    "status": "get_state method missing"}

            # Motor Driver Status (Example)
            motor_driver = self.get_resource("motor_driver")
            if motor_driver and hasattr(motor_driver, "get_status"):
                try:
                    sensor_data["motor_driver_status"] = motor_driver.get_status()
                except Exception as e:
                    logger.warning(f"Failed to get motor driver status: {e}")
                    sensor_data["motor_driver_status"] = {"error": str(e)}
            elif motor_driver:
                sensor_data["motor_driver_status"] = {
                    "status": "get_status method missing"}

            # Camera Status
            camera = self.get_resource("camera")
            # Use is_operational()
            if camera and hasattr(camera, "is_operational"):
                try:
                    sensor_data["camera_status"] = {
                        "operational": camera.is_operational()
                    }
                except Exception as e:
                    logger.warning(f"Failed to get camera status: {e}")
                    sensor_data["camera_status"] = {"error": str(e)}
            elif camera:
                logger.warning(
                    "Camera object present but 'is_operational' method missing."
                )
                sensor_data["camera_status"] = {
                    "status": "is_operational method missing"}

        except Exception as e:
            logger.error(
                f"General error collecting sensor data: {e}",
                exc_info=True)
            sensor_data["collection_error"] = str(e)

        return sensor_data

    def get_avoidance_algorithm(self) -> Optional[AvoidanceAlgorithm]:
        """Get the avoidance algorithm instance."""
        aa = self.get_resource("avoidance_algorithm")
        if aa is None and self._initialized:
            logger.info(
                "Avoidance algorithm not found, attempting on-demand initialization.")
            try:
                self._resources["avoidance_algorithm"] = AvoidanceAlgorithm(
                    self)
                logger.info("Avoidance algorithm initialized on demand.")
                return self._resources["avoidance_algorithm"]
            except Exception as e:
                logger.error(
                    f"Failed to initialize avoidance algorithm on demand: {e}")
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
            name="SystemWatchdogThread"
        )
        self._watchdog_thread.start()
        logger.info("System watchdog thread started.")

    def start(self):
        """Start the main controller operations (placeholder)."""
        logger.info(
            "Main controller 'start' method called (currently a placeholder).")
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
                nav_controller.enable_manual_control()
                # Consider a dedicated MANUAL_CONTROL state
                self.current_state = SystemState.IDLE
                logger.info("Manual control enabled.")
                return True
            except Exception as e:
                logger.error(f"Failed to enable manual control: {e}")
                return False
        else:
            logger.warning(
                "Nav controller unavailable or no manual control support."
            )
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
                logger.warning(
                    "Motor driver present but 'stop_motors' method missing.")
            else:
                logger.warning("Motor driver not available to stop motors.")
                success = False

            # Stop blades
            blade_controller = self.get_resource("blade")
            if blade_controller and hasattr(blade_controller, "stop_blade"):
                blade_controller.stop_blade()
                logger.info("Blades stopped.")
            elif blade_controller:
                logger.warning(
                    "Blade controller present but 'stop_blade' method missing.")
            else:
                logger.warning(
                    "Blade controller not available to stop blades.")
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
        if gps_info and gps_info.get(
                "latitude") is not None and gps_info.get("longitude") is not None:
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
            if isinstance(
                    location,
                    dict) and "lat" in location and "lng" in location:
                normalized_location = [location["lat"], location["lng"]]
            elif isinstance(location, (list, tuple)) and len(location) == 2:
                # Ensure it's a list for JSON
                normalized_location = list(location)
            else:
                logger.error(
                    f"Invalid location format for set_home_location: {location}")
                return False

            # Load existing data or create new if file doesn't exist
            data = {}
            if self.user_polygon_path.exists():
                try:
                    with open(self.user_polygon_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except json.JSONDecodeError:
                    logger.warning(
                        f"Error decoding JSON from {self.user_polygon_path}. "
                        "Will overwrite with new data."
                    )
                except Exception as e:
                    logger.warning(
                        f"Error reading config file {self.user_polygon_path}, "
                        f"will create/overwrite: {e}"
                    )
            else:
                logger.info(
                    f"Config file "
                    f"{self.user_polygon_path} not found. Creating new.")

            # Update home location
            data["home"] = normalized_location

            # Save to configuration file
            try:
                with open(self.user_polygon_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)  # Add indent for readability
                logger.info(
                    f"Home location saved to {self.user_polygon_path}"
                    f": {normalized_location}"
                )
                return True
            except Exception as e:
                logger.error(
                    f"Failed to save home location to "
                    f"{self.user_polygon_path}: {e}")
                return False
        except Exception as e:
            logger.error(f"Error setting home location: {e}", exc_info=True)
            return False


def main():
    """
    Main entry point for the autonomous mower application.

    This function:
    1. Initializes logging.
    2. Sets up signal handlers for graceful shutdown (SIGTERM, SIGINT).
    3. Initializes the ResourceManager.
    4. Starts the watchdog thread.
    5. Starts the web interface.
    6. Enters a main loop, waiting for a shutdown signal.
    7. Cleans up resources on exit.
    """
    LoggerConfigInfo.setup_logging()
    logger.info("Initializing autonomous mower system...")

    shutdown_flag = threading.Event()
    resource_manager = None  # Initialize to None for robust finally block
    exit_code = 0

    def signal_handler(signum, frame):
        logger.info(
            f"Signal {signal.Signals(signum).name} received. "
            "Initiating graceful shutdown..."
        )
        shutdown_flag.set()

    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        resource_manager = ResourceManager()
        if not resource_manager.init_all_resources():
            logger.error(
                "Failed to initialize critical resources. Exiting application."
            )
            exit_code = 1
            # No need to call sys.exit here; finally block handles cleanup.
            # Setting shutdown_flag ensures the loop (if it were to run)
            # terminates.
            shutdown_flag.set()
        else:
            logger.info("All resources initialized successfully.")
            resource_manager._start_watchdog()  # Start watchdog after successful init
            resource_manager.start_web_interface()  # Start web UI

            logger.info(
                "Main controller running. Waiting for shutdown signal."
            )
            while not shutdown_flag.is_set():
                # Main operational logic would go here or be managed by
                # other threads started by ResourceManager or a dedicated
                # MainController class (if it existed separately).
                # This loop keeps the main thread alive for signals.
                time.sleep(0.5)  # Check flag periodically

            logger.info(
                "Shutdown signal received or init failed, exiting main loop.")

    except SystemExit as e:
        # This might be raised if sys.exit() is called directly somewhere
        # unexpected.
        logger.info(f"SystemExit caught with code {e.code}.")
        exit_code = e.code if isinstance(e.code, int) else 1
    except Exception as e:
        logger.error(f"Unhandled exception in main: {e}", exc_info=True)
        exit_code = 1  # Indicate an error occurred
    finally:
        logger.info("Main function's finally block: Cleaning up resources...")
        if resource_manager:
            resource_manager.cleanup_all_resources()
        else:
            logger.info(
                "ResourceManager was not instantiated, no cleanup needed from it.")
        logger.info(
            f"Shutdown sequence complete. Exiting with code {exit_code}.")
        # Ensure the process terminates with the correct code,
        # especially when run directly as a script.
        if __name__ == "__main__":
            sys.exit(exit_code)
    return exit_code


if __name__ == "__main__":
    main()
