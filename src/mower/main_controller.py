"""
Main controller module for the autonomous mower.

This module serves as the primary entry point and consolidates functionality
from the previous mower.py and robot.py files. It provides a centralized
resource management system and coordinates the overall operation of the mower.

Architecture:
- ResourceManager: Handles initialization, access, and cleanup of all hardware and software components
- RobotController: Manages the core mowing operation logic

Usage:
    python -m mower.main_controller

Dependencies:
    Hardware modules for sensors, motors, and peripherals
    Navigation modules for GPS, localization, and path planning
    Obstacle detection modules for safety and avoidance
    UI modules for user interfaces
    Utility modules for logging and helpers

Configuration files are stored in the 'config' directory within the mower module.
"""

import os
import threading
import json
from pathlib import Path
import time
from enum import Enum

# Hardware imports
from mower.hardware.blade_controller import BladeController
from mower.hardware.bme280 import BME280Sensor
from mower.hardware.camera_instance import get_camera_instance
from mower.hardware.gpio_manager import GPIOManager
from mower.hardware.imu import BNO085Sensor
from mower.hardware.ina3221 import INA3221Sensor
from mower.hardware.robohat import RoboHATDriver
from mower.hardware.sensor_interface import get_sensor_interface
from mower.hardware.serial_port import SerialPort
from mower.hardware.tof import VL53L0XSensors

# Navigation imports
from mower.navigation.gps import (
    GpsNmeaPositions, GpsLatestPosition, GpsPosition
)
from mower.navigation.localization import Localization
from mower.navigation.path_planning import PathPlanner
from mower.navigation.navigation import NavigationController, NavigationStatus

# Obstacle Detection imports
from mower.obstacle_detection.avoidance_algorithm import AvoidanceAlgorithm
from mower.obstacle_detection.local_obstacle_detection import (
    detect_obstacle, detect_drop, stream_frame_with_overlays
)

# UI and utilities imports
from mower.ui.web_ui.app import WebInterface
from mower.utilities.logger_config import LoggerConfigInfo as LoggerConfig
from mower.utilities.text_writer import TextLogger, CsvLogger
from mower.utilities.utils import Utils

# Set up base directory for consistent file referencing
BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = BASE_DIR / "config"
# Create config directory if it doesn't exist
CONFIG_DIR.mkdir(exist_ok=True)

# Initialize logger
logging = LoggerConfig.get_logger(__name__)

# Add a RobotState enum for state machine
class RobotState(Enum):
    """
    Enum representing the possible states of the robot.
    
    These states define the overall operational mode of the robot and
    are used to coordinate the various subsystems.
    
    States:
        IDLE: Robot is powered on but not actively operating
        INITIALIZING: Robot is starting up and initializing components
        MANUAL_CONTROL: Robot is under direct user control via remote interface
        MOWING: Robot is autonomously mowing according to plan
        AVOIDING: Robot is actively avoiding an obstacle
        RETURNING_HOME: Robot is returning to home/charging location
        DOCKED: Robot is at home base/charging station
        ERROR: Robot has encountered an error that requires attention
        EMERGENCY_STOP: Robot has triggered emergency stop condition
    """
    IDLE = 0
    INITIALIZING = 1
    MANUAL_CONTROL = 2
    MOWING = 3
    AVOIDING = 4
    RETURNING_HOME = 5
    DOCKED = 6
    ERROR = 7
    EMERGENCY_STOP = 8

