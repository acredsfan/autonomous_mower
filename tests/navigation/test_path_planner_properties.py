"""
Test module for test_path_planner_properties.py.
"""

from typing import List, Tuple

import numpy as np
import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from mower.navigation.path_planner import LearningConfig, PathPlanner, PatternConfig, PatternType


# Helper strategies for generating test data
@st.composite


def pattern_config_strategy(draw):
    """Strategy for generating valid PatternConfig instances."""
    pattern_type = draw(st.sampled_from(list(PatternType)))
    spacing = draw(st.floats(min_value=0.1, max_value=2.0))
    angle = draw(st.floats(min_value=0.0, max_value=359.0))
    overlap = draw(st.floats(min_value=0.0, max_value=0.5))
    start_point = (
        draw(st.floats(min_value=- 100.0, max_value=100.0)),
        draw(st.floats(min_value=- 100.0, max_value=100.0)),
    )

    # Generate a valid boundary(convex polygon)
    num_points = draw(st.integers(min_value=3, max_value=8))

    # Generate points on a circle for a convex polygon
    angles = sorted(
        [
            draw(st.floats(min_value=0, max_value=2 * np.pi))
            for _ in range(num_points)
        ]
    )
    radius = draw(st.floats(min_value=5.0, max_value=50.0))
    center_x = draw(st.floats(min_value=- 50.0, max_value=50.0))
    center_y = draw(st.floats(min_value=- 50.0, max_value=50.0))

    boundary_points = [
        (center_x + radius * np.cos(angle), center_y + radius * np.sin(angle))
        for angle in angles
    ]

    return PatternConfig(
        pattern_type=pattern_type,
        spacing=spacing,
        angle=angle,
        overlap=overlap,
        start_point=start_point,
        boundary_points=boundary_points,
    )


@st.composite


def learning_config_strategy(draw):
    """Strategy for generating valid LearningConfig instances."""
    learning_rate = draw(st.floats(min_value=0.01, max_value=0.5))
    discount_factor = draw(st.floats(min_value=0.5, max_value=0.99))
    exploration_rate = draw(st.floats(min_value=0.01, max_value=0.5))
    memory_size = draw(st.integers(min_value=100, max_value=2000))
    batch_size = draw(st.integers(min_value=8, max_value=64))
    update_frequency = draw(st.integers(min_value=10, max_value=200))
    model_path = "test_model_path"

    return LearningConfig(
        learning_rate=learning_rate,
        discount_factor=discount_factor,
        exploration_rate=exploration_rate,
        memory_size=memory_size,
        batch_size=batch_size,
        update_frequency=update_frequency,
        model_path=model_path,
    )


