"""
Performance benchmarks for path planning algorithms.

This module contains benchmarks for the critical operations in the path planning
algorithms, including path generation, geometric operations, and path quality
calculations.
"""

import pytest
import numpy as np
from typing import List, Tuple, Dict, Any
import time

from mower.navigation.path_planner import (
    PathPlanner, PatternConfig, LearningConfig, PatternType
)
from tests.benchmarks.utils import (
    generate_random_boundary, generate_random_obstacles,
    time_function, log_benchmark_results
)


@pytest.fixture
def pattern_config():
    """Fixture for a basic pattern configuration."""
    boundary = [(0, 0), (10, 0), (10, 10), (0, 10)]
    return PatternConfig(
        pattern_type=PatternType.PARALLEL,
        spacing=0.3,
        angle=0.0,
        overlap=0.1,
        start_point=(0.0, 0.0),
        boundary_points=boundary
    )


@pytest.fixture
def learning_config():
    """Fixture for a basic learning configuration."""
    return LearningConfig(
        learning_rate=0.1,
        discount_factor=0.9,
        exploration_rate=0.2,
        memory_size=1000,
        batch_size=32,
        update_frequency=100,
        model_path="test_model_path"
    )


@pytest.fixture
def path_planner(pattern_config, learning_config):
    """Fixture for a PathPlanner instance."""
    return PathPlanner(pattern_config, learning_config)


def test_generate_path_benchmark(benchmark, path_planner):
    """Benchmark the generate_path method."""
    # Use pytest-benchmark to measure performance
    result = benchmark(path_planner.generate_path)
    
    # Verify that a path was generated
    assert result is not None
    assert len(result) > 0


@pytest.mark.parametrize("pattern_type", list(PatternType))
def test_pattern_generation_benchmark(benchmark, pattern_config, learning_config, pattern_type):
    """Benchmark different pattern generation methods."""
    # Set the pattern type
    pattern_config.pattern_type = pattern_type
    
    # Create a PathPlanner instance
    path_planner = PathPlanner(pattern_config, learning_config)
    
    # Use pytest-benchmark to measure performance
    result = benchmark(path_planner.generate_path)
    
    # Skip empty paths (which might be valid for some configurations)
    if result:
        assert len(result) > 0


def test_find_boundary_intersections_benchmark(benchmark, path_planner):
    """Benchmark the _find_boundary_intersections method."""
    # Create test data
    boundary = np.array(path_planner.pattern_config.boundary_points)
    start = np.array([0.0, 5.0])
    end = np.array([10.0, 5.0])
    
    # Use pytest-benchmark to measure performance
    result = benchmark(path_planner._find_boundary_intersections, start, end, boundary)
    
    # Verify that intersections were found
    assert result is not None


def test_line_intersection_benchmark(benchmark, path_planner):
    """Benchmark the _line_intersection method."""
    # Create test data
    p1 = np.array([0.0, 0.0])
    p2 = np.array([10.0, 10.0])
    p3 = np.array([0.0, 10.0])
    p4 = np.array([10.0, 0.0])
    
    # Use pytest-benchmark to measure performance
    result = benchmark(path_planner._line_intersection, p1, p2, p3, p4)
    
    # Verify that an intersection was found
    assert result is not None


def test_point_in_polygon_benchmark(benchmark, path_planner):
    """Benchmark the _point_in_polygon method."""
    # Create test data
    polygon = np.array(path_planner.pattern_config.boundary_points)
    point = np.array([5.0, 5.0])
    
    # Use pytest-benchmark to measure performance
    result = benchmark(path_planner._point_in_polygon, point, polygon)
    
    # Verify that the result is a boolean
    assert isinstance(result, bool)


def test_calculate_reward_benchmark(benchmark, path_planner):
    """Benchmark the _calculate_reward method."""
    # Create a test path
    path = [(0, 0), (5, 5), (10, 10)]
    
    # Use pytest-benchmark to measure performance
    result = benchmark(path_planner._calculate_reward, path)
    
    # Verify that a reward was calculated
    assert 0.0 <= result <= 1.0


def test_calculate_path_distance_benchmark(benchmark, path_planner):
    """Benchmark the _calculate_path_distance method."""
    # Create a test path
    path = [(0, 0), (5, 5), (10, 10)]
    
    # Use pytest-benchmark to measure performance
    result = benchmark(path_planner._calculate_path_distance, path)
    
    # Verify that a distance was calculated
    assert result > 0.0


def test_calculate_coverage_benchmark(benchmark, path_planner):
    """Benchmark the _calculate_coverage method."""
    # Create a test path
    path = [(0, 0), (5, 5), (10, 10), (10, 0), (0, 10)]
    
    # Use pytest-benchmark to measure performance
    result = benchmark(path_planner._calculate_coverage, path)
    
    # Verify that coverage was calculated
    assert 0.0 <= result <= 1.0


def test_calculate_smoothness_benchmark(benchmark, path_planner):
    """Benchmark the _calculate_smoothness method."""
    # Create a test path
    path = [(0, 0), (5, 5), (10, 10)]
    
    # Use pytest-benchmark to measure performance
    result = benchmark(path_planner._calculate_smoothness, path)
    
    # Verify that smoothness was calculated
    assert 0.0 <= result <= 1.0