class ResourceManager:
    """
    Manages all hardware and software resources used by the autonomous mower.
    
    This class implements a dependency injection pattern to provide centralized
    resource management and lazy loading of components. Resources are only 
    initialized when first requested through their respective getter methods.
    
    The ResourceManager handles initialization, access, and proper cleanup of:
    - Hardware components (sensors, motors, controllers)
    - Navigation systems (GPS, path planning, localization)
    - Obstacle detection (cameras, distance sensors, avoidance logic)
    - User interfaces (web UI, mobile app connectivity)
    - Utilities (logging, data storage)
    
    Configuration files are stored in standardized locations:
    - user_polygon_path: Defines the mowing area boundaries
    - home_location_path: Defines the home/charging station location
    - mowing_schedule_path: Defines mowing schedules and patterns
    
    Troubleshooting:
    - If a component fails to initialize, check its physical connections
    - For serial port issues, verify port names in .env configuration
    - For hardware errors, check power supply and connection status
    - For software errors, check log files for specific error messages
    """
    
    def __init__(self):
        """
        Initialize the resource manager with empty references to all components.
        
        All resources start as None and are initialized on first access via getter methods.
        File paths for configuration are set up with standardized locations.
        """
        # Hardware resources
        self._blade_controller = None
        self._bme280_sensor = None
        self._camera_instance = None
        self._gpio_manager = None
        self._imu_sensor = None
        self._ina3221_sensor = None
        self._robohat_driver = None
        self._serial_port = None
        self._tof_sensors = None
        self._sensor_interface = None
        
        # Navigation resources
        self._gps_nmea_positions = None
        self._gps_latest_position = None
        self._gps_position = None
        self._localization = None
        self._path_planner = None
        self._navigation_controller = None
        
        # Obstacle Detection resources
        self._avoidance_algorithm = None
        
        # UI resources
        self._web_interface = None
        
        # Utility resources
        self._logger_config = None
        self._text_logger = None
        self._csv_logger = None
        self._utils = None
        
        # Path configurations - using standardized locations
        self.user_polygon_path = CONFIG_DIR / "user_polygon.json"
        self.home_location_path = CONFIG_DIR / "home_location.json"
        self.mowing_schedule_path = CONFIG_DIR / "mowing_schedule.json"

    # Hardware getters

    def get_blade_controller(self):
        """
        Get or initialize the blade controller for mower blades.
        
        Returns:
            BladeController: Instance for controlling mower blade motors
            
        Troubleshooting:
            - Check motor connections and power supply
            - Verify motor driver configuration
            - For PWM issues, check driver settings
        """
        if self._blade_controller is None:
            self._blade_controller = BladeController()
        return self._blade_controller

    def get_bme280_sensor(self):
        """
        Get or initialize the BME280 environmental sensor.
        
        Returns:
            BME280Sensor: Instance for reading temperature, humidity, and pressure
            
        Troubleshooting:
            - Check I2C connections and address (usually 0x76 or 0x77)
            - Verify power connections
            - For read errors, check bus speed settings
        """
        if self._bme280_sensor is None:
            self._bme280_sensor = BME280Sensor()
        return self._bme280_sensor

    def get_camera(self):
        """
        Get or initialize the camera module.
        
        Returns:
            CameraInstance: Instance for capturing images and video
            
        Troubleshooting:
            - Check camera ribbon cable connection
            - Verify camera is enabled in system settings
            - For image quality issues, check lighting conditions
        """
        if self._camera_instance is None:
            self._camera_instance = get_camera_instance()
        return self._camera_instance

    def get_gpio_manager(self):
        """
        Get or initialize the GPIO manager for direct pin control.
        
        Returns:
            GPIOManager: Instance for GPIO pin management
            
        Troubleshooting:
            - Check pin assignments for conflicts
            - Verify GPIO permissions
            - For electrical issues, check for proper pull-up/down resistors
        """
        if self._gpio_manager is None:
            self._gpio_manager = GPIOManager()
        return self._gpio_manager

    def get_imu_sensor(self):
        """
        Get or initialize the Inertial Measurement Unit (IMU) sensor.
        
        Returns:
            BNO085Sensor: Instance for orientation and motion sensing
            
        Troubleshooting:
            - Check serial or I2C connections
            - For orientation errors, run calibration
            - Verify correct UART settings in .env file
        """
        if self._imu_sensor is None:
            self._imu_sensor = BNO085Sensor()
        return self._imu_sensor

    def get_ina3221_sensor(self):
        """
        Get or initialize the INA3221 power monitor sensor.
        
        Returns:
            INA3221Sensor: Instance for monitoring voltage and current
            
        Troubleshooting:
            - Check I2C connections and address
            - Verify shunt resistor values match configuration
            - For reading errors, check bus voltage settings
        """
        if self._ina3221_sensor is None:
            self._ina3221_sensor = INA3221Sensor()
        return self._ina3221_sensor

    def get_robohat_driver(self):
        """
        Get or initialize the RoboHAT driver for motor control.
        
        Returns:
            RoboHATDriver: Instance for controlling wheel motors
            
        Troubleshooting:
            - Check serial connection to RoboHAT controller
            - Verify motor connections and power
            - For movement issues, check PWM settings
        """
        if self._robohat_driver is None:
            self._robohat_driver = RoboHATDriver()
        return self._robohat_driver

    def get_sensors(self):
        """
        Get or initialize the unified sensor interface.
        
        Returns:
            SensorInterface: Instance providing access to all sensors
            
        Troubleshooting:
            - Check individual sensor connections
            - For data fusion issues, verify sensor polling rates
        """
        if self._sensor_interface is None:
            self._sensor_interface = get_sensor_interface()
        return self._sensor_interface

    def get_serial_port(self):
        """
        Get or initialize the serial port handler.
        
        Returns:
            SerialPort: Instance for serial communications
            
        Troubleshooting:
            - Check port name in configuration
            - Verify baudrate settings
            - For Linux, ensure user has permissions to access port
        """
        if self._serial_port is None:
            self._serial_port = SerialPort()
        return self._serial_port

    def get_tof_sensors(self):
        """
        Get or initialize the Time-of-Flight distance sensors.
        
        Returns:
            VL53L0XSensors: Instance for distance measurement
            
        Troubleshooting:
            - Check I2C connections and addresses
            - For multiple sensors, verify address assignment
            - For range issues, check sensor placement
        """
        if self._tof_sensors is None:
            self._tof_sensors = VL53L0XSensors()
        return self._tof_sensors

    # Navigation getters

    def get_gps_nmea_positions(self):
        """
        Get or initialize the GPS NMEA sentence parser.
        
        Returns:
            GpsNmeaPositions: Instance for handling raw NMEA data
            
        Troubleshooting:
            - Check GPS module connections
            - Ensure antenna has clear view of sky
            - For parsing errors, check for supported NMEA sentences
        """
        if self._gps_nmea_positions is None:
            self._gps_nmea_positions = GpsNmeaPositions()
        return self._gps_nmea_positions

    def get_gps_latest_position(self):
        """
        Get or initialize the latest GPS position handler.
        
        Returns:
            GpsLatestPosition: Instance providing current position
            
        Troubleshooting:
            - If no position available, check GPS fix status
            - For RTK GPS, verify base station connection
            - Check number of satellites in view
        """
        if self._gps_latest_position is None:
            self._gps_latest_position = GpsLatestPosition(
                self.get_gps_nmea_positions())
        return self._gps_latest_position

    def get_gps_position(self):
        """
        Get or initialize the GPS position handler.
        
        Returns:
            GpsPosition: Instance for GPS positioning
            
        Troubleshooting:
            - Check serial connection to GPS module
            - Verify correct port and baudrate settings
            - For poor accuracy, check HDOP values
        """
        if self._gps_position is None:
            self._gps_position = GpsPosition()
        return self._gps_position

    def get_localization(self):
        """
        Get or initialize the localization system.
        
        Provides position tracking by fusing GPS and other sensor data.
        
        Returns:
            Localization: Instance for position tracking
            
        Troubleshooting:
            - For position drift, check IMU calibration
            - Verify GPS signal quality
            - For issues in covered areas, check sensor fusion settings
        """
        if self._localization is None:
            self._localization = Localization()
        return self._localization

    def get_path_planner(self):
        """
        Get or initialize the path planning system.
        
        Plans efficient mowing paths based on yard boundaries and obstacles.
        
        Returns:
            PathPlanner: Instance for path planning
            
        Troubleshooting:
            - Verify mowing area polygon is defined
            - Check if obstacle map is current
            - For inefficient paths, adjust planning parameters
        """
        if self._path_planner is None:
            self._path_planner = PathPlanner(self.get_localization())
        return self._path_planner

    def get_navigation_controller(self):
        """
        Get or initialize the navigation controller.
        
        Controls robot movement to follow planned paths.
        
        Returns:
            NavigationController: Instance for navigation control
            
        Troubleshooting:
            - For tracking errors, check PID controller settings
            - Verify motor responses
            - For oscillations, adjust control parameters
        """
        if self._navigation_controller is None:
            self._navigation_controller = NavigationController(
                gps_latest_position=self.get_gps_latest_position(),
                robohat_driver=self.get_robohat_driver(),
                sensor_interface=self.get_sensors())
        return self._navigation_controller

    # Obstacle Detection getters

    def get_avoidance_algorithm(self):
        """
        Get or initialize the obstacle avoidance algorithm.
        
        Detects and navigates around obstacles in the mowing path.
        
        Returns:
            AvoidanceAlgorithm: Instance for obstacle avoidance
            
        Troubleshooting:
            - For false detections, adjust sensitivity thresholds
            - Check sensor calibration
            - For avoidance issues, verify path planning settings
        """
        if self._avoidance_algorithm is None:
            self._avoidance_algorithm = AvoidanceAlgorithm(
                path_planner=self.get_path_planner(),
                motor_controller=self.get_navigation_controller(),
                sensor_interface=self.get_sensors())
        return self._avoidance_algorithm

    def get_detect_obstacle(self):
        """
        Get the obstacle detection function.
        
        Returns:
            function: Function to detect obstacles using sensors and camera
            
        Troubleshooting:
            - Check camera and sensor positioning
            - Verify object detection model is loaded
            - For misdetections, adjust detection thresholds
        """
        return detect_obstacle

    def get_detect_drop(self):
        """
        Get the drop/cliff detection function.
        
        Returns:
            function: Function to detect drops or cliffs ahead
            
        Troubleshooting:
            - Check downward-facing sensor positioning
            - For false positives, adjust detection thresholds
            - Verify sensor is clean and unobstructed
        """
        return detect_drop

    def get_stream_frame_with_overlays(self):
        """
        Get the function for streaming camera frames with detection overlays.
        
        Returns:
            function: Function for annotated video streaming
            
        Troubleshooting:
            - Check camera initialization
            - For network streaming issues, verify network settings
            - For overlay errors, check detection system
        """
        return stream_frame_with_overlays

    # UI and utilities getters

    def get_web_interface(self):
        """
        Get or initialize the web interface for control and monitoring.
        
        Returns:
            WebInterface: Instance of the web UI
            
        Troubleshooting:
            - Check network connectivity
            - Verify Flask installation
            - For UI errors, check browser compatibility
            - For connection issues, check firewall settings
        """
        if self._web_interface is None:
            self._web_interface = WebInterface(self)
        return self._web_interface

    def get_logger_config(self):
        """
        Get or initialize the logging configuration.
        
        Returns:
            LoggerConfig: Instance for logging settings
            
        Troubleshooting:
            - Check log file permissions
            - Verify log directory exists
            - For missing logs, check log levels
        """
        if self._logger_config is None:
            self._logger_config = LoggerConfig()
        return self._logger_config

    def get_text_logger(self):
        """
        Get or initialize the text logger.
        
        Returns:
            TextLogger: Instance for text-based logging
            
        Troubleshooting:
            - Check file write permissions
            - Verify storage space availability
        """
        if self._text_logger is None:
            self._text_logger = TextLogger()
        return self._text_logger

    def get_csv_logger(self):
        """
        Get or initialize the CSV data logger.
        
        Returns:
            CsvLogger: Instance for CSV data logging
            
        Troubleshooting:
            - Check file write permissions
            - Verify CSV format settings
            - For column mismatch errors, check field definitions
        """
        if self._csv_logger is None:
            self._csv_logger = CsvLogger()
        return self._csv_logger

    def get_utils(self):
        """
        Get or initialize utility functions.
        
        Returns:
            Utils: Instance with common utility functions
        """
        if self._utils is None:
            self._utils = Utils()
        return self._utils

    def init_all_resources(self):
        """
        Initialize all hardware and software resources at once.
        
        This method provides eager initialization of all components,
        ensuring all systems are operational before starting the robot.
        
        Returns:
            bool: True if initialization succeeded, False otherwise
            
        Troubleshooting:
            - Check logs for specific component failures
            - Verify hardware connections
            - For initialization sequence issues, try individual components
        """
        try:
            logging.info("Initializing all resources...")
            
            # Hardware initialization
            self.get_blade_controller()
            self.get_bme280_sensor()
            self.get_camera()
            self.get_gpio_manager()
            self.get_imu_sensor()
            self.get_ina3221_sensor()
            self.get_robohat_driver()
            self.get_sensors()
            self.get_serial_port()
            self.get_tof_sensors()
            
            # Navigation initialization
            self.get_gps_nmea_positions()
            self.get_gps_latest_position()
            self.get_gps_position()
            self.get_localization()
            self.get_path_planner()
            self.get_navigation_controller()
            
            # Obstacle Detection initialization
            self.get_avoidance_algorithm()
            
            # UI initialization
            self.get_web_interface()
            
            # Utilities initialization
            self.get_logger_config()
            self.get_text_logger()
            self.get_csv_logger()
            self.get_utils()
            
            logging.info("All resources initialized successfully.")
            return True
        except Exception as e:
            logging.error(f"Error initializing resources: {e}")
            return False

    def cleanup_all_resources(self):
        """
        Clean up all hardware and software resources.
        
        Performs a safe shutdown of all system components to prevent
        hardware damage and resource leaks. This should be called
        before program termination.
        
        Troubleshooting:
            - For components that fail to clean up, check connections
            - For hung threads, check thread management
            - For hardware shutdown issues, verify control interfaces
        """
        logging.info("Cleaning up all resources...")
        
        # Hardware cleanup - proper shutdown to prevent damage
        if self._blade_controller:
            try:
                self._blade_controller.cleanup()
            except Exception as e:
                logging.error(f"Error cleaning up blade controller: {e}")
                
        if self._bme280_sensor:
            try:
                self._bme280_sensor.cleanup()
            except Exception as e:
                logging.error(f"Error cleaning up BME280 sensor: {e}")
                
        if self._camera_instance:
            try:
                self._camera_instance.cleanup()
            except Exception as e:
                logging.error(f"Error cleaning up camera: {e}")
                
        if self._gpio_manager:
            try:
                self._gpio_manager.clean()
            except Exception as e:
                logging.error(f"Error cleaning up GPIO manager: {e}")
                
        if self._imu_sensor:
            try:
                self._imu_sensor.cleanup()
            except Exception as e:
                logging.error(f"Error cleaning up IMU sensor: {e}")
                
        if self._ina3221_sensor:
            try:
                self._ina3221_sensor.cleanup()
            except Exception as e:
                logging.error(f"Error cleaning up INA3221 sensor: {e}")
                
        if self._robohat_driver:
            try:
                self._robohat_driver.shutdown()
            except Exception as e:
                logging.error(f"Error shutting down RoboHAT driver: {e}")
                
        if self._sensor_interface:
            try:
                self._sensor_interface.shutdown()
            except Exception as e:
                logging.error(f"Error shutting down sensor interface: {e}")
                
        if self._serial_port:
            try:
                self._serial_port.stop()
            except Exception as e:
                logging.error(f"Error stopping serial port: {e}")
                
        if self._tof_sensors:
            try:
                self._tof_sensors.cleanup()
            except Exception as e:
                logging.error(f"Error cleaning up ToF sensors: {e}")
        
        # Navigation cleanup
        if self._gps_nmea_positions:
            try:
                self._gps_nmea_positions.shutdown()
            except Exception as e:
                logging.error(f"Error shutting down GPS NMEA positions: {e}")
                
        if self._gps_position:
            try:
                self._gps_position.shutdown()
            except Exception as e:
                logging.error(f"Error shutting down GPS position: {e}")
                
        if self._path_planner:
            try:
                self._path_planner.shutdown()
            except Exception as e:
                logging.error(f"Error shutting down path planner: {e}")
        
        # Obstacle detection cleanup
        if self._avoidance_algorithm:
            try:
                self._avoidance_algorithm.stop()
            except Exception as e:
                logging.error(f"Error stopping avoidance algorithm: {e}")
        
        # UI cleanup
        if self._web_interface:
            try:
                self._web_interface.shutdown()
            except Exception as e:
                logging.error(f"Error shutting down web interface: {e}")
        
        logging.info("All resources cleaned up.")

    def start_web_interface(self):
        """
        Start the web interface for remote control and monitoring.
        
        Initializes and starts the Flask-based web server that provides
        the user interface for controlling the mower, viewing sensor data,
        and setting up mowing parameters.
        
        Troubleshooting:
            - Check network connectivity and firewall settings
            - Verify port availability (default: 8080)
            - For connection issues, check network interface settings
            - For UI errors, check browser JavaScript support
        """
        try:
            interface = self.get_web_interface()
            if hasattr(interface, 'start'):
                interface.start()
                logging.info("Web interface started.")
            else:
                logging.error("Web interface has no 'start' method.")
        except Exception as e:
            logging.error(f"Error starting web interface: {e}")


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
        resource_manager: Reference to the ResourceManager for accessing components
        current_state: Current state of the robot (from RobotState enum)
        avoidance_active: Flag indicating if obstacle avoidance is currently active
        error_condition: Description of current error (if in ERROR state)
        mowing_paused: Flag indicating if mowing is temporarily paused
        home_location: Coordinates of the home/charging location
        
    Troubleshooting:
        - If robot won't start mowing, check error_condition and logs
        - If robot gets stuck in a state, check the state transition conditions
        - For navigation issues, verify the path planning and GPS signal quality
        - For unexpected stops, check sensor readings and obstacle detection
    """
    
    def __init__(self, resource_manager):
        """
        Initialize the robot controller with resource manager and default state.
        
        Args:
            resource_manager: ResourceManager instance for accessing components
        
        The controller starts in the IDLE state and needs to be explicitly
        started via run_robot().
        """
        self.resource_manager = resource_manager
        self.current_state = RobotState.IDLE
        self.avoidance_active = False
        self.error_condition = None
        self.mowing_paused = False
        self.home_location = None
        
        # Load home location from configuration
        try:
            home_config = self._load_config('home_location.json')
            if home_config and 'location' in home_config:
                self.home_location = home_config['location']
                logging.info(f"Loaded home location: {self.home_location}")
        except Exception as e:
            logging.error(f"Failed to load home location: {e}")
        
        logging.info("Robot controller initialized")
    
    def _load_config(self, filename):
        """Load a configuration file from the standard config location."""
        config_path = self.resource_manager.user_polygon_path.parent / filename
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Error loading config file {filename}: {e}")
        return None
        
    def run_robot(self):
        """
        Main entry point to start the robot operation.
        
        This method initializes all required resources, starts the web interface,
        and transitions to the IDLE state, ready to receive commands.
        
        The robot remains in operation until shutdown is requested, handling
        state transitions and commands from the web interface.
        """
        logging.info("Starting robot...")
        
        try:
            # Initialize robot in INITIALIZING state
            self.current_state = RobotState.INITIALIZING
            
            # Initialize all resources
            self.resource_manager.init_all_resources()
            
            # Initialize key components for quick access
            self.blade_controller = self.resource_manager.get_blade_controller()
            self.imu_sensor = self.resource_manager.get_imu_sensor()
            self.avoidance_algorithm = self.resource_manager.get_avoidance_algorithm()
            self.path_planner = self.resource_manager.get_path_planner()
            self.navigation_controller = self.resource_manager.get_navigation_controller()
            
            # Start the web interface
            self.resource_manager.start_web_interface()
            
            # Start primary systems
            self.avoidance_algorithm.start()
            
            # Transition to IDLE state
            self.current_state = RobotState.IDLE
            logging.info("Robot ready and in IDLE state")
            
            # Start the main control loop
            self._main_control_loop()
            
        except Exception as e:
            logging.error(f"Error in run_robot: {e}")
            self.current_state = RobotState.ERROR
            self.error_condition = str(e)
        finally:
            # Clean up resources when shutting down
            logging.info("Shutting down robot...")
            if hasattr(self, 'avoidance_algorithm'):
                self.avoidance_algorithm.stop()
            self.resource_manager.cleanup_all_resources()
    
    def _main_control_loop(self):
        """
        Main control loop that handles state transitions and monitoring.
        
        This loop continuously checks system status, handles state transitions,
        and performs appropriate actions based on the current state.
        """
        try:
            while self.current_state != RobotState.ERROR:
                # Check for emergency stop conditions (battery, temperature, etc.)
                if self._check_emergency_conditions():
                    self.current_state = RobotState.EMERGENCY_STOP
                    logging.warning("Emergency stop condition detected")
                
                # State-specific actions
                if self.current_state == RobotState.IDLE:
                    # In IDLE state, just check for commands from UI
                    time.sleep(0.5)
                
                elif self.current_state == RobotState.MOWING:
                    # Check if avoidance is active and handle it
                    avoidance_state = self.avoidance_algorithm.current_state
                    if avoidance_state != AvoidanceState.NORMAL:
                        if not self.avoidance_active:
                            logging.info("Avoidance activated, pausing mowing")
                            self.avoidance_active = True
                            self.current_state = RobotState.AVOIDING
                    
                elif self.current_state == RobotState.AVOIDING:
                    # Check if avoidance has completed
                    avoidance_state = self.avoidance_algorithm.current_state
                    if avoidance_state == AvoidanceState.NORMAL:
                        if self.avoidance_active:
                            logging.info("Avoidance completed, resuming mowing")
                            self.avoidance_active = False
                            self.current_state = RobotState.MOWING
                    # Check for recovery failures
                    elif avoidance_state == AvoidanceState.RECOVERY:
                        recovery_attempts = self.avoidance_algorithm.recovery_attempts
                        if recovery_attempts >= self.avoidance_algorithm.max_recovery_attempts:
                            logging.error("Failed to recover from obstacle after multiple attempts")
                            self.error_condition = "Failed to recover from obstacle"
                            self.current_state = RobotState.ERROR
                
                elif self.current_state == RobotState.RETURNING_HOME:
                    # Check if we've reached home
                    if self._check_at_home():
                        logging.info("Reached home location")
                        self.navigation_controller.stop()
                        self.current_state = RobotState.DOCKED
                
                elif self.current_state == RobotState.EMERGENCY_STOP:
                    # Handle emergency stop - ensure all motors are stopped
                    self.navigation_controller.stop()
                    self.blade_controller.stop_blade()
                    logging.critical("Emergency stop - all motors stopped")
                    
                    # Check if emergency condition is cleared
                    if not self._check_emergency_conditions():
                        logging.info("Emergency condition cleared")
                        self.current_state = RobotState.IDLE
                
                # Brief pause to avoid CPU spinning
                time.sleep(0.1)
        
        except Exception as e:
            logging.error(f"Error in main control loop: {e}")
            self.current_state = RobotState.ERROR
            self.error_condition = str(e)
    
    def _check_emergency_conditions(self):
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
            if battery_voltage < 10.5:  # Critical voltage for LiFePO4 batteries
                logging.warning(f"Emergency: Battery voltage critical at {battery_voltage}V")
                return True
            
            # Check for other emergency conditions like:
            # - Extreme IMU readings (tilt beyond safe limits)
            # - Motor overcurrent conditions
            # - Temperature exceeding safe limits
            
            return False
        except Exception as e:
            logging.error(f"Error checking emergency conditions: {e}")
            # Default to emergency stop on error to be safe
            return True
    
    def _check_at_home(self):
        """
        Check if the robot has reached the home location.
        
        Returns:
            bool: True if at home location, False otherwise
        """
        if not self.home_location:
            logging.warning("Home location not set, can't determine if at home")
            return False
            
        try:
            # Get current position
            gps = self.resource_manager.get_gps_latest_position()
            current_position = gps.run()
            
            if not current_position:
                logging.warning("Unable to get current position")
                return False
            
            # Calculate distance to home
            home_lat, home_lng = self.home_location
            current_lat, current_lng = current_position[1], current_position[2]
            
            # Simple Euclidean distance (for more accurate distance, use haversine formula)
            distance = ((home_lat - current_lat) ** 2 + (home_lng - current_lng) ** 2) ** 0.5
            
            # Threshold distance to consider "at home" (in coordinate units)
            # This should be converted to meters and set appropriately
            threshold = 0.0001  # approximately 10 meters
            
            return distance < threshold
        except Exception as e:
            logging.error(f"Error checking home position: {e}")
            return False
    
    def mow_yard(self):
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
        if self.current_state != RobotState.IDLE:
            logging.warning(f"Cannot start mowing from state {self.current_state}")
            return False
        
        logging.info("Starting mowing operation")
        
        try:
            # Transition to MOWING state
            self.current_state = RobotState.MOWING
            
            # Get path from planner
            mowing_path = self.path_planner.generate_mowing_path()
            if not mowing_path or len(mowing_path) == 0:
                logging.error("Failed to generate mowing path")
                self.error_condition = "Failed to generate mowing path"
                self.current_state = RobotState.ERROR
                return False
            
            logging.info(f"Generated mowing path with {len(mowing_path)} waypoints")
            
            # Start the blade motor
            self.blade_controller.start_blade()
            
            # Navigate through each waypoint
            for waypoint_idx, waypoint in enumerate(mowing_path):
                # Check if we're still in MOWING state (might have changed due to
                # obstacle avoidance or user commands)
                if self.current_state != RobotState.MOWING:
                    logging.info(f"Mowing interrupted: state changed to {self.current_state}")
                    break
                
                # Extract coordinates from waypoint
                lat, lng = waypoint['lat'], waypoint['lng']
                logging.debug(f"Navigating to waypoint {waypoint_idx+1}/{len(mowing_path)}: {lat}, {lng}")
                
                # Command navigation to waypoint
                self.navigation_controller.navigate_to_location((lat, lng))
                
                # Monitor progress to waypoint
                start_time = time.time()
                timeout = 300  # 5 minutes timeout per waypoint
                
                while time.time() - start_time < timeout:
                    # Check if state has changed (e.g., to AVOIDING)
                    if self.current_state != RobotState.MOWING:
                        logging.info(f"Navigation interrupted: state changed to {self.current_state}")
                        break
                    
                    # Check if target reached
                    nav_status = self.navigation_controller.get_status()
                    if nav_status == NavigationStatus.TARGET_REACHED:
                        logging.debug(f"Reached waypoint {waypoint_idx+1}")
                        break
                    elif nav_status == NavigationStatus.ERROR:
                        logging.error("Navigation error occurred")
                        self.error_condition = "Navigation error"
                        self.current_state = RobotState.ERROR
                        return False
                    
                    # Brief pause before checking again
                    time.sleep(0.5)
                    
                # Check for timeout
                if time.time() - start_time >= timeout:
                    logging.warning(f"Timeout reaching waypoint {waypoint_idx+1}")
                    # Continue to next waypoint instead of failing completely
            
            # Path completed successfully
            logging.info("Mowing path completed")
            
            # Stop the blade motor
            self.blade_controller.stop_blade()
            
            # Return home
            self._return_home()
            
            return True
            
        except Exception as e:
            logging.error(f"Error during mowing operation: {e}")
            self.error_condition = f"Mowing error: {str(e)}"
            self.current_state = RobotState.ERROR
            
            # Safety: ensure blade is stopped
            try:
                self.blade_controller.stop_blade()
            except:
                pass
            
            return False
    
    def _return_home(self):
        """
        Navigate back to the home/charging location.
        
        Returns:
            bool: True if successfully started returning home, False otherwise
        """
        if not self.home_location:
            logging.error("Home location not set, cannot return home")
            return False
        
        try:
            logging.info("Initiating return to home")
            self.current_state = RobotState.RETURNING_HOME
            
            # Extract home coordinates
            home_lat, home_lng = self.home_location
            
            # Command navigation to home
            self.navigation_controller.navigate_to_location((home_lat, home_lng))
            
            return True
        except Exception as e:
            logging.error(f"Error initiating return to home: {e}")
            return False
            
    def start_manual_control(self):
        """
        Switch to manual control mode.
        
        Returns:
            bool: True if successfully switched to manual mode, False otherwise
        """
        if self.current_state in [RobotState.ERROR, RobotState.EMERGENCY_STOP]:
            logging.warning(f"Cannot start manual control from state {self.current_state}")
            return False
        
        try:
            # Stop any active autonomous operations
            if self.current_state in [RobotState.MOWING, RobotState.AVOIDING, RobotState.RETURNING_HOME]:
                self.navigation_controller.stop()
            
            self.current_state = RobotState.MANUAL_CONTROL
            logging.info("Switched to manual control mode")
            return True
        except Exception as e:
            logging.error(f"Error switching to manual control: {e}")
            return False
    
    def stop_all_operations(self):
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
            if self.current_state not in [RobotState.ERROR, RobotState.EMERGENCY_STOP]:
                self.current_state = RobotState.IDLE
            
            logging.info("All operations stopped")
            return True
        except Exception as e:
            logging.error(f"Error stopping operations: {e}")
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
            logging.error("Failed to initialize resources. Exiting.")
            return
            
        # Create the robot controller
        robot_controller = RobotController(resource_manager)
        
        # Start the robot logic in a separate thread
        # Using daemon=True ensures thread terminates when main thread exits
        robot_thread = threading.Thread(
            target=robot_controller.run_robot, 
            daemon=True
        )
        robot_thread.start()
        logging.info("Robot logic thread started.")
        
        # Start the web interface for user control
        resource_manager.start_web_interface()
        logging.info("Web interface started.")
        
        # Keep the main thread running
        # This loop keeps the application alive and responsive to keyboard interrupts
        while True:
            try:
                # Sleep to avoid high CPU usage while waiting
                threading.Event().wait(1)
            except KeyboardInterrupt:
                logging.info("Keyboard interrupt received. Exiting.")
                break
                
    except Exception as e:
        logging.exception(f"An error occurred in the main function: {e}")
    finally:
        # Ensure all resources are properly cleaned up
        resource_manager.cleanup_all_resources()
        logging.info("Main controller exited.")


if __name__ == "__main__":
    main() 