"""
Shared fixtures for pytest.

This file contains fixtures that can be used across all tests.
"""

from mower.config_management import (
    get_config_manager, get_config, set_config,
    CONFIG_DIR, initialize_config_manager
)
import os
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the modules we need to mock


@pytest.fixture
def config_manager():
    """Fixture for a clean configuration manager with test values."""
    # Initialize configuration manager with test values
    test_config = {
        "test": {
            "string_value": "test_string",
            "int_value": 42,
            "float_value": 3.14,
            "bool_value": True,
            "list_value": [1, 2, 3],
            "dict_value": {"key": "value"}
        }
    }

    # Initialize configuration manager
    initialize_config_manager(defaults=test_config)

    # Get configuration manager
    return get_config_manager()


@pytest.fixture
def mock_hardware():
    """Fixture for mocked hardware components."""
    # Create mock objects for hardware components
    mock_gpio = MagicMock()
    mock_imu = MagicMock()
    mock_bme280 = MagicMock()
    mock_ina3221 = MagicMock()
    mock_tof = MagicMock()
    mock_motor_driver = MagicMock()
    mock_blade_controller = MagicMock()
    mock_camera = MagicMock()
    mock_gps_serial = MagicMock()
    mock_sensor_interface = MagicMock()

    # Return a dictionary of mock objects
    return {
        "gpio": mock_gpio,
        "imu": mock_imu,
        "bme280": mock_bme280,
        "ina3221": mock_ina3221,
        "tof": mock_tof,
        "motor_driver": mock_motor_driver,
        "blade_controller": mock_blade_controller,
        "camera": mock_camera,
        "gps_serial": mock_gps_serial,
        "sensor_interface": mock_sensor_interface
    }


@pytest.fixture
def mock_resource_manager(mock_hardware):
    """Fixture for a mocked ResourceManager."""
    # Create a mock ResourceManager
    mock_resource_manager = MagicMock()

    # Configure the mock to return the mock hardware components
    mock_resource_manager.get_resource.side_effect = lambda name: mock_hardware.get(
        name)
    mock_resource_manager.get_path_planner.return_value = MagicMock()
    mock_resource_manager.get_navigation.return_value = MagicMock()
    mock_resource_manager.get_obstacle_detection.return_value = MagicMock()
    mock_resource_manager.get_blade_controller.return_value = mock_hardware[
        "blade_controller"]
    mock_resource_manager.get_bme280_sensor.return_value = mock_hardware["bme280"]
    mock_resource_manager.get_camera.return_value = mock_hardware["camera"]
    mock_resource_manager.get_robohat_driver.return_value = mock_hardware["motor_driver"]
    mock_resource_manager.get_gps_serial.return_value = mock_hardware["gps_serial"]
    mock_resource_manager.get_imu_sensor.return_value = mock_hardware["imu"]
    mock_resource_manager.get_ina3221_sensor.return_value = mock_hardware["ina3221"]
    mock_resource_manager.get_tof_sensors.return_value = mock_hardware["tof"]
    mock_resource_manager.get_sensor_interface.return_value = mock_hardware[
        "sensor_interface"]

    return mock_resource_manager


@pytest.fixture
def temp_config_dir(tmpdir):
    """Fixture for a temporary configuration directory."""
    # Create a temporary directory for configuration files
    config_dir = tmpdir.mkdir("config")

    # Patch the CONFIG_DIR constant
    with patch("mower.config_management.CONFIG_DIR", Path(config_dir)):
        yield config_dir
