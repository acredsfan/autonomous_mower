"""
Test fixtures for hardware components.

This module provides pytest fixtures for hardware components using the simulation
capabilities. These fixtures can be used in tests to simulate hardware components
without requiring physical hardware.
"""

from mower.simulation.actuators.motor_sim import SimulatedMotorController
from mower.simulation.actuators.blade_sim import SimulatedBladeController
from mower.simulation.sensors.tof_sim import SimulatedToF
from mower.simulation.sensors.imu_sim import SimulatedImu
from mower.simulation.sensors.gps_sim import SimulatedGpsPosition, SimulatedGpsLatestPosition
from mower.simulation.world_model import get_world_instance, Vector2D, reset_world
from mower.simulation import enable_simulation, is_simulation_enabled
import os
import pytest
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Union, Type

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import simulation modules

# Import simulated hardware components


@pytest.fixture(scope="function")
def sim_world():
    """
    Fixture for a clean virtual world instance.

    This fixture enables simulation mode and provides a clean virtual world
    instance for each test. The world is reset after the test.

    Returns:
        VirtualWorld: The virtual world instance
    """
    # Enable simulation mode
    enable_simulation()
    assert is_simulation_enabled(), "Simulation mode should be enabled"

    # Reset the virtual world
    reset_world()
    world = get_world_instance()

    # Return the world instance
    yield world

    # Clean up
    reset_world()


@pytest.fixture(scope="function")
def sim_gps(sim_world):
    """
    Fixture for a simulated GPS sensor.

    This fixture provides a simulated GPS position sensor that interacts with
    the virtual world.

    Args:
        sim_world: The virtual world instance

    Returns:
        SimulatedGpsPosition: The simulated GPS position sensor
    """
    # Create a simulated GPS position sensor
    gps = SimulatedGpsPosition()

    # Initialize the sensor
    gps._initialize()

    # Return the sensor
    yield gps

    # Clean up
    gps.cleanup()


@pytest.fixture(scope="function")
def sim_gps_latest(sim_gps):
    """
    Fixture for a simulated GPS latest position sensor.

    This fixture provides a simulated GPS latest position sensor that gets
    data from the simulated GPS position sensor.

    Args:
        sim_gps: The simulated GPS position sensor

    Returns:
        SimulatedGpsLatestPosition: The simulated GPS latest position sensor
    """
    # Create a simulated GPS latest position sensor
    gps_latest = SimulatedGpsLatestPosition(sim_gps)

    # Initialize the sensor
    gps_latest._initialize()

    # Return the sensor
    yield gps_latest

    # Clean up
    gps_latest.cleanup()


@pytest.fixture(scope="function")
def sim_imu(sim_world):
    """
    Fixture for a simulated IMU sensor.

    This fixture provides a simulated IMU sensor that interacts with the
    virtual world.

    Args:
        sim_world: The virtual world instance

    Returns:
        SimulatedImu: The simulated IMU sensor
    """
    # Create a simulated IMU sensor
    imu = SimulatedImu()

    # Initialize the sensor
    imu._initialize()

    # Return the sensor
    yield imu

    # Clean up
    imu.cleanup()


@pytest.fixture(scope="function")
def sim_tof(sim_world):
    """
    Fixture for a simulated ToF sensor.

    This fixture provides a simulated ToF sensor that interacts with the
    virtual world.

    Args:
        sim_world: The virtual world instance

    Returns:
        SimulatedToF: The simulated ToF sensor
    """
    # Create a simulated ToF sensor
    tof = SimulatedToF()

    # Initialize the sensor
    tof._initialize()

    # Return the sensor
    yield tof

    # Clean up
    tof.cleanup()


@pytest.fixture(scope="function")
def sim_blade_controller(sim_world):
    """
    Fixture for a simulated blade controller.

    This fixture provides a simulated blade controller that interacts with the
    virtual world.

    Args:
        sim_world: The virtual world instance

    Returns:
        SimulatedBladeController: The simulated blade controller
    """
    # Create a simulated blade controller
    blade_controller = SimulatedBladeController()

    # Initialize the controller
    blade_controller._initialize()

    # Return the controller
    yield blade_controller

    # Clean up
    blade_controller.cleanup()


@pytest.fixture(scope="function")
def sim_motor_controller(sim_world):
    """
    Fixture for a simulated motor controller.

    This fixture provides a simulated motor controller that interacts with the
    virtual world.

    Args:
        sim_world: The virtual world instance

    Returns:
        SimulatedMotorController: The simulated motor controller
    """
    # Create a simulated motor controller
    motor_controller = SimulatedMotorController()

    # Initialize the controller
    motor_controller._initialize()

    # Return the controller
    yield motor_controller

    # Clean up
    motor_controller.cleanup()


@pytest.fixture(scope="function")
def sim_hardware(sim_gps, sim_imu, sim_tof, sim_blade_controller, sim_motor_controller):
    """
    Fixture for all simulated hardware components.

    This fixture provides all simulated hardware components in a dictionary.

    Args:
        sim_gps: The simulated GPS position sensor
        sim_imu: The simulated IMU sensor
        sim_tof: The simulated ToF sensor
        sim_blade_controller: The simulated blade controller
        sim_motor_controller: The simulated motor controller

    Returns:
        Dict[str, Any]: Dictionary containing all simulated hardware components
    """
    # Create a dictionary of all simulated hardware components
    hardware = {
        "gps": sim_gps,
        "imu": sim_imu,
        "tof": sim_tof,
        "blade_controller": sim_blade_controller,
        "motor_controller": sim_motor_controller
    }

    # Return the dictionary
    return hardware
