"""
Test module for hardware_fixtures.py.
"""

# Correct class, keep alias
from mower.simulation.actuators.motor_sim import (
    SimulatedRoboHATDriver as SimulatedMotorController
)
from mower.simulation.actuators.blade_sim import SimulatedBladeController
# Correct class, keep alias
from mower.simulation.sensors.tof_sim import (
    SimulatedVL53L0XSensors as SimulatedToF
)
# Correct class, keep alias
from mower.simulation.sensors.imu_sim import (
    SimulatedBNO085Sensor as SimulatedImu
)
from mower.simulation.sensors.gps_sim import (
    SimulatedGpsPosition,
    SimulatedGpsLatestPosition,
)
from mower.simulation.world_model import (
    get_world_instance,
    reset_world,
)
from mower.simulation import enable_simulation, is_simulation_enabled
import pytest
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
def sim_imu(sim_world, request):
    """
    Fixture for a simulated IMU sensor(BNO085).

    This fixture provides a simulated IMU sensor that interacts with the
    virtual world. It can accept initial_status via request.param.

    Args:
        sim_world: The virtual world instance
        request: Pytest request object to access parameters.

    Returns:
        SimulatedImu: The simulated IMU sensor(alias for SimulatedBNO085Sensor)
    """
    initial_status = getattr(request, "param", True)  # Default to working
    # Create a simulated IMU sensor
    imu = SimulatedImu(initial_status=initial_status)  # Uses alias

    # Initialize the sensor
    imu._initialize()  #
    # This now calls _initialize_sim which uses initial_status

    # Return the sensor
    yield imu

    # Clean up
    imu.cleanup()


@pytest.fixture(scope="function")
def sim_tof(sim_world, request):
    """
    Fixture for a simulated ToF sensor.

    This fixture provides a simulated ToF sensor that interacts with the
    virtual world. It can accept initial_statuses via request.param.

    Args:
        sim_world: The virtual world instance
        request: Pytest request object to access parameters.

    Returns:
        SimulatedToF: The simulated ToF sensor
    """
    initial_statuses = getattr(request, "param", None)
    # Create a simulated ToF sensor
    tof = SimulatedToF(initial_statuses=initial_statuses)

    # Initialize the sensor
    tof._initialize()  #
    # This now calls _initialize_sim which uses initial_statuses

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
    Fixture for a simulated motor controller(RoboHATDriver).

    This fixture provides a simulated motor controller that interacts with the
    virtual world.

    Args:
        sim_world: The virtual world instance

    Returns:
        SimulatedMotorController: The simulated motor controller
                                  (alias for SimulatedRoboHATDriver)
    """
    # Create a simulated motor controller
    # Uses alias for SimulatedRoboHATDriver
    motor_controller = SimulatedMotorController()

    # Initialize the controller
    motor_controller._initialize()

    # Return the controller
    yield motor_controller

    # Clean up
    motor_controller.cleanup()


@pytest.fixture(scope="function")
def sim_hardware(
    sim_gps, sim_imu, sim_tof, sim_blade_controller, sim_motor_controller
):
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
        dict: Dictionary containing all simulated hardware components
    """
    # Create a dictionary of all simulated hardware components
    hardware = {
        "gps": sim_gps,
        "imu": sim_imu,  # Alias for SimulatedBNO085Sensor
        "tof": sim_tof,  # Alias for SimulatedVL53L0XSensors
        "blade_controller": sim_blade_controller,
        "motor_controller": sim_motor_controller,  # Alias for SimulatedRoboHATDriver
    }

    # Return the dictionary
    return hardware
