"""
Test module for test_navigation_obstacle_avoidance.py.
"""
import pytest
from unittest.mock import MagicMock  # patch was unused

from mower.navigation.path_planner import (
    PathPlanner,
    PatternConfig,
    LearningConfig,
    PatternType,
)
from mower.obstacle_detection.avoidance_algorithm import (
    AvoidanceAlgorithm,
    NavigationStatus,  # AvoidanceState and Obstacle were unused
)


class TestNavigationObstacleAvoidance:
    """Integration tests for navigation and obstacle avoidance."""

    @pytest.fixture
    def setup_navigation_and_avoidance(self):
        """Set up navigation and obstacle avoidance components for testing."""
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

        # Create a PathPlanner instance
        path_planner = PathPlanner(pattern_config, learning_config)

        # Create an AvoidanceAlgorithm instance
        avoidance_algorithm = AvoidanceAlgorithm(pattern_planner=path_planner)

        # Mock the motor controller
        motor_controller = MagicMock()
        motor_controller.get_current_position.return_value = (0.0, 0.0)
        motor_controller.get_current_heading.return_value = 0.0
        motor_controller.get_status.return_value = NavigationStatus.IDLE

        # Set the motor controller on the avoidance algorithm
        avoidance_algorithm.motor_controller = motor_controller

        return {
            "path_planner": path_planner,
            "avoidance_algorithm": avoidance_algorithm,
            "motor_controller": motor_controller,
        }

    def test_path_planning_with_obstacle_avoidance(
        self, setup_navigation_and_avoidance
    ):
        """Test that path planning works correctly with obstacle avoidance."""
        # Get the components
        path_planner = setup_navigation_and_avoidance["path_planner"]
        avoidance_algorithm = setup_navigation_and_avoidance[
            "avoidance_algorithm"
        ]
        motor_controller = setup_navigation_and_avoidance["motor_controller"]

        # Generate a path
        original_path = path_planner.generate_path()

        # Verify that a path was generated
        assert len(original_path) > 0

        # Add an obstacle
        obstacle_position = (5.0, 5.0)
        path_planner.update_obstacle_map([obstacle_position])

        # Simulate obstacle detection
        avoidance_algorithm.obstacle_left = True
        avoidance_algorithm.obstacle_right = False
        avoidance_algorithm.camera_obstacle_detected = False
        avoidance_algorithm.dropoff_detected = False

        # Detect the obstacle
        obstacle_detected, obstacle_data = (
            avoidance_algorithm._detect_obstacle()
        )

        # Verify that an obstacle was detected
        assert obstacle_detected is True
        assert obstacle_data is not None

        # Start avoidance
        avoidance_algorithm._start_avoidance()

        # Verify that the motor controller was called to execute the avoidance
        # maneuver
        assert motor_controller.get_current_heading.called
        assert (
            motor_controller.rotate_to_heading.called
            or motor_controller.move_distance.called
        )

        # Generate a new path that avoids the obstacle
        new_path = path_planner.generate_path()

        # Verify that a new path was generated
        assert len(new_path) > 0

        # Verify that the new path avoids the obstacle
        for point in new_path:
            # Check that the point is not too close to the obstacle
            distance = (
                (point[0] - obstacle_position[0]) ** 2 +
                (point[1] - obstacle_position[1]) ** 2) ** 0.5
            assert distance > 0.5  # Minimum distance from obstacle

    def test_obstacle_avoidance_during_navigation(
        self, setup_navigation_and_avoidance
    ):
        """Test that obstacle avoidance works correctly during navigation."""
        # Get the components
        path_planner = setup_navigation_and_avoidance["path_planner"]
        avoidance_algorithm = setup_navigation_and_avoidance[
            "avoidance_algorithm"
        ]
        motor_controller = setup_navigation_and_avoidance["motor_controller"]

        # Generate a path
        path = path_planner.generate_path()

        # Verify that a path was generated
        assert len(path) > 0

        # Start navigation
        motor_controller.get_status.return_value = NavigationStatus.MOVING

        # Simulate obstacle detection during navigation
        avoidance_algorithm.obstacle_left = True
        avoidance_algorithm.obstacle_right = False
        avoidance_algorithm.camera_obstacle_detected = False
        avoidance_algorithm.dropoff_detected = False

        # Detect the obstacle
        obstacle_detected, obstacle_data = (
            avoidance_algorithm._detect_obstacle()
        )

        # Verify that an obstacle was detected
        assert obstacle_detected is True
        assert obstacle_data is not None

        # Start avoidance
        avoidance_algorithm._start_avoidance()

        # Verify that the motor controller was called to execute the avoidance
        # maneuver
        assert motor_controller.get_current_heading.called
        assert (
            motor_controller.rotate_to_heading.called
            or motor_controller.move_distance.called
        )

        # Simulate successful avoidance
        motor_controller.get_status.return_value = (
            NavigationStatus.TARGET_REACHED
        )

        # Continue avoidance
        avoidance_complete = avoidance_algorithm._continue_avoidance()

        # Verify that avoidance is complete
        assert avoidance_complete is True

        # Verify that the obstacle is added to the obstacle map
        obstacle_position = avoidance_algorithm._estimate_obstacle_position()
        assert obstacle_position is not None
        assert "position" in obstacle_position

        # Generate a new path that avoids the obstacle
        new_path = path_planner.generate_path()

        # Verify that a new path was generated
        assert len(new_path) > 0

        # Verify that the new path avoids the obstacle
        if obstacle_position and "position" in obstacle_position:
            for point in new_path:
                # Check that the point is not too close to the obstacle
                distance = (
                    (point[0] - obstacle_position["position"][0]) ** 2 +
                    (point[1] - obstacle_position["position"][1]) ** 2) ** 0.5
                assert distance > 0.5  # Minimum distance from obstacle

    def test_recovery_from_persistent_obstacle(
        self, setup_navigation_and_avoidance
    ):
        """Test recovery from a persistent obstacle that cannot be avoided."""
        # Get the components
        path_planner = setup_navigation_and_avoidance["path_planner"]
        avoidance_algorithm = setup_navigation_and_avoidance[
            "avoidance_algorithm"
        ]
        motor_controller = setup_navigation_and_avoidance["motor_controller"]

        # Generate a path
        path = path_planner.generate_path()

        # Verify that a path was generated
        assert len(path) > 0

        # Start navigation
        motor_controller.get_status.return_value = NavigationStatus.MOVING

        # Simulate obstacle detection during navigation
        avoidance_algorithm.obstacle_left = True
        avoidance_algorithm.obstacle_right = True
        avoidance_algorithm.camera_obstacle_detected = True
        avoidance_algorithm.dropoff_detected = False

        # Detect the obstacle
        obstacle_detected, obstacle_data = (
            avoidance_algorithm._detect_obstacle()
        )

        # Verify that an obstacle was detected
        assert obstacle_detected is True
        assert obstacle_data is not None

        # Start avoidance
        avoidance_algorithm._start_avoidance()

        # Verify that the motor controller was called to execute the avoidance
        # maneuver
        assert motor_controller.get_current_heading.called
        assert (
            motor_controller.rotate_to_heading.called
            or motor_controller.move_distance.called
        )

        # Simulate failed avoidance(obstacle still detected)
        motor_controller.get_status.return_value = (
            NavigationStatus.TARGET_REACHED
        )
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

        # Verify that the motor controller was called to execute the recovery
        # maneuver
        assert motor_controller.get_current_heading.called
        assert (
            motor_controller.rotate_to_heading.called
            or motor_controller.move_distance.called
        )

        # Simulate successful recovery(obstacle no longer detected)
        avoidance_algorithm.obstacle_left = False
        avoidance_algorithm.obstacle_right = False
        avoidance_algorithm.camera_obstacle_detected = False

        # Detect the obstacle again
        obstacle_detected, _ = avoidance_algorithm._detect_obstacle()

        # Verify that the obstacle is no longer detected
        assert obstacle_detected is False
