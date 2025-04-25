"""
Example tests using hardware fixtures.

This module demonstrates how to use the hardware fixtures for testing
without requiring physical hardware.
"""

from mower.simulation.world_model import Vector2D
from tests.hardware_fixtures import (
    sim_world, sim_gps, sim_imu, sim_tof,
    sim_blade_controller, sim_motor_controller, sim_hardware
)
import pytest
import time
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the hardware fixtures

# Import simulation modules


def test_gps_sensor(sim_world, sim_gps):
    """Test that the GPS sensor provides position data."""
    # Set up the virtual world
    sim_world.set_robot_position(Vector2D(10.0, 10.0), 0.0)

    # Get data from the GPS sensor
    data = sim_gps.get_data()

    # Check that we have position data
    assert "position" in data, "GPS data should include position"
    assert "status" in data, "GPS data should include status"

    # Get the position directly
    position = sim_gps.get_position()

    # If we have a GPS fix, position should not be None
    if data["fix_quality"] > 0:
        assert position is not None, "Position should not be None when we have a GPS fix"

        # Position should be a tuple of (timestamp, easting, northing, zone_number, zone_letter)
        assert len(position) == 5, "Position should be a 5-tuple"

        # Log the position
        logger.info(f"GPS position: {position}")
    else:
        logger.info("No GPS fix available")


def test_imu_sensor(sim_world, sim_imu):
    """Test that the IMU sensor provides orientation data."""
    # Set up the virtual world
    sim_world.set_robot_position(
        Vector2D(10.0, 10.0), 0.5)  # 0.5 radians heading

    # Get data from the IMU sensor
    data = sim_imu.get_data()

    # Check that we have orientation data
    assert "orientation" in data, "IMU data should include orientation"
    assert "acceleration" in data, "IMU data should include acceleration"
    assert "gyro" in data, "IMU data should include gyro"

    # Get the orientation directly
    orientation = sim_imu.get_orientation()

    # Orientation should be a tuple of (roll, pitch, yaw)
    assert len(orientation) == 3, "Orientation should be a 3-tuple"

    # The yaw should be close to the robot's heading
    robot_heading = sim_world.get_robot_state()["heading"]
    assert abs(
        orientation[2] - robot_heading) < 0.1, "IMU yaw should be close to robot heading"

    # Log the orientation
    logger.info(f"IMU orientation: {orientation}")


def test_tof_sensor(sim_world, sim_tof):
    """Test that the ToF sensor provides distance data."""
    # Set up the virtual world
    sim_world.set_robot_position(Vector2D(10.0, 10.0), 0.0)

    # Add an obstacle in front of the robot
    sim_world.add_obstacle(Vector2D(15.0, 10.0), 1.0, obstacle_type="rock")

    # Get data from the ToF sensor
    data = sim_tof.get_data()

    # Check that we have distance data
    assert "distances" in data, "ToF data should include distances"

    # Get the distances directly
    distances = sim_tof.get_distances()

    # We should have distances for all sensors
    assert len(distances) > 0, "Should have distances for at least one sensor"

    # The front sensor should detect the obstacle
    front_distance = distances.get("front")
    if front_distance is not None:
        # The distance should be approximately 5m (obstacle at 15m, robot at 10m, obstacle radius 1m)
        assert 3.0 < front_distance < 7.0, f"Front distance should be about 5m, got {front_distance}m"

        # Log the distance
        logger.info(f"ToF front distance: {front_distance}m")
    else:
        logger.info("No front ToF sensor available")


def test_blade_controller(sim_world, sim_blade_controller):
    """Test that the blade controller can control the blade."""
    # Set up the virtual world
    sim_world.set_robot_position(Vector2D(10.0, 10.0), 0.0)

    # Initially, the blade should be off
    assert not sim_world.get_robot_state(
    )["blade_running"], "Blade should initially be off"

    # Turn on the blade
    sim_blade_controller.set_blade_state(True)

    # Update the world to apply the change
    sim_world.update(0.2)

    # The blade should now be on
    assert sim_world.get_robot_state(
    )["blade_running"], "Blade should be on after setting state to True"

    # Turn off the blade
    sim_blade_controller.set_blade_state(False)

    # Update the world to apply the change
    sim_world.update(0.2)

    # The blade should now be off
    assert not sim_world.get_robot_state(
    )["blade_running"], "Blade should be off after setting state to False"

    # Log the blade state
    logger.info(f"Blade state: {sim_world.get_robot_state()['blade_running']}")


