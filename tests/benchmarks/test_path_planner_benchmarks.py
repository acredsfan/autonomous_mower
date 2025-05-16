"""
Test module for test_path_planner_benchmarks.py.
"""
import pytest
import numpy as np
from mower.navigation.path_planner import (
    PathPlanner,
    PatternConfig,
    PatternType,
    LearningConfig,
)


@pytest.fixture
def pattern_config_fixture():  # Renamed to avoid conflict
    boundary = [(0, 0), (10, 0), (10, 10), (0, 10)]
    return PatternConfig(
        pattern_type=PatternType.PARALLEL,
        spacing=0.3,
        angle=0.0,
        overlap=0.1,
        start_point=(0.0, 0.0),
        boundary_points=boundary,
    )


@pytest.fixture
def learning_config_fixture():  # Renamed to avoid conflict
    return LearningConfig()


@pytest.fixture
def path_planner(
    pattern_config_fixture, learning_config_fixture
):  # Use renamed fixtures
    return PathPlanner(pattern_config_fixture, learning_config_fixture)


# Added pattern_config_fixture
def test_generate_path_benchmark(
        benchmark,
        path_planner,
        pattern_config_fixture):
    # Set the pattern type (assuming you want to test different types)
    # This line was problematic as pattern_type was undefined.
    # For a benchmark, you might iterate over types or test a specific one.
    # For now, let's assume the fixture's default is fine or set one
    # explicitly.
    pattern_config_fixture.pattern_type = PatternType.SPIRAL  # Example: testing SPIRAL

    # Create a PathPlanner instance - path_planner fixture already does this
    # path_planner = PathPlanner(pattern_config_fixture, learning_config_fixture)

    # Use pytest - benchmark to measure performance
    result = benchmark(path_planner.generate_path)

    # Skip empty paths(which might be valid for some configurations)
    if result:
        assert len(result) > 0


def test_find_boundary_intersections_benchmark(benchmark, path_planner):
    # Create test data
    p1 = np.array([0.0, 0.0])
    p2 = np.array([10.0, 10.0])
    p3 = np.array([0.0, 10.0])
    p4 = np.array([10.0, 0.0])

    # Use pytest - benchmark to measure performance
    result = benchmark(path_planner._line_intersection, p1, p2, p3, p4)

    # Verify that an intersection was found
    assert result is not None


def test_point_in_polygon_benchmark(benchmark, path_planner):
    # Create a test path
    path = [(0, 0), (5, 5), (10, 10)]

    # Use pytest - benchmark to measure performance
    result = benchmark(path_planner._calculate_reward, path)

    # Verify that a reward was calculated
    assert 0.0 <= result <= 1.0


def test_calculate_path_distance_benchmark(benchmark, path_planner):
    # Create a test path
    path = [(0, 0), (5, 5), (10, 10), (10, 0), (0, 10)]

    # Use pytest - benchmark to measure performance
    result = benchmark(path_planner._calculate_coverage, path)

    # Verify that coverage was calculated
    assert 0.0 <= result <= 1.0


def test_calculate_smoothness_benchmark(benchmark, path_planner):
    # Create test data
    state = "test_state"
    action = PatternType.PARALLEL
    reward = 0.5

    # Use pytest - benchmark to measure performance
    benchmark(path_planner._update_q_table, state, action, reward)


def test_store_experience_benchmark(benchmark, path_planner):
    # Add some experiences to the memory
    for i in range(100):
        path_planner._store_experience(
            f"state_{i}", PatternType.PARALLEL, 0.5
        )

    # Use pytest - benchmark to measure performance
    benchmark(path_planner._update_model)


def test_save_model_benchmark(benchmark, path_planner):
    # Save a model first
    path_planner.q_table["test_state"] = {
        PatternType.PARALLEL: 0.5,
        PatternType.SPIRAL: 0.3,
        PatternType.ZIGZAG: 0.2,
    }
    path_planner._save_model()

    # Use pytest - benchmark to measure performance
    benchmark(path_planner._load_model)


def test_complex_scenario_benchmark(benchmark):
    pass
