"""
Power optimization module for autonomous mower.

This module provides tools for optimizing power consumption
to extend battery life in resource-constrained environments.
"""

import time
import threading
import functools
import os
import psutil
from typing import Dict, Any, List, Optional, Callable, Set, Tuple
from enum import Enum, auto

from mower.utilities.logger_config import LoggerConfig

# Initialize logger
logger = LoggerConfig.get_logger(__name__)


class PowerMode(Enum):
    """Power modes for the system."""
    HIGH_PERFORMANCE = auto()  # Maximum performance, no power saving
    BALANCED = auto()          # Balance between performance and power saving
    POWER_SAVING = auto()      # Aggressive power saving
    CRITICAL = auto()          # Critical battery level, maximum power saving


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
        self.monitoring_thread = None
        self.stop_monitoring = threading.Event()

        # Current power mode
        self.power_mode = PowerMode.BALANCED

        # Battery thresholds for power modes
        self.battery_thresholds = {
            PowerMode.HIGH_PERFORMANCE: 80,  # Above 80%
            PowerMode.BALANCED: 50,          # 50-80%
            PowerMode.POWER_SAVING: 20,      # 20-50%
            PowerMode.CRITICAL: 0            # Below 20%
        }

        # Component power settings for each mode
        self.power_settings = {
            PowerMode.HIGH_PERFORMANCE: {
                'cpu_governor': 'performance',
                'sensor_poll_interval': 0.1,  # seconds
                'camera_resolution': 'high',
                'gps_update_interval': 1.0,   # seconds
                'background_processes': True
            },
            PowerMode.BALANCED: {
                'cpu_governor': 'ondemand',
                'sensor_poll_interval': 0.5,  # seconds
                'camera_resolution': 'medium',
                'gps_update_interval': 3.0,   # seconds
                'background_processes': True
            },
            PowerMode.POWER_SAVING: {
                'cpu_governor': 'powersave',
                'sensor_poll_interval': 1.0,  # seconds
                'camera_resolution': 'low',
                'gps_update_interval': 5.0,   # seconds
                'background_processes': False
            },
            PowerMode.CRITICAL: {
                'cpu_governor': 'powersave',
                'sensor_poll_interval': 2.0,  # seconds
                'camera_resolution': 'lowest',
                'gps_update_interval': 10.0,  # seconds
                'background_processes': False
            }
        }

        # Optimized components
        self.optimized_components = set()

        # Power usage statistics
        self.stats = {
            'battery_levels': [],
            'power_modes': [],
            'cpu_usage': []
        }

        # Start monitoring if enabled
        if self.enable_monitoring:
            self.start_monitoring()

        logger.info("Power optimizer initialized")

    def start_monitoring(self):
        """Start power usage monitoring."""
        if self.monitoring_thread is not None and self.monitoring_thread.is_alive():
            logger.warning("Monitoring thread is already running")
            return

        self.stop_monitoring.clear()
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True
        )
        self.monitoring_thread.start()
        logger.info("Power monitoring started")

    def stop_monitoring(self):
        """Stop power usage monitoring."""
        if self.monitoring_thread is None or not self.monitoring_thread.is_alive():
            logger.warning("Monitoring thread is not running")
            return

        self.stop_monitoring.set()
        self.monitoring_thread.join(timeout=2)
        logger.info("Power monitoring stopped")

    def _monitoring_loop(self):
        """Main monitoring loop."""
        while not self.stop_monitoring.is_set():
            try:
                # Get current battery level
                battery_level = self.get_battery_level()

                # Get current CPU usage
                cpu_usage = psutil.cpu_percent(interval=0.1)

                # Store statistics
                self.stats['battery_levels'].append(battery_level)
                self.stats['power_modes'].append(self.power_mode.name)
                self.stats['cpu_usage'].append(cpu_usage)

                # Keep only the last 100 measurements
                if len(self.stats['battery_levels']) > 100:
                    self.stats['battery_levels'] = self.stats['battery_levels'][-100:]
                    self.stats['power_modes'] = self.stats['power_modes'][-100:]
                    self.stats['cpu_usage'] = self.stats['cpu_usage'][-100:]

                # Update power mode based on battery level
                self._update_power_mode(battery_level)

                # Sleep for the monitoring interval
                time.sleep(self.monitoring_interval)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.monitoring_interval)

    def _update_power_mode(self, battery_level: float):
        """
        Update power mode based on battery level.

        Args:
            battery_level: Current battery level (0-100)
        """
        # Determine appropriate power mode
        new_mode = None
        if battery_level >= self.battery_thresholds[PowerMode.HIGH_PERFORMANCE]:
            new_mode = PowerMode.HIGH_PERFORMANCE
        elif battery_level >= self.battery_thresholds[PowerMode.BALANCED]:
            new_mode = PowerMode.BALANCED
        elif battery_level >= self.battery_thresholds[PowerMode.POWER_SAVING]:
            new_mode = PowerMode.POWER_SAVING
        else:
            new_mode = PowerMode.CRITICAL

        # If mode has changed, apply new settings
        if new_mode != self.power_mode:
            logger.info(
                f"Changing power mode from {self.power_mode.name} to {new_mode.name} (battery: {battery_level}%)")
            self.power_mode = new_mode
            self._apply_power_settings()

    def _apply_power_settings(self):
        """Apply power settings for the current power mode."""
        settings = self.power_settings[self.power_mode]

        # Apply CPU governor setting
        self._set_cpu_governor(settings['cpu_governor'])

        # Apply settings to all optimized components
        for component_name in self.optimized_components:
            self._apply_component_settings(component_name, settings)

        logger.info(f"Applied power settings for {self.power_mode.name} mode")

    def _set_cpu_governor(self, governor: str):
        """
        Set CPU governor.

        Args:
            governor: CPU governor to set (performance, ondemand, powersave)
        """
        try:
            # This requires root privileges and only works on Linux
            if os.name == 'posix':
                # Get number of CPU cores
                cpu_count = psutil.cpu_count()

                # Set governor for each CPU core
                for i in range(cpu_count):
                    governor_path = f"/sys/devices/system/cpu/cpu{i}/cpufreq/scaling_governor"
                    if os.path.exists(governor_path):
                        with open(governor_path, 'w') as f:
                            f.write(governor)

                logger.info(f"Set CPU governor to {governor}")
            else:
                logger.warning(
                    f"Setting CPU governor not supported on {os.name}")
        except Exception as e:
            logger.error(f"Error setting CPU governor: {e}")

    def _apply_component_settings(self, component_name: str, settings: Dict[str, Any]):
        """
        Apply power settings to a component.

        Args:
            component_name: Name of the component
            settings: Power settings to apply
        """
        try:
            # Get component
            component = self._get_component(component_name)
            if component is None:
                return

            # Apply settings based on component type
            if hasattr(component, 'set_poll_interval') and 'sensor_poll_interval' in settings:
                component.set_poll_interval(settings['sensor_poll_interval'])
                logger.debug(
                    f"Set poll interval for {component_name} to {settings['sensor_poll_interval']}s")

            if hasattr(component, 'set_resolution') and 'camera_resolution' in settings:
                component.set_resolution(settings['camera_resolution'])
                logger.debug(
                    f"Set resolution for {component_name} to {settings['camera_resolution']}")

            if hasattr(component, 'set_update_interval') and 'gps_update_interval' in settings:
                component.set_update_interval(settings['gps_update_interval'])
                logger.debug(
                    f"Set update interval for {component_name} to {settings['gps_update_interval']}s")

            if hasattr(component, 'set_background_processes') and 'background_processes' in settings:
                component.set_background_processes(
                    settings['background_processes'])
                logger.debug(
                    f"Set background processes for {component_name} to {settings['background_processes']}")
        except Exception as e:
            logger.error(f"Error applying settings to {component_name}: {e}")

    def _get_component(self, component_name: str) -> Any:
        """
        Get a component by name.

        Args:
            component_name: Name of the component

        Returns:
            The component or None if not found
        """
        # This is a placeholder implementation
        # In a real system, this would look up components from a registry
        return None

    def get_battery_level(self) -> float:
        """
        Get current battery level.

        Returns:
            Battery level (0-100)
        """
        try:
            # Try to get battery info from psutil
            battery = psutil.sensors_battery()
            if battery:
                return battery.percent

            # If psutil doesn't provide battery info, try reading from sysfs
            if os.path.exists('/sys/class/power_supply/BAT0/capacity'):
                with open('/sys/class/power_supply/BAT0/capacity', 'r') as f:
                    return float(f.read().strip())

            # If no battery info is available, assume a default value
            logger.warning("Could not get battery level, assuming 50%")
            return 50.0
        except Exception as e:
            logger.error(f"Error getting battery level: {e}")
            return 50.0  # Default to 50% if there's an error

    def optimize_component(self, component_name: str, component: Any):
        """
        Optimize power usage for a component.

        Args:
            component_name: Name of the component
            component: The component to optimize
        """
        if component_name in self.optimized_components:
            logger.debug(f"Component {component_name} already optimized")
            return

        logger.info(f"Optimizing power usage for {component_name}")

        # Apply power optimizations based on component type
        settings = self.power_settings[self.power_mode]
        self._apply_component_settings(component_name, settings)

        # Add component to optimized set
        self.optimized_components.add(component_name)

    def set_power_mode(self, mode: PowerMode):
        """
        Manually set power mode.

        Args:
            mode: Power mode to set
        """
        if mode == self.power_mode:
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
        return {
            'battery_level': self.get_battery_level(),
            'power_mode': self.power_mode.name,
            'cpu_usage': psutil.cpu_percent(interval=0.1),
            'stats': self.stats
        }

    def print_power_usage(self):
        """Print current power usage statistics."""
        usage = self.get_power_usage()

        logger.info("Power Usage:")
        logger.info(f"  Battery: {usage['battery_level']}%")
        logger.info(f"  Power Mode: {usage['power_mode']}")
        logger.info(f"  CPU Usage: {usage['cpu_usage']}%")

    def cleanup(self):
        """Clean up resources used by the optimizer."""
        if self.enable_monitoring:
            self.stop_monitoring()

        # Restore default power settings
        self.set_power_mode(PowerMode.BALANCED)

        logger.info("Power optimizer cleaned up")

