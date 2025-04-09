"""
Diagnostics package for the autonomous mower.

This package provides diagnostic tools for testing and troubleshooting the hardware
and software components of the autonomous mower system.

Modules:
    hardware_test: Comprehensive testing of all hardware components
    blade_test: Testing and calibration of blade motors
    camera_test: Testing and configuration of camera systems
    encoder_test: Testing of wheel encoders
    gps_test: Testing and validation of GPS signals
    imu_test: Testing and calibration of IMU sensors
    motor_test: Testing of drive motors
    bme280_test: Testing of environmental sensors
    imu_calibration: Calibration procedures for IMU sensors
    sensor_test: Visualization and validation of all sensor data
"""

from mower.utilities.logger_config import LoggerConfigInfo as LoggerConfig

# Initialize logger
logging = LoggerConfig.get_logger(__name__)
