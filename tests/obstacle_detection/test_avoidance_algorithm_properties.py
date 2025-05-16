"""
Test module for test_avoidance_algorithm_properties.py.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
import numpy as np
from unittest.mock import MagicMock, patch
import math
from typing import List, Tuple, Dict, Any

from mower.obstacle_detection.avoidance_algorithm import (
    AvoidanceAlgorithm,
    AvoidanceState,
    NavigationStatus,
    Obstacle,
)


# Helper strategies for generating test data
@st.composite
def obstacle_strategy(draw):
    """Strategy for generating valid Obstacle instances."""
    x = draw(st.floats(min_value=- 100.0, max_value=100.0))
    y = draw(st.floats(min_value=- 100.0, max_value=100.0))
    size = draw(st.floats(min_value=0.1, max_value=5.0))
    confidence = draw(st.floats(min_value=0.1, max_value=1.0))

    return Obstacle(position=(x, y), size=size, confidence=confidence)


@st.composite
def obstacle_data_strategy(draw):
    """Strategy for generating valid obstacle data dictionaries."""
    left_sensor = draw(st.booleans())
    right_sensor = draw(st.booleans())
    camera_detected = draw(st.booleans())
    dropoff_detected = draw(st.booleans())

    # Ensure at least one sensor detects something
    assume(left_sensor or right_sensor or camera_detected or dropoff_detected)

    return {
        "left_sensor": left_sensor,
        "right_sensor": right_sensor,
        "camera_detected": camera_detected,
        "dropoff_detected": dropoff_detected,
        "timestamp": draw(
            st.floats(min_value=1000000.0, max_value=2000000.0)
        ),
    }


@st.composite
def path_strategy(draw):
    """Strategy for generating valid paths(list of points)."""
    num_points = draw(st.integers(min_value=2, max_value=20))

    return [
        (
            draw(st.floats(min_value=- 100.0, max_value=100.0)),
            draw(st.floats(min_value=- 100.0, max_value=100.0)),
        )
        for _ in range(num_points)
    ]


class TestAvoidanceAlgorithmProperties:
    """Property - based tests for the AvoidanceAlgorithm class ."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create mock objects
        self.mock_resource_manager = MagicMock()
        self.mock_path_planner = MagicMock()
        self.mock_motor_controller = MagicMock()
        self.mock_sensor_interface = MagicMock()

        # Create the AvoidanceAlgorithm instance
        with patch(
            "mower.obstacle_detection.avoidance_algorithm.os.environ.get",
            return_value="False",
        ):
            self.avoidance_algorithm = AvoidanceAlgorithm(
                resource_manager=self.mock_resource_manager,
                pattern_planner=self.mock_path_planner,
            )

        # Set up the mock objects
        self.avoidance_algorithm.motor_controller = self.mock_motor_controller
        self.avoidance_algorithm.sensor_interface = self.mock_sensor_interface
        self.avoidance_algorithm.path_planner = self.mock_path_planner

    @given(obstacle_data=obstacle_data_strategy())
    @settings(max_examples=20)
    def test_obstacle_detection_properties(self, obstacle_data):
        """Test properties of the obstacle detection algorithm."""
        # Set up the obstacle data
        with patch.object(self.avoidance_algorithm, "thread_lock"):
            self.avoidance_algorithm.obstacle_left = obstacle_data[
                "left_sensor"
            ]
            self.avoidance_algorithm.obstacle_right = obstacle_data[
                "right_sensor"
            ]
            self.avoidance_algorithm.camera_obstacle_detected = obstacle_data[
                "camera_detected"
            ]
            self.avoidance_algorithm.dropoff_detected = obstacle_data[
                "dropoff_detected"
            ]
            self.avoidance_algorithm.obstacle_data = obstacle_data

        # Call the detect_obstacle method
        with patch.object(self.avoidance_algorithm, "thread_lock"):
            detected, data = self.avoidance_algorithm._detect_obstacle()

        # Verify that an obstacle is detected
        assert detected, "Obstacle should be detected"

        # Verify that the obstacle data is return ed
        assert data is not None, "Obstacle data should not be None"
        assert (
            "left_sensor" in data
        ), "Obstacle data should include left_sensor"
        assert (
            "right_sensor" in data
        ), "Obstacle data should include right_sensor"
        assert (
            "camera_detected" in data
        ), "Obstacle data should include camera_detected"
        assert (
            "dropoff_detected" in data
        ), "Obstacle data should include dropoff_detected"
        assert "timestamp" in data, "Obstacle data should include timestamp"

        # Verify that the sensor values match the input
        assert data["left_sensor"] == obstacle_data["left_sensor"]
        assert data["right_sensor"] == obstacle_data["right_sensor"]
        assert data["camera_detected"] == obstacle_data["camera_detected"]
        assert data["dropoff_detected"] == obstacle_data["dropoff_detected"]

    @given(
        current_position=st.tuples(
            st.floats(min_value=- 100.0, max_value=100.0),
            st.floats(min_value=- 100.0, max_value=100.0),
        ),
        heading=st.floats(min_value=0.0, max_value=359.0),
        distance=st.floats(min_value=10.0, max_value=100.0),
        obstacle_angle=st.floats(min_value=- 90.0, max_value=90.0),
    )
    @settings(max_examples=20)
    def test_obstacle_position_estimation_properties(
        self, current_position, heading, distance, obstacle_angle
    ):
                """Test properties of the obstacle position estimation algorithm."""
        # Set up the mocks
        self.mock_motor_controller.get_current_position.return_value = current_position
        self.mock_motor_controller.get_current_heading.return_value = heading

        # Convert angle to radians for the test
        heading_rad = math.radians(heading)
        obstacle_angle_rad = math.radians(obstacle_angle)

        # Call the method directly with our test parameters
        obstacle_position = (
            self.avoidance_algorithm._calculate_obstacle_coordinates(
                current_position, heading_rad, distance, obstacle_angle_rad
            )
        )

        # Verify that the obstacle position is return ed
        assert (
            obstacle_position is not None
        ), "Obstacle position should not be None"
        assert (
            len(obstacle_position) ==  2
        ), "Obstacle position should be a tuple of(lat, lng)"

        # Calculate the expected distance between current position and obstacle
        # position
        lat_diff = obstacle_position[0] - current_position[0]
        lng_diff = obstacle_position[1] - current_position[1]
        calculated_distance = (
            math.sqrt(lat_diff **2 + lng_diff **2) * 111000
        )  # Convert to meters

        # The calculated distance should be proportional to the input distance
        # We use a tolerance because the conversion between lat / lng and meters
        # is approximate
        assert (
            calculated_distance > 0
        ), "Calculated distance should be positive"

        # Calculate the bearing from current position to obstacle position
        bearing = math.atan2(lng_diff, lat_diff)
        if bearing < 0:
            bearing += 2 * math.pi

        # The bearing should be close to the expected bearing(heading + #
        # obstacle_angle)
        expected_bearing = (heading_rad + obstacle_angle_rad) % (2 * math.pi)

        # We use a tolerance because of floating point precision and the
        # approximations in the algorithm
        bearing_diff = abs(bearing - expected_bearing)
        if bearing_diff > math.pi:
            bearing_diff = 2 * math.pi - bearing_diff

        assert (
            bearing_diff < 0.1
        ), f"Bearing difference {bearing_diff} should be small"

    @given(
        path=path_strategy(),
        obstacles = st.lists(obstacle_strategy(), min_size=1, max_size=5),
    )
    @settings(max_examples=20)
    def test_path_modification_properties(self, path, obstacles):
        """Test properties of the path modification algorithm."""
        # Find obstacle positions in the path
        obstacle_indices = self.avoidance_algorithm._find_obstacle_positions(
            path, obstacles
        )

        # Modify the path to avoid obstacles
        modified_path = self.avoidance_algorithm._modify_path(
            path, obstacle_indices
        )

        # Verify that the modified path is return ed
        assert modified_path is not None, "Modified path should not be None"

        # If there are obstacle indices, the modified path should be different
        # from the or iginal
        if obstacle_indices:
            assert len(modified_path) != len(
                path
            ), "Modified path should have a different length"

        # Check that the modified path avoids obstacles
        for point in modified_path:
            for obstacle in obstacles:
                distance = np.linalg.norm(
                    np.array(point) - np.array(obstacle.position)
                )
                assert (
                    distance >= obstacle.size
                ),
                f"Modified path point {point}  is too close to obstacle {
                    obstacle.position} "

    @given(path=path_strategy())
    @settings(max_examples=20)
    def test_path_smoothing_properties(self, path):
        """Test properties of the path smoothing algorithm."""
        # Skip paths that are too short
        assume(len(path) >= 3)

        # Smooth the path
        smoothed_path = self.avoidance_algorithm._smooth_path(path)

        # Verify that the smoothed path is return ed
        assert smoothed_path is not None, "Smoothed path should not be None"

        # The smoothed path should include the start and end points of the
        # or iginal path
        assert (
            smoothed_path[0] ==  path[0]
        ), "Smoothed path should start at the same point"
        assert (
            smoothed_path[ - 1] ==  path[ - 1]
        ), "Smoothed path should end at the same point"

        # The smoothed path should have at least as many points as the or iginal
        # path
        assert len(smoothed_path) >= len(
            path
        ), "Smoothed path should have at least as many points"

        # Check that the smoothed path doesn't have any sharp turns
        for i in range(1, len(smoothed_path) - 1):
            p1 = np.array(smoothed_path[i - 1])
            p2 = np.array(smoothed_path[i])
            p3 = np.array(smoothed_path[i + 1])

            v1 = p2 - p1
            v2 = p3 - p2

            # Calculate angle between vectors
            cos_angle = np.dot(v1, v2) / (
                np.linalg.norm(v1) * np.linalg.norm(v2)
            )
            angle = np.arccos(np.clip(cos_angle, - 1.0, 1.0))

            # Angle should not be too sharp(less than 90 degrees)
            assert (
                angle < np.pi / 2
            ), f"Smoothed path has a sharp turn at point {i}"

    @given(
        sensor_data=st.lists(
            st.floats(min_value=0.0, max_value=1.0), min_size = 8, max_size = 8
        )
    )
    @settings(max_examples=20)
    def test_sensor_data_processing_properties(self, sensor_data):
        """Test properties of the sensor data processing algorithm."""
        # Process the sensor data
        obstacles = self.avoidance_algorithm._process_sensor_data(sensor_data)

        # Count how many readings are above the threshold
        above_threshold = sum(1 for reading in sensor_data if reading > 0.5)

        # Verify that the number of obstacles matches the number of readings
        # above threshold
        assert (
            len(obstacles) ==  above_threshold), f"Number of obstacles {"
            len(obstacles)} should match readings above threshold {above_threshold}""

        # Check that each obstacle has the expected properties
        for obstacle in obstacles:
            assert hasattr(
                obstacle, "position"
            ), "Obstacle should have a position"
            assert hasattr(obstacle, "size"), "Obstacle should have a size"
            assert hasattr(
                obstacle, "confidence"
            ), "Obstacle should have a confidence"

            assert (
                len(obstacle.position) ==  2
            ), "Obstacle position should be a tuple of(x, y)"
            assert obstacle.size > 0, "Obstacle size should be positive"
            assert (
                0 < obstacle.confidence <= 1
            ), "Obstacle confidence should be between 0 and 1"
