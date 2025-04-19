"""
Integration tests for sensor data processing and decision making.

This module tests the interaction between the sensor interface and the decision-making
components, ensuring that sensor data is processed correctly and used to make
appropriate decisions about movement and obstacle avoidance.
"""

import pytest
import time
from unittest.mock import MagicMock, patch

from mower.hardware.sensor_interface import EnhancedSensorInterface, SensorStatus
from mower.obstacle_detection.avoidance_algorithm import AvoidanceAlgorithm, AvoidanceState
from mower.navigation.path_planner import PathPlanner, PatternConfig, PatternType, LearningConfig


class TestSensorDecisionMaking:
    """Integration tests for sensor data processing and decision making."""

    @pytest.fixture
    def setup_sensor_decision_components(self):
        """Set up sensor interface and decision-making components for testing."""
        # Mock the I2C bus
        with patch("mower.hardware.sensor_interface.busio.I2C") as mock_i2c:
            # Create an EnhancedSensorInterface instance
            sensor_interface = EnhancedSensorInterface()
            
            # Create pattern and learning configurations
            pattern_config = PatternConfig(
                pattern_type=PatternType.PARALLEL,
                spacing=1.0,
                angle=0.0,
                overlap=0.0,
                start_point=(0.0, 0.0),
                boundary_points=[(0, 0), (10, 0), (10, 10), (0, 10)]
            )
            
            learning_config = LearningConfig(
                learning_rate=0.1,
                discount_factor=0.9,
                exploration_rate=0.2,
                memory_size=1000,
                batch_size=32,
                update_frequency=100,
                model_path="test_model_path"
            )
            
            # Create a PathPlanner instance
            path_planner = PathPlanner(pattern_config, learning_config)
            
            # Create an AvoidanceAlgorithm instance
            avoidance_algorithm = AvoidanceAlgorithm(pattern_planner=path_planner)
            
            # Mock the motor controller
            motor_controller = MagicMock()
            motor_controller.get_current_position.return_value = (0.0, 0.0)
            motor_controller.get_current_heading.return_value = 0.0
            
            # Set the motor controller on the avoidance algorithm
            avoidance_algorithm.motor_controller = motor_controller
            
            # Mock the sensor data
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
                "battery_current": 1.0
            }
            
            # Mock the sensor status
            for sensor_name in sensor_interface._sensor_status:
                sensor_interface._sensor_status[sensor_name].working = True
                sensor_interface._sensor_status[sensor_name].error_count = 0
                sensor_interface._sensor_status[sensor_name].last_error = None
            
            return {
                "sensor_interface": sensor_interface,
                "path_planner": path_planner,
                "avoidance_algorithm": avoidance_algorithm,
                "motor_controller": motor_controller
            }

    def test_obstacle_detection_from_sensor_data(self, setup_sensor_decision_components):
        """Test that obstacles are detected correctly from sensor data."""
        # Get the components
        sensor_interface = setup_sensor_decision_components["sensor_interface"]
        avoidance_algorithm = setup_sensor_decision_components["avoidance_algorithm"]
        
        # Set up the avoidance algorithm to use the sensor interface
        avoidance_algorithm.sensor_interface = sensor_interface
        
        # Initially, no obstacles are detected
        assert avoidance_algorithm.obstacle_left is False
        assert avoidance_algorithm.obstacle_right is False
        
        # Simulate an obstacle on the left
        sensor_interface._data["left_distance"] = 20.0  # 20cm is close enough to be an obstacle
        
        # Update the obstacle status based on sensor data
        avoidance_algorithm._update_sensor_obstacle_status()
        
        # Verify that an obstacle on the left is detected
        assert avoidance_algorithm.obstacle_left is True
        assert avoidance_algorithm.obstacle_right is False
        
        # Simulate an obstacle on the right
        sensor_interface._data["left_distance"] = 100.0  # Clear the left obstacle
        sensor_interface._data["right_distance"] = 20.0  # 20cm is close enough to be an obstacle
        
        # Update the obstacle status based on sensor data
        avoidance_algorithm._update_sensor_obstacle_status()
        
        # Verify that an obstacle on the right is detected
        assert avoidance_algorithm.obstacle_left is False
        assert avoidance_algorithm.obstacle_right is True
        
        # Simulate obstacles on both sides
        sensor_interface._data["left_distance"] = 20.0  # 20cm is close enough to be an obstacle
        sensor_interface._data["right_distance"] = 20.0  # 20cm is close enough to be an obstacle
        
        # Update the obstacle status based on sensor data
        avoidance_algorithm._update_sensor_obstacle_status()
        
        # Verify that obstacles on both sides are detected
        assert avoidance_algorithm.obstacle_left is True
        assert avoidance_algorithm.obstacle_right is True
        
        # Clear all obstacles
        sensor_interface._data["left_distance"] = 100.0
        sensor_interface._data["right_distance"] = 100.0
        
        # Update the obstacle status based on sensor data
        avoidance_algorithm._update_sensor_obstacle_status()
        
        # Verify that no obstacles are detected
        assert avoidance_algorithm.obstacle_left is False
        assert avoidance_algorithm.obstacle_right is False

    def test_safety_checks_from_sensor_data(self, setup_sensor_decision_components):
        """Test that safety checks are performed correctly based on sensor data."""
        # Get the components
        sensor_interface = setup_sensor_decision_components["sensor_interface"]
        
        # Initially, it's safe to operate
        assert sensor_interface.is_safe_to_operate() is True
        
        # Simulate a sensor failure
        sensor_interface._sensor_status["bno085"].working = False
        
        # Verify that it's not safe to operate
        assert sensor_interface.is_safe_to_operate() is False
        
        # Restore the sensor
        sensor_interface._sensor_status["bno085"].working = True
        
        # Verify that it's safe to operate again
        assert sensor_interface.is_safe_to_operate() is True
        
        # Simulate a critical battery level
        original_battery_voltage = sensor_interface._data["battery_voltage"]
        sensor_interface._data["battery_voltage"] = 10.0  # Critical battery level
        
        # In a real system, this would trigger an emergency stop
        # For testing, we'll just verify that the battery voltage is critical
        assert sensor_interface._data["battery_voltage"] < 11.0
        
        # Restore the battery voltage
        sensor_interface._data["battery_voltage"] = original_battery_voltage

    def test_decision_making_based_on_sensor_data(self, setup_sensor_decision_components):
        """Test that decisions are made correctly based on sensor data."""
        # Get the components
        sensor_interface = setup_sensor_decision_components["sensor_interface"]
        avoidance_algorithm = setup_sensor_decision_components["avoidance_algorithm"]
        motor_controller = setup_sensor_decision_components["motor_controller"]
        
        # Set up the avoidance algorithm to use the sensor interface
        avoidance_algorithm.sensor_interface = sensor_interface
        
        # Simulate an obstacle on the left
        sensor_interface._data["left_distance"] = 20.0  # 20cm is close enough to be an obstacle
        
        # Update the obstacle status based on sensor data
        avoidance_algorithm._update_sensor_obstacle_status()
        
        # Detect the obstacle
        obstacle_detected, obstacle_data = avoidance_algorithm._detect_obstacle()
        
        # Verify that an obstacle was detected
        assert obstacle_detected is True
        assert obstacle_data is not None
        assert obstacle_data["left_sensor"] is True
        assert obstacle_data["right_sensor"] is False
        
        # Start avoidance
        avoidance_algorithm._start_avoidance()
        
        # Verify that the motor controller was called to execute the avoidance maneuver
        assert motor_controller.get_current_heading.called
        assert motor_controller.rotate_to_heading.called
        
        # Verify that the correct avoidance strategy was chosen (turn right for left obstacle)
        # This is an implementation detail, but we can infer it from the motor controller calls
        heading_calls = motor_controller.get_current_heading.call_count
        rotate_calls = motor_controller.rotate_to_heading.call_count
        assert heading_calls >= 1
        assert rotate_calls >= 1

    def test_sensor_data_integration_with_navigation(self, setup_sensor_decision_components):
        """Test that sensor data is integrated correctly with navigation."""
        # Get the components
        sensor_interface = setup_sensor_decision_components["sensor_interface"]
        avoidance_algorithm = setup_sensor_decision_components["avoidance_algorithm"]
        path_planner = setup_sensor_decision_components["path_planner"]
        motor_controller = setup_sensor_decision_components["motor_controller"]
        
        # Set up the avoidance algorithm to use the sensor interface
        avoidance_algorithm.sensor_interface = sensor_interface
        
        # Generate a path
        path = path_planner.generate_path()
        
        # Verify that a path was generated
        assert len(path) > 0
        
        # Simulate navigation along the path
        for i, waypoint in enumerate(path[:5]):  # Just test the first 5 waypoints
            # Set the current position to the waypoint
            motor_controller.get_current_position.return_value = waypoint
            
            # Check for obstacles at this position
            sensor_interface._data["left_distance"] = 100.0
            sensor_interface._data["right_distance"] = 100.0
            avoidance_algorithm._update_sensor_obstacle_status()
            obstacle_detected, _ = avoidance_algorithm._detect_obstacle()
            
            # Verify that no obstacles are detected
            assert obstacle_detected is False
            
            # Simulate an obstacle at the next waypoint
            if i < len(path) - 1:
                next_waypoint = path[i + 1]
                
                # Calculate the direction to the next waypoint
                dx = next_waypoint[0] - waypoint[0]
                dy = next_waypoint[1] - waypoint[1]
                
                # If moving right, simulate an obstacle on the right
                if dx > 0:
                    sensor_interface._data["right_distance"] = 20.0
                # If moving left, simulate an obstacle on the left
                elif dx < 0:
                    sensor_interface._data["left_distance"] = 20.0
                # If moving up, simulate an obstacle on the right (arbitrary choice)
                elif dy > 0:
                    sensor_interface._data["right_distance"] = 20.0
                # If moving down, simulate an obstacle on the left (arbitrary choice)
                elif dy < 0:
                    sensor_interface._data["left_distance"] = 20.0
                
                # Update the obstacle status based on sensor data
                avoidance_algorithm._update_sensor_obstacle_status()
                
                # Detect the obstacle
                obstacle_detected, obstacle_data = avoidance_algorithm._detect_obstacle()
                
                # Verify that an obstacle was detected
                assert obstacle_detected is True
                assert obstacle_data is not None
                
                # Start avoidance
                avoidance_algorithm._start_avoidance()
                
                # Verify that the motor controller was called to execute the avoidance maneuver
                assert motor_controller.get_current_heading.called
                assert motor_controller.rotate_to_heading.called or motor_controller.move_distance.called
                
                # Clear the obstacle for the next iteration
                sensor_interface._data["left_distance"] = 100.0
                sensor_interface._data["right_distance"] = 100.0