"""
Test the simulation mode capabilities.

This module demonstrates how to use the simulation capabilities for testing
the autonomous mower system without requiring physical hardware.
"""

import os
import time
import pytest
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import simulation modules
from mower.simulation import enable_simulation, is_simulation_enabled
from mower.simulation.world_model import get_world_instance, Vector2D, reset_world

# Import mower modules
from mower.main_controller import MainController
from mower.robot_di import Robot as RobotDI
from mower.config_management import get_config, set_config


@pytest.fixture
def simulation_environment():
    """Set up a simulation environment for testing."""
    # Enable simulation mode
    enable_simulation()
    assert is_simulation_enabled(), "Simulation mode should be enabled"

    # Reset the virtual world
    reset_world()
    world = get_world_instance()

    # Set up a simple virtual world with obstacles
    world.set_robot_position(Vector2D(10.0, 10.0), 0.0)  # Start at (10, 10) facing east

    # Add some obstacles
    world.add_obstacle(Vector2D(15.0, 10.0), 1.0, obstacle_type="rock")  # Rock at (15, 10)
    world.add_obstacle(Vector2D(10.0, 15.0), 0.5, obstacle_type="small_rock")  # Small rock at (10, 15)
    world.add_obstacle(Vector2D(5.0, 5.0), 2.0, obstacle_type="tree")  # Tree at (5, 5)

    # Configure the mower for simulation
    set_config('use_simulation', True)

    # Return the world instance for test use
    yield world

    # Clean up
    reset_world()


def test_obstacle_detection(simulation_environment):
    """Test that the mower can detect obstacles in simulation mode."""
    world = simulation_environment

    # Get the robot's current position and heading
    robot_state = world.get_robot_state()
    position = Vector2D(*robot_state["position"])
    heading = robot_state["heading"]

    logger.info(f"Robot starting at position {position}, heading {heading}")

    # Check for obstacles in front of the robot
    direction = Vector2D(1.0, 0.0)  # East
    distance, obstacle = world.get_distance_to_nearest_obstacle(position, direction, max_range=10.0)

    # We should detect the rock at (15, 10)
    assert obstacle is not None, "Should detect an obstacle"
    assert obstacle.obstacle_type == "rock", f"Should detect a rock, got {obstacle.obstacle_type}"
    assert 4.0 < distance < 6.0, f"Distance should be about 5m, got {distance}m"

    logger.info(f"Detected {obstacle.obstacle_type} at distance {distance}m")


def test_robot_movement(simulation_environment):
    """Test that the robot can move in the virtual world."""
    world = simulation_environment

    # Get initial position
    initial_state = world.get_robot_state()
    initial_position = Vector2D(*initial_state["position"])

    logger.info(f"Robot starting at position {initial_position}")

    # Set motor speeds to move forward
    world.set_robot_motor_speeds(0.5, 0.5)  # 50% speed on both motors

    # Update the world for 2 seconds
    for _ in range(20):  # 20 updates at 0.1s each
        world.update(0.1)
        time.sleep(0.01)  # Small delay to not hog CPU

    # Get new position
    new_state = world.get_robot_state()
    new_position = Vector2D(*new_state["position"])

    # Calculate distance moved
    distance_moved = initial_position.distance_to(new_position)

    logger.info(f"Robot moved to position {new_position}, distance moved: {distance_moved}m")

    # We should have moved forward
    assert distance_moved > 0.5, f"Robot should have moved, only moved {distance_moved}m"

    # Stop the robot
    world.set_robot_motor_speeds(0.0, 0.0)


def test_collision_handling(simulation_environment):
    """Test that collisions are properly handled in the virtual world."""
    world = simulation_environment

    # Position the robot near an obstacle
    world.set_robot_position(Vector2D(14.0, 10.0), 0.0)  # Near the rock at (15, 10)

    # Get initial position
    initial_state = world.get_robot_state()
    initial_position = Vector2D(*initial_state["position"])

    logger.info(f"Robot starting at position {initial_position}")

    # Set motor speeds to move toward the obstacle
    world.set_robot_motor_speeds(0.5, 0.5)  # 50% speed on both motors

    # Update the world for 2 seconds
    for _ in range(20):  # 20 updates at 0.1s each
        world.update(0.1)
        time.sleep(0.01)  # Small delay to not hog CPU

    # Get new position
    new_state = world.get_robot_state()
    new_position = Vector2D(*new_state["position"])

    logger.info(f"Robot moved to position {new_position}")

    # Calculate distance to obstacle
    obstacle_position = Vector2D(15.0, 10.0)
    distance_to_obstacle = new_position.distance_to(obstacle_position)

    # We should not have penetrated the obstacle (radius 1.0)
    assert distance_to_obstacle >= 1.0, f"Robot should not penetrate obstacle, distance: {distance_to_obstacle}m"

    # Stop the robot
    world.set_robot_motor_speeds(0.0, 0.0)


def test_system_integration(simulation_environment):
    """Test the integration of the mower system with simulation mode."""
    # This test would initialize the actual mower system with simulation mode enabled
    # For now, we'll just verify that simulation mode is properly enabled
    assert is_simulation_enabled(), "Simulation mode should be enabled"

    # In a real test, we would:
    # 1. Initialize the mower system
    # 2. Run a simple scenario
    # 3. Verify the expected behavior

    # For demonstration purposes, we'll just log a message
    logger.info("System integration test with simulation mode would go here")

    # This is a placeholder for future implementation
    pass


if __name__ == "__main__":
    # This allows running the tests directly without pytest
    # Enable simulation mode
    enable_simulation()

    # Create a simulation environment
    reset_world()
    world = get_world_instance()

    # Set up a simple virtual world with obstacles
    world.set_robot_position(Vector2D(10.0, 10.0), 0.0)
    world.add_obstacle(Vector2D(15.0, 10.0), 1.0, obstacle_type="rock")
    world.add_obstacle(Vector2D(10.0, 15.0), 0.5, obstacle_type="small_rock")
    world.add_obstacle(Vector2D(5.0, 5.0), 2.0, obstacle_type="tree")

    # Run the tests
    try:
        test_obstacle_detection(world)
        test_robot_movement(world)
        test_collision_handling(world)
        test_system_integration(world)
        logger.info("All tests passed!")
    except AssertionError as e:
        logger.error(f"Test failed: {e}")
    finally:
        # Clean up
        reset_world()
