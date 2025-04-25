"""
Performance benchmarks for obstacle detection and avoidance algorithms.

This module contains benchmarks for the critical operations in the obstacle
detection and avoidance algorithms, including obstacle detection, position
estimation, and path modification.
"""

import pytest
import numpy as np
from typing import List, Tuple, Dict, Any
import time
from unittest.mock import MagicMock, patch

from mower.obstacle_detection.avoidance_algorithm import (
    AvoidanceAlgorithm, AvoidanceState, NavigationStatus, Obstacle
)
from mower.navigation.path_planner import (
    PathPlanner, PatternConfig, PatternType
)
from tests.benchmarks.utils import (
    generate_random_boundary, generate_random_obstacles,
    time_function, log_benchmark_results
)


@pytest.fixture
def mock_resource_manager():
    """Fixture for a mock resource manager."""
    mock = MagicMock()

    # Mock the necessary methods
    mock.get_camera.return_value = None
    mock.get_obstacle_detector.return_value = None

    return mock


@pytest.fixture
def mock_path_planner():
    """Fixture for a mock path planner."""
    mock = MagicMock()

    # Mock the necessary methods
    mock.generate_path.return_value = [(0, 0), (5, 5), (10, 10)]
    mock.update_obstacle_map.return_value = None
    mock.get_current_goal.return_value = (10, 10)
    mock.coord_to_grid.return_value = (100, 100)
    mock.get_path.return_value = [(0, 0), (5, 5), (10, 10)]

    return mock


@pytest.fixture
def avoidance_algorithm(mock_resource_manager, mock_path_planner):
    """Fixture for an AvoidanceAlgorithm instance."""
    with patch('mower.obstacle_detection.avoidance_algorithm.os.environ.get', return_value='False'):
        algorithm = AvoidanceAlgorithm(
            resource_manager=mock_resource_manager,
            pattern_planner=mock_path_planner
        )

    # Mock the necessary components
    algorithm.motor_controller = MagicMock()
    algorithm.sensor_interface = MagicMock()

    return algorithm


def test_detect_obstacle_benchmark(benchmark, avoidance_algorithm):
    """Benchmark the _detect_obstacle method."""
    # Set up the obstacle data
    with patch.object(avoidance_algorithm, 'thread_lock'):
        avoidance_algorithm.obstacle_left = True
        avoidance_algorithm.obstacle_right = False
        avoidance_algorithm.camera_obstacle_detected = False
        avoidance_algorithm.dropoff_detected = False

    # Use pytest-benchmark to measure performance
    with patch.object(avoidance_algorithm, 'thread_lock'):
        result = benchmark(avoidance_algorithm._detect_obstacle)

    # Verify that an obstacle was detected
    assert result is not None
    assert len(result) == 2
    assert result[0] is True  # Obstacle detected
    assert result[1] is not None  # Obstacle data


def test_start_avoidance_benchmark(benchmark, avoidance_algorithm):
    """Benchmark the _start_avoidance method."""
    # Set up the obstacle data
    avoidance_algorithm.obstacle_data = {
        "left_sensor": True,
        "right_sensor": False,
        "camera_detected": False,
        "dropoff_detected": False,
        "timestamp": time.time()
    }

    # Mock the motor controller
    avoidance_algorithm.motor_controller.get_current_heading.return_value = 0.0
    avoidance_algorithm.motor_controller.rotate_to_heading.return_value = None

    # Use pytest-benchmark to measure performance
    result = benchmark(avoidance_algorithm._start_avoidance)

    # Verify that avoidance was started
    assert result is True


def test_continue_avoidance_benchmark(benchmark, avoidance_algorithm):
    """Benchmark the _continue_avoidance method."""
    # Set up the obstacle data
    avoidance_algorithm.obstacle_data = {
        "left_sensor": True,
        "right_sensor": False,
        "camera_detected": False,
        "dropoff_detected": False,
        "timestamp": time.time()
    }

    # Mock the motor controller
    avoidance_algorithm.motor_controller.get_status.return_value = NavigationStatus.TARGET_REACHED

    # Use pytest-benchmark to measure performance
    result = benchmark(avoidance_algorithm._continue_avoidance)

    # Verify that avoidance is complete
    assert result is True