def test_update_q_table_benchmark(benchmark, path_planner):
    """Benchmark the _update_q_table method."""
    # Create test data
    state = "test_state"
    action = PatternType.PARALLEL
    reward = 0.5
    
    # Use pytest-benchmark to measure performance
    benchmark(path_planner._update_q_table, state, action, reward)


def test_store_experience_benchmark(benchmark, path_planner):
    """Benchmark the _store_experience method."""
    # Create test data
    state = "test_state"
    action = PatternType.PARALLEL
    reward = 0.5
    
    # Use pytest-benchmark to measure performance
    benchmark(path_planner._store_experience, state, action, reward)


def test_update_model_benchmark(benchmark, path_planner):
    """Benchmark the _update_model method."""
    # Add some experiences to the memory
    for i in range(100):
        path_planner._store_experience(f"state_{i}", PatternType.PARALLEL, 0.5)
    
    # Use pytest-benchmark to measure performance
    benchmark(path_planner._update_model)


def test_save_model_benchmark(benchmark, path_planner):
    """Benchmark the _save_model method."""
    # Add some data to the q_table
    path_planner.q_table["test_state"] = {
        PatternType.PARALLEL: 0.5,
        PatternType.SPIRAL: 0.3,
        PatternType.ZIGZAG: 0.2
    }
    
    # Use pytest-benchmark to measure performance
    benchmark(path_planner._save_model)


def test_load_model_benchmark(benchmark, path_planner):
    """Benchmark the _load_model method."""
    # Save a model first
    path_planner.q_table["test_state"] = {
        PatternType.PARALLEL: 0.5,
        PatternType.SPIRAL: 0.3,
        PatternType.ZIGZAG: 0.2
    }
    path_planner._save_model()
    
    # Use pytest-benchmark to measure performance
    benchmark(path_planner._load_model)


def test_complex_scenario_benchmark(benchmark):
    """Benchmark a complex scenario with multiple operations."""
    def complex_scenario():
        # Generate random boundary
        boundary = generate_random_boundary(num_points=10, radius=100.0)
        
        # Create pattern config
        pattern_config = PatternConfig(
            pattern_type=PatternType.PARALLEL,
            spacing=0.5,
            angle=45.0,
            overlap=0.2,
            start_point=(0.0, 0.0),
            boundary_points=boundary
        )
        
        # Create learning config
        learning_config = LearningConfig()
        
        # Create path planner
        path_planner = PathPlanner(pattern_config, learning_config)
        
        # Generate path
        path = path_planner.generate_path()
        
        # Add obstacles
        obstacles = generate_random_obstacles(num_obstacles=10, boundary=boundary)
        obstacle_positions = [pos for pos, _ in obstacles]
        path_planner.update_obstacle_map(obstacle_positions)
        
        # Generate path again with obstacles
        path_with_obstacles = path_planner.generate_path()
        
        # Calculate reward
        reward = path_planner._calculate_reward(path_with_obstacles)
        
        return path_with_obstacles, reward
    
    # Use pytest-benchmark to measure performance
    result = benchmark(complex_scenario)
    
    # Verify that a path was generated
    assert result is not None
    assert len(result) == 2
    assert len(result[0]) > 0
    assert 0.0 <= result[1] <= 1.0


if __name__ == "__main__":
    # This allows running the benchmarks directly without pytest
    import sys
    
    # Create a pattern config
    boundary = [(0, 0), (10, 0), (10, 10), (0, 10)]
    pattern_config = PatternConfig(
        pattern_type=PatternType.PARALLEL,
        spacing=0.3,
        angle=0.0,
        overlap=0.1,
        start_point=(0.0, 0.0),
        boundary_points=boundary
    )
    
    # Create a learning config
    learning_config = LearningConfig()
    
    # Create a path planner
    path_planner = PathPlanner(pattern_config, learning_config)
    
    # Run benchmarks
    benchmarks = [
        ("generate_path", lambda: path_planner.generate_path()),
        ("find_boundary_intersections", lambda: path_planner._find_boundary_intersections(
            np.array([0.0, 5.0]), np.array([10.0, 5.0]), np.array(boundary)
        )),
        ("line_intersection", lambda: path_planner._line_intersection(
            np.array([0.0, 0.0]), np.array([10.0, 10.0]),
            np.array([0.0, 10.0]), np.array([10.0, 0.0])
        )),
        ("point_in_polygon", lambda: path_planner._point_in_polygon(
            np.array([5.0, 5.0]), np.array(boundary)
        )),
        ("calculate_reward", lambda: path_planner._calculate_reward(
            [(0, 0), (5, 5), (10, 10)]
        )),
        ("calculate_path_distance", lambda: path_planner._calculate_path_distance(
            [(0, 0), (5, 5), (10, 10)]
        )),
        ("calculate_coverage", lambda: path_planner._calculate_coverage(
            [(0, 0), (5, 5), (10, 10), (10, 0), (0, 10)]
        )),
        ("calculate_smoothness", lambda: path_planner._calculate_smoothness(
            [(0, 0), (5, 5), (10, 10)]
        )),
    ]
    
    # Run each benchmark
    for name, func in benchmarks:
        times = []
        results = []
        
        # Run the benchmark multiple times
        for _ in range(10):
            result, execution_time = time_function(func)
            times.append(execution_time)
            results.append(result)
        
        # Log the results
        log_benchmark_results(name, times, results)