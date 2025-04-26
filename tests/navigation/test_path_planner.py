"""
Tests for the PathPlanner class.

This module tests the functionality of the PathPlanner class in
navigation/path_planner.py, including:
1. Initialization of the path planner
2. Generating paths
3. Handling obstacles
4. Learning and optimization
"""

import pytest
import numpy as np
from unittest.mock import MagicMock, patch, call

from mower.navigation.path_planner import (
    PathPlanner,
    PatternConfig,
    LearningConfig,
    PatternType,
)


class TestPathPlanner:
    """Tests for the PathPlanner class."""

    def test_initialization(self):
        """Test initialization of the path planner."""
        # Create pattern and learning configurations
        pattern_config = PatternConfig(
            pattern_type=PatternType.PARALLEL,
            spacing=0.3,
            angle=0.0,
            overlap=0.1,
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

        # Verify that the configurations were stored correctly
        assert path_planner.pattern_config is pattern_config
        assert path_planner.learning_config is learning_config

        # Verify that the path planner was initialized correctly
        assert path_planner.current_path == []
        assert path_planner.obstacle_map == []
        assert path_planner.coverage_map is not None
        assert path_planner.learning_model is not None

    def test_generate_parallel_path(self):
        """Test generating a parallel path."""
        # Create pattern and learning configurations
        pattern_config = PatternConfig(
            pattern_type=PatternType.PARALLEL,
            spacing=1.0,  # Use a larger spacing for easier testing
            angle=0.0,
            overlap=0.0,  # No overlap for easier testing
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

        # Generate a path
        path = path_planner.generate_path()

        # Verify that a path was generated
        assert len(path) > 0

        # Verify that the path starts at the start point
        assert path[0] == (0.0, 0.0)

        # Verify that the path covers the entire area
        x_coords = [point[0] for point in path]
        y_coords = [point[1] for point in path]
        assert min(x_coords) <= 0.0
        assert max(x_coords) >= 10.0
        assert min(y_coords) <= 0.0
        assert max(y_coords) >= 10.0

        # Verify that the path follows a parallel pattern
        # For a parallel pattern with angle=0.0, all points with the same y-coordinate
        # should have x-coordinates that are either increasing or decreasing
        y_values = sorted(set(y_coords))
        for y in y_values:
            points_at_y = [
                (x, y_idx)
                for x_idx, (x, y_idx) in enumerate(path)
                if y_idx == y
            ]
            x_values = [x for x, _ in points_at_y]
            # Check if x values are monotonically increasing or decreasing
            assert all(
                x_values[i] <= x_values[i + 1]
                for i in range(len(x_values) - 1)
            ) or all(
                x_values[i] >= x_values[i + 1]
                for i in range(len(x_values) - 1)
            )

    def test_generate_spiral_path(self):
        """Test generating a spiral path."""
        # Create pattern and learning configurations
        pattern_config = PatternConfig(
            pattern_type=PatternType.SPIRAL,
            spacing=1.0,  # Use a larger spacing for easier testing
            angle=0.0,
            overlap=0.0,  # No overlap for easier testing
            start_point=(5.0, 5.0),  # Start in the center
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

        # Generate a path
        path = path_planner.generate_path()

        # Verify that a path was generated
        assert len(path) > 0

        # Verify that the path starts near the center
        assert abs(path[0][0] - 5.0) < 1.0
        assert abs(path[0][1] - 5.0) < 1.0

        # Verify that the path covers the entire area
        x_coords = [point[0] for point in path]
        y_coords = [point[1] for point in path]
        assert min(x_coords) <= 1.0
        assert max(x_coords) >= 9.0
        assert min(y_coords) <= 1.0
        assert max(y_coords) >= 9.0

        # Verify that the path follows a spiral pattern
        # For a spiral pattern, the distance from the center should generally increase
        center = (5.0, 5.0)
        distances = [
            ((x - center[0]) ** 2 + (y - center[1]) ** 2) ** 0.5
            for x, y in path
        ]
        # Check if distances are generally increasing
        # We allow some fluctuations, so we check if the trend is increasing
        increasing_count = sum(
            distances[i] <= distances[i + 1]
            for i in range(len(distances) - 1)
        )
        # At least 70% should be increasing
        assert increasing_count >= len(distances) * 0.7

    def test_update_obstacle_map(self):
        """Test updating the obstacle map."""
        # Create pattern and learning configurations
        pattern_config = PatternConfig(
            pattern_type=PatternType.PARALLEL,
            spacing=0.3,
            angle=0.0,
            overlap=0.1,
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

        # Update the obstacle map
        obstacles = [(5.0, 5.0), (7.0, 7.0)]
        path_planner.update_obstacle_map(obstacles)

        # Verify that the obstacle map was updated
        assert len(path_planner.obstacle_map) == 2
        assert (5.0, 5.0) in path_planner.obstacle_map
        assert (7.0, 7.0) in path_planner.obstacle_map

        # Update the obstacle map again with a new obstacle
        path_planner.update_obstacle_map([(3.0, 3.0)])

        # Verify that the obstacle map was updated
        assert len(path_planner.obstacle_map) == 3
        assert (3.0, 3.0) in path_planner.obstacle_map

    def test_get_path(self):
        """Test getting a path between two points."""
        # Create pattern and learning configurations
        pattern_config = PatternConfig(
            pattern_type=PatternType.PARALLEL,
            spacing=0.3,
            angle=0.0,
            overlap=0.1,
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

        # Get a path between two points
        start = (0, 0)
        goal = (10, 10)
        path = path_planner.get_path(start, goal)

        # Verify that a path was generated
        assert len(path) > 0

        # Verify that the path starts at the start point and ends at the goal point
        assert path[0] == start
        assert path[-1] == goal

        # Add an obstacle and get a new path
        path_planner.update_obstacle_map([(5, 5)])
        path_with_obstacle = path_planner.get_path(start, goal)

        # Verify that a path was generated
        assert len(path_with_obstacle) > 0

        # Verify that the path starts at the start point and ends at the goal point
        assert path_with_obstacle[0] == start
        assert path_with_obstacle[-1] == goal

        # Verify that the path avoids the obstacle
        assert (5, 5) not in path_with_obstacle

    def test_optimize_path(self):
        """Test optimizing a path."""
        # Create pattern and learning configurations
        pattern_config = PatternConfig(
            pattern_type=PatternType.PARALLEL,
            spacing=0.3,
            angle=0.0,
            overlap=0.1,
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

        # Create a path with unnecessary detours
        path = [
            (0, 0),
            (1, 1),
            (2, 2),
            (3, 3),
            (4, 4),
            (5, 5),
            (6, 6),
            (7, 7),
            (8, 8),
            (9, 9),
            (10, 10),
        ]

        # Optimize the path
        optimized_path = path_planner.optimize_path(path)

        # Verify that the optimized path is shorter than the original path
        assert len(optimized_path) <= len(path)

        # Verify that the optimized path still starts and ends at the same points
        assert optimized_path[0] == path[0]
        assert optimized_path[-1] == path[-1]

    def test_coord_to_grid(self):
        """Test converting coordinates to grid indices."""
        # Create pattern and learning configurations
        pattern_config = PatternConfig(
            pattern_type=PatternType.PARALLEL,
            spacing=0.3,
            angle=0.0,
            overlap=0.1,
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

        # Convert coordinates to grid indices
        grid_x, grid_y = path_planner.coord_to_grid(5.0, 5.0)

        # Verify that the conversion is correct
        assert isinstance(grid_x, int)
        assert isinstance(grid_y, int)
        assert grid_x >= 0
        assert grid_y >= 0

    def test_grid_to_coord(self):
        """Test converting grid indices to coordinates."""
        # Create pattern and learning configurations
        pattern_config = PatternConfig(
            pattern_type=PatternType.PARALLEL,
            spacing=0.3,
            angle=0.0,
            overlap=0.1,
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

        # Convert grid indices to coordinates
        coord_x, coord_y = path_planner.grid_to_coord(50, 50)

        # Verify that the conversion is correct
        assert isinstance(coord_x, float)
        assert isinstance(coord_y, float)

        # Convert back to grid indices
        grid_x, grid_y = path_planner.coord_to_grid(coord_x, coord_y)

        # Verify that the conversion is reversible
        assert grid_x == 50
        assert grid_y == 50

    def test_get_current_goal(self):
        """Test getting the current goal."""
        # Create pattern and learning configurations
        pattern_config = PatternConfig(
            pattern_type=PatternType.PARALLEL,
            spacing=0.3,
            angle=0.0,
            overlap=0.1,
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

        # Generate a path
        path = path_planner.generate_path()

        # Get the current goal
        goal = path_planner.get_current_goal()

        # Verify that the goal is the last point in the path
        assert goal == path[-1]