def test_execute_recovery_benchmark(benchmark, avoidance_algorithm):
    """Benchmark the _execute_recovery method."""
    # Set up the obstacle data
    avoidance_algorithm.obstacle_data = {
        "left_sensor": True,
        "right_sensor": False,
        "camera_detected": False,
        "dropoff_detected": False,
        "timestamp": time.time()
    }

    # Mock the motor controller
    avoidance_algorithm.motor_controller.get_current_heading.return_value = 0.0
    avoidance_algorithm.motor_controller.rotate_to_heading.return_value = None

    # Use pytest-benchmark to measure performance
    with patch.object(avoidance_algorithm, 'thread_lock'):
        result = benchmark(avoidance_algorithm._execute_recovery)

    # Verify that recovery was executed
    assert result is True


def test_select_random_strategy_benchmark(benchmark, avoidance_algorithm):
    """Benchmark the _select_random_strategy method."""
    # Mock the motor controller
    avoidance_algorithm.motor_controller.get_current_heading.return_value = 0.0
    avoidance_algorithm.motor_controller.rotate_to_heading.return_value = None

    # Use pytest-benchmark to measure performance
    result = benchmark(avoidance_algorithm._select_random_strategy)

    # Verify that a strategy was selected
    assert result is True


def test_turn_right_strategy_benchmark(benchmark, avoidance_algorithm):
    """Benchmark the _turn_right_strategy method."""
    # Mock the motor controller
    avoidance_algorithm.motor_controller.get_current_heading.return_value = 0.0
    avoidance_algorithm.motor_controller.rotate_to_heading.return_value = None

    # Use pytest-benchmark to measure performance
    result = benchmark(avoidance_algorithm._turn_right_strategy, angle=45.0)

    # Verify that the strategy was executed
    assert result is True


def test_turn_left_strategy_benchmark(benchmark, avoidance_algorithm):
    """Benchmark the _turn_left_strategy method."""
    # Mock the motor controller
    avoidance_algorithm.motor_controller.get_current_heading.return_value = 0.0
    avoidance_algorithm.motor_controller.rotate_to_heading.return_value = None

    # Use pytest-benchmark to measure performance
    result = benchmark(avoidance_algorithm._turn_left_strategy, angle=45.0)

    # Verify that the strategy was executed
    assert result is True


def test_backup_strategy_benchmark(benchmark, avoidance_algorithm):
    """Benchmark the _backup_strategy method."""
    # Mock the motor controller
    avoidance_algorithm.motor_controller.get_current_heading.return_value = 0.0
    avoidance_algorithm.motor_controller.rotate_to_heading.return_value = None
    avoidance_algorithm.motor_controller.move_distance.return_value = None

    # Use pytest-benchmark to measure performance
    with patch('time.sleep'):  # Mock sleep to speed up the test
        result = benchmark(avoidance_algorithm._backup_strategy, distance=30.0)

    # Verify that the strategy was executed
    assert result is True


def test_alternative_route_strategy_benchmark(benchmark, avoidance_algorithm):
    """Benchmark the _alternative_route_strategy method."""
    # Mock the motor controller
    avoidance_algorithm.motor_controller.get_current_position.return_value = (
        0.0, 0.0)
    avoidance_algorithm.motor_controller.navigate_to_location.return_value = None

    # Mock the path planner
    avoidance_algorithm.pattern_planner.get_current_goal.return_value = (
        10.0, 10.0)
    avoidance_algorithm.pattern_planner.coord_to_grid.return_value = (100, 100)
    avoidance_algorithm.pattern_planner.get_path.return_value = [
        {'lat': 1.0, 'lng': 1.0},
        {'lat': 5.0, 'lng': 5.0},
        {'lat': 10.0, 'lng': 10.0}
    ]

    # Mock the _estimate_obstacle_position method
    avoidance_algorithm._estimate_obstacle_position = MagicMock(return_value={
        'position': (5.0, 5.0),
        'type': 'static',
        'confidence': 0.8,
        'sensor': 'tof_left'
    })

    # Use pytest-benchmark to measure performance
    result = benchmark(avoidance_algorithm._alternative_route_strategy)

    # Verify that the strategy was executed
    assert result is True


