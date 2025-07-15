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
from pathlib import Path

# Fix: Import load_dotenv for .env support
from dotenv import load_dotenv

# ADDED: Import initialize_config_manager and CONFIG_DIR from constants
from mower.config_management import initialize_config_manager
from mower.config_management.config_manager import get_config
from mower.config_management.constants import CONFIG_DIR as APP_CONFIG_DIR
from mower.hardware.async_sensor_manager import AsyncSensorInterface
#  from mower.hardware.shared_sensor_data import get_shared_sensor_manager
from mower.obstacle_detection.obstacle_detector import ObstacleDetector
from mower.hardware.serial_port import SerialPort
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
from mower.ui.web_process import launch as launch_web
from mower.utilities.process_management import validate_startup_environment, is_port_available
from mower.ui.web_ui.web_interface import WebInterface
from mower.utilities.logger_config import LoggerConfigInfo
from mower.utilities.single_instance import ensure_single_instance

# Load environment variables from .env file
load_dotenv()

# Get logger for environment variable debugging
env_logger = LoggerConfigInfo.get_logger(__name__)

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
        
    def _initialize_hardware(self):
        """Initialize hardware components.
        
        This method initializes hardware components using the hardware_registry.
        It handles GPIO, motor drivers, sensors, and other hardware interfaces.
        """
        try:
            from mower.hardware.hardware_registry import get_hardware_registry
            
            # Get hardware registry and initialize it
            hardware_registry = get_hardware_registry()
            hardware_registry.initialize()
            logger.info("Hardware registry initialized successfully")
                
            # Store hardware components in resources dict
            self._resources["hardware_registry"] = hardware_registry
            
            # Add reference to critical hardware components for easy access
            try:
                self._resources["motor_driver"] = hardware_registry.get_robohat()
                logger.info("Motor driver added to resources")
            except Exception as e:
                logger.warning(f"Failed to get motor driver: {e}")
                
            try:
                # Initialize sensor interface with enhanced error handling
                logger.info("Initializing sensor interface...")
                
                from mower.hardware.sensor_interface import get_sensor_interface
                sensor_interface = get_sensor_interface()
                
                if sensor_interface:
                    self._resources["sensor_interface"] = sensor_interface
                    logger.info("Sensor interface initialized successfully")
                else:
                    logger.warning("Sensor interface initialization returned None")
                    self._resources["sensor_interface"] = None
            except Exception as e:
                logger.error(f"Critical error in sensor interface setup: {e}")
                self._resources["sensor_interface"] = None
                
                try:
                    self._resources["camera"] = hardware_registry.get_camera()
                    logger.info("Camera added to resources")
                except Exception as e:
                    logger.warning(f"Failed to get camera: {e}")
                
                try:
                    blade_ctrl = hardware_registry.get_blade_controller()
                    self._resources["blade_controller"] = blade_ctrl
                    # Provide backward compatible key
                    self._resources["blade"] = blade_ctrl
                    logger.info("Blade controller added to resources")
                except Exception as e:
                    logger.warning(f"Failed to get blade controller: {e}")
                
                logger.info("Hardware initialization complete with fallbacks for missing components")
                return True
        except Exception as e:
            logger.error(f"Critical error during hardware initialization: {e}", exc_info=True)
            return False
            
    

    def _initialize_software(self):
        """Initialize all software components."""
        try:
            from mower.hardware.hardware_registry import get_hardware_registry
            hardware_registry = get_hardware_registry()
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

            # Initialize NavigationController
            try:
                # Get GPS latest position from GPS service
                gps_service = self._resources.get("gps_service")
                if gps_service and gps_service.gps_position:
                    from mower.navigation.gps import GpsLatestPosition
                    gps_latest_position = GpsLatestPosition(gps_position_instance=gps_service.gps_position)
                    
                    sensor_if = hardware_registry.get_sensor_interface()
                    if gps_latest_position and sensor_if:
                        # Pass self as resource_manager for safety validation
                        self._resources["navigation"] = NavigationController(
                            gps_latest_position, 
                            sensor_if, 
                            debug=False, 
                            resource_manager=self
                        )
                        logger.info("Navigation controller initialized successfully with safety validation")
                    else:
                        missing_items = []
                        if not gps_latest_position:
                            missing_items.append("gps_latest_position")
                        if not sensor_if:
                            missing_items.append("sensor_interface")
                        logger.error(f"Cannot initialize navigation controller - missing dependencies: {missing_items}")
                        self._resources["navigation"] = None
                else:
                    logger.error("Cannot initialize navigation controller - GPS service not available")
                    self._resources["navigation"] = None
            except Exception as e:
                logger.error(f"Failed to initialize navigation controller: {e}", exc_info=True)
                self._resources["navigation"] = None

            # Initialize the avoidance algorithm
            try:
                avoidance_algorithm = AvoidanceAlgorithm(self)
                self._resources["avoidance_algorithm"] = avoidance_algorithm
                logger.info("Avoidance algorithm initialized successfully")
                
                # Start the avoidance algorithm background monitoring
                try:
                    avoidance_algorithm.start()
                    logger.info("Avoidance algorithm started successfully")
                except Exception as e:
                    logger.error(f"Failed to start avoidance algorithm: {e}")
            except Exception as e:
                logger.error(f"Failed to initialize avoidance algorithm: {e}")
                self._resources["avoidance_algorithm"] = None

            # Initialize web interface placeholder - actual launch happens in start_web_interface
            self.web_interface = None # Ensure attribute exists even if init fails
            # Web process will be started by start_web_interface method

            logger.info("Software components initialized with fallbacks for any " "failures")
        except Exception as e:
            logger.error(f"Critical error in software initialization: {e}")
            # Don't re-raise here to allow partial initialization

        # Initialize GPS service (singleton) instead of creating individual instances
        try:
            from mower.services.gps_service import GpsService
            gps_port = os.environ.get("GPS_SERIAL_PORT", "/dev/ttyACM0")
            if gps_port:
                gps_service = GpsService()
                gps_service.start(serial_port=gps_port)
                self._resources["gps_service"] = gps_service
                # Also provide a reference to the GPS position reader for compatibility
                self._resources["gps_position_reader"] = gps_service.gps_position
                logger.info(f"GPS service started on port {gps_port}.")
            else:
                logger.warning("GPS serial port not available, cannot start GPS service.")
                self._resources["gps_service"] = None
                self._resources["gps_position_reader"] = None
        except Exception as e:
            logger.error(f"Failed to initialize GPS service: {e}", exc_info=True)
            self._resources["gps_service"] = None
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

            # Initialize hardware first
            self._initialize_hardware()
            logger.info("Hardware initialization complete.")

            # Mark ResourceManager as initialized here so software components can use it
            self._initialized = True
            logger.info("ResourceManager marked as initialized.")

            # Now initialize software components
            self._initialize_software()
            logger.info("Software components initialization attempt complete.")
            
            # Initialize IPC command processor for web UI communication
            try:
                from mower.ipc import get_command_processor
                self._command_processor = get_command_processor(self.execute_command)
                self._command_processor.start()
                logger.info("IPC command processor initialized and started")
            except Exception as e:
                logger.warning(f"Failed to initialize IPC command processor: {e}")
                self._command_processor = None

            # If we reached here, both hardware and software initialization phases were attempted.
            logger.info("All resource initialization phases complete with fallbacks for any individual failures.")
        except Exception as e:
            logger.error(f"Critical error during resource initialization process: {e}", exc_info=True)
            self._initialized = False  # Ensure this is set on any overriding failure

    def init_all_resources(self) -> bool:
        """
        Initialize all resources; return True if successful, False otherwise.
        """
        try:
            logger.info("Starting ResourceManager initialization...")
            self.initialize()
            
            logger.info(f"ResourceManager initialization completed successfully: {self._initialized}")
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
            
            # Stop IPC command processor
            if hasattr(self, '_command_processor') and self._command_processor:
                try:
                    logger.info("Stopping IPC command processor...")
                    self._command_processor.stop()
                except Exception as e:
                    logger.error(f"Error stopping IPC command processor: {e}")

            # Stop web process
            web_process = self._resources.get("web_process")
            if web_process and web_process.is_alive():
                try:
                    logger.info("Terminating web interface process...")
                    web_process.terminate()
                    web_process.join(timeout=15)  # Increased from 5 to 15 seconds
                    if web_process.is_alive():
                        logger.warning("Web interface process did not terminate in time, forcing kill...")
                        web_process.kill()
                        web_process.join(timeout=5)  # Give it 5 more seconds after kill
                except Exception as e:
                    logger.error(f"Error terminating web interface process: {e}", exc_info=True)

            # Cleanup other resources in reverse order of initialization if necessary
            # For now, iterating through all and calling cleanup if available
            for name, resource in reversed(list(self._resources.items())):
                if resource is None or name == "web_interface":  # Web interface already handled
                    continue

                # Special handling for AsyncSensorInterface
                if name == "sensor_interface" and hasattr(resource, 'stop'):
                    try:
                        logger.info(f"Stopping {name}...")
                        start_time = time.time()
                        resource.stop()
                        cleanup_time = time.time() - start_time
                        logger.info(f"Stop of {name} completed in {cleanup_time:.2f} seconds")
                        continue
                    except Exception as e:
                        logger.error(f"Error stopping {name}: {e}", exc_info=True)

                cleanup_method = getattr(resource, "cleanup", None)
                if cleanup_method is None:
                    cleanup_method = getattr(resource, "close", None)  # Common for file-like objects or connections
                if cleanup_method is None and name == "gpio": # GPIOManager specific
                    cleanup_method = getattr(resource, "cleanup_gpio", None)


                if callable(cleanup_method):
                    try:
                        logger.info(f"Cleaning up {name}...")
                        start_time = time.time()
                        cleanup_method()
                        cleanup_time = time.time() - start_time
                        logger.info(f"Cleanup of {name} completed in {cleanup_time:.2f} seconds")
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
                # To prevent errors when checking for resources before init,
                # return None without logging a warning.
                return None
            resource = self._resources.get(name)
            if resource is None:
                # Only log if initialization is complete, to avoid noise.
                self.logger.warning(f"Resource '{name}' not found.")
            return resource

    def get(self, name: str) -> Any:
        """
        Get a resource by name (alias for get_resource for compatibility).

        Args:
            name (str): Name of the resource to get.

        Returns:
            object: The requested resource, or None if not found or not initialized.
        """
        return self.get_resource(name)

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

    def get_camera(self) -> Optional[Any]:
        """Get the camera instance."""
        from mower.hardware.hardware_registry import get_hardware_registry # MOVED HERE
        return get_hardware_registry().get_camera()

    def get_sensor_interface(self) -> Optional[Any]:
        """Get the sensor interface instance."""
        return self._resources.get("sensor_interface")

    def get_gps(self):
        """Get the GPS instance."""
        from mower.hardware.hardware_registry import get_hardware_registry # MOVED HERE
        return get_hardware_registry().get_gps_serial()

    def get_robohat(self):
        """Get the RoboHAT motor driver instance."""
        from mower.hardware.hardware_registry import get_hardware_registry # MOVED HERE
        return get_hardware_registry().get_robohat()

    def get_ina3221(self) -> Optional[INA3221Sensor]:
        """Get the INA3221 power monitor instance."""
        from mower.hardware.hardware_registry import get_hardware_registry # MOVED HERE
        return get_hardware_registry().get_ina3221()

    def get_gps_serial(self) -> Optional[SerialPort]:
        """Get the GPS serial port instance."""
        from mower.hardware.hardware_registry import get_hardware_registry # MOVED HERE
        return get_hardware_registry().get_gps_serial()

    def execute_command(self, command: str, params: Optional[dict] = None) -> dict:
        """Execute a command from the Web UI."""
        params = params or {}
        try:
            if command == "manual_drive":
                # Extract forward and turn values from web UI
                forward = float(params.get("forward", 0))
                turn = float(params.get("turn", 0))
                logger.info(f"Manual drive command: forward={forward}, turn={turn}")
                
                # Get the RoboHAT motor driver
                motor = self.get_resource("motor_driver")
                if not motor:
                    # Fallback to direct hardware registry access
                    motor = self.get_robohat()
                    
                logger.info(f"Motor driver resource: {motor}, type: {type(motor)}")
                
                if motor and hasattr(motor, "set_pulse"):
                    # RoboHAT expects set_pulse(steering, throttle)
                    # Map our parameters: steering=turn, throttle=forward
                    logger.info(f"Calling motor.set_pulse(steering={turn}, throttle={forward})")
                    motor.set_pulse(steering=turn, throttle=forward)
                    return {"success": True, "message": f"Motors set: throttle={forward}, steering={turn}"}
                elif motor and hasattr(motor, "run"):
                    # Alternative method if set_pulse not available
                    logger.info(f"Calling motor.run(steering={turn}, throttle={forward})")
                    motor.run(steering=turn, throttle=forward)
                    return {"success": True, "message": f"Motors run: throttle={forward}, steering={turn}"}
                else:
                    error_msg = f"Motor driver unavailable or missing control methods. Motor: {motor}, has_set_pulse: {hasattr(motor, 'set_pulse') if motor else False}, has_run: {hasattr(motor, 'run') if motor else False}"
                    logger.error(error_msg)
                    return {"success": False, "error": error_msg}

            if command == "blade_on":
                blade = self.get_resource("blade_controller") or self.get_resource("blade")
                if blade and hasattr(blade, "enable"):
                    blade.enable()
                    if hasattr(blade, "set_speed"):
                        blade.set_speed(1.0)
                    return {"success": True}
                return {"success": False, "error": "Blade controller unavailable"}

            if command == "blade_off":
                blade = self.get_resource("blade_controller") or self.get_resource("blade")
                if blade and hasattr(blade, "disable"):
                    if hasattr(blade, "set_speed"):
                        blade.set_speed(0)
                    blade.disable()
                    return {"success": True}
                return {"success": False, "error": "Blade controller unavailable"}

            if command == "set_blade_speed":
                blade = self.get_resource("blade_controller") or self.get_resource("blade")
                speed = float(params.get("speed", 0))
                if blade and hasattr(blade, "set_speed"):
                    blade.set_speed(speed)
                    return {"success": True}
                return {"success": False, "error": "Blade controller unavailable"}

            if command == "emergency_stop":
                self.emergency_stop()
                return {"success": True}

            if command == "stop":
                self.stop_all_operations()
                return {"success": True}

            if command == "start_mowing":
                # TODO: Implement start_mowing logic when autonomous navigation is ready
                return {"success": False, "error": "Autonomous mowing not yet implemented"}

            if command == "return_home":
                # TODO: Implement return_home logic when autonomous navigation is ready  
                return {"success": False, "error": "Return home not yet implemented"}

            # Unknown command
            return {"success": False, "error": f"Unknown command: {command}"}
        except Exception as e:
            self.logger.error(f"Error executing command {command}: {e}")
            return {"success": False, "error": str(e)}

    def start_web_interface(self):
        """
        Initializes and starts the web interface in a separate process.
        
        Returns:
            bool: True if web interface started successfully, False otherwise
        """
        try:
            if os.getenv("DISABLE_WEB_UI", "false").lower() == "true":
                logger.info("Web UI disabled via environment variable")
                return True
                
            # Validate startup environment and clean up any port conflicts
            web_port = int(os.environ.get("WEB_UI_PORT", 5000))
            if not validate_startup_environment(web_port, "mower"):
                logger.error(f"Cannot start web interface - port {web_port} conflicts could not be resolved")
                return False
                
            logger.info("Starting web interface in separate process...")
            
            # Start web process with timeout protection
            start_time = time.time()
            # Store the web process in resources so it can be properly cleaned up
            self.web_proc = launch_web()
            self._resources["web_process"] = self.web_proc
            
            # Give web process time to start (with timeout)
            while time.time() - start_time < 30:  # 30 second timeout
                time.sleep(1)
                if hasattr(self, 'web_proc') and self.web_proc.is_alive():
                    logger.info(f"Web interface started successfully (PID: {self.web_proc.pid})")
                    return True
            
            logger.error("Web interface process failed to start within timeout")
            return False
                
        except Exception as e:
            logger.error(f"Failed to start web interface: {e}")
            return False
    
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
            blade_controller = self.get_resource("blade_controller") or self.get_resource("blade")
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

    def get_gps_location(self):
        """
        Get GPS location data from the GPS service.
        
        Returns:
            dict: GPS location data with latitude, longitude, and metadata
                  or None if GPS not available
        """
        try:
            gps_service = self._resources.get("gps_service")
            if not gps_service:
                return None
                
            # Get position from GPS service
            position = gps_service.get_position()
            if not position:
                return None
                
            # Convert from UTM to lat/lng
            try:
                import utm
                # position format: (timestamp, easting, northing, zone_number, zone_letter)
                if len(position) >= 5:
                    timestamp, easting, northing, zone_number, zone_letter = position[:5]
                    lat, lng = utm.to_latlon(easting, northing, zone_number, zone_letter)
                    
                    # Get metadata if available
                    metadata = gps_service.get_metadata() if hasattr(gps_service, 'get_metadata') else {}
                    
                    return {
                        "latitude": lat,
                        "longitude": lng,
                        "timestamp": timestamp,
                        "utm_easting": easting,
                        "utm_northing": northing,
                        "utm_zone": f"{zone_number}{zone_letter}",
                        "metadata": metadata or {}
                    }
            except Exception as e:
                logger.error(f"Error converting GPS position to lat/lng: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting GPS location: {e}")
            return None

    def get_gps_coordinates(self):
        """Get GPS coordinates, simple wrapper around get_gps_location."""
        gps_info = self.get_gps_location()
        if gps_info and gps_info.get("latitude") is not None and gps_info.get("longitude") is not None:
            return {"lat": gps_info["latitude"], "lng": gps_info["longitude"]}
        return None

    def get_sensor_data(self):
        """
        Get comprehensive sensor data including GPS for WebUI with robust error handling.
        
        Returns:
            dict: Combined sensor data from sensor interface and GPS service
        """
        try:
            logger.debug("ResourceManager:get_sensor_data - Attempting to fetch sensor data.")
            # Get base sensor data from sensor interface with timeout protection
            sensor_data_from_interface = self._get_sensor_data_with_timeout()
            
            if sensor_data_from_interface is None:
                logger.warning("ResourceManager:get_sensor_data - _get_sensor_data_with_timeout returned None. Using ResourceManager fallback.")
                # Fallback to safe sensor data structure
                sensor_data = self._get_fallback_sensor_data()
            else:
                logger.debug(f"ResourceManager:get_sensor_data - Received from interface: {sensor_data_from_interface}")
                sensor_data = sensor_data_from_interface
            
            # Add GPS data with error protection
            try:
                logger.debug("ResourceManager:get_sensor_data - Attempting to fetch GPS location.")
                gps_location = self.get_gps_location()
                if gps_location:
                    fix_quality = gps_location.get("metadata", {}).get("fix_quality", 0)
                    if fix_quality >= 1:
                        status = "valid"
                    else:
                        status = "no_fix"

                    current_gps_data = {
                        "latitude": gps_location.get("latitude"),
                        "longitude": gps_location.get("longitude"),
                        "timestamp": gps_location.get("timestamp"),
                        "utm_easting": gps_location.get("utm_easting"),
                        "utm_northing": gps_location.get("utm_northing"),
                        "utm_zone": gps_location.get("utm_zone"),
                        "satellites": gps_location.get("metadata", {}).get("satellites", 0),
                        "hdop": gps_location.get("metadata", {}).get("hdop", 99.9),
                        "fix_quality": fix_quality,
                        "status": status
                    }
                    sensor_data["gps"] = current_gps_data
                    logger.debug(f"ResourceManager:get_sensor_data - GPS data added: {current_gps_data}")
                else:
                    logger.warning("ResourceManager:get_sensor_data - get_gps_location returned None. Using GPS fallback.")
                    sensor_data["gps"] = self._get_fallback_gps_data()
            except Exception as gps_error:
                logger.warning(f"ResourceManager:get_sensor_data - GPS data collection failed: {gps_error}. Using GPS fallback.")
                sensor_data["gps"] = self._get_fallback_gps_data()

            logger.debug(f"ResourceManager:get_sensor_data - Final sensor data before writing to shared storage: {sensor_data}")
            # Write sensor data to shared storage for web process with error protection
            try:
                shared_manager = get_shared_sensor_manager()
                shared_manager.write_sensor_data(sensor_data)
                # logger.debug("Successfully wrote sensor data to shared storage") # Already in shared_manager
            except Exception as e:
                logger.warning(f"ResourceManager:get_sensor_data - Failed to write sensor data to shared storage: {e}")
            
            return sensor_data
            
        except Exception as e:
            logger.error(f"ResourceManager:get_sensor_data - Critical error in sensor data collection: {e}", exc_info=True)
            # Return fallback data structure to maintain system stability
            fallback_data_to_return = self._get_complete_fallback_data()
            logger.warning(f"ResourceManager:get_sensor_data - Returning complete fallback data due to critical error: {fallback_data_to_return}")
            return fallback_data_to_return

    def _get_sensor_data_with_timeout(self):
        """
        Get sensor data with thread-safe timeout protection without signal.alarm.
        Uses threading approach compatible with Python 3.11+
        
        Returns:
            dict: Sensor data with fallback values if sensors fail
        """
        import time
        import threading
        import queue
        
        try:
            # Get sensor interface
            sensor_interface = self.get_sensor_interface()
            if not sensor_interface:
                logger.warning("Sensor interface not available")
                return None
            
            # Use threading + queue approach instead of signal.alarm
            result_queue = queue.Queue()
            exception_queue = queue.Queue()
            
            def sensor_read_worker():
                try:
                    sensor_data = sensor_interface.get_sensor_data()
                    result_queue.put(sensor_data)
                except Exception as e:
                    exception_queue.put(e)
            
            # Create and start worker thread
            worker_thread = threading.Thread(target=sensor_read_worker)
            worker_thread.daemon = True
            worker_thread.start()
            
            # Wait for completion with timeout
            worker_thread.join(timeout=8.0)
            
            if worker_thread.is_alive():
                logger.error("Sensor data collection timed out after 8 seconds")
                return None
            
            # Check for exceptions
            if not exception_queue.empty():
                sensor_error = exception_queue.get()
                logger.error(f"Sensor data collection failed: {sensor_error}")
                return None
            
            # Get result
            if not result_queue.empty():
                sensor_data = result_queue.get()
                if sensor_data and isinstance(sensor_data, dict):
                    logger.debug(f"Sensor data collected successfully: {len(sensor_data)} data types")
                    return sensor_data
                else:
                    logger.warning("Invalid sensor data received")
                    return None
            else:
                logger.warning("No sensor data received")
                return None
                
        except Exception as e:
            logger.error(f"Critical error in sensor data collection: {e}")
            return {
                "environment": {"temperature": "N/A", "humidity": "N/A", "pressure": "N/A"},
                "imu": {"heading": "N/A", "roll": "N/A", "pitch": "N/A", "calibration": "N/A"}, 
                "power": {"voltage": "N/A", "current": "N/A", "power": "N/A", "percentage": "N/A"},
                "tof": {"left": -1, "right": -1, "working": False},
                "timestamp": time.time(),
                "status": "critical_error_fallback"
            }

    def _get_fallback_sensor_data(self):
        """
        Get fallback sensor data when primary collection fails.
        
        Returns:
            dict: Safe fallback sensor data structure
        """
        logger.info("Using fallback sensor data due to collection failure")
        return {
            "environment": {
                "temperature": "N/A",
                "humidity": "N/A", 
                "pressure": "N/A"
            },
            "imu": {
                "heading": "N/A",
                "roll": "N/A",
                "pitch": "N/A",
                "acceleration": {"x": "N/A", "y": "N/A", "z": "N/A"},
                "gyroscope": {"x": "N/A", "y": "N/A", "z": "N/A"},
                "magnetometer": {"x": "N/A", "y": "N/A", "z": "N/A"},
                "calibration": "N/A",
                "safety_status": {"is_safe": False, "status": "sensor_unavailable"}
            },
            "power": {
                "voltage": "N/A",
                "current": "N/A",
                "power": "N/A",
                "percentage": "N/A",
                "solar_voltage": "N/A",
                "solar_current": "N/A",
                "solar_power": "N/A"
            },
            "tof": {
                "left": "N/A",
                "right": "N/A",
                "working": False
            }
        }

    def _get_fallback_gps_data(self):
        """
        Get fallback GPS data structure.
        
        Returns:
            dict: Safe fallback GPS data
        """
        return {
            "latitude": None,
            "longitude": None,
            "timestamp": None,
            "utm_easting": None,
            "utm_northing": None,
            "utm_zone": None,
            "satellites": 0,
            "hdop": 99.9,
            "fix_quality": 0,
            "status": "no_fix"
        }

    def _get_complete_fallback_data(self):
        """
        Get complete fallback data structure for critical errors.
        
        Returns:
            dict: Complete safe fallback data
        """
        fallback_data = self._get_fallback_sensor_data()
        fallback_data["gps"] = self._get_fallback_gps_data()
        fallback_data["error"] = "Sensor data collection failed - using fallback data"
        return fallback_data

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
        """Initialize all resources (legacy method, use initialize() instead)."""
        logger.warning("initialize_resources() is deprecated, use initialize() instead")
        return self.initialize()

    def get_obstacle_detector(self) -> Optional[ObstacleDetector]:
        return self.get_resource("obstacle_detector")

    def _start_watchdog(self):
        """Start the watchdog timer thread."""
        if self._watchdog_thread and self._watchdog_thread.is_alive():
            logger.warning("Watchdog thread already running")
            return
            
        self._watchdog_stop_event = threading.Event()
        self._watchdog_thread = threading.Thread(
            target=self._watchdog_task,
            daemon=True  # Make it a daemon thread so it doesn't block program exit
        )
        self._watchdog_thread.start()
        logger.info(f"Watchdog timer started with interval {WATCHDOG_INTERVAL_S}s")
    
    def _stop_watchdog(self):
        """Stop the watchdog timer thread."""
        if not self._watchdog_thread or not self._watchdog_thread.is_alive():
            logger.debug("No watchdog thread to stop")
            return
            
        logger.info("Stopping watchdog thread...")
        self._watchdog_stop_event.set()
        self._watchdog_thread.join(timeout=5)
        if self._watchdog_thread.is_alive():
            logger.warning("Watchdog thread did not stop in time")
        else:
            logger.info("Watchdog thread stopped successfully")
    
    def _watchdog_task(self):
        """Watchdog task that runs in a separate thread."""
        logger.info("Watchdog task started")
        while not self._watchdog_stop_event.is_set():
            time.sleep(WATCHDOG_INTERVAL_S)
            if not self._watchdog_stop_event.is_set():  # Check again after sleeping
                logger.debug("Watchdog check...")
                try:
                    # Perform any periodic checks here
                    pass
                except Exception as e:
                    logger.error(f"Error in watchdog task: {e}")
        logger.info("Watchdog task exiting")
    
    def start_web_only_mode(self):
        """Starts only the web interface for safe mode."""
        self.logger.info("Entering SAFE-MODE; starting web interface only.")
        self.start_web_interface()
        # Keep the main thread alive
        while not self._watchdog_stop_event.is_set():
            time.sleep(1)


