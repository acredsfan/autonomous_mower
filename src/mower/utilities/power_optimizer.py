"""
Power optimization module for autonomous mower.

This module provides tools for optimizing power consumption
to extend battery life in resource-constrained environments.
"""
import os
import threading
import time
import subprocess  # Added for _set_cpu_governor
import functools  # Added for power_aware decorator
from typing import Dict, Any, List, Optional, Callable, Set  # Removed Tuple
from enum import Enum, auto

try:
    import psutil  # For CPU and battery info
except ImportError:
    psutil = None  # Gracefully handle if psutil is not installed

from mower.utilities.logger_config import LoggerConfigInfo  # Changed LoggerConfig to LoggerConfigInfo

# Initialize logger
logger = LoggerConfigInfo.get_logger(__name__)  # Changed LoggerConfig to LoggerConfigInfo


class PowerMode(Enum):
    """Power modes for the system."""

    HIGH_PERFORMANCE = auto()  # Maximum performance, no power saving
    BALANCED = auto()  # Balance between performance and power saving
    POWER_SAVING = auto()  # Aggressive power saving
    CRITICAL = auto()  # Critical battery level, maximum power saving


class PowerOptimizer:
    """
    Power optimizer for the autonomous mower system.

    This class provides methods for optimizing power consumption by:
    1. Adjusting CPU frequency and governor
    2. Managing sensor polling frequencies
    3. Controlling background processes
    4. Implementing dynamic power modes based on battery level
    5. Optimizing hardware component usage
    """

    def __init__(self, enable_monitoring: bool = True):
        """
        Initialize the power optimizer.

        Args:
            enable_monitoring: Whether to enable power monitoring
        """
        self.enable_monitoring = enable_monitoring
        self.monitoring_interval = 60  # seconds
        self.monitoring_thread: Optional[threading.Thread] = None  # Type hint for thread
        self.stop_monitoring_event = threading.Event()  # Renamed for clarity

        # Current power mode
        self.power_mode = PowerMode.BALANCED

        # Battery thresholds for power modes
        self.battery_thresholds = {
            PowerMode.HIGH_PERFORMANCE: 80,  # Above 80%
            PowerMode.BALANCED: 50,  # 50-80%
            PowerMode.POWER_SAVING: 20,  # 20-50%
            PowerMode.CRITICAL: 0,  # Below 20%
        }

        # Component power settings for each mode
        self.power_settings = {
            PowerMode.HIGH_PERFORMANCE: {
                "cpu_governor": "performance",
                "sensor_poll_interval": 0.1,  # seconds
                "camera_resolution": "high",
                "gps_update_interval": 1.0,  # seconds
                "background_processes": True,
            },
            PowerMode.BALANCED: {
                "cpu_governor": "ondemand",  # or "schedutil" on newer kernels
                "sensor_poll_interval": 0.5,  # seconds
                "camera_resolution": "medium",
                "gps_update_interval": 3.0,  # seconds
                "background_processes": True,
            },
            PowerMode.POWER_SAVING: {
                "cpu_governor": "powersave",
                "sensor_poll_interval": 1.0,  # seconds
                "camera_resolution": "low",
                "gps_update_interval": 5.0,  # seconds
                "background_processes": False,
            },
            PowerMode.CRITICAL: {
                "cpu_governor": "powersave",
                "sensor_poll_interval": 2.0,  # seconds
                "camera_resolution": "lowest",  # e.g., disable or minimal
                "gps_update_interval": 10.0,  # seconds
                "background_processes": False,
            },
        }

        # Optimized components
        self.optimized_components: Set[str] = set()

        # Power usage statistics
        self.stats: Dict[str, List[Any]] = {
            "battery_levels": [],
            "power_modes": [],
            "cpu_usage": [],
        }

        # Placeholder for actual components - in a real system, these would be registered
        self._component_registry: Dict[str, Any] = {}

        # Start monitoring if enabled
        if self.enable_monitoring:
            self.start_monitoring()

        logger.info("Power optimizer initialized")

    def register_component(self, name: str, component: Any):
        """Registers a component for power optimization."""
        self._component_registry[name] = component
        logger.info(f"Component '{name}' registered for power optimization.")
        # Immediately apply current mode settings if component is already in optimized_components
        if name in self.optimized_components:
            self._apply_component_settings(name, self.power_settings[self.power_mode])

    def start_monitoring(self):
        """Start power usage monitoring."""
        if (
            self.monitoring_thread is not None
            and self.monitoring_thread.is_alive()
        ):
            logger.warning("Monitoring thread is already running")
            return

        self.stop_monitoring_event.clear()
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop, daemon=True
        )
        self.monitoring_thread.start()
        logger.info("Power monitoring started")

    def stop_monitoring(self):  # Corrected method name from attachment
        """Stop power usage monitoring."""
        if (
            self.monitoring_thread is None
            or not self.monitoring_thread.is_alive()
        ):
            logger.warning("Monitoring thread is not running or already stopped")
            return

        self.stop_monitoring_event.set()
        self.monitoring_thread.join(timeout=5)  # Increased timeout slightly
        if self.monitoring_thread.is_alive():
            logger.warning("Monitoring thread did not stop in time.")
        else:
            logger.info("Power monitoring stopped")
        self.monitoring_thread = None

    def _monitoring_loop(self):
        """Main monitoring loop."""
        while not self.stop_monitoring_event.is_set():
            try:
                battery_level = self.get_battery_level()
                self._update_power_mode(battery_level)

                # Log statistics
                self.stats["battery_levels"].append(battery_level)
                self.stats["power_modes"].append(self.power_mode.name)
                if psutil:
                    cpu_usage = psutil.cpu_percent(interval=None)  # Non-blocking
                    self.stats["cpu_usage"].append(cpu_usage)
                    logger.debug(
                        f"Monitoring: Batt={battery_level}%, Mode={self.power_mode.name}, CPU={cpu_usage}%"
                    )
                else:
                    logger.debug(
                        f"Monitoring: Batt={battery_level}%, Mode={self.power_mode.name}, "
                        f"CPU=N/A (psutil not available)"
                    )

                # Wait for the next interval
                # Check event more frequently to allow faster shutdown
                for _ in range(self.monitoring_interval):
                    if self.stop_monitoring_event.is_set():
                        break
                    time.sleep(1)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                # Avoid rapid error logging if a persistent issue occurs
                time.sleep(self.monitoring_interval)

    def _update_power_mode(self, battery_level: float):
        """
        Update power mode based on battery level.

        Args:
            battery_level: Current battery level (0-100)
        """
        new_mode = self.power_mode  # Default to current mode

        # Determine appropriate power mode
        # Iterate in order of precedence (Critical first if thresholds overlap)
        if battery_level <= self.battery_thresholds[PowerMode.POWER_SAVING]:  # Corrected logic for critical
            new_mode = PowerMode.CRITICAL
        elif battery_level <= self.battery_thresholds[PowerMode.BALANCED]:
            new_mode = PowerMode.POWER_SAVING
        elif battery_level < self.battery_thresholds[PowerMode.HIGH_PERFORMANCE]:
            new_mode = PowerMode.BALANCED
        else:  # battery_level >= self.battery_thresholds[PowerMode.HIGH_PERFORMANCE]
            new_mode = PowerMode.HIGH_PERFORMANCE

        # If mode has changed, apply new settings
        if new_mode != self.power_mode:
            logger.info(
                (
                    f"Changing power mode from {self.power_mode.name} to"
                    f" {new_mode.name} (battery: {battery_level:.1f}%)"
                )
            )
            self.power_mode = new_mode
            self._apply_power_settings()

    def _apply_power_settings(self):
        """Apply power settings for the current power mode."""
        if self.power_mode not in self.power_settings:
            logger.error(f"Power mode {self.power_mode} not found in power_settings.")
            return
        settings = self.power_settings[self.power_mode]

        # Apply CPU governor setting
        self._set_cpu_governor(settings["cpu_governor"])

        # Apply settings to all optimized components
        for component_name in self.optimized_components:
            self._apply_component_settings(component_name, settings)

        logger.info(f"Applied power settings for {self.power_mode.name} mode")

    def _set_cpu_governor(self, governor: str):
        """
        Set CPU governor. Requires root privileges and works on Linux.

        Args:
            governor: CPU governor to set (e.g., performance, ondemand, powersave)
        """
        if os.name != "posix":
            logger.warning(f"Cannot set CPU governor: Not a POSIX system (os.name: {os.name}).")
            return
        if not psutil:
            logger.warning("Cannot set CPU governor: psutil not available.")
            return

        try:
            # Find all CPU frequency directories
            cpu_dirs = [
                d for d in os.listdir("/sys/devices/system/cpu")
                if d.startswith("cpu") and d[3:].isdigit()
            ]
            if not cpu_dirs:
                logger.warning("Could not find CPU directories for setting governor.")
                return

            for cpu_dir_name in cpu_dirs:
                governor_file = f"/sys/devices/system/cpu/{cpu_dir_name}/cpufreq/scaling_governor"
                if os.path.exists(governor_file):
                    try:
                        # This command typically requires root privileges
                        subprocess.run(
                            ["sudo", "tee", governor_file],
                            input=governor.encode(),
                            check=True,
                            capture_output=True,
                        )
                        logger.info(f"Set CPU governor for {cpu_dir_name} to {governor}")
                    except FileNotFoundError:  # tee or sudo not found
                        logger.error(
                            f"Failed to set CPU governor for {cpu_dir_name}: sudo or tee command not found. "
                            "Ensure they are in PATH."
                        )
                        break  # Stop trying if essential commands are missing
                    except subprocess.CalledProcessError as e:
                        error_msg = e.stderr.decode().strip() if e.stderr else str(e)
                        logger.error(
                            f"Error setting CPU governor for {cpu_dir_name} to {governor}: {error_msg}. "
                            "This may require root privileges or the governor may not be supported."
                        )
                        # Continue to try other CPUs if one fails
                    except Exception as e_inner:
                        logger.error(f"Unexpected error setting CPU governor for {cpu_dir_name}: {e_inner}")
                else:
                    logger.debug(f"Governor file not found for {cpu_dir_name}: {governor_file}")
        except PermissionError:
            logger.error(
                "Permission denied when trying to list CPU directories or write to governor file. "
                "Root privileges are likely required."
            )
        except Exception as e:
            logger.error(f"General error setting CPU governor: {e}", exc_info=True)

    def _apply_component_settings(
        self, component_name: str, settings: Dict[str, Any]
    ):
        """
        Apply power settings to a component.

        Args:
            component_name: Name of the component
            settings: Power settings to apply
        """
        component = self._get_component(component_name)
        if component is None:
            logger.warning(f"Component '{component_name}' not found in registry for applying settings.")
            return

        try:
            logger.debug(f"Applying settings to component '{component_name}': {settings}")
            # Apply settings based on component type and available methods
            if (
                hasattr(component, "set_poll_interval")
                and "sensor_poll_interval" in settings
            ):
                component.set_poll_interval(settings["sensor_poll_interval"])
                logger.info(f"Set poll interval for {component_name} to {settings['sensor_poll_interval']}")

            if (
                hasattr(component, "set_resolution")
                and "camera_resolution" in settings
            ):
                component.set_resolution(settings["camera_resolution"])
                logger.info(f"Set camera resolution for {component_name} to {settings['camera_resolution']}")

            if (
                hasattr(component, "set_update_interval")
                and "gps_update_interval" in settings
            ):
                component.set_update_interval(settings["gps_update_interval"])
                logger.info(f"Set GPS update interval for {component_name} to {settings['gps_update_interval']}")

            if (
                hasattr(component, "enable_background_processes")  # Assuming a method like this
                and "background_processes" in settings
            ):
                component.enable_background_processes(settings["background_processes"])
                logger.info(f"Set background processes for {component_name} to {settings['background_processes']}")

            # Add more component-specific settings here
            if hasattr(component, "apply_power_settings"):
                component.apply_power_settings(self.power_mode, settings)
                logger.info(f"Called apply_power_settings on {component_name} for mode {self.power_mode.name}")

        except Exception as e:
            logger.error(f"Error applying settings to {component_name}: {e}", exc_info=True)

    def _get_component(self, component_name: str) -> Any:
        """
        Get a component by name from the internal registry.

        Args:
            component_name: Name of the component

        Returns:
            The component or None if not found
        """
        return self._component_registry.get(component_name)

    def get_battery_level(self) -> float:
        """
        Get current battery level.

        Returns:
            Battery level (0-100). Returns 100.0 if unable to determine.
        """
        if not psutil:
            logger.warning("psutil is not available, cannot get battery level via psutil.")
        else:
            try:
                battery = psutil.sensors_battery()
                if battery and battery.percent is not None:
                    logger.debug(f"Battery level from psutil: {battery.percent}%")
                    return float(battery.percent)
                else:
                    logger.debug("psutil.sensors_battery() returned None or no percent.")
            except Exception as e:
                logger.warning(f"Could not get battery level from psutil: {e}")

        # Fallback: Try reading from sysfs (common on Linux for embedded devices)
        # This is a common path, but might vary.
        sysfs_paths = [
            "/sys/class/power_supply/BAT0/capacity",
            "/sys/class/power_supply/BAT1/capacity",
            "/sys/class/power_supply/battery/capacity",  # Generic path
        ]
        for path in sysfs_paths:
            if os.path.exists(path):
                capacity_str = ""  # Initialize capacity_str
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        capacity_str = f.read().strip()
                        capacity = float(capacity_str)
                        logger.debug(f"Battery level from sysfs ({path}): {capacity}%")
                        return capacity
                except ValueError:
                    logger.warning(f"Could not parse battery capacity from {path}: \'{capacity_str}\'")
                except Exception as e:
                    logger.warning(f"Could not read battery level from sysfs ({path}): {e}")

        logger.warning(
            "Unable to determine battery level. Assuming 100% and HIGH_PERFORMANCE mode might be stuck "
            "if not overridden."
        )
        return 100.0  # Default if no method works, to avoid immediate critical mode

    def optimize_component(self, component_name: str):
        """
        Add a component to the set of optimized components and apply current settings.
        The component must be registered first using `register_component`.

        Args:
            component_name: Name of the component (must be pre-registered)
        """
        if component_name not in self._component_registry:
            logger.error(f"Cannot optimize component '{component_name}': Not registered.")
            return

        if component_name in self.optimized_components:
            logger.warning(f"Component {component_name} is already being optimized.")
            return

        logger.info(f"Enabling power optimization for component: {component_name}")

        # Apply current power mode settings to this newly optimized component
        settings = self.power_settings.get(self.power_mode)
        if settings:
            self._apply_component_settings(component_name, settings)
        else:
            logger.error(f"Current power mode {self.power_mode} has no defined settings.")

        # Add component to optimized set
        self.optimized_components.add(component_name)

    def set_power_mode(self, mode: PowerMode):
        """
        Manually set power mode.

        Args:
            mode: Power mode to set
        """
        if not isinstance(mode, PowerMode):
            logger.error(f"Invalid power mode type: {type(mode)}. Must be a PowerMode enum member.")
            return

        if mode == self.power_mode:
            logger.info(f"Power mode is already {mode.name}.")
            return

        logger.info(f"Manually setting power mode to {mode.name}")
        self.power_mode = mode
        self._apply_power_settings()

    def get_power_mode(self) -> PowerMode:
        """
        Get current power mode.

        Returns:
            Current power mode
        """
        return self.power_mode

    def get_power_usage(self) -> Dict[str, Any]:
        """
        Get current power usage statistics.

        Returns:
            Dictionary with power usage statistics
        """
        cpu_val = "N/A"
        if psutil:
            try:
                cpu_val = psutil.cpu_percent(interval=0.1)  # Short interval for responsiveness
            except Exception as e:
                logger.warning(f"Could not get CPU percent: {e}")
                cpu_val = "Error"

        return {
            "battery_level": self.get_battery_level(),
            "power_mode": self.power_mode.name,
            "cpu_usage": cpu_val,
            "stats": self.stats.copy(),  # Return a copy to prevent external modification
        }

    def print_power_usage(self):
        """Print current power usage statistics."""
        usage = self.get_power_usage()

        logger.info("--- Power Usage Report ---")
        logger.info(f"  Battery Level: {usage['battery_level']:.1f}%")
        logger.info(f"  Current Power Mode: {usage['power_mode']}")
        logger.info(f"  Current CPU Usage: {usage['cpu_usage']}%")
        if self.stats["battery_levels"]:
            logger.info(f"  Monitored Battery Levels (last 10): {self.stats['battery_levels'][-10:]}")
            logger.info(f"  Monitored Power Modes (last 10): {self.stats['power_modes'][-10:]}")
        if self.stats["cpu_usage"]:
            logger.info(f"  Monitored CPU Usage (last 10): {self.stats['cpu_usage'][-10:]}")
        logger.info("--------------------------")

    def cleanup(self):
        """Clean up resources used by the optimizer."""
        logger.info("Cleaning up PowerOptimizer...")
        if self.enable_monitoring:
            self.stop_monitoring()  # Ensure monitoring is stopped

        # Restore default power settings (e.g., BALANCED or a system default governor)
        # Setting to BALANCED might be a good default.
        logger.info("Attempting to restore to BALANCED power mode settings.")
        # Create a temporary settings dict for BALANCED to restore CPU governor
        # This avoids changing self.power_mode if cleanup is called unexpectedly
        balanced_settings = self.power_settings.get(PowerMode.BALANCED)
        if balanced_settings and "cpu_governor" in balanced_settings:
            self._set_cpu_governor(balanced_settings["cpu_governor"])
        else:
            # Fallback to a common default if BALANCED settings are missing
            self._set_cpu_governor("ondemand")

        # Optionally, revert settings for all optimized components to their defaults
        # This would require components to have a 'restore_default_settings()' method
        for component_name in list(self.optimized_components):  # Iterate over a copy
            component = self._get_component(component_name)
            if component and hasattr(component, "restore_default_settings"):
                try:
                    component.restore_default_settings()
                    logger.info(f"Restored default settings for {component_name}")
                except Exception as e:
                    logger.error(f"Error restoring defaults for {component_name}: {e}")
            self.optimized_components.remove(component_name)

        logger.info("Power optimizer cleaned up")