def test_estimate_obstacle_position_benchmark(benchmark, avoidance_algorithm):
    """Benchmark the _estimate_obstacle_position method."""
    # Mock the motor controller
    avoidance_algorithm.motor_controller.get_current_position.return_value = (
        0.0, 0.0)
    avoidance_algorithm.motor_controller.get_current_heading.return_value = 0.0

    # Set up the obstacle data
    avoidance_algorithm.obstacle_data = {
        "left_sensor": True,
        "right_sensor": False,
        "camera_detected": False,
        "dropoff_detected": False,
        "timestamp": time.time()
    }

    # Use pytest-benchmark to measure performance
    with patch.object(avoidance_algorithm, 'thread_lock'):
        result = benchmark(avoidance_algorithm._estimate_obstacle_position)

    # Verify that an obstacle position was estimated
    assert result is not None
    assert 'position' in result
    assert 'type' in result
    assert 'confidence' in result
    assert 'sensor' in result


def test_calculate_obstacle_coordinates_benchmark(benchmark, avoidance_algorithm):
    """Benchmark the _calculate_obstacle_coordinates method."""
    # Create test data
    current_position = (0.0, 0.0)
    heading_rad = 0.0
    distance = 50.0
    obstacle_angle = 0.0

    # Use pytest-benchmark to measure performance
    result = benchmark(
        avoidance_algorithm._calculate_obstacle_coordinates,
        current_position, heading_rad, distance, obstacle_angle
    )

    # Verify that obstacle coordinates were calculated
    assert result is not None
    assert len(result) == 2
    assert isinstance(result[0], float)
    assert isinstance(result[1], float)


def test_determine_obstacle_parameters_benchmark(benchmark, avoidance_algorithm):
    """Benchmark the _determine_obstacle_parameters method."""
    # Create test data
    obstacle_data = {
        "left_sensor": True,
        "right_sensor": False,
        "camera_detected": False,
        "dropoff_detected": False,
        "timestamp": time.time()
    }

    # Use pytest-benchmark to measure performance
    result = benchmark(
        avoidance_algorithm._determine_obstacle_parameters, obstacle_data)

    # Verify that obstacle parameters were determined
    assert result is not None
    assert len(result) == 3
    assert result[0] is not None
    assert isinstance(result[1], float)
    assert isinstance(result[2], float)


def test_process_sensor_data_benchmark(benchmark, avoidance_algorithm):
    """Benchmark the _process_sensor_data method."""
    # Create test data
    sensor_data = [0.6, 0.2, 0.8, 0.1, 0.3, 0.7, 0.4, 0.9]

    # Use pytest-benchmark to measure performance
    result = benchmark(avoidance_algorithm._process_sensor_data, sensor_data)

    # Verify that sensor data was processed
    assert result is not None
    assert isinstance(result, list)

    # Count how many readings are above the threshold (0.5)
    above_threshold = sum(1 for reading in sensor_data if reading > 0.5)
    assert len(result) == above_threshold


def test_find_obstacle_positions_benchmark(benchmark, avoidance_algorithm):
    """Benchmark the _find_obstacle_positions method."""
    # Create test data
    path = [(0, 0), (5, 5), (10, 10)]
    obstacles = [
        Obstacle(position=(3, 3), size=1.0, confidence=0.8),
        Obstacle(position=(7, 7), size=1.0, confidence=0.8)
    ]

    # Use pytest-benchmark to measure performance
    result = benchmark(
        avoidance_algorithm._find_obstacle_positions, path, obstacles)

    # Verify that obstacle positions were found
    assert result is not None
    assert isinstance(result, list)
    assert len(result) > 0


def test_modify_path_benchmark(benchmark, avoidance_algorithm):
    """Benchmark the _modify_path method."""
    # Create test data
    path = [(0, 0), (5, 5), (10, 10)]
    obstacle_indices = [1]  # Obstacle at (5, 5)

    # Use pytest-benchmark to measure performance
    result = benchmark(avoidance_algorithm._modify_path,
                       path, obstacle_indices)

    # Verify that the path was modified
    assert result is not None
    assert isinstance(result, list)
    assert len(result) > 0
    assert (5, 5) not in result  # The obstacle point should be removed


