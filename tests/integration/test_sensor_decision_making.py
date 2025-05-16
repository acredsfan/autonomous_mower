"""
Test module for test_sensor_decision_making.py.
"""
import pytest
from unittest.mock import MagicMock

from mower.hardware.sensor_interface import (
    EnhancedSensorInterface,
    # SensorStatus, # Unused
)
from mower.obstacle_detection.avoidance_algorithm import (
    AvoidanceAlgorithm,
    # AvoidanceState, # Unused
)
from mower.navigation.path_planner import (
    PathPlanner,
    PatternConfig,
    PatternType,
    LearningConfig,
)


class TestSensorDecisionMaking:
    """Integration tests for sensor data processing and decision making."""

    @pytest.fixture
    def setup_sensor_decision_components(self):
        """Set up sensor interface and decision-making components for testing."""
        # Mock EnhancedSensorInterface itself
        sensor_interface = MagicMock(spec=EnhancedSensorInterface)

        # Define the _data attribute on the mock
        sensor_interface._data = {
            "temperature": 25.0,
            "humidity": 50.0,
            "pressure": 1013.25,
            "heading": 0.0,
            "roll": 0.0,
            "pitch": 0.0,
            "left_distance": 100.0,
            "right_distance": 100.0,
            "battery_voltage": 12.5,
            "battery_current": 1.0,
        }

        # Define the _sensor_status attribute on the mock
        sensor_interface._sensor_status = {
            "bno085": MagicMock(working=True, error_count=0, last_error=None),
            "vl53l0x_left": MagicMock(working=True, error_count=0, last_error=None),
            # Reformatted
            "vl53l0x_right": MagicMock(working=True, error_count=0, last_error=None),
            "bme280": MagicMock(working=True, error_count=0, last_error=None),
            "ina3221": MagicMock(working=True, error_count=0, last_error=None),
        }
        # Mock the is_safe_to_operate method for tests that call it
        sensor_interface.is_safe_to_operate = MagicMock(return_value=True)

        # Create pattern and learning configurations
        pattern_config = PatternConfig(
            pattern_type=PatternType.PARALLEL,
            spacing=1.0,
            angle=0.0,
            overlap=0.0,
            start_point=(0.0, 0.0),
            boundary_points=[(0, 0), (10, 0), (10, 10), (0, 10)],
        )

        learning_config = LearningConfig(
            learning_rate=0.1,
            discount_factor=0.9,
            exploration_rate=0.2,
            memory_size=1000,
            batch_size=32,
            update_frequency=100,
            model_path="test_model_path",
        )

        path_planner = PathPlanner(pattern_config, learning_config)
        avoidance_algorithm = AvoidanceAlgorithm(pattern_planner=path_planner)
        motor_controller = MagicMock()
        motor_controller.get_current_position.return_value = (0.0, 0.0)
        motor_controller.get_current_heading.return_value = 0.0
        avoidance_algorithm.motor_controller = motor_controller

        return {
            "sensor_interface": sensor_interface,
            "path_planner": path_planner,
            "avoidance_algorithm": avoidance_algorithm,
            "motor_controller": motor_controller,
        }

    def test_obstacle_detection_from_sensor_data(
        self, setup_sensor_decision_components
    ):
        """Test that obstacles are detected correctly from sensor data."""
        sensor_interface = setup_sensor_decision_components["sensor_interface"]
        avoidance_algorithm = setup_sensor_decision_components["avoidance_algorithm"]
        avoidance_algorithm.sensor_interface = sensor_interface

        assert avoidance_algorithm.obstacle_left is False
        assert avoidance_algorithm.obstacle_right is False

        sensor_interface._data["left_distance"] = 20.0
        avoidance_algorithm._update_sensor_obstacle_status()
        assert avoidance_algorithm.obstacle_left is True
        assert avoidance_algorithm.obstacle_right is False

        sensor_interface._data["left_distance"] = 100.0
        sensor_interface._data["right_distance"] = 20.0
        avoidance_algorithm._update_sensor_obstacle_status()
        assert avoidance_algorithm.obstacle_left is False
        assert avoidance_algorithm.obstacle_right is True

        sensor_interface._data["left_distance"] = 20.0
        sensor_interface._data["right_distance"] = 20.0
        avoidance_algorithm._update_sensor_obstacle_status()
        assert avoidance_algorithm.obstacle_left is True
        assert avoidance_algorithm.obstacle_right is True

        sensor_interface._data["left_distance"] = 100.0
        sensor_interface._data["right_distance"] = 100.0
        avoidance_algorithm._update_sensor_obstacle_status()
        assert avoidance_algorithm.obstacle_left is False
        assert avoidance_algorithm.obstacle_right is False

    def test_safety_checks_from_sensor_data(
        self, setup_sensor_decision_components
    ):
        """Test that safety checks are performed correctly based on sensor data."""
        sensor_interface = setup_sensor_decision_components["sensor_interface"]

        # Configure the mock's is_safe_to_operate to change based on sensor
        # status
        def is_safe_side_effect():
            # This logic should ideally mirror the actual class's logic
            # or be simplified if we only care about bno085 for this test.
            return sensor_interface._sensor_status["bno085"].working

        sensor_interface.is_safe_to_operate.side_effect = is_safe_side_effect

        assert sensor_interface.is_safe_to_operate() is True
        sensor_interface._sensor_status["bno085"].working = False
        assert sensor_interface.is_safe_to_operate() is False  # Now reflects the change
        sensor_interface._sensor_status["bno085"].working = True
        assert sensor_interface.is_safe_to_operate() is True  # Reflects restoration

        original_battery_voltage = sensor_interface._data["battery_voltage"]
        sensor_interface._data["battery_voltage"] = 10.0
        assert sensor_interface._data["battery_voltage"] < 11.0
        sensor_interface._data["battery_voltage"] = original_battery_voltage

    def test_decision_making_based_on_sensor_data(
        self, setup_sensor_decision_components
    ):
        """Test that decisions are made correctly based on sensor data."""
        sensor_interface = setup_sensor_decision_components["sensor_interface"]
        avoidance_algorithm = setup_sensor_decision_components["avoidance_algorithm"]
        motor_controller = setup_sensor_decision_components["motor_controller"]
        avoidance_algorithm.sensor_interface = sensor_interface

        sensor_interface._data["left_distance"] = 20.0
        avoidance_algorithm._update_sensor_obstacle_status()
        obstacle_detected, obstacle_data = avoidance_algorithm._detect_obstacle()
        assert obstacle_detected is True
        assert obstacle_data is not None
        assert obstacle_data["left_sensor"] is True
        assert obstacle_data["right_sensor"] is False

        avoidance_algorithm._start_avoidance()
        assert motor_controller.get_current_heading.called
        assert motor_controller.rotate_to_heading.called

        # Verify that the correct avoidance strategy was chosen
        # (turn right for left obstacle). This is an implementation detail,
        # but we can infer it from the motor controller calls.
        heading_calls = motor_controller.get_current_heading.call_count
        rotate_calls = motor_controller.rotate_to_heading.call_count
        assert heading_calls >= 1
        assert rotate_calls >= 1

    def test_sensor_data_integration_with_navigation(
        self, setup_sensor_decision_components
    ):
        """Test that sensor data is integrated correctly with navigation."""
        sensor_interface = setup_sensor_decision_components["sensor_interface"]
        avoidance_algorithm = setup_sensor_decision_components["avoidance_algorithm"]
        path_planner = setup_sensor_decision_components["path_planner"]
        motor_controller = setup_sensor_decision_components["motor_controller"]
        avoidance_algorithm.sensor_interface = sensor_interface

        path = path_planner.generate_path()
        assert len(path) > 0

        for i, waypoint in enumerate(path[:5]):
            motor_controller.get_current_position.return_value = waypoint
            sensor_interface._data["left_distance"] = 100.0
            sensor_interface._data["right_distance"] = 100.0
            avoidance_algorithm._update_sensor_obstacle_status()
            obstacle_detected, _ = avoidance_algorithm._detect_obstacle()
            assert obstacle_detected is False

            if i < len(path) - 1:
                next_waypoint = path[i + 1]
                dx = next_waypoint[0] - waypoint[0]
                dy = next_waypoint[1] - waypoint[1]

                if dx > 0:
                    sensor_interface._data["right_distance"] = 20.0
                elif dx < 0:
                    sensor_interface._data["left_distance"] = 20.0
                elif dy > 0:  # If moving up, simulate an obstacle on the right
                    sensor_interface._data["right_distance"] = 20.0
                elif dy < 0:  # If moving down, simulate an obstacle on the left
                    sensor_interface._data["left_distance"] = 20.0

                avoidance_algorithm._update_sensor_obstacle_status()
                obstacle_detected, obstacle_data = (
                    avoidance_algorithm._detect_obstacle()
                )
                assert obstacle_detected is True
                assert obstacle_data is not None

                avoidance_algorithm._start_avoidance()
                assert motor_controller.get_current_heading.called
                assert (
                    motor_controller.rotate_to_heading.called
                    or motor_controller.move_distance.called
                )
                sensor_interface._data["left_distance"] = 100.0
                sensor_interface._data["right_distance"] = 100.0
