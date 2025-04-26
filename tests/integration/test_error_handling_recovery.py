"""
Integration tests for error handling and recovery mechanisms.

This module tests the interaction between error detection and recovery mechanisms,
ensuring that the system can detect and recover from various error conditions.
"""

import pytest
import time
from unittest.mock import MagicMock, patch, call

from mower.hardware.sensor_interface import (
    EnhancedSensorInterface,
    SensorStatus,
)
from mower.obstacle_detection.avoidance_algorithm import (
    AvoidanceAlgorithm,
    AvoidanceState,
)
from mower.navigation.path_planner import (
    PathPlanner,
    PatternConfig,
    PatternType,
    LearningConfig,
)
from mower.mower import ResourceManager, Mower, MowerMode


class TestErrorHandlingRecovery:
    """Integration tests for error handling and recovery mechanisms."""

    @pytest.fixture
    def setup_error_recovery_components(self):
        """Set up components for testing error handling and recovery."""
        # Mock the ResourceManager
        mock_resource_manager = MagicMock()

        # Mock the hardware components
        mock_blade_controller = MagicMock()
        mock_motor_driver = MagicMock()
        mock_imu_sensor = MagicMock()
        mock_bme280_sensor = MagicMock()
        mock_ina3221_sensor = MagicMock()
        mock_tof_sensors = MagicMock()
        mock_camera = MagicMock()
        mock_gps_serial = MagicMock()
        mock_sensor_interface = MagicMock()

        # Configure the resource manager to return the mock components
        mock_resource_manager.get_blade_controller.return_value = (
            mock_blade_controller
        )
        mock_resource_manager.get_robohat_driver.return_value = (
            mock_motor_driver
        )
        mock_resource_manager.get_imu_sensor.return_value = mock_imu_sensor
        mock_resource_manager.get_bme280_sensor.return_value = (
            mock_bme280_sensor
        )
        mock_resource_manager.get_ina3221_sensor.return_value = (
            mock_ina3221_sensor
        )
        mock_resource_manager.get_tof_sensors.return_value = mock_tof_sensors
        mock_resource_manager.get_camera.return_value = mock_camera
        mock_resource_manager.get_gps_serial.return_value = mock_gps_serial
        mock_resource_manager.get_sensor_interface.return_value = (
            mock_sensor_interface
        )

        # Create a Mower instance with the mock resource manager
        with patch(
            "mower.mower.ResourceManager", return_value=mock_resource_manager
        ):
            mower = Mower()

            # Configure the mock components for specific tests
            mock_ina3221_sensor.get_battery_voltage.return_value = (
                12.5  # Normal battery voltage
            )

            return {
                "mower": mower,
                "resource_manager": mock_resource_manager,
                "blade_controller": mock_blade_controller,
                "motor_driver": mock_motor_driver,
                "imu_sensor": mock_imu_sensor,
                "bme280_sensor": mock_bme280_sensor,
                "ina3221_sensor": mock_ina3221_sensor,
                "tof_sensors": mock_tof_sensors,
                "camera": mock_camera,
                "gps_serial": mock_gps_serial,
                "sensor_interface": mock_sensor_interface,
            }

    def test_emergency_stop_recovery(self, setup_error_recovery_components):
        """Test that the system can recover from an emergency stop."""
        # Get the components
        mower = setup_error_recovery_components["mower"]
        blade_controller = setup_error_recovery_components["blade_controller"]
        motor_driver = setup_error_recovery_components["motor_driver"]

        # Verify initial state
        assert mower.mode == MowerMode.IDLE

        # Start mowing
        mower.start()

        # Verify that mowing has started
        assert mower.mode == MowerMode.MOWING
        blade_controller.start_blade.assert_called_once()

        # Trigger an emergency stop
        mower.emergency_stop()

        # Verify that the emergency stop was executed
        assert mower.mode == MowerMode.EMERGENCY_STOP
        blade_controller.stop_blade.assert_called_once()
        motor_driver.stop.assert_called_once()

        # Reset the mower to IDLE state
        mower.stop()

        # Verify that the mower has been reset
        assert mower.mode == MowerMode.IDLE

        # Start mowing again
        mower.start()

        # Verify that mowing has started again
        assert mower.mode == MowerMode.MOWING
        assert blade_controller.start_blade.call_count == 2

    def test_low_battery_detection(self, setup_error_recovery_components):
        """Test that the system can detect and handle low battery conditions."""
        # Get the components
        mower = setup_error_recovery_components["mower"]
        ina3221_sensor = setup_error_recovery_components["ina3221_sensor"]

        # Set up a normal battery voltage
        ina3221_sensor.get_battery_voltage.return_value = 12.5

        # Get the safety status
        safety_status = mower.get_safety_status()

        # Verify that the battery is not low
        assert safety_status["battery_low"] is False

        # Set up a low battery voltage
        ina3221_sensor.get_battery_voltage.return_value = 10.5

        # Get the safety status again
        safety_status = mower.get_safety_status()

        # Verify that the battery is now low
        assert safety_status["battery_low"] is True

        # In a real system, this would trigger an emergency stop or return to home
        # For testing, we'll just verify that the safety status is correct

    def test_sensor_failure_recovery(self, setup_error_recovery_components):
        """Test that the system can recover from sensor failures."""
        # Get the components
        mower = setup_error_recovery_components["mower"]
        sensor_interface = setup_error_recovery_components["sensor_interface"]

        # Create a mock EnhancedSensorInterface
        with patch(
            "mower.hardware.sensor_interface.EnhancedSensorInterface"
        ) as MockSensorInterface:
            # Configure the mock to return a mock sensor interface
            mock_sensor_interface = MagicMock()
            MockSensorInterface.return_value = mock_sensor_interface

            # Configure the mock sensor interface
            mock_sensor_interface.is_safe_to_operate.return_value = True
            mock_sensor_interface._sensor_status = {
                "bme280": MagicMock(
                    working=True, error_count=0, last_error=None
                ),
                "bno085": MagicMock(
                    working=True, error_count=0, last_error=None
                ),
                "ina3221": MagicMock(
                    working=True, error_count=0, last_error=None
                ),
                "vl53l0x": MagicMock(
                    working=True, error_count=0, last_error=None
                ),
            }

            # Create a new EnhancedSensorInterface instance
            sensor_interface = MockSensorInterface()

            # Verify that it's safe to operate
            assert sensor_interface.is_safe_to_operate() is True

            # Simulate a sensor failure
            mock_sensor_interface._sensor_status["bno085"].working = False
            mock_sensor_interface._sensor_status["bno085"].error_count = 3
            mock_sensor_interface._sensor_status["bno085"].last_error = (
                "Sensor not responding"
            )

            # Verify that it's not safe to operate
            assert sensor_interface.is_safe_to_operate() is False

            # Simulate sensor recovery
            mock_sensor_interface._init_sensor_with_retry = MagicMock(
                return_value=True
            )

            # Call the recovery method
            sensor_interface._attempt_sensor_recovery("bno085")

            # Verify that the recovery method was called
            mock_sensor_interface._init_sensor_with_retry.assert_called_once()

            # Simulate successful recovery
            mock_sensor_interface._sensor_status["bno085"].working = True
            mock_sensor_interface._sensor_status["bno085"].error_count = 0
            mock_sensor_interface._sensor_status["bno085"].last_error = None

            # Verify that it's safe to operate again
            assert sensor_interface.is_safe_to_operate() is True

    def test_obstacle_avoidance_failure_recovery(
        self, setup_error_recovery_components
    ):
        """Test that the system can recover from obstacle avoidance failures."""
        # Create a mock pattern planner
        mock_pattern_planner = MagicMock()

        # Create an AvoidanceAlgorithm instance
        avoidance_algorithm = AvoidanceAlgorithm(
            pattern_planner=mock_pattern_planner
        )

        # Mock the motor controller
        motor_controller = MagicMock()
        motor_controller.get_current_position.return_value = (0.0, 0.0)
        motor_controller.get_current_heading.return_value = 0.0

        # Set the motor controller on the avoidance algorithm
        avoidance_algorithm.motor_controller = motor_controller

        # Simulate obstacle detection
        avoidance_algorithm.obstacle_left = True
        avoidance_algorithm.obstacle_right = True

        # Detect the obstacle
        obstacle_detected, obstacle_data = (
            avoidance_algorithm._detect_obstacle()
        )

        # Verify that an obstacle was detected
        assert obstacle_detected is True
        assert obstacle_data is not None

        # Start avoidance
        avoidance_algorithm._start_avoidance()

        # Verify that the motor controller was called to execute the avoidance maneuver
        assert motor_controller.get_current_heading.called
        assert (
            motor_controller.rotate_to_heading.called
            or motor_controller.move_distance.called
        )

        # Simulate failed avoidance (obstacle still detected)
        motor_controller.get_status.return_value = "TARGET_REACHED"
        avoidance_algorithm.obstacle_left = True
        avoidance_algorithm.obstacle_right = True

        # Continue avoidance
        avoidance_complete = avoidance_algorithm._continue_avoidance()

        # Verify that avoidance is complete
        assert avoidance_complete is True

        # Detect the obstacle again
        obstacle_detected, _ = avoidance_algorithm._detect_obstacle()

        # Verify that the obstacle is still detected
        assert obstacle_detected is True

        # Execute recovery
        avoidance_algorithm.recovery_attempts = 0
        recovery_success = avoidance_algorithm._execute_recovery()

        # Verify that recovery was successful
        assert recovery_success is True

        # Verify that the motor controller was called to execute the recovery maneuver
        assert motor_controller.get_current_heading.called
        assert (
            motor_controller.rotate_to_heading.called
            or motor_controller.move_distance.called
        )

        # Simulate successful recovery (obstacle no longer detected)
        avoidance_algorithm.obstacle_left = False
        avoidance_algorithm.obstacle_right = False

        # Detect the obstacle again
        obstacle_detected, _ = avoidance_algorithm._detect_obstacle()

        # Verify that the obstacle is no longer detected
        assert obstacle_detected is False

    def test_navigation_error_recovery(self, setup_error_recovery_components):
        """Test that the system can recover from navigation errors."""
        # Get the components
        mower = setup_error_recovery_components["mower"]
        resource_manager = setup_error_recovery_components["resource_manager"]

        # Mock the navigation controller
        mock_navigation = MagicMock()
        resource_manager.get_navigation.return_value = mock_navigation

        # Mock the path planner
        mock_path_planner = MagicMock()
        resource_manager.get_path_planner.return_value = mock_path_planner

        # Simulate a navigation error
        mock_navigation.get_status.return_value = {"error": "GPS signal lost"}

        # Get the mower status
        status = mower.get_status()

        # Verify that the error is reported in the status
        assert "error" in status
        assert status["error"] == "GPS signal lost"

        # Simulate recovery from the navigation error
        mock_navigation.get_status.return_value = {
            "position": (0.0, 0.0),
            "heading": 0.0,
        }

        # Get the mower status again
        status = mower.get_status()

        # Verify that the error is no longer reported
        assert "error" not in status or status["error"] is None
        assert "position" in status