def test_smooth_path_benchmark(benchmark, avoidance_algorithm):
    """Benchmark the _smooth_path method."""
    # Create test data
    path = [(0, 0), (5, 5), (10, 10)]

    # Use pytest-benchmark to measure performance
    result = benchmark(avoidance_algorithm._smooth_path, path)

    # Verify that the path was smoothed
    assert result is not None
    assert isinstance(result, list)
    assert len(result) >= len(path)  # Smoothing should add points


def test_complex_scenario_benchmark(benchmark):
    """Benchmark a complex scenario with multiple operations."""
    def complex_scenario():
        # Create a mock resource manager
        mock_resource_manager = MagicMock()
        mock_resource_manager.get_camera.return_value = None
        mock_resource_manager.get_obstacle_detector.return_value = None

        # Create a mock path planner
        mock_path_planner = MagicMock()
        mock_path_planner.generate_path.return_value = [
            (0, 0), (5, 5), (10, 10)]
        mock_path_planner.update_obstacle_map.return_value = None
        mock_path_planner.get_current_goal.return_value = (10, 10)
        mock_path_planner.coord_to_grid.return_value = (100, 100)
        mock_path_planner.get_path.return_value = [
            {'lat': 1.0, 'lng': 1.0},
            {'lat': 5.0, 'lng': 5.0},
            {'lat': 10.0, 'lng': 10.0}
        ]

        # Create an AvoidanceAlgorithm instance
        with patch('mower.obstacle_detection.avoidance_algorithm.os.environ.get', return_value='False'):
            algorithm = AvoidanceAlgorithm(
                resource_manager=mock_resource_manager,
                pattern_planner=mock_path_planner
            )

        # Mock the necessary components
        algorithm.motor_controller = MagicMock()
        algorithm.motor_controller.get_current_position.return_value = (
            0.0, 0.0)
        algorithm.motor_controller.get_current_heading.return_value = 0.0
        algorithm.motor_controller.get_status.return_value = NavigationStatus.TARGET_REACHED
        algorithm.motor_controller.rotate_to_heading.return_value = None
        algorithm.motor_controller.move_distance.return_value = None
        algorithm.motor_controller.navigate_to_location.return_value = None

        algorithm.sensor_interface = MagicMock()

        # Set up the obstacle data
        algorithm.obstacle_data = {
            "left_sensor": True,
            "right_sensor": False,
            "camera_detected": False,
            "dropoff_detected": False,
            "timestamp": time.time()
        }

        # Detect an obstacle
        with patch.object(algorithm, 'thread_lock'):
            detected, obstacle_data = algorithm._detect_obstacle()

        # Start avoidance
        avoidance_started = algorithm._start_avoidance()

        # Continue avoidance
        avoidance_complete = algorithm._continue_avoidance()

        # Estimate obstacle position
        with patch.object(algorithm, 'thread_lock'):
            obstacle_position = algorithm._estimate_obstacle_position()

        # Process sensor data
        sensor_data = [0.6, 0.2, 0.8, 0.1, 0.3, 0.7, 0.4, 0.9]
        obstacles = algorithm._process_sensor_data(sensor_data)

        # Find obstacle positions in path
        path = [(0, 0), (5, 5), (10, 10)]
        obstacle_objects = [
            Obstacle(position=(3, 3), size=1.0, confidence=0.8),
            Obstacle(position=(7, 7), size=1.0, confidence=0.8)
        ]
        obstacle_indices = algorithm._find_obstacle_positions(
            path, obstacle_objects)

        # Modify path to avoid obstacles
        modified_path = algorithm._modify_path(path, obstacle_indices)

        # Smooth the path
        smoothed_path = algorithm._smooth_path(modified_path)

        return {
            "detected": detected,
            "avoidance_started": avoidance_started,
            "avoidance_complete": avoidance_complete,
            "obstacle_position": obstacle_position,
            "obstacles": obstacles,
            "obstacle_indices": obstacle_indices,
            "modified_path": modified_path,
            "smoothed_path": smoothed_path
        }

    # Use pytest-benchmark to measure performance
    result = benchmark(complex_scenario)

    # Verify that the scenario was executed
    assert result is not None
    assert "detected" in result
    assert "avoidance_started" in result
    assert "avoidance_complete" in result
    assert "obstacle_position" in result
    assert "obstacles" in result
    assert "obstacle_indices" in result
    assert "modified_path" in result
    assert "smoothed_path" in result


