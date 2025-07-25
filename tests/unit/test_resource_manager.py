"""
Test module for test_resource_manager.py.
"""

from unittest.mock import MagicMock, patch

import pytest

from mower.main_controller import ResourceManager as MainResourceManager


class TestMainResourceManager:
    """Tests for the ResourceManager class in main_controller.py."""

    @patch("mower.main_controller.GPIOManager")
    @patch("mower.main_controller.BNO085Sensor")
    @patch("mower.main_controller.BME280Sensor")
    @patch("mower.main_controller.INA3221Sensor")
    @patch("mower.main_controller.VL53L0XSensors")
    @patch("mower.main_controller.RoboHATDriver")
    @patch("mower.main_controller.BladeController")
    @patch("mower.main_controller.get_camera_instance")
    @patch("mower.main_controller.SerialPort")
    @patch("mower.main_controller.EnhancedSensorInterface")
    def test_initialize_hardware(
        self,
        mock_sensor_interface,
        mock_serial_port,
        mock_camera,
        mock_blade,
        mock_robohat,
        mock_tof,
        mock_ina3221,
        mock_bme280,
        mock_imu,
        mock_gpio,
    ):
        """Test initialization of hardware components."""
        # Create a ResourceManager instance
        resource_manager = MainResourceManager()

        # Call _initialize_hardware
        resource_manager._initialize_hardware()

        # Verify that all hardware components were initialized
        mock_gpio.assert_called_once()
        mock_gpio.return_value._initialize.assert_called_once()

        mock_imu.assert_called_once()
        mock_imu.return_value._initialize.assert_called_once()

        mock_bme280.assert_called_once()
        mock_bme280.return_value._initialize.assert_called_once()

        mock_ina3221.assert_called_once()
        mock_ina3221.return_value._initialize.assert_called_once()

        mock_tof.assert_called_once()
        mock_tof.return_value._initialize.assert_called_once()

        mock_robohat.assert_called_once()
        mock_robohat.return_value.__init__.assert_called_once()

        mock_blade.assert_called_once()
        mock_blade.return_value.__init__.assert_called_once()

        mock_camera.assert_called_once()
        mock_camera.return_value.__init__.assert_called_once()

        mock_serial_port.assert_called_once()
        mock_serial_port.return_value._initialize.assert_called_once()

        mock_sensor_interface.assert_called_once()

    @patch("mower.main_controller.Localization")
    @patch("mower.main_controller.PathPlanner")
    @patch("mower.main_controller.NavigationController")
    @patch("mower.main_controller.AvoidanceAlgorithm")
    @patch("mower.main_controller.WebInterface")
    @patch("mower.main_controller.get_config")
    def test_initialize_software(
        self,
        mock_get_config,
        mock_web_interface,
        mock_avoidance,
        mock_navigation,
        mock_path_planner,
        mock_localization,
    ):
        """Test initialization of software components."""
        # Configure mock_get_config to return appropriate values
        mock_get_config.side_effect = lambda key, default=None: {
            "path_planning.pattern_type": "PARALLEL",
            "path_planning.spacing": 0.3,
            "path_planning.angle": 0.0,
            "path_planning.overlap": 0.1,
            "path_planning.learning_rate": 0.1,
            "path_planning.discount_factor": 0.9,
            "path_planning.exploration_rate": 0.2,
            "path_planning.memory_size": 1000,
            "path_planning.batch_size": 32,
            "path_planning.update_frequency": 100,
        }.get(key, default)

        # Create a ResourceManager instance with mocked hardware components
        resource_manager = MainResourceManager()
        resource_manager._resources = {
            "gps_serial": MagicMock(),
            "motor_driver": MagicMock(),
            "sensor_interface": MagicMock(),
            "path_planner": MagicMock(),
        }

        # Call _initialize_software
        resource_manager._initialize_software()

        # Verify that all software components were initialized
        mock_localization.assert_called_once()
        mock_path_planner.assert_called_once()
        mock_navigation.assert_called_once()
        mock_avoidance.assert_called_once()
        mock_web_interface.assert_called_once()

    def test_get_resource(self):
        """Test getting resources by name."""
        # Create a ResourceManager instance
        resource_manager = MainResourceManager()
        resource_manager._initialized = True
        resource_manager._resources = {
            "test_resource": MagicMock(),
        }

        # Get a resource by name
        resource = resource_manager.get_resource("test_resource")

        # Verify that the correct resource was returned
        assert resource is resource_manager._resources["test_resource"]

        # Test getting a non-existent resource
        with pytest.raises(KeyError):
            resource_manager.get_resource("non_existent_resource")

        # Test getting a resource when not initialized
        resource_manager._initialized = False
        with pytest.raises(RuntimeError):
            resource_manager.get_resource("test_resource")

    @patch("mower.main_controller.cleanup_resources")
    def test_cleanup(self, mock_cleanup_resources):
        """Test cleanup of resources."""
        # Configure mock_cleanup_resources to return True
        mock_cleanup_resources.return_value = True

        # Create a ResourceManager instance
        resource_manager = MainResourceManager()
        resource_manager._initialized = True
        resource_manager._resources = {
            "test_resource": MagicMock(),
        }

        # Call cleanup
        result = resource_manager.cleanup()

        # Verify that cleanup_resources was called with the correct arguments
        mock_cleanup_resources.assert_called_once_with(resource_manager._resources, True, resource_manager._lock)

        # Verify that _initialized was set to False
        assert resource_manager._initialized is False

        # Verify that cleanup returned True
        assert result is True