def main():
    """
    Main function to initialize and run the autonomous mower application.
    """
    logger.info("Starting Autonomous Mower Application...")
    
    # CRITICAL: Ensure only one instance runs to prevent hardware resource conflicts
    logger.info("Checking for existing mower instances...")
    force_cleanup = '--force-cleanup' in sys.argv
    if not ensure_single_instance(force_cleanup=force_cleanup):
        logger.error("Another mower instance is already running. Exiting to prevent hardware conflicts.")
        logger.error("Use --force-cleanup argument to forcefully terminate existing instances.")
        sys.exit(1)
    
    # Debug environment variable loading
    logger.debug(f"USE_SIMULATION env var: {os.getenv('USE_SIMULATION', 'not set')}")
    logger.debug(f"LOG_LEVEL env var: {os.getenv('LOG_LEVEL', 'not set')}")
    logger.debug(f"GPS_SERIAL_PORT env var: {os.getenv('GPS_SERIAL_PORT', 'not set')}")
    
    # Check if .env file exists
    env_file_path = Path(".env")
    logger.debug(f".env file exists: {env_file_path.exists()}")
    if env_file_path.exists():
        logger.debug(f".env file path: {env_file_path.absolute()}")

    # Global stop event for all threads
    stop_event = threading.Event()
    resource_manager = None  # Ensure resource_manager is defined in this scope

    def signal_handler(signum, frame):
        logger.info(f"Signal {signum} received. Initiating shutdown...")
        start_time = time.time()
        stop_event.set()
        if resource_manager:
            logger.info("Cleaning up resources...")
            resource_manager.cleanup_all_resources()
            cleanup_time = time.time() - start_time
            logger.info(f"Resources cleaned up in {cleanup_time:.2f} seconds.")
        else:
            logger.info("No resource manager to clean up.")
        logger.info("Exiting application.")
        sys.exit(0)

    # Register signal handlers for SIGINT (Ctrl+C) and SIGTERM
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        resource_manager = ResourceManager(config_path=str(MAIN_CONFIG_FILE))
        init_ok = resource_manager.init_all_resources()

        # Check for truly critical resources (motor driver, safety)
        # Navigation is NOT critical for sensor data collection
        nav = resource_manager.get_navigation()
        motor = resource_manager.get_robohat() if hasattr(resource_manager, 'get_robohat') else None
        safety = resource_manager.get_sensor_interface()

        if not (init_ok and motor and safety):
            logger.error("Failed to initialize one or more critical resources (navigation, motor, safety).")
            logger.error(f"Initialization status: init_ok={init_ok}, motor={type(motor) if motor else None}, safety={type(safety) if safety else None}")
            
            # Check if safe mode is explicitly allowed
            safe_mode_allowed = os.getenv("SAFE_MODE_ALLOWED", "false").lower() in ("true", "1", "yes")
            
            # Auto-enable safe mode for hardware timeout issues to prevent service hanging
            auto_safe_mode = not init_ok and not safe_mode_allowed
            if auto_safe_mode:
                logger.warning("AUTO-ENABLING SAFE MODE: Hardware initialization failed/timed out")
                logger.warning("This prevents the service from hanging. Set SAFE_MODE_ALLOWED=true to suppress this message.")
                safe_mode_allowed = True
            
            if safe_mode_allowed:
                mode_reason = "explicitly enabled" if not auto_safe_mode else "auto-enabled due to hardware timeout"
                logger.warning(f"SAFE_MODE_ALLOWED is {mode_reason}. Starting web interface only.")
                try:
                    logger.info("MAIN: Attempting to start the web interface in safe mode...")
                    if resource_manager.start_web_interface():
                         logger.info("Web interface process started in safe mode.")
                         # Keep the main thread alive for the web server
                         while not stop_event.is_set():
                            time.sleep(1)
                    else:
                        logger.error("Failed to start web interface in safe mode.")
                except Exception as e:
                    logger.error(f"MAIN: Failed to start web interface in safe mode: {e}", exc_info=True)
                
                # Clean exit on signal even in safe mode
                if resource_manager:
                    resource_manager.cleanup_all_resources()
                sys.exit(1) # Exit with error code as main function failed
            else:
                logger.error("Exiting because SAFE_MODE_ALLOWED is not enabled.")
                if resource_manager:
                    resource_manager.cleanup_all_resources()
                sys.exit(1)
        # Warn if running in degraded mode (non-critical resources missing)
        if not resource_manager.get_obstacle_detection() or not resource_manager.get_path_planner():
            logger.warning("Non-critical resources missing. Running in degraded mode. WebUI will still be available.")

        # Start the web interface regardless of degraded mode
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
        if resource_manager:
            resource_manager._start_watchdog()


        logger.info("Application started. Waiting for shutdown signal...")
        
        # Main loop with periodic sensor data sharing
        # Main sensor data collection loop with enhanced error handling
        consecutive_errors = 0
        max_consecutive_errors = 10
        base_delay = 2.0  # Base delay between collections (seconds)
        
        logger.info("Starting enhanced sensor data collection loop")
        while not stop_event.is_set():
            try:
                collection_start_time = time.time()
                
                # Collect sensor data with comprehensive error handling
                if resource_manager:
                    logger.debug("Main loop: Starting sensor data collection...")
                    
                    try:
                        sensor_data = resource_manager.get_sensor_data()
                        
                        if sensor_data and "error" not in sensor_data:
                            # Successful collection - reset error counter
                            if consecutive_errors > 0:
                                logger.info(f"Sensor collection recovered after {consecutive_errors} consecutive errors")
                                consecutive_errors = 0
                            
                            collection_time = time.time() - collection_start_time
                            logger.debug(f"Sensor data collected successfully in {collection_time:.3f}s")
                            
                        else:
                            # Collection returned error data
                            consecutive_errors += 1
                            logger.warning(f"Sensor collection returned error data (consecutive: {consecutive_errors})")
                            
                    except Exception as sensor_error:
                        consecutive_errors += 1
                        logger.error(f"Sensor collection exception (consecutive: {consecutive_errors}): {sensor_error}", exc_info=True)
                        
                        # Implement exponential backoff for persistent failures
                        if consecutive_errors >= max_consecutive_errors:
                            logger.critical(f"Maximum consecutive sensor errors reached ({max_consecutive_errors}). Implementing extended backoff.")
                            stop_event.wait(timeout=30.0)  # Extended delay for critical failures
                            consecutive_errors = 0  # Reset counter after extended delay
                        
                else:
                    logger.warning("ResourceManager not available for sensor collection")
                    consecutive_errors += 1
                
                # Calculate dynamic delay based on error count
                delay = base_delay
                if consecutive_errors > 0:
                    # Exponential backoff: 2s, 4s, 8s, max 16s
                    delay = min(base_delay * (2 ** min(consecutive_errors - 1, 3)), 16.0)
                    logger.debug(f"Using extended delay of {delay}s due to {consecutive_errors} consecutive errors")
                
                # Wait for shutdown signal with dynamic timeout
                logger.debug(f"Waiting {delay}s before next sensor collection cycle")
                stop_event.wait(timeout=delay)
                
            except Exception as loop_error:
                # Catch-all for any unhandled exceptions in the main loop
                consecutive_errors += 1
                logger.critical(f"Unhandled exception in sensor collection loop (consecutive: {consecutive_errors}): {loop_error}", exc_info=True)
                
                # Prevent infinite error loops
                if consecutive_errors >= max_consecutive_errors:
                    logger.critical("Too many consecutive loop errors. Implementing emergency delay.")
                    stop_event.wait(timeout=60.0)  # Emergency delay
                    consecutive_errors = 0
                else:
                    stop_event.wait(timeout=base_delay)

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