# Decorator for power-aware functions


def power_aware(func):
    """
    Decorator for making functions power-aware.

    This decorator adjusts function behavior based on the current power mode.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Get current power mode
        power_mode = get_power_optimizer().get_power_mode()

        # Add power mode to kwargs
        kwargs['power_mode'] = power_mode

        # Call the function
        return func(*args, **kwargs)

    return wrapper


# Singleton instance
_power_optimizer = None


def get_power_optimizer(enable_monitoring: bool = True) -> PowerOptimizer:
    """
    Get or create the singleton power optimizer instance.

    Args:
        enable_monitoring: Whether to enable power monitoring

    Returns:
        The power optimizer instance
    """
    global _power_optimizer

    if _power_optimizer is None:
        _power_optimizer = PowerOptimizer(enable_monitoring)

    return _power_optimizer


def optimize_power_consumption():
    """Optimize power consumption for all major components."""
    logger.info("Optimizing power consumption for all major components")

    # Get optimizer
    optimizer = get_power_optimizer()

    # Optimize path planning
    try:
        from mower.navigation.path_planner import PathPlanner

        # Create a power-aware wrapper for the generate_path method
        def power_aware_generate_path(planner, power_mode=None):
            """Power-aware wrapper for generate_path."""
            # Adjust path planning based on power mode
            if power_mode == PowerMode.CRITICAL:
                # Use simpler path planning in critical power mode
                planner.pattern_config.pattern_type = "PARALLEL"
            elif power_mode == PowerMode.POWER_SAVING:
                # Use more efficient path planning in power saving mode
                planner.pattern_config.pattern_type = "ZIGZAG"

            # Call original method
            return planner.generate_path()

        # Monkey patch the PathPlanner class
        original_generate_path = PathPlanner.generate_path
        PathPlanner.generate_path = power_aware(power_aware_generate_path)

        logger.info("Optimized power consumption for path planning")
    except Exception as e:
        logger.error(f"Failed to optimize path planning: {e}")

    # Optimize obstacle detection
    try:
        from mower.obstacle_detection.obstacle_detector import ObstacleDetector

        # Create a power-aware wrapper for the detect_obstacles method
        def power_aware_detect_obstacles(detector, frame=None, power_mode=None):
            """Power-aware wrapper for detect_obstacles."""
            # Adjust detection based on power mode
            if power_mode == PowerMode.CRITICAL:
                # Use only OpenCV detection in critical power mode
                return detector._detect_obstacles_opencv(frame)
            elif power_mode == PowerMode.POWER_SAVING:
                # Use ML detection less frequently in power saving mode
                if hasattr(detector, 'detection_count'):
                    detector.detection_count += 1
                    if detector.detection_count % 3 != 0:  # Only use ML every 3rd frame
                        return detector._detect_obstacles_opencv(frame)
                else:
                    detector.detection_count = 0

            # Call original method
            return detector.detect_obstacles(frame)

        # Monkey patch the ObstacleDetector class
        original_detect_obstacles = ObstacleDetector.detect_obstacles
        ObstacleDetector.detect_obstacles = power_aware(
            power_aware_detect_obstacles)

        logger.info("Optimized power consumption for obstacle detection")
    except Exception as e:
        logger.error(f"Failed to optimize obstacle detection: {e}")

    # Optimize GPS updates
    try:
        from mower.navigation.gps import GPSManager

        # Create a power-aware wrapper for the update method
        def power_aware_update(gps_manager, power_mode=None):
            """Power-aware wrapper for GPS update."""
            # Adjust update interval based on power mode
            if power_mode == PowerMode.CRITICAL:
                gps_manager.update_interval = 10.0  # seconds
            elif power_mode == PowerMode.POWER_SAVING:
                gps_manager.update_interval = 5.0  # seconds
            elif power_mode == PowerMode.BALANCED:
                gps_manager.update_interval = 3.0  # seconds
            else:  # HIGH_PERFORMANCE
                gps_manager.update_interval = 1.0  # seconds

            # Call original method
            return gps_manager.update()

        # Monkey patch the GPSManager class
        if hasattr(GPSManager, 'update'):
            original_update = GPSManager.update
            GPSManager.update = power_aware(power_aware_update)

            logger.info("Optimized power consumption for GPS updates")
    except Exception as e:
        logger.error(f"Failed to optimize GPS updates: {e}")

    logger.info("Power consumption optimization complete")

    return optimizer


if __name__ == "__main__":
    # Run power optimization
    optimizer = optimize_power_consumption()
    optimizer.print_power_usage()
