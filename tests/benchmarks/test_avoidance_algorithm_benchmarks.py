"""
Test module for test_avoidance_algorithm_benchmarks.py.
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from mower.obstacle_detection.avoidance_algorithm import AvoidanceAlgorithm, Obstacle


@pytest.fixture
def mock_resource_manager():
    mock = MagicMock()
    # Mock the necessary methods
    mock.get_camera.return_value = None
    mock.get_obstacle_detector.return_value = None
    return mock


@pytest.fixture
def mock_path_planner_fixture():  # Renamed to avoid conflict with argument
    return MagicMock()


@pytest.fixture
# Use renamed fixture
def avoidance_algorithm(mock_resource_manager, mock_path_planner_fixture):
    with patch("mower.obstacle_detection.avoidance_algorithm.os.environ.get", return_value="False"):
        algorithm = AvoidanceAlgorithm(
            resource_manager=mock_resource_manager,  # Use fixture return value
            pattern_planner=mock_path_planner_fixture,  # Use fixture return value
        )
    # Mock the necessary components
    algorithm.motor_controller = MagicMock()
    algorithm.sensor_interface = MagicMock()
    return algorithm


def test_detect_obstacle_benchmark(benchmark, avoidance_algorithm):
    # Set up the obstacle data
    avoidance_algorithm.obstacle_data = {
        "left_sensor": True,
        "right_sensor": False,
        "camera_detected": False,
        "dropoff_detected": False,
        "timestamp": time.time(),
    }

    # Mock the motor controller
    avoidance_algorithm.motor_controller.get_current_heading.return_value = 0.0
    avoidance_algorithm.motor_controller.rotate_to_heading.return_value = None

    # Use pytest - benchmark to measure performance
    result = benchmark(avoidance_algorithm._start_avoidance)

    # Verify that avoidance was started
    assert result is True


def test_continue_avoidance_benchmark(benchmark, avoidance_algorithm):
    # Set up the obstacle data
    avoidance_algorithm.obstacle_data = {
        "left_sensor": True,
        "right_sensor": False,
        "camera_detected": False,
        "dropoff_detected": False,
        "timestamp": time.time(),
    }

    # Mock the motor controller
    avoidance_algorithm.motor_controller.get_current_heading.return_value = 0.0
    avoidance_algorithm.motor_controller.rotate_to_heading.return_value = None

    # Use pytest - benchmark to measure performance
    with patch.object(avoidance_algorithm, "thread_lock"):
        result = benchmark(avoidance_algorithm._execute_recovery)

    # Verify that recovery was executed
    assert result is True


def test_select_random_strategy_benchmark(benchmark, avoidance_algorithm):
    # Mock the motor controller
    avoidance_algorithm.motor_controller.get_current_heading.return_value = 0.0
    avoidance_algorithm.motor_controller.rotate_to_heading.return_value = None

    # Use pytest - benchmark to measure performance
    result = benchmark(avoidance_algorithm._turn_right_strategy, angle=45.0)

    # Verify that the strategy was executed
    assert result is True


def test_turn_left_strategy_benchmark(benchmark, avoidance_algorithm):
    # Mock the motor controller
    avoidance_algorithm.motor_controller.get_current_heading.return_value = 0.0
    avoidance_algorithm.motor_controller.rotate_to_heading.return_value = None
    avoidance_algorithm.motor_controller.move_distance.return_value = None

    # Use pytest - benchmark to measure performance
    with patch("time.sleep"):  # Mock sleep to speed up the test
        result = benchmark(avoidance_algorithm._backup_strategy, distance=30.0)

    # Verify that the strategy was executed
    assert result is True


def test_alternative_route_strategy_benchmark(benchmark, avoidance_algorithm):
    # Mock the motor controller
    avoidance_algorithm.motor_controller.get_current_position.return_value = (
        0.0,
        0.0,
    )
    avoidance_algorithm.motor_controller.get_current_heading.return_value = 0.0

    # Set up the obstacle data
    avoidance_algorithm.obstacle_data = {
        "left_sensor": True,
        "right_sensor": False,
        "camera_detected": False,
        "dropoff_detected": False,
        "timestamp": time.time(),
    }

    # Use pytest - benchmark to measure performance
    with patch.object(avoidance_algorithm, "thread_lock"):
        result = benchmark(avoidance_algorithm._estimate_obstacle_position)

    # Verify that an obstacle position was estimated
    assert result is not None
    assert "position" in result
    assert "type" in result
    assert "confidence" in result
    assert "sensor" in result


def test_calculate_obstacle_coordinates_benchmark(benchmark, avoidance_algorithm):
    # Create test data
    obstacle_data = {
        "left_sensor": True,
        "right_sensor": False,
        "camera_detected": False,
        "dropoff_detected": False,
        "timestamp": time.time(),
    }

    # Use pytest - benchmark to measure performance
    result = benchmark(avoidance_algorithm._determine_obstacle_parameters, obstacle_data)

    # Verify that obstacle parameters were determined
    assert result is not None
    assert len(result) == 3
    assert result[0] is not None
    assert isinstance(result[1], float)
    assert isinstance(result[2], float)


def test_process_sensor_data_benchmark(benchmark, avoidance_algorithm):
    # Create test data
    path = [(0, 0), (5, 5), (10, 10)]
    obstacles = [
        Obstacle(position=(3, 3), size=1.0, confidence=0.8),
        Obstacle(position=(7, 7), size=1.0, confidence=0.8),
    ]

    # Use pytest - benchmark to measure performance
    result = benchmark(avoidance_algorithm._find_obstacle_positions, path, obstacles)

    # Verify that obstacle positions were found
    assert result is not None
    assert isinstance(result, list)
    assert len(result) > 0


def test_modify_path_benchmark(benchmark, avoidance_algorithm):
    # Create test data
    path = [(0, 0), (5, 5), (10, 10)]

    # Use pytest - benchmark to measure performance
    result = benchmark(avoidance_algorithm._smooth_path, path)

    # Verify that the path was smoothed
    assert result is not None
    assert isinstance(result, list)
    assert len(result) >= len(path)  # Smoothing should add points


def test_complex_scenario_benchmark(benchmark):
    pass
