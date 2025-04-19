# Simulation Testing

This directory contains tests that demonstrate how to use the simulation capabilities of the autonomous mower system for testing without requiring physical hardware.

## Overview

The autonomous mower project includes a comprehensive simulation framework that allows testing the system's behavior without physical hardware. This is useful for:

- Development without access to the physical mower
- Automated testing in CI/CD pipelines
- Testing scenarios that would be difficult or dangerous with a physical mower
- Reproducing and debugging issues in a controlled environment

## Components

The simulation framework includes:

1. **Virtual World Model** - Simulates the environment, including terrain, obstacles, and the robot
2. **Simulated Sensors** - Provides realistic sensor data based on the virtual world state
3. **Simulated Actuators** - Allows controlling the virtual robot and observing its behavior
4. **Integration with the Main System** - The main system can run in simulation mode without code changes

## Running Simulation Tests

### Using pytest

To run the simulation tests using pytest:

```bash
# Run all simulation tests
pytest tests/simulation

# Run a specific test file
pytest tests/simulation/test_simulation_mode.py

# Run a specific test function
pytest tests/simulation/test_simulation_mode.py::test_obstacle_detection
```

### Running Directly

The test files can also be run directly as Python scripts:

```bash
# Run the simulation mode test
python tests/simulation/test_simulation_mode.py
```

## Creating Your Own Simulation Tests

To create your own simulation tests:

1. Enable simulation mode using `enable_simulation()`
2. Set up the virtual world with obstacles, terrain, etc.
3. Initialize the mower system components
4. Run your test scenario
5. Verify the expected behavior

Example:

```python
from mower.simulation import enable_simulation
from mower.simulation.world_model import get_world_instance, Vector2D

# Enable simulation mode
enable_simulation()

# Get the virtual world instance
world = get_world_instance()

# Set up the virtual world
world.set_robot_position(Vector2D(10.0, 10.0), 0.0)
world.add_obstacle(Vector2D(15.0, 10.0), 1.0, obstacle_type="rock")

# Run your test scenario
# ...

# Verify the expected behavior
# ...
```

## Simulation Configuration

The simulation behavior can be configured through the configuration system:

```python
from mower.config_management import set_config

# Enable simulation mode
set_config('use_simulation', True)

# Configure simulation parameters
set_config('simulation.noise_level', 0.05)  # 5% sensor noise
set_config('simulation.update_rate', 10)    # 10Hz update rate
```

## Extending the Simulation

The simulation framework can be extended with new components:

1. **New Sensors** - Create a new class that extends `SimulatedSensor`
2. **New Actuators** - Create a new class that extends `SimulatedActuator`
3. **New World Features** - Extend the `VirtualWorld` class with new features

See the existing simulation components in `src/mower/simulation/` for examples.