if __name__ == "__main__":
    # This allows running the benchmarks directly without pytest
    import sys

    # Create a mock resource manager
    mock_resource_manager = MagicMock()
    mock_resource_manager.get_camera.return_value = None
    mock_resource_manager.get_obstacle_detector.return_value = None

    # Create a mock path planner
    mock_path_planner = MagicMock()
    mock_path_planner.generate_path.return_value = [(0, 0), (5, 5), (10, 10)]
    mock_path_planner.update_obstacle_map.return_value = None
    mock_path_planner.get_current_goal.return_value = (10, 10)
    mock_path_planner.coord_to_grid.return_value = (100, 100)
    mock_path_planner.get_path.return_value = [
        {'lat': 1.0, 'lng': 1.0},
        {'lat': 5.0, 'lng': 5.0},
        {'lat': 10.0, 'lng': 10.0}
    ]

    # Create an AvoidanceAlgorithm instance
    with patch('mower.obstacle_detection.avoidance_algorithm.os.environ.get', return_value='False'):
        algorithm = AvoidanceAlgorithm(
            resource_manager=mock_resource_manager,
            pattern_planner=mock_path_planner
        )

    # Mock the necessary components
    algorithm.motor_controller = MagicMock()
    algorithm.motor_controller.get_current_position.return_value = (0.0, 0.0)
    algorithm.motor_controller.get_current_heading.return_value = 0.0
    algorithm.motor_controller.get_status.return_value = NavigationStatus.TARGET_REACHED
    algorithm.motor_controller.rotate_to_heading.return_value = None
    algorithm.motor_controller.move_distance.return_value = None
    algorithm.motor_controller.navigate_to_location.return_value = None

    algorithm.sensor_interface = MagicMock()

    # Set up the obstacle data
    algorithm.obstacle_data = {
        "left_sensor": True,
        "right_sensor": False,
        "camera_detected": False,
        "dropoff_detected": False,
        "timestamp": time.time()
    }

    # Run benchmarks
    benchmarks = [
        ("detect_obstacle", lambda: algorithm._detect_obstacle()),
        ("start_avoidance", lambda: algorithm._start_avoidance()),
        ("continue_avoidance", lambda: algorithm._continue_avoidance()),
        ("execute_recovery", lambda: algorithm._execute_recovery()),
        ("select_random_strategy", lambda: algorithm._select_random_strategy()),
        ("turn_right_strategy", lambda: algorithm._turn_right_strategy(angle=45.0)),
        ("turn_left_strategy", lambda: algorithm._turn_left_strategy(angle=45.0)),
        ("backup_strategy", lambda: algorithm._backup_strategy(distance=30.0)),
        ("estimate_obstacle_position", lambda: algorithm._estimate_obstacle_position()),
        ("calculate_obstacle_coordinates", lambda: algorithm._calculate_obstacle_coordinates(
            (0.0, 0.0), 0.0, 50.0, 0.0
        )),
        ("determine_obstacle_parameters", lambda: algorithm._determine_obstacle_parameters(
            algorithm.obstacle_data
        )),
        ("process_sensor_data", lambda: algorithm._process_sensor_data(
            [0.6, 0.2, 0.8, 0.1, 0.3, 0.7, 0.4, 0.9]
        )),
        ("find_obstacle_positions", lambda: algorithm._find_obstacle_positions(
            [(0, 0), (5, 5), (10, 10)],
            [
                Obstacle(position=(3, 3), size=1.0, confidence=0.8),
                Obstacle(position=(7, 7), size=1.0, confidence=0.8)
            ]
        )),
        ("modify_path", lambda: algorithm._modify_path(
            [(0, 0), (5, 5), (10, 10)],
            [1]
        )),
        ("smooth_path", lambda: algorithm._smooth_path(
            [(0, 0), (5, 5), (10, 10)]
        )),
    ]

    # Run each benchmark
    for name, func in benchmarks:
        times = []
        results = []

        # Run the benchmark multiple times
        for _ in range(10):
            try:
                result, execution_time = time_function(func)
                times.append(execution_time)
                results.append(result)
            except Exception as e:
                print(f"Error running benchmark {name}: {e}")
                break

        # Log the results
        if times:
            log_benchmark_results(name, times, results)
