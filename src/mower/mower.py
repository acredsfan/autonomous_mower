# Updated 11.1.24
"""
Module to initialize and manage all resources used in the project.
Each resource is initialized in a separate function to allow on-demand setup.
"""

import threading

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

# Global variables to hold instances
_blade_controller = None
_bme280_sensor = None
_camera_instance = None
_gpio_manager = None
_imu_sensor = None
_ina3221_sensor = None
_robohat_driver = None
_serial_port = None
_tof_sensors = None

_gps_nmea_positions = None
_gps_latest_position = None
_gps_position = None
_localization = None
_path_planner = None

_avoidance_algorithm = None
_web_interface = None

_logger_config = None
_text_logger = None
_csv_logger = None
_utils = None

_sensor_interface = None

# Initialize logger
logging = LoggerConfig.get_logger(__name__)

# Hardware initialization functions


def get_blade_controller():
    global _blade_controller
    if _blade_controller is None:
        _blade_controller = BladeController()
    return _blade_controller


def get_bme280_sensor():
    global _bme280_sensor
    if _bme280_sensor is None:
        _bme280_sensor = BME280Sensor()
    return _bme280_sensor


def get_camera():
    global _camera_instance
    if _camera_instance is None:
        _camera_instance = get_camera_instance()
    return _camera_instance


def get_gpio_manager():
    global _gpio_manager
    if _gpio_manager is None:
        _gpio_manager = GPIOManager()
    return _gpio_manager


def get_imu_sensor():
    global _imu_sensor
    if _imu_sensor is None:
        _imu_sensor = BNO085Sensor()
    return _imu_sensor


def get_ina3221_sensor():
    global _ina3221_sensor
    if _ina3221_sensor is None:
        _ina3221_sensor = INA3221Sensor()
    return _ina3221_sensor


def get_robohat_driver():
    global _robohat_driver
    if _robohat_driver is None:
        _robohat_driver = RoboHATDriver()
    return _robohat_driver


def get_sensors():
    global _sensor_interface
    if _sensor_interface is None:
        _sensor_interface = get_sensor_interface()
    return _sensor_interface


def get_serial_port():
    global _serial_port
    if _serial_port is None:
        _serial_port = SerialPort()
    return _serial_port


def get_tof_sensors():
    global _tof_sensors
    if _tof_sensors is None:
        _tof_sensors = VL53L0XSensors()
    return _tof_sensors

# Navigation initialization functions


def get_gps_nmea_positions():
    global _gps_nmea_positions
    if _gps_nmea_positions is None:
        _gps_nmea_positions = GpsNmeaPositions()
    return _gps_nmea_positions


def get_gps_latest_position():
    global _gps_latest_position
    if _gps_latest_position is None:
        _gps_latest_position = GpsLatestPosition(
            get_gps_nmea_positions())
    return _gps_latest_position


def get_gps_position():
    global _gps_position
    if _gps_position is None:
        _gps_position = GpsPosition()
    return _gps_position


def get_localization():
    global _localization
    if _localization is None:
        _localization = Localization()
    return _localization


def get_path_planner():
    global _path_planner
    if _path_planner is None:
        _path_planner = PathPlanner(get_localization())
    return _path_planner


def get_navigation_controller():
    global _navigation_controller
    if _navigation_controller is None:
        _navigation_controller = NavigationController(
            gps_latest_position=get_gps_latest_position(),
            robohat_driver=get_robohat_driver(),
            sensor_interface=get_sensor_interface())
    return _navigation_controller

# Obstacle Detection initialization functions


def get_avoidance_algorithm():
    global _avoidance_algorithm
    if _avoidance_algorithm is None:
        _avoidance_algorithm = AvoidanceAlgorithm()
    return _avoidance_algorithm


def get_detect_obstacle():
    return detect_obstacle


def get_detect_drop():
    return detect_drop


def get_stream_frame_with_overlays():
    return stream_frame_with_overlays

# UI and utilities initialization functions


def get_web_interface():
    global _web_interface
    if _web_interface is None:
        _web_interface = WebInterface()
    return _web_interface


def get_logger_config():
    global _logger_config
    if _logger_config is None:
        _logger_config = LoggerConfig()
    return _logger_config


def get_text_logger():
    global _text_logger
    if _text_logger is None:
        _text_logger = TextLogger()
    return _text_logger


def get_csv_logger():
    global _csv_logger
    if _csv_logger is None:
        _csv_logger = CsvLogger()
    return _csv_logger


def get_utils():
    global _utils
    if _utils is None:
        _utils = Utils()
    return _utils

# Function to initialize all resources


def init_resources():
    get_blade_controller()
    get_bme280_sensor()
    get_camera()
    get_gpio_manager()
    get_imu_sensor()
    get_ina3221_sensor()
    get_robohat_driver()
    get_sensors()
    get_serial_port()
    get_tof_sensors()

    get_gps_nmea_positions()
    get_gps_latest_position()
    get_gps_position()
    get_localization()
    get_path_planner()

    get_avoidance_algorithm()
    get_detect_obstacle()
    get_detect_drop()
    get_stream_frame_with_overlays()

    get_web_interface()

    get_logger_config()
    get_text_logger()
    get_csv_logger()
    get_utils()

# Function to cleanup all resources


def cleanup_resources():
    if _blade_controller is not None:
        _blade_controller.cleanup()
    if _bme280_sensor is not None:
        _bme280_sensor.cleanup()
    if _camera_instance is not None:
        _camera_instance.cleanup()
    if _gpio_manager is not None:
        _gpio_manager.cleanup()
    if _imu_sensor is not None:
        _imu_sensor.cleanup()
    if _ina3221_sensor is not None:
        _ina3221_sensor.cleanup()
    if _robohat_driver is not None:
        _robohat_driver.shutdown()  # Use shutdown method
    if _sensor_interface is not None:
        _sensor_interface.shutdown()
    if _serial_port is not None:
        _serial_port.cleanup()
    if _tof_sensors is not None:
        _tof_sensors.cleanup()

    if _gps_nmea_positions is not None:
        _gps_nmea_positions.cleanup()
    if _gps_latest_position is not None:
        _gps_latest_position.cleanup()
    if _gps_position is not None:
        _gps_position.cleanup()
    if _localization is not None:
        _localization.cleanup()
    if _path_planner is not None:
        _path_planner.cleanup()

    if _avoidance_algorithm is not None:
        _avoidance_algorithm.cleanup()

    if _web_interface is not None:
        _web_interface.shutdown()

    if _logger_config is not None:
        _logger_config.cleanup()
    if _text_logger is not None:
        _text_logger.cleanup()
    if _csv_logger is not None:
        _csv_logger.cleanup()
    if _utils is not None:
        _utils.cleanup()

# Function to start the web interface


def start_web_interface():
    get_web_interface().start()

# Function to start the robot logic


def start_robot_logic():
    from mower.robot import run_robot
    robot_thread = threading.Thread(target=run_robot, daemon=True)
    robot_thread.start()


if __name__ == "__main__":
    try:
        init_resources()
        start_robot_logic()
        start_web_interface()
    except KeyboardInterrupt:
        logging.info("Exiting")
    finally:
        cleanup_resources()
