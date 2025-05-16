"""
Test module for test_avoidance_algorithm.py.
"""

import pytest
import threading
import time
from unittest.mock import MagicMock, patch, call

from mower.obstacle_detection.avoidance_algorithm import (
    AvoidanceAlgorithm,
    AvoidanceState,
    Obstacle,
    NavigationStatus,
)


class TestAvoidanceAlgorithm:
    """Tests for the AvoidanceAlgorithm class ."""

    def test_initialization(self):
        """Test initialization of the avoidance algorithm."""
        # Create a mock pattern planner
        mock_pattern_planner = MagicMock()

        # Create an AvoidanceAlgorithm instance
        avoidance_algorithm = AvoidanceAlgorithm(
            pattern_planner=mock_pattern_planner
        )

        # Verify that the pattern planner was stored correctly
        assert avoidance_algorithm.pattern_planner is mock_pattern_planner

        # Verify that the avoidance algorithm was initialized correctly
        assert avoidance_algorithm.current_state == AvoidanceState.NORMAL
        assert avoidance_algorithm.obstacle_data is None
        assert avoidance_algorithm.thread_lock is not None
        assert avoidance_algorithm.running is False
        assert avoidance_algorithm.stop_thread is False
        assert avoidance_algorithm.avoidance_thread is None
        assert avoidance_algorithm.recovery_attempts == 0
        assert avoidance_algorithm.max_recovery_attempts == 3

    @patch("mower.obstacle_detection.avoidance_algorithm.threading.Thread")
    def test_start(self, mock_thread):
        """Test starting the avoidance algorithm."""
        # Create a mock pattern planner
        mock_pattern_planner = MagicMock()

        # Create an AvoidanceAlgorithm instance
        avoidance_algorithm = AvoidanceAlgorithm(
            pattern_planner=mock_pattern_planner
        )

        # Call start
        avoidance_algorithm.start()

        # Verify that the thread was started
        mock_thread.assert_called_once_with(
            target=avoidance_algorithm._avoidance_loop, daemon=True
        )
        mock_thread.return_value.start.assert_called_once()

        # Verify that the state was updated
        assert avoidance_algorithm.running is True
        assert avoidance_algorithm.stop_thread is False
        assert avoidance_algorithm.current_state == AvoidanceState.NORMAL
        assert (
            avoidance_algorithm.avoidance_thread is mock_thread.return_value
        )

    def test_stop(self):
        """Test stopping the avoidance algorithm."""
        # Create a mock pattern planner
        mock_pattern_planner = MagicMock()

        # Create an AvoidanceAlgorithm instance
        avoidance_algorithm = AvoidanceAlgorithm(
            pattern_planner=mock_pattern_planner
        )

        # Set up the avoidance thread
        mock_thread = MagicMock()
        avoidance_algorithm.avoidance_thread = mock_thread
        avoidance_algorithm.running = True

        # Call stop
        avoidance_algorithm.stop()

        # Verify that the thread was joined
        mock_thread.join.assert_called_once()

        # Verify that the state was updated
        assert avoidance_algorithm.running is False
        assert avoidance_algorithm.stop_thread is True
        assert avoidance_algorithm.avoidance_thread is None

    def test_detect_obstacle(self):
        """Test detecting obstacles."""
        # Create a mock pattern planner
        mock_pattern_planner = MagicMock()

        # Create an AvoidanceAlgorithm instance
        avoidance_algorithm = AvoidanceAlgorithm(
            pattern_planner=mock_pattern_planner
        )

        # Set up obstacle data
        avoidance_algorithm.obstacle_left = True
        avoidance_algorithm.obstacle_right = False
        avoidance_algorithm.camera_obstacle_detected = False
        avoidance_algorithm.dropoff_detected = False

        # Call _detect_obstacle
        obstacle_detected, obstacle_data = (
            avoidance_algorithm._detect_obstacle()
        )

        # Verify that an obstacle was detected
        assert obstacle_detected is True
        assert obstacle_data is not None
        assert obstacle_data["left_sensor"] is True
        assert obstacle_data["right_sensor"] is False
        assert obstacle_data["camera_detected"] is False
        assert obstacle_data["dropoff_detected"] is False
        assert "timestamp" in obstacle_data

        # Set up no obstacle data
        avoidance_algorithm.obstacle_left = False
        avoidance_algorithm.obstacle_right = False
        avoidance_algorithm.camera_obstacle_detected = False
        avoidance_algorithm.dropoff_detected = False

        # Call _detect_obstacle
        obstacle_detected, obstacle_data = (
            avoidance_algorithm._detect_obstacle()
        )

        # Verify that no obstacle was detected
        assert obstacle_detected is False
        assert obstacle_data is None

    def test_start_avoidance(self):
        """Test starting obstacle avoidance."""
        # Create a mock pattern planner
        mock_pattern_planner = MagicMock()

        # Create an AvoidanceAlgorithm instance
        avoidance_algorithm = AvoidanceAlgorithm(
            pattern_planner=mock_pattern_planner
        )

        # Set up obstacle data
        avoidance_algorithm.obstacle_data = {
            "left_sensor": True,
            "right_sensor": False,
            "camera_detected": False,
            "dropoff_detected": False,
            "timestamp": time.time(),
        }

        # Mock the avoidance strategies
        avoidance_algorithm._turn_right_strategy = MagicMock(
            return_value=True
        )
        avoidance_algorithm._turn_left_strategy = MagicMock(return_value=True)
        avoidance_algorithm._backup_strategy = MagicMock(return_value=True)
        avoidance_algorithm.motor_controller = MagicMock()

        # Call _start_avoidance
        result = avoidance_algorithm._start_avoidance()

        # Verify that the appropriate strategy was called
        avoidance_algorithm._turn_right_strategy.assert_called_once()
        avoidance_algorithm._turn_left_strategy.assert_not_called()
        avoidance_algorithm._backup_strategy.assert_not_called()

        # Verify that the function return ed True
        assert result is True

        # Set up different obstacle data
        avoidance_algorithm.obstacle_data = {
            "left_sensor": False,
            "right_sensor": True,
            "camera_detected": False,
            "dropoff_detected": False,
            "timestamp": time.time(),
        }

        # Reset the mocks
        avoidance_algorithm._turn_right_strategy.reset_mock()
        avoidance_algorithm._turn_left_strategy.reset_mock()
        avoidance_algorithm._backup_strategy.reset_mock()

        # Call _start_avoidance
        result = avoidance_algorithm._start_avoidance()

        # Verify that the appropriate strategy was called
        avoidance_algorithm._turn_right_strategy.assert_not_called()
        avoidance_algorithm._turn_left_strategy.assert_called_once()
        avoidance_algorithm._backup_strategy.assert_not_called()

        # Verify that the function return ed True
        assert result is True

    def test_continue_avoidance(self):
        """Test continuing obstacle avoidance."""
        # Create a mock pattern planner
        mock_pattern_planner = MagicMock()

        # Create an AvoidanceAlgorithm instance
        avoidance_algorithm = AvoidanceAlgorithm(
            pattern_planner=mock_pattern_planner
        )

        # Set up the motor controller
        avoidance_algorithm.motor_controller = MagicMock()

        # Test when avoidance is complete
        avoidance_algorithm.motor_controller.get_status.return_value = (
            NavigationStatus.TARGET_REACHED
        )

        # Call _continue_avoidance
        result = avoidance_algorithm._continue_avoidance()

        # Verify that the function return ed True
        assert result is True

        # Test when avoidance is still in progress
        avoidance_algorithm.motor_controller.get_status.return_value = (
            NavigationStatus.MOVING
        )

        # Call _continue_avoidance
        result = avoidance_algorithm._continue_avoidance()

        # Verify that the function return ed False
        assert result is False

        # Test when there's an error
        avoidance_algorithm.motor_controller.get_status.return_value = (
            NavigationStatus.ERROR
        )

        # Call _continue_avoidance
        result = avoidance_algorithm._continue_avoidance()

        # Verify that the function return ed False
        assert result is False

    def test_execute_recovery(self):
        """Test executing recovery strategies."""
        # Create a mock pattern planner
        mock_pattern_planner = MagicMock()

        # Create an AvoidanceAlgorithm instance
        avoidance_algorithm = AvoidanceAlgorithm(
            pattern_planner=mock_pattern_planner
        )

        # Set up the obstacle data
        avoidance_algorithm.obstacle_data = {
            "left_sensor": True,
            "right_sensor": False,
            "camera_detected": False,
            "dropoff_detected": False,
            "timestamp": time.time(),
        }

        # Mock the recovery strategies
        avoidance_algorithm._turn_right_strategy = MagicMock(
            return_value=True
        )
        avoidance_algorithm._turn_left_strategy = MagicMock(return_value=True)
        avoidance_algorithm._backup_strategy = MagicMock(return_value=True)
        avoidance_algorithm._alternative_route_strategy = MagicMock(
            return_value=True
        )

        # Test first recovery attempt
        avoidance_algorithm.recovery_attempts = 0

        # Call _execute_recovery
        result = avoidance_algorithm._execute_recovery()

        # Verify that the appropriate strategy was called
        avoidance_algorithm._turn_right_strategy.assert_called_once()
        avoidance_algorithm._turn_left_strategy.assert_not_called()
        avoidance_algorithm._backup_strategy.assert_not_called()
        avoidance_algorithm._alternative_route_strategy.assert_not_called()

        # Verify that the function return ed True
        assert result is True

        # Reset the mocks
        avoidance_algorithm._turn_right_strategy.reset_mock()
        avoidance_algorithm._turn_left_strategy.reset_mock()
        avoidance_algorithm._backup_strategy.reset_mock()
        avoidance_algorithm._alternative_route_strategy.reset_mock()

        # Test second recovery attempt
        avoidance_algorithm.recovery_attempts = 1

        # Call _execute_recovery
        result = avoidance_algorithm._execute_recovery()

        # Verify that the appropriate strategy was called
        avoidance_algorithm._turn_right_strategy.assert_not_called()
        avoidance_algorithm._turn_left_strategy.assert_not_called()
        avoidance_algorithm._backup_strategy.assert_called_once()
        avoidance_algorithm._alternative_route_strategy.assert_not_called()

        # Verify that the function return ed True
        assert result is True

        # Reset the mocks
        avoidance_algorithm._turn_right_strategy.reset_mock()
        avoidance_algorithm._turn_left_strategy.reset_mock()
        avoidance_algorithm._backup_strategy.reset_mock()
        avoidance_algorithm._alternative_route_strategy.reset_mock()

        # Test third recovery attempt
        avoidance_algorithm.recovery_attempts = 2

        # Call _execute_recovery
        result = avoidance_algorithm._execute_recovery()

        # Verify that the appropriate strategy was called
        avoidance_algorithm._turn_right_strategy.assert_not_called()
        avoidance_algorithm._turn_left_strategy.assert_not_called()
        avoidance_algorithm._backup_strategy.assert_not_called()
        avoidance_algorithm._alternative_route_strategy.assert_called_once()

        # Verify that the function return ed True
        assert result is True

    def test_select_random_strategy(self):
        """Test selecting a random avoidance strategy."""
        # Create a mock pattern planner
        mock_pattern_planner = MagicMock()

        # Create an AvoidanceAlgorithm instance
        avoidance_algorithm = AvoidanceAlgorithm(
            pattern_planner=mock_pattern_planner
        )

        # Mock the avoidance strategies
        avoidance_algorithm._turn_right_strategy = MagicMock(
            return_value=True
        )
        avoidance_algorithm._turn_left_strategy = MagicMock(return_value=True)
        avoidance_algorithm._backup_strategy = MagicMock(return_value=True)

        # Call _select_random_strategy
        result = avoidance_algorithm._select_random_strategy()

        # Verify that one of the strategies was called
        assert (
            avoidance_algorithm._turn_right_strategy.called
            or avoidance_algorithm._turn_left_strategy.called
            or avoidance_algorithm._backup_strategy.called
        )

        # Verify that the function return ed True
        assert result is True

    def test_turn_right_strategy(self):
        """Test the turn right avoidance strategy."""
        # Create a mock pattern planner
        mock_pattern_planner = MagicMock()

        # Create an AvoidanceAlgorithm instance
        avoidance_algorithm = AvoidanceAlgorithm(
            pattern_planner=mock_pattern_planner
        )

        # Set up the motor controller
        avoidance_algorithm.motor_controller = MagicMock()
        avoidance_algorithm.motor_controller.get_current_heading.return_value = (
            0.0)

        # Call _turn_right_strategy
        result = avoidance_algorithm._turn_right_strategy(angle=45.0)

        # Verify that the motor controller was called correctly
        avoidance_algorithm.motor_controller.get_current_heading.assert_called_once()
        avoidance_algorithm.motor_controller.rotate_to_heading.assert_called_once_with(
            45.0)

        # Verify that the function return ed True
        assert result is True

    def test_turn_left_strategy(self):
        """Test the turn left avoidance strategy."""
        # Create a mock pattern planner
        mock_pattern_planner = MagicMock()

        # Create an AvoidanceAlgorithm instance
        avoidance_algorithm = AvoidanceAlgorithm(
            pattern_planner=mock_pattern_planner
        )

        # Set up the motor controller
        avoidance_algorithm.motor_controller = MagicMock()
        avoidance_algorithm.motor_controller.get_current_heading.return_value = (
            45.0)

        # Call _turn_left_strategy
        result = avoidance_algorithm._turn_left_strategy(angle=45.0)

        # Verify that the motor controller was called correctly
        avoidance_algorithm.motor_controller.get_current_heading.assert_called_once()
        avoidance_algorithm.motor_controller.rotate_to_heading.assert_called_once_with(
            0.0)

        # Verify that the function return ed True
        assert result is True

    def test_backup_strategy(self):
        """Test the backup avoidance strategy."""
        # Create a mock pattern planner
        mock_pattern_planner = MagicMock()

        # Create an AvoidanceAlgorithm instance
        avoidance_algorithm = AvoidanceAlgorithm(
            pattern_planner=mock_pattern_planner
        )

        # Set up the motor controller
        avoidance_algorithm.motor_controller = MagicMock()
        avoidance_algorithm.motor_controller.get_current_heading.return_value = (
            0.0)

        # Mock the time.sleep function
        with patch(
            "mower.obstacle_detection.avoidance_algorithm.time.sleep"
        ) as mock_sleep:
            # Call _backup_strategy
            result = avoidance_algorithm._backup_strategy(distance=30.0)

            # Verify that the motor controller was called correctly
            avoidance_algorithm.motor_controller.get_current_heading.assert_called_once()
            avoidance_algorithm.motor_controller.rotate_to_heading.assert_called_once_with(
                180.0)
            mock_sleep.assert_called_once_with(2.0)
            avoidance_algorithm.motor_controller.move_distance.assert_called_once_with(
                0.3)

            # Verify that the function return ed True
            assert result is True

    def test_alternative_route_strategy(self):
        """Test the alternative route avoidance strategy."""
        # Create a mock pattern planner
        mock_pattern_planner = MagicMock()

        # Create an AvoidanceAlgorithm instance
        avoidance_algorithm = AvoidanceAlgorithm(
            pattern_planner=mock_pattern_planner
        )

        # Set up the motor controller
        avoidance_algorithm.motor_controller = MagicMock()
        avoidance_algorithm.motor_controller.get_current_position.return_value = (
            0.0, 0.0, )

        # Set up the pattern planner
        avoidance_algorithm.pattern_planner.get_current_goal.return_value = (
            10.0,
            10.0,
        )
        avoidance_algorithm.pattern_planner.coord_to_grid.return_value = (
            0,
            0,
        )
        avoidance_algorithm.pattern_planner.get_path.return_value = [
            {"lat": 1.0, "lng": 1.0},
            {"lat": 2.0, "lng": 2.0},
            {"lat": 3.0, "lng": 3.0},
        ]

        # Mock the _estimate_obstacle_position method
        avoidance_algorithm._estimate_obstacle_position = MagicMock(
            return_value={
                "position": (5.0, 5.0),
                "type": "static",
                "confidence": 0.8,
                "sensor": "tof_left",
            }
        )

        # Call _alternative_route_strategy
        result = avoidance_algorithm._alternative_route_strategy()

        # Verify that the pattern planner was called correctly
        avoidance_algorithm._estimate_obstacle_position.assert_called_once()
        avoidance_algorithm.pattern_planner.update_obstacle_map.assert_called_once_with(
            [(5.0, 5.0)]
        )
        avoidance_algorithm.pattern_planner.get_current_goal.assert_called_once()
        avoidance_algorithm.pattern_planner.coord_to_grid.assert_called()
        avoidance_algorithm.pattern_planner.get_path.assert_called_once()

        # Verify that the motor controller was called correctly
        avoidance_algorithm.motor_controller.navigate_to_location.assert_called_once_with(
            (1.0, 1.0))

        # Verify that the function return ed True
        assert result is True

    def test_estimate_obstacle_position(self):
        """Test estimating obstacle position."""
        # Create a mock pattern planner
        mock_pattern_planner = MagicMock()

        # Create an AvoidanceAlgorithm instance
        avoidance_algorithm = AvoidanceAlgorithm(
            pattern_planner=mock_pattern_planner
        )

        # Set up the motor controller
        avoidance_algorithm.motor_controller = MagicMock()
        avoidance_algorithm.motor_controller.get_current_position.return_value = (
            0.0, 0.0, )
        avoidance_algorithm.motor_controller.get_current_heading.return_value = (
            0.0)

        # Set up obstacle data
        avoidance_algorithm.obstacle_data = {
            "left_sensor": True,
            "right_sensor": False,
            "camera_detected": False,
            "dropoff_detected": False,
            "timestamp": time.time(),
        }

        # Call _estimate_obstacle_position
        result = avoidance_algorithm._estimate_obstacle_position()

        # Verify that the result is a dictionary with the expected keys
        assert isinstance(result, dict)
        assert "position" in result
        assert "type" in result
        assert "confidence" in result
        assert "sensor" in result

        # Verify that the position is a tuple of two floats
        assert isinstance(result["position"], tuple)
        assert len(result["position"]) == 2
        assert isinstance(result["position"][0], float)
        assert isinstance(result["position"][1], float)

    def test_check_obstacles(self):
        """Test checking for obstacles."""
        # Create a mock pattern planner
        mock_pattern_planner = MagicMock()

        # Create an AvoidanceAlgorithm instance
        avoidance_algorithm = AvoidanceAlgorithm(
            pattern_planner=mock_pattern_planner
        )

        # Mock the _get_sensor_data and _process_sensor_data methods
        avoidance_algorithm._get_sensor_data = MagicMock(
            return_value=[0.5, 0.6, 0.7]
        )
        avoidance_algorithm._process_sensor_data = MagicMock(
            return_value=[
                Obstacle(position=(1.0, 1.0), size=0.2, confidence=0.8)
            ]
        )

        # Call check_obstacles
        result = avoidance_algorithm.check_obstacles()

        # Verify that the methods were called
        avoidance_algorithm._get_sensor_data.assert_called_once()
        avoidance_algorithm._process_sensor_data.assert_called_once_with(
            [0.5, 0.6, 0.7]
        )

        # Verify that the function return ed True
        assert result is True

        # Verify that the obstacles were stored
        assert len(avoidance_algorithm.obstacles) == 1
        assert avoidance_algorithm.obstacles[0].position == (1.0, 1.0)
        assert avoidance_algorithm.obstacles[0].size == 0.2
        assert avoidance_algorithm.obstacles[0].confidence == 0.8

        # Test with no obstacles
        avoidance_algorithm._process_sensor_data.return_value = []

        # Call check_obstacles
        result = avoidance_algorithm.check_obstacles()

        # Verify that the function return ed False
        assert result is False

    def test_avoid_obstacle(self):
        """Test avoiding obstacles."""
        # Create a mock pattern planner
        mock_pattern_planner = MagicMock()

        # Create an AvoidanceAlgorithm instance
        avoidance_algorithm = AvoidanceAlgorithm(
            pattern_planner=mock_pattern_planner
        )

        # Set up obstacles
        avoidance_algorithm.obstacles = [
            Obstacle(position=(5.0, 5.0), size=0.2, confidence=0.8)
        ]

        # Mock the _find_obstacle_positions and _modify_path methods
        avoidance_algorithm._find_obstacle_positions = MagicMock(
            return_value=[5]
        )
        avoidance_algorithm._modify_path = MagicMock(
            return_value=[(0, 0), (2, 2), (4, 4), (6, 6), (8, 8), (10, 10)]
        )

        # Set up the pattern planner
        avoidance_algorithm.pattern_planner.current_path = [
            (0, 0),
            (2, 2),
            (4, 4),
            (5, 5),
            (6, 6),
            (8, 8),
            (10, 10),
        ]

        # Call avoid_obstacle
        result = avoidance_algorithm.avoid_obstacle()

        # Verify that the methods were called
        avoidance_algorithm._find_obstacle_positions.assert_called_once_with(
            avoidance_algorithm.pattern_planner.current_path,
            avoidance_algorithm.obstacles,
        )
        avoidance_algorithm._modify_path.assert_called_once_with(
            avoidance_algorithm.pattern_planner.current_path, [5]
        )

        # Verify that the pattern planner's current path was updated
        assert avoidance_algorithm.pattern_planner.current_path == [
            (0, 0),
            (2, 2),
            (4, 4),
            (6, 6),
            (8, 8),
            (10, 10),
        ]

        # Verify that the function returned True
        assert result is True

        # Test with no obstacles
        avoidance_algorithm.obstacles = []

        # Call avoid_obstacle
        result = avoidance_algorithm.avoid_obstacle()

        # Verify that the function return ed True
        assert result is True