class TestPathPlannerProperties:
    """Property - based tests for the PathPlanner class ."""

    @given(pattern_config=pattern_config_strategy())
    @settings(max_examples=10)
    def test_path_within_boundary(self, pattern_config):
        """Test that generated paths stay with in the boundary."""
        # Create a PathPlanner instance
        path_planner = PathPlanner(pattern_config)

        # Generate a path
        path = path_planner.generate_path()

        # Skip empty paths(which might be valid for some configurations)
        assume(len(path) > 0)

        # Check that all points in the path are with in or very close to the
        # boundary
        for point in path:
            assert self._point_near_or_in_polygon(
                point, pattern_config.boundary_points
            ), f"Point {point} is outside the boundary"

    @given(
        pattern_config=pattern_config_strategy(),
        learning_config = learning_config_strategy(),
    )
    @settings(max_examples=10)
    def test_learning_improves_path(self, pattern_config, learning_config):
        """Test that learning improves path quality over time."""
        # Create a PathPlanner instance with learning
        path_planner = PathPlanner(pattern_config, learning_config)

        # Generate initial path and calculate initial reward
        initial_path = path_planner.generate_path()

        # Skip if initial path is empty
        assume(len(initial_path) > 0)

        initial_reward = path_planner._calculate_reward(initial_path)

        # Generate multiple paths to allow learning to occur
        rewards = []
        for _ in range(5):
            path = path_planner.generate_path()
            if path:
                reward = path_planner._calculate_reward(path)
                rewards.append(reward)

        # Skip if we didn't get enough valid paths
        assume(len(rewards) > 2)

        # Check that the average reward of the last 3 paths is not worse than the initial reward
        # We use a tolerance because learning might not always improve in a
        # small number of iterations
        avg_recent_reward = sum(rewards[ - 3: ]) / 3
        assert (
            avg_recent_reward >= initial_reward * 0.9
 (
     f"Learning did not improve path quality: initial = {initial_reward}"
     f", recent = {avg_recent_reward}"
 )

    @given(pattern_config=pattern_config_strategy())
    @settings(max_examples=10)
    def test_path_smoothness(self, pattern_config):
        """Test that generated paths have reasonable smoothness."""
        # Create a PathPlanner instance
        path_planner = PathPlanner(pattern_config)

        # Generate a path
        path = path_planner.generate_path()

        # Skip if path is too short to measure smoothness
        assume(len(path) >= 3)

        # Calculate smoothness
        smoothness = path_planner._calculate_smoothness(path)

        # Smoothness should be between 0 and 1
        assert (
            0.0 <= smoothness <= 1.0
        ), f"Smoothness {smoothness} is outside the expected range [0, 1]"

    @given(
        pattern_config=pattern_config_strategy(),
        obstacles = st.lists(
            st.tuples(
                st.floats(min_value=- 100.0, max_value=100.0),
                st.floats(min_value=- 100.0, max_value=100.0),
            ),
            min_size = 0,
            max_size = 5,
        ),
    )
    @settings(max_examples=10)
    def test_obstacle_avoidance(self, pattern_config, obstacles):
        """Test that paths avoid obstacles when obstacles are added."""
        # Create a PathPlanner instance
        path_planner = PathPlanner(pattern_config)

        # Generate a path with out obstacles
        path_without_obstacles = path_planner.generate_path()

        # Skip if initial path is empty
        assume(len(path_without_obstacles) > 0)

        # Add obstacles
        path_planner.update_obstacle_map(obstacles)

        # Generate a path with obstacles
        path_with_obstacles = path_planner.generate_path()

        # Skip if path with obstacles is empty
        assume(len(path_with_obstacles) > 0)

        # Check that all points in the path are not too close to obstacles
        for point in path_with_obstacles:
            for obstacle in obstacles:
                distance = np.sqrt(
                    (point[0] - obstacle[0]) ** 2 + (point[1] - obstacle[1]) ** 2
                )
                assert (
                    distance >= 0.5
 (
     f"Path point {point} is too close to obstacle {obstacle}(distance="
     f"{distance})"
 )

    @given(
        p1=st.tuples(st.floats(), st.floats()),
        p2 = st.tuples(st.floats(), st.floats()),
        p3 = st.tuples(st.floats(), st.floats()),
        p4 = st.tuples(st.floats(), st.floats()),
    )
    @settings(max_examples=50)
    def test_line_intersection_properties(self, p1, p2, p3, p4):
        """Test properties of the line intersection algorithm."""
        # Create a PathPlanner instance with a simple configuration
        pattern_config = PatternConfig(
            pattern_type=PatternType.PARALLEL,
            spacing=1.0,
            angle=0.0,
            overlap=0.0,
            start_point=(0.0, 0.0),
            boundary_points = [(0, 0), (10, 0), (10, 10), (0, 10)],
        )
        path_planner = PathPlanner(pattern_config)

        # Skip degenerate cases where lines are points
        assume(p1 != p2 and p3 != p4)

        # Convert to numpy arrays
        p1_np = np.array(p1)
        p2_np = np.array(p2)
        p3_np = np.array(p3)
        p4_np = np.array(p4)

        # Calculate intersection
        intersection = path_planner._line_intersection(
            p1_np, p2_np, p3_np, p4_np
        )

        # If there's an intersection, it should lie on both lines
        if intersection is not None:
            # Check if the intersection point lies on the first line segment
            on_first_line = min(p1[0], p2[0]) <= intersection[0] <= max(
                p1[0], p2[0]
            ) and min(p1[1], p2[1]) <= intersection[1] <= max(p1[1], p2[1])

            # Check if the intersection point lies on the second line segment
            on_second_line = min(p3[0], p4[0]) <= intersection[0] <= max(
                p3[0], p4[0]
            ) and min(p3[1], p4[1]) <= intersection[1] <= max(p3[1], p4[1])

            assert (
                on_first_line and on_second_line
            ), f"Intersection {intersection} is not on both line segments"

    def _point_near_or_in_polygon(self, point, polygon, tolerance=1.0):
        """Check if a point is inside or near a polygon."""
        # First check if point is inside the polygon
        if self._point_in_polygon(point, polygon):
            return True

        # If not inside, check if it's near the boundary
        for i in range(len(polygon)):
            p1 = polygon[i]
            p2 = polygon[(i + 1) % len(polygon)]

            # Calculate distance from point to line segment
            distance = self._point_to_line_distance(point, p1, p2)
            if distance <= tolerance:
                return True

        return False

    def _point_in_polygon(self, point, polygon):
        """Check if a point is inside a polygon using ray casting algorithm."""
        x, y = point
        n = len(polygon)
        inside = False

        j = n - 1
        for i in range(n):
            xi, yi = polygon[i]
            xj, yj = polygon[j]

            if ((yi > y) != (yj > y)) and (
                x < (xj - xi) * (y - yi) / (yj - yi) + xi
            ):
                inside = not inside

            j = i

        return inside

    def _point_to_line_distance(self, point, line_start, line_end):
        """Calculate the distance from a point to a line segment."""
        x, y = point
        x1, y1 = line_start
        x2, y2 = line_end

        # Calculate the squared length of the line segment
        line_length_squared = (x2 - x1) ** 2 + (y2 - y1) ** 2

        # If the line segment is actually a point, return the distance to that
        # point
        if line_length_squared == 0:
            return np.sqrt((x - x1) ** 2 + (y - y1) ** 2)

        # Calculate the projection of the point onto the line
        t = max(
            0,
            min(
                1,
                ((x - x1) * (x2 - x1) + (y - y1) * (y2 - y1)) / line_length_squared,
            ),
        )

        # Calculate the closest point on the line segment
        closest_x = x1 + t * (x2 - x1)
        closest_y = y1 + t * (y2 - y1)

        # Return the distance to the closest point
        return np.sqrt((x - closest_x) ** 2 + (y - closest_y) ** 2)