# Decorator for power-aware functions
def power_aware(optimizer_instance: PowerOptimizer):  # Pass optimizer instance
    """
    Decorator factory for making functions power-aware.
    It provides the current power_mode to the wrapped function.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_mode = optimizer_instance.get_power_mode()
            logger.debug(f"Function '{func.__name__}' called in power mode: {current_mode.name}")
            # Pass power_mode as a keyword argument if the function accepts it
            # This requires the decorated function to have `power_mode=None` or similar in its signature
            if "power_mode" in func.__code__.co_varnames:
                kwargs_updated = {**kwargs, "power_mode": current_mode}
                return func(*args, **kwargs_updated)
            # Otherwise, call normally - the function might access the optimizer directly
            return func(*args, **kwargs)
        return wrapper
    return decorator


# Singleton instance
_power_optimizer_instance: Optional[PowerOptimizer] = None
_optimizer_lock = threading.Lock()


def get_power_optimizer(enable_monitoring: bool = True, **kwargs) -> PowerOptimizer:
    """
    Get or create the singleton power optimizer instance.

    Args:
        enable_monitoring: Whether to enable power monitoring on first creation.
        **kwargs: Additional arguments for PowerOptimizer constructor on first creation.

    Returns:
        The power optimizer instance
    """
    global _power_optimizer_instance
    if _power_optimizer_instance is None:
        with _optimizer_lock:
            if _power_optimizer_instance is None:  # Double-check locking
                _power_optimizer_instance = PowerOptimizer(
                    enable_monitoring=enable_monitoring, **kwargs
                )
    return _power_optimizer_instance


def optimize_system_power():  # Renamed for clarity
    """
    Sets up power optimization for known system components.
    Components should be registered with the optimizer.
    This function serves as an example setup.
    """
    logger.info("Configuring system-wide power optimization...")

    optimizer = get_power_optimizer()

    # Example: If you have a PathPlanner class instance
    # from mower.navigation.path_planner import PathPlanner # Assuming this exists
    # path_planner_instance = PathPlanner(...) # Get or create your instance
    # optimizer.register_component("path_planner", path_planner_instance)
    # optimizer.optimize_component("path_planner")
    # PathPlanner.generate_path = power_aware(optimizer)(PathPlanner.generate_path) # If static/classmethod

    # Example: ObstacleDetector
    # from mower.obstacle_detection.obstacle_detector import ObstacleDetector
    # obstacle_detector_instance = ObstacleDetector(...)
    # optimizer.register_component("obstacle_detector", obstacle_detector_instance)
    # optimizer.optimize_component("obstacle_detector")
    # ObstacleDetector.detect_obstacles = power_aware(optimizer)(ObstacleDetector.detect_obstacles)

    # Example: GPSManager
    # from mower.navigation.gps import GPSManager
    # gps_manager_instance = GPSManager(...)
    # optimizer.register_component("gps_manager", gps_manager_instance)
    # optimizer.optimize_component("gps_manager")
    # if hasattr(GPSManager, "update"):
    #     GPSManager.update = power_aware(optimizer)(GPSManager.update)

    # --- How to use the power_aware decorator for methods of existing instances ---
    # For instance methods, you need to be careful with `self`.
    # One way is to make the decorated method a free function that takes `self`
    # or to rebind the decorated method to the instance.

    # Example for an instance method `my_method` of `my_instance`:
    # original_method = my_instance.my_method
    # @power_aware(optimizer) # The decorator needs the optimizer instance
    # def power_aware_method_wrapper(self_obj, *args, power_mode=None, **kwargs): # Add power_mode
    #     # `self_obj` is the instance (`my_instance`)
    #     # `power_mode` is injected by the decorator
    #     logger.info(f"{self_obj.__class__.__name__}.{original_method.__name__} running in {power_mode} mode")
    #     if power_mode == PowerMode.CRITICAL and hasattr(self_obj, 'perform_critical_action'):
    #         return self_obj.perform_critical_action(*args, **kwargs)
    #     return original_method(*args, **kwargs) # Call original method bound to the instance

    # # Replace the method on the instance (or class if you want it for all instances)
    # my_instance.my_method = functools.partial(power_aware_method_wrapper, my_instance)
    # # or for class: MyClass.my_method = power_aware_method_wrapper (if wrapper handles self correctly)

    logger.info("System power optimization setup attempted (examples are commented out).")
    logger.info("Ensure components are registered and `optimize_component` is called for them.")
    logger.info("For methods to be power_aware, decorate them appropriately.")

    return optimizer


if __name__ == "__main__":
    # Configure logger for standalone testing
    LoggerConfigInfo.configure_logging()

    logger.info("Starting PowerOptimizer example...")

    # Get the optimizer (starts monitoring by default if not already started)
    optimizer_main = get_power_optimizer(enable_monitoring=True)

    # --- Example Component (mock) ---
    class MockSensor:
        def __init__(self, name):
            self.name = name
            self.poll_interval = 1.0
            self.resolution = "default"
            self.is_active = True
            logger.info(f"MockSensor {self.name} initialized.")

        def set_poll_interval(self, interval: float):
            logger.info(
                f"MockSensor {self.name}: Poll interval set to {interval}s (was {self.poll_interval}s)"
            )
            self.poll_interval = interval

        def set_resolution(self, resolution: str):
            logger.info(
                f"MockSensor {self.name}: Resolution set to {resolution} (was {self.resolution})"
            )
            self.resolution = resolution

        def perform_critical_action(self, *args, **kwargs):
            logger.warning(f"MockSensor {self.name}: Performing critical action due to power mode!")
            return "Critical action taken"

        def read_data(self, *args, power_mode: Optional[PowerMode] = None, **kwargs):  # Accepts power_mode
            logger.info(
                f"MockSensor {self.name}: Reading data. Current poll: {self.poll_interval}, "
                f"Res: {self.resolution}, PowerMode: {power_mode.name if power_mode else 'N/A'}"
            )
            if power_mode == PowerMode.CRITICAL:
                logger.warning(f"MockSensor {self.name}: In CRITICAL mode, reducing functionality.")
                return f"{self.name} data (minimal)"
            return f"{self.name} data (full)"

        def restore_default_settings(self):
            self.poll_interval = 1.0
            self.resolution = "default"
            logger.info(f"MockSensor {self.name}: Restored default settings.")

    mock_camera = MockSensor("Camera")
    mock_gps = MockSensor("GPS")
    mock_lidar = MockSensor("Lidar")

    # Register and optimize components
    optimizer_main.register_component("camera_sensor", mock_camera)
    optimizer_main.optimize_component("camera_sensor")
    optimizer_main.register_component("gps_sensor", mock_gps)
    optimizer_main.optimize_component("gps_sensor")
    optimizer_main.register_component("lidar_sensor", mock_lidar)  # Register Lidar
    optimizer_main.optimize_component("lidar_sensor")  # Optimize Lidar

    # Decorate the read_data methods of the instances
    # We need to bind the decorated function back to the instance
    mock_camera.read_data = power_aware(optimizer_main)(
        functools.partial(mock_camera.read_data, mock_camera)  # Pass instance for self
    )
    mock_gps.read_data = power_aware(optimizer_main)(
        functools.partial(mock_gps.read_data, mock_gps)
    )
    mock_lidar.read_data = power_aware(optimizer_main)(  # Decorate Lidar's method
        functools.partial(mock_lidar.read_data, mock_lidar)
    )

    # --- Simulate battery drain and power mode changes ---
    logger.info("\\\\n--- Simulating Battery Drain ---")
    # Override get_battery_level for testing
    # pylint: disable=protected-access
    original_get_battery_level = optimizer_main.get_battery_level

    def mock_get_battery_level_factory(level_provider_func):
        def mock_get_battery_level(*args, **kwargs):
            # Call the provided function to get the current mock level
            level = level_provider_func()
            logger.info(f"[SIMULATED] get_battery_level returning: {level}%")
            return level
        return mock_get_battery_level

    # Use a mutable list to change the battery level from outside the mock function
    current_simulated_battery_level = [100.0]
    optimizer_main.get_battery_level = mock_get_battery_level_factory(lambda: current_simulated_battery_level[0])

    # Test different power modes
    test_battery_levels = [90.0, 70.0, 40.0, 15.0, 5.0]  # Test various levels including critical
    for level in test_battery_levels:
        current_simulated_battery_level[0] = level
        logger.info(f"\\\\nSetting simulated battery level to: {level}%")

        # Trigger monitoring loop iteration (simplified for testing)
        # In a real scenario, the monitoring loop runs in its own thread.
        # Here, we directly call _update_power_mode to reflect the change.
        optimizer_main._update_power_mode(level)  # pylint: disable=protected-access

        logger.info(f"Current Power Mode: {optimizer_main.get_power_mode().name}")
        optimizer_main.print_power_usage()

        # Test power-aware functions
        logger.info(f"Camera data: {mock_camera.read_data()}")
        logger.info(f"GPS data: {mock_gps.read_data()}")
        logger.info(f"Lidar data: {mock_lidar.read_data()}")  # Test Lidar

        # Simulate some time passing (not strictly necessary for this direct call test)
        # time.sleep(1) # Removed to speed up test, monitoring loop is not running here

    # Restore original get_battery_level
    optimizer_main.get_battery_level = original_get_battery_level
    # pylint: enable=protected-access

    # --- Test manual power mode setting ---
    logger.info("\\n--- Testing Manual Power Mode Setting ---")
    optimizer_main.set_power_mode(PowerMode.POWER_SAVING)
    logger.info(f"Manually set Power Mode: {optimizer_main.get_power_mode().name}")
    optimizer_main.print_power_usage()
    logger.info(f"Camera data after manual set: {mock_camera.read_data()}")
    logger.info(f"GPS data after manual set: {mock_gps.read_data()}")
    logger.info(f"Lidar data after manual set: {mock_lidar.read_data()}")

    # --- Test cleanup ---
    logger.info("\\\\n--- Testing Cleanup ---")
    optimizer_main.cleanup()
    logger.info(f"Optimized components after cleanup: {optimizer_main.optimized_components}")
    monitoring_status_main = (
        "Alive" if optimizer_main.monitoring_thread and optimizer_main.monitoring_thread.is_alive()
        else "Not running/None"
    )
    logger.info(f"Is monitoring thread alive after cleanup? {monitoring_status_main}")

    # Try to get a new instance to ensure singleton and cleanup work well together
    logger.info("\\\\n--- Testing new optimizer instance post-cleanup ---")
    optimizer_new = get_power_optimizer(enable_monitoring=False)  # Get new, don't start monitoring
    logger.info(f"New optimizer instance ID: {id(optimizer_new)}")
    # Should be the same if singleton is robust
    logger.info(f"Original optimizer instance ID: {id(optimizer_main)}")
    monitoring_status_new = (
        "Alive" if optimizer_new.monitoring_thread and optimizer_new.monitoring_thread.is_alive()
        else "Not running/None"
    )
    logger.info(f"Is new optimizer monitoring? {monitoring_status_new}")
    optimizer_new.cleanup()  # Cleanup the new one as well

    logger.info("\\\\nPowerOptimizer example finished.")
