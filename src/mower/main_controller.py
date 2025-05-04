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
from dotenv import load_dotenv

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
from mower.navigation.navigation import NavigationController
from mower.obstacle_detection.avoidance_algorithm import AvoidanceAlgorithm
from mower.obstacle_detection.obstacle_detector import ObstacleDetector
from mower.ui.web_ui import WebInterface
from mower.utilities.logger_config import LoggerConfigInfo
from mower.config_management.config_manager import get_config

# Load environment variables
load_dotenv()

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
        self.current_state = SystemState.IDLE  # Initialize current_state
        # Path to user polygon config
        self.user_polygon_path = CONFIG_DIR / "user_polygon.json"
        # Path to home location config
        self.home_location_path = CONFIG_DIR / "home_location.json"
        # allow web UI to access resource manager
        self.resource_manager = self

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
                with open(config_path, "r") as f:
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
            min_pwm = float(os.getenv("BLADE_MIN_PWM", "0.0"))
            max_pwm = float(os.getenv("BLADE_MAX_PWM", "1.0"))
            self._resources["blade"] = BladeController(min_pwm=min_pwm, max_pwm=max_pwm)
            logger.info(
                "Blade controller initialized successfully with calibration values."
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
            self._resources["gps_serial"] = SerialPort(
                GPS_PORT if GPS_PORT is not None else "COM1", GPS_BAUDRATE
            )
            logger.info(
                f"GPS serial port initialized on {GPS_PORT} at " f"{GPS_BAUDRATE} baud"
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
            "Hardware components initialized with fallbacks for any " "failures"
        )

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
                    logger.info("Navigation controller initialized successfully")
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
                logger.error(f"Failed to initialize navigation controller: {e}")
                self._resources["navigation"] = None

            # Initialize the avoidance algorithm
            try:
                # Initialize with resource manager for dependency resolution
                self._resources["avoidance_algorithm"] = AvoidanceAlgorithm(self)
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
                "Software components initialized with fallbacks for any " "failures"
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
                    f"User polygon file not found at "
                    f"{self.user_polygon_path} "
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
            logger.info("All resources initialized with fallbacks for any failures")
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
                logger.error(f"Failed to initialize sensor interface on demand: {e}")
                return None
        return self._resources.get("sensor_interface")

    def get_gps(self) -> Optional[SerialPort]:
        """Get the GPS serial port instance."""
        if "gps_serial" not in self._resources or self._resources["gps_serial"] is None:
            try:
                from mower.hardware.serial_port import (
                    SerialPort,
                    GPS_PORT,
                    GPS_BAUDRATE,
                )

                self._resources["gps_serial"] = SerialPort(
                    GPS_PORT if GPS_PORT is not None else "COM1", GPS_BAUDRATE
                )
                logger.info(f"GPS serial port initialized on demand on {GPS_PORT}")
            except Exception as e:
                logger.error(f"Failed to initialize GPS serial port on demand: {e}")
                return None
        return self._resources.get("gps_serial")

    def get_navigation_controller(self) -> Optional[NavigationController]:
        """Return navigation controller instance."""
        return self._resources.get("navigation")

    def start_web_interface(self):
        """Start the web interface."""
        web = self._resources.get("web_interface")
        if web:
            web.start()
        else:
            logger.warning("Web interface resource not available")

    def get_home_location(self):
        """
        Get the currently configured home location.

        Returns:
            tuple or list: The home location as [lat, lng] coordinates,
                 or [0.0, 0.0] if not configured
        """
        try:
            if self.home_location_path.exists():
                with open(self.home_location_path, "r") as f:
                    data = json.load(f)
                    return data.get("location", [0.0, 0.0])
            else:
                logger.warning(
                    f"Home location file not found: {self.home_location_path}"
                )
                return [0.0, 0.0]
        except Exception as e:
            logger.error(f"Error loading home location: {e}")
            return [0.0, 0.0]

    def set_home_location(self, location):
        """
        Set and save the home location.

        Args:
            location: The location coordinates as [lat, lng] array or
                {"lat": lat, "lng": lng} dict

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Process the input data which might be in different formats
            if isinstance(location, dict):
                lat = float(location.get("lat", 0.0))
                lng = float(location.get("lng", 0.0))
                coords = [lat, lng]
            elif isinstance(location, (list, tuple)) and len(location) >= 2:
                coords = [float(location[0]), float(location[1])]
            else:
                logger.error(f"Invalid location format: {location}")
                return False

            # Save the location to the config file
            with open(self.home_location_path, "w") as f:
                json.dump({"location": coords}, f, indent=2)

            logger.info(f"Home location saved: {coords}")
            return True
        except Exception as e:
            logger.error(f"Error saving home location: {e}")
            return False

    def get_safety_status(self):
        """Retrieve safety status from the sensor interface.

        Returns:
            dict: Safety status information, with fallbacks when unavailable
        """
        # Use the class-level variable we initialized in __init__
        vars = self._safety_status_vars

        try:
            # Try to get safety status from the sensor interface
            sensor_interface = self.get_sensor_interface()
            if sensor_interface and hasattr(sensor_interface, "get_safety_status"):
                # Reset warning flag if we successfully get data
                vars["warning_logged"] = False
                return sensor_interface.get_safety_status()

            # Try to get safety status directly from the IMU if available
            imu = self.get_imu_sensor()
            if imu and hasattr(imu, "get_safety_status"):
                # Reset warning flag if we successfully get data
                vars["warning_logged"] = False
                return imu.get_safety_status()

            # Check if it's time to log a warning
            current_time = time.time()
            should_log = (
                not vars["warning_logged"]
                or current_time - vars["last_warning_time"] > vars["warning_interval"]
            )

            if should_log:
                logger.warning(
                    "Safety status not available from sensor interface or IMU."
                )
                vars["warning_logged"] = True
                vars["last_warning_time"] = current_time

                # Add UI notification about limited safety monitoring
                try:
                    web_ui = self.get_web_interface()
                    if web_ui and hasattr(web_ui, "send_alert"):
                        web_ui.send_alert(
                            "Limited safety monitoring available", "warning"
                        )
                except Exception as e:
                    logger.debug(f"Failed to send safety status alert: {e}")

            # Return a structured safety status even without hardware
            return {
                "is_safe": True,  # Assume safe by default
                "tilt_ok": True,
                "impact_detected": False,
                "acceleration_ok": True,
                "hardware_available": False,  # Flag showing hardware status
                "messages": [],
            }
        except Exception as e:
            logger.error(f"Error getting safety status: {e}")
            # Return safe defaults
            return {
                "is_safe": True,  # Assume safe by default
                "tilt_ok": True,
                "impact_detected": False,
                "acceleration_ok": True,
                "hardware_available": False,
                "messages": ["Error getting safety data"],
            }

    def get_status(self):
        """Retrieve the current status of the mower."""
        return {
            "state": (self.current_state.name if self.current_state else "UNKNOWN"),
            "battery": self.get_battery_status(),
            "location": self.get_gps_location(),
        }

    def get_battery_status(self):
        """Get the battery status information.

        Returns:
            dict: Battery status including percentage,
            voltage, and charging state
        """
        try:
            # Try to get battery information from INA3221 sensor if available
            ina3221 = self.get_ina3221_sensor()
            if ina3221 and hasattr(ina3221, "get_bus_voltage"):
                # Assuming channel 1 is battery
                voltage = ina3221.get_bus_voltage(1)
                # Simple voltage to percentage conversion
                # (adjust based on your battery)
                # Assumes 12V battery where 10.5V is empty and 14.6V is full
                percentage = max(0, min(100, (voltage - 10.5) / 0.025))
                charging = voltage > 14.6  # Simple charging detection
                return {
                    "percentage": percentage,
                    "voltage": voltage,
                    "charging": charging,
                }

            # Fallback to a default value if hardware access fails
            return {
                "percentage": 50,  # Default to 50%
                "voltage": 12.0,  # Default voltage
                "charging": False,  # Default to not charging
            }
        except Exception as e:
            logger.error(f"Error getting battery status: {e}")
            # Return safe defaults
            return {"percentage": 50, "voltage": 12.0, "charging": False}

    def get_gps_location(self):
        """Get the current GPS location.

        Returns:
            tuple: (latitude, longitude) coordinates or (0, 0) if unavailable
        """
        try:
            # Try to get location from localization system if available
            localization = self._resources.get("localization")
            if localization and hasattr(localization, "get_location"):
                return localization.get_location()

            # Try to get directly from GPS if available
            gps = self.get_gps()
            if gps and hasattr(gps, "get_position"):
                return gps.get_position()

            # Fallback to a default value if hardware access fails
            return (0.0, 0.0)  # Default coordinates
        except Exception as e:
            logger.error(f"Error getting GPS location: {e}")
            # Return safe defaults
            return (0.0, 0.0)

    def get_sensor_data(self):
        """Get all sensor data for the web UI and diagnostics.

        Returns:
            dict: Sensor data including IMU, GPS, environment sensors, etc.
        """
        try:
            # Initialize an empty dictionary to store all sensor data
            sensor_data = {}

            # Get IMU data if available
            imu = self.get_imu_sensor()
            if imu:
                try:
                    sensor_data["imu"] = {
                        "heading": (
                            imu.get_heading() if hasattr(imu, "get_heading") else 0.0
                        ),
                        "roll": (imu.get_roll() if hasattr(imu, "get_roll") else 0.0),
                        "pitch": (
                            imu.get_pitch() if hasattr(imu, "get_pitch") else 0.0
                        ),
                        "calibration": (
                            imu.get_calibration()
                            if hasattr(imu, "get_calibration")
                            else "Unknown"
                        ),
                        "safety_status": (
                            imu.get_safety_status()
                            if hasattr(imu, "get_safety_status")
                            else {}
                        ),
                    }
                except Exception as e:
                    logger.warning(f"Error getting IMU data: {e}")
                    sensor_data["imu"] = {}
            else:
                sensor_data["imu"] = {}

            # Get GPS data
            try:
                gps = self.get_gps()
                location = self.get_gps_location()
                sensor_data["gps"] = {
                    "latitude": location[0],
                    "longitude": location[1],
                    # Simple check if we have a valid fix
                    "fix": location != (0.0, 0.0),
                    "satellites": 0,  # Default value
                    # Default value (high dilution of precision)
                    "hdop": 99.9,
                }

                # Try to get more detailed GPS data if available
                if gps and hasattr(gps, "get_info"):
                    gps_info = gps.get_info()
                    if gps_info:
                        sensor_data["gps"].update(gps_info)
            except Exception as e:
                logger.warning(f"Error getting GPS data: {e}")
                sensor_data["gps"] = {"latitude": 0.0, "longitude": 0.0, "fix": False}

            # Get motor data if available
            try:
                motor_driver = self.get_robohat_driver()
                if motor_driver and hasattr(motor_driver, "get_status"):
                    motor_status = motor_driver.get_status()
                    sensor_data["motors"] = motor_status
                else:
                    sensor_data["motors"] = {
                        "leftSpeed": 0.0,
                        "rightSpeed": 0.0,
                        "bladeSpeed": 0.0,
                    }
            except Exception as e:
                logger.warning(f"Error getting motor data: {e}")
                sensor_data["motors"] = {
                    "leftSpeed": 0.0,
                    "rightSpeed": 0.0,
                    "bladeSpeed": 0.0,
                }

            # Get environment data if available (e.g., from BME280)
            try:
                bme280 = self._resources.get("bme280")
                if bme280:
                    sensor_data["environment"] = {
                        "temperature": (
                            bme280.get_temperature()
                            if hasattr(bme280, "get_temperature")
                            else 0.0
                        ),
                        "humidity": (
                            bme280.get_humidity()
                            if hasattr(bme280, "get_humidity")
                            else 0.0
                        ),
                        "pressure": (
                            bme280.get_pressure()
                            if hasattr(bme280, "get_pressure")
                            else 0.0
                        ),
                    }
                else:
                    sensor_data["environment"] = {
                        "temperature": 0.0,
                        "humidity": 0.0,
                        "pressure": 0.0,
                    }
            except Exception as e:
                logger.warning(f"Error getting environment data: {e}")
                sensor_data["environment"] = {
                    "temperature": 0.0,
                    "humidity": 0.0,
                    "pressure": 0.0,
                }

            # Get ToF sensor data if available
            try:
                tof_sensors = self._resources.get("tof")
                if tof_sensors and hasattr(tof_sensors, "get_distances"):
                    distances = tof_sensors.get_distances()
                    sensor_data["tof"] = distances
                else:
                    sensor_data["tof"] = {"left": 0, "right": 0, "front": 0}
            except Exception as e:
                logger.warning(f"Error getting ToF sensor data: {e}")
                sensor_data["tof"] = {"left": 0, "right": 0, "front": 0}

            return sensor_data
        except Exception as e:
            logger.error(f"Error getting sensor data: {e}")
            # Return empty dict with basic structure as fallback
            return {
                "imu": {},
                "gps": {"latitude": 0.0, "longitude": 0.0, "fix": False},
                "motors": {"leftSpeed": 0.0, "rightSpeed": 0.0, "bladeSpeed": 0.0},
                "environment": {"temperature": 0.0, "humidity": 0.0, "pressure": 0.0},
                "tof": {"left": 0, "right": 0, "front": 0},
            }

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

    def get_ina3221_sensor(self) -> Optional[INA3221Sensor]:
        """Return INA3221 power monitor sensor instance."""
        return self._resources.get("ina3221")

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

                self._resources["avoidance_algorithm"] = AvoidanceAlgorithm(self)
                logger.info("Avoidance algorithm initialized on demand")
            except Exception as e:
                logger.error(f"Failed to initialize avoidance algorithm on demand: {e}")
                return None
        return self._resources.get("avoidance_algorithm")

    def _start_watchdog(self):
        """Start a watchdog thread to monitor system health."""

        def watchdog_loop():
            while self._running:
                try:
                    # Example: Check critical system metrics
                    if not self._resources["gpio"].get_pin(
                        GPIOManager.PIN_CONFIG["EMERGENCY_STOP"]
                    ):
                        logger.warning("Emergency stop button pressed!")
                        self.emergency_stop()

                    # Add more health checks as needed
                    time.sleep(1)  # Adjust interval as necessary
                except Exception as e:
                    logger.error(f"Watchdog encountered an error: {e}")

        self._watchdog_thread = threading.Thread(target=watchdog_loop, daemon=True)
        self._watchdog_thread.start()

    def start(self):
        """Start the main controller."""
        self._running = True
        self._start_watchdog()
        logger.info("Main controller started.")

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
                f"Cannot start manual control from state " f"{self.current_state}"
            )
            return False

        try:
            # Stop any active autonomous operations
            if self.current_state in [
                SystemState.MOWING,
                SystemState.DOCKING,
            ]:
                navigation_controller = self.get_navigation_controller()
                if navigation_controller:
                    navigation_controller.stop()

            self.current_state = SystemState.IDLE
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
            navigation_controller = self.get_navigation_controller()
            if navigation_controller:
                navigation_controller.stop()
            blade_controller = self.get_blade_controller()
            if blade_controller:
                blade_controller.disable()
            else:
                logger.warning("Blade controller is not available.")

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

    def emergency_stop(self):
        """Trigger an emergency stop to halt all operations."""
        logger.warning("Emergency stop activated!")
        if "gpio" in self._resources and self._resources["gpio"]:
            self._resources["gpio"].set_pin(GPIOManager.PIN_CONFIG["EMERGENCY_STOP"], 1)
        self.current_state = SystemState.EMERGENCY_STOP
        # Additional actions like stopping motors, disabling blades, etc.
        if "motor_driver" in self._resources and self._resources["motor_driver"]:
            self._resources["motor_driver"].stop()
        if "blade" in self._resources and self._resources["blade"]:
            self._resources["blade"].disable()
        logger.info("All systems halted due to emergency stop.")

    def execute_command(self, command, params=None):
        """
        Execute a command received from the web UI.

        Args:
            command: The command name (string)
            params: Command parameters (dict)

        Returns:
            dict: Command result
        """
        logger.info(f"Executing command: {command} with params: {params}")

        if command == "manual_drive":
            return self._handle_manual_drive(params)
        elif command == "blade_on":
            blade = self.get_blade_controller()
            if blade:
                blade.enable()
                return {"status": "Blade enabled"}
        elif command == "blade_off":
            blade = self.get_blade_controller()
            if blade:
                blade.disable()
                return {"status": "Blade disabled"}
        elif command == "set_blade_speed":
            blade = self.get_blade_controller()
            if blade and "speed" in params:
                speed = float(params["speed"])
                blade.set_speed(speed)
                return {"status": f"Blade speed set to {speed}"}
        elif command == "save_area":
            # Save mowing area boundary
            if params and "coordinates" in params:
                path_planner = self.get_path_planner()
                if path_planner:
                    success = path_planner.set_boundary_points(params["coordinates"])
                    if success:
                        return {"status": "Boundary area saved successfully"}
                    return {"error": "Failed to save boundary area"}
                return {"error": "Path planner not available"}
            return {"error": "Missing coordinates parameter"}
        elif command == "set_home":
            # Save home location
            if params and "location" in params:
                success = self.set_home_location(params["location"])
                if success:
                    return {"status": "Home location saved successfully"}
                return {"error": "Failed to save home location"}
            return {"error": "Missing location parameter"}
        elif command == "start_mowing":
            # Implement start mowing logic
            return {"status": "Mowing started"}
        elif command == "stop":
            # Stop all movement
            motor = self.get_robohat_driver()
            if motor:
                motor.stop()
            return {"status": "Motors stopped"}
        elif command == "return_home":
            # Implement return home logic
            return {"status": "Returning home"}
        else:
            logger.warning(f"Unknown command: {command}")
            return {"error": f"Unknown command: {command}"}

    def _handle_manual_drive(self, params):
        """
        Handle manual drive commands from the joystick.

        Args:
            params: Dict containing 'forward' and 'turn' values between -1.0 and 1.0

        Returns:
            dict: Command result
        """
        if params is None or "forward" not in params or "turn" not in params:
            return {"error": "Missing required parameters"}

        try:
            forward = float(params["forward"])
            turn = float(params["turn"])

            # Ensure values are within allowed range
            forward = max(-1.0, min(1.0, forward))
            turn = max(-1.0, min(1.0, turn))

            motor = self.get_robohat_driver()
            if motor:
                # Set the state to MANUAL when manual drive is used
                if forward != 0.0 or turn != 0.0:
                    self.current_state = SystemState.MANUAL_CONTROL

                # Convert joystick values to steering/throttle for the motor driver
                motor.run(turn, forward)
                logger.debug(f"Manual drive: forward={forward}, turn={turn}")
                return {"status": "ok", "forward": forward, "turn": turn}
            else:
                logger.error("Motor driver not available")
                return {"error": "Motor driver not available"}
        except Exception as e:
            logger.error(f"Error in manual drive: {e}")
            return {"error": f"Error in manual drive: {str(e)}"}


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