def test_motor_controller(sim_world, sim_motor_controller):
    """Test that the motor controller can control the motors."""
    # Set up the virtual world
    sim_world.set_robot_position(Vector2D(10.0, 10.0), 0.0)

    # Initially, the motors should be stopped
    initial_state = sim_world.get_robot_state()
    assert initial_state["motor_speeds"][0] == 0.0, "Left motor should initially be stopped"
    assert initial_state["motor_speeds"][1] == 0.0, "Right motor should initially be stopped"

    # Set the motor speeds
    sim_motor_controller.set_motor_speeds(0.5, 0.5)  # 50% speed on both motors

    # Update the world to apply the change
    sim_world.update(0.2)

    # The motors should now be running
    motor_state = sim_world.get_robot_state()
    assert motor_state["motor_speeds"][0] == 0.5, "Left motor should be at 50% speed"
    assert motor_state["motor_speeds"][1] == 0.5, "Right motor should be at 50% speed"

    # The robot should be moving
    assert motor_state["velocity"].magnitude() > 0.0, "Robot should be moving"

    # Stop the motors
    sim_motor_controller.set_motor_speeds(0.0, 0.0)

    # Update the world to apply the change
    sim_world.update(0.2)

    # The motors should now be stopped
    final_state = sim_world.get_robot_state()
    assert final_state["motor_speeds"][0] == 0.0, "Left motor should be stopped"
    assert final_state["motor_speeds"][1] == 0.0, "Right motor should be stopped"

    # Log the motor speeds
    logger.info(f"Motor speeds: {final_state['motor_speeds']}")


def test_all_hardware(sim_world, sim_hardware):
    """Test that all hardware components can be used together."""
    # Set up the virtual world
    sim_world.set_robot_position(Vector2D(10.0, 10.0), 0.0)

    # Add an obstacle in front of the robot
    sim_world.add_obstacle(Vector2D(15.0, 10.0), 1.0, obstacle_type="rock")

    # Get data from all sensors
    gps_data = sim_hardware["gps"].get_data()
    imu_data = sim_hardware["imu"].get_data()
    tof_data = sim_hardware["tof"].get_data()

    # Check that we have data from all sensors
    assert "position" in gps_data, "GPS data should include position"
    assert "orientation" in imu_data, "IMU data should include orientation"
    assert "distances" in tof_data, "ToF data should include distances"

    # Turn on the blade
    sim_hardware["blade_controller"].set_blade_state(True)

    # Set the motor speeds
    sim_hardware["motor_controller"].set_motor_speeds(0.5, 0.5)

    # Update the world to apply the changes
    sim_world.update(0.2)

    # Check that the blade is on and the motors are running
    robot_state = sim_world.get_robot_state()
    assert robot_state["blade_running"], "Blade should be on"
    assert robot_state["motor_speeds"][0] == 0.5, "Left motor should be at 50% speed"
    assert robot_state["motor_speeds"][1] == 0.5, "Right motor should be at 50% speed"

    # Log the robot state
    logger.info(f"Robot state: {robot_state}")

    # Clean up
    sim_hardware["blade_controller"].set_blade_state(False)
    sim_hardware["motor_controller"].set_motor_speeds(0.0, 0.0)
    sim_world.update(0.2)


if __name__ == "__main__":
    # This allows running the tests directly without pytest
    import sys
    from mower.simulation import enable_simulation

    # Enable simulation mode
    enable_simulation()

    # Create a simulation environment
    from mower.simulation.world_model import reset_world, get_world_instance
    reset_world()
    world = get_world_instance()

    # Create simulated hardware components
    from mower.simulation.sensors.gps_sim import SimulatedGpsPosition
    from mower.simulation.sensors.imu_sim import SimulatedImu
    from mower.simulation.sensors.tof_sim import SimulatedToF
    from mower.simulation.actuators.blade_sim import SimulatedBladeController
    from mower.simulation.actuators.motor_sim import SimulatedMotorController

    gps = SimulatedGpsPosition()
    gps._initialize()

    imu = SimulatedImu()
    imu._initialize()

    tof = SimulatedToF()
    tof._initialize()

    blade_controller = SimulatedBladeController()
    blade_controller._initialize()

    motor_controller = SimulatedMotorController()
    motor_controller._initialize()

    # Run the tests
    try:
        test_gps_sensor(world, gps)
        test_imu_sensor(world, imu)
        test_tof_sensor(world, tof)
        test_blade_controller(world, blade_controller)
        test_motor_controller(world, motor_controller)

        hardware = {
            "gps": gps,
            "imu": imu,
            "tof": tof,
            "blade_controller": blade_controller,
            "motor_controller": motor_controller
        }

        test_all_hardware(world, hardware)

        logger.info("All tests passed!")
    except AssertionError as e:
        logger.error(f"Test failed: {e}")
        sys.exit(1)
    finally:
        # Clean up
        gps.cleanup()
        imu.cleanup()
        tof.cleanup()
        blade_controller.cleanup()
        motor_controller.cleanup()
        reset_world()
