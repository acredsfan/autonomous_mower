# Updated 11.1.24
"""
Module to initialize and manage all resources used in the project.
Each resource is initialized in a separate function to allow on-demand setup.
"""

import warnings

from mower.main_controller import ResourceManager

# Singleton ResourceManager instance for the whole application
_resource_manager = ResourceManager()


def init_resources():
    """Initialize all hardware and software resources."""
    _resource_manager.init_all_resources()


def cleanup_resources():
    """Clean up all resources."""
    _resource_manager.cleanup_all_resources()


def get_status():
    """Aggregate and return system status for the web UI and diagnostics."""
    return _resource_manager.get_status()


def start_web_interface():
    _resource_manager.start_web_interface()


def start_robot_logic():
    import threading

    from mower.main_controller import RobotController

    robot_controller = RobotController(_resource_manager)
    robot_thread = threading.Thread(target=robot_controller.run_robot, daemon=True)
    robot_thread.start()


# --- Legacy API: Deprecated global resource getters (for compatibility) ---
def _warn_deprecated(name):
    warnings.warn(
        f"{name}() is deprecated. Use ResourceManager instead.",
        DeprecationWarning,
        stacklevel=2,
    )


def get_blade_controller():
    _warn_deprecated("get_blade_controller")
    return _resource_manager.get_blade_controller()


def get_bme280_sensor():
    _warn_deprecated("get_bme280_sensor")
    return _resource_manager.get_resource("bme280") if hasattr(_resource_manager, "get_resource") else None


def get_camera():
    _warn_deprecated("get_camera")
    return _resource_manager.get_camera()


def get_gpio_manager():
    _warn_deprecated("get_gpio_manager")
    return _resource_manager.get_resource("gpio") if hasattr(_resource_manager, "get_resource") else None


def get_imu_sensor():
    _warn_deprecated("get_imu_sensor")
    return _resource_manager.get_imu_sensor()


def get_ina3221_sensor():
    _warn_deprecated("get_ina3221_sensor")
    return _resource_manager.get_ina3221_sensor()


def get_robohat_driver():
    _warn_deprecated("get_robohat_driver")
    return _resource_manager.get_robohat_driver()


def get_sensors():
    _warn_deprecated("get_sensors")
    return _resource_manager.get_sensor_interface()


def get_serial_port():
    _warn_deprecated("get_serial_port")
    return _resource_manager.get_gps()


def get_tof_sensors():
    _warn_deprecated("get_tof_sensors")
    return _resource_manager.get_resource("tof") if hasattr(_resource_manager, "get_resource") else None


def get_gps_nmea_positions():
    _warn_deprecated("get_gps_nmea_positions")
    return _resource_manager.get_resource("gps_nmea_positions") if hasattr(_resource_manager, "get_resource") else None


def get_gps_latest_position():
    _warn_deprecated("get_gps_latest_position")
    return _resource_manager.get_gps_latest_position()


def get_gps_position():
    _warn_deprecated("get_gps_position")
    return _resource_manager.get_resource("gps_position") if hasattr(_resource_manager, "get_resource") else None


def get_localization():
    _warn_deprecated("get_localization")
    return _resource_manager.get_resource("localization") if hasattr(_resource_manager, "get_resource") else None


def get_path_planner():
    _warn_deprecated("get_path_planner")
    return _resource_manager.get_path_planner()


def get_navigation_controller():
    _warn_deprecated("get_navigation_controller")
    return _resource_manager.get_navigation_controller()


def get_avoidance_algorithm():
    _warn_deprecated("get_avoidance_algorithm")
    return _resource_manager.get_avoidance_algorithm()


def get_web_interface():
    _warn_deprecated("get_web_interface")
    return _resource_manager.get_web_interface()


def get_home_location():
    """Get the home location from resource manager."""
    _warn_deprecated("get_home_location")
    return _resource_manager.get_home_location()


def set_home_location(location):
    """Set the home location using resource manager."""
    _warn_deprecated("set_home_location")
    return _resource_manager.set_home_location(location)


if __name__ == "__main__":
    try:
        init_resources()
        start_robot_logic()
        start_web_interface()
    except KeyboardInterrupt:
        import logging

        logging.info("Exiting")
    finally:
        cleanup_resources()
