# Developer Guide

This guide provides information for developers who want to contribute to the Autonomous Mower project.

## Development Environment Setup

### Prerequisites

- **Python**: Python 3.9 or newer is required
- **Raspberry Pi**: For hardware testing, a Raspberry Pi 4B (4GB RAM or better) is recommended
- **Operating System**: Raspberry Pi OS (Bookworm or newer) for hardware testing, any OS for simulation
- **Git**: For version control
- **IDE**: Any Python IDE (VS Code recommended)

### Setting Up the Development Environment

1. **Clone the Repository**:

   ```bash
   git clone https://github.com/yourusername/autonomous_mower.git
   cd autonomous_mower
   ```

2. **Create a Virtual Environment** (optional but recommended):

   ```bash
   python -m venv venv

   # On Windows
   venv\Scripts\activate

   # On Linux/macOS
   source venv/bin/activate
   ```

3. **Install Dependencies**:

   ```bash
   # Install in editable mode with development dependencies
   pip install -e .[dev]
   ```


4. **Set Up Pre-commit Hooks**:

   ```bash
   # Install pre-commit
   pip install pre-commit

   # Install the git hooks
   pre-commit install
   ```

5. **Configure Environment Variables**:
   Create a `.env` file in the project root with the following variables:
   ```
   USE_SIMULATION=True  # Set to False for hardware testing
   LOG_LEVEL=DEBUG
   CONFIG_DIR=./config
   ```

## Project Structure

The project is organized into several modules, each responsible for a specific aspect of the system's functionality:

```
autonomous_mower/
├── docs/                  # Documentation
├── src/                   # Source code
│   └── mower/             # Main package
│       ├── config/        # Configuration files
│       ├── config_management/ # Configuration management
│       ├── diagnostics/   # Diagnostic tools
│       ├── error_handling/ # Error handling
│       ├── events/        # Event system
│       ├── hardware/      # Hardware interfaces
│       ├── interfaces/    # Interface definitions
│       ├── navigation/    # Path planning and navigation
│       ├── obstacle_detection/ # Obstacle detection
│       ├── plugins/       # Plugin system
│       ├── simulation/    # Simulation capabilities
│       ├── state_management/ # State management
│       ├── ui/            # User interface
│       └── utilities/     # Utility functions
├── tests/                 # Test suite
│   ├── benchmarks/        # Performance benchmarks
│   ├── integration/       # Integration tests
│   ├── navigation/        # Navigation tests
│   ├── obstacle_detection/ # Obstacle detection tests
│   ├── regression/        # Regression tests
│   ├── simulation/        # Simulation tests
│   └── unit/              # Unit tests
├── scripts/               # Utility scripts
├── models/                # ML models
└── config/                # Configuration files
```

## Key Components

### Main Controller

The `main_controller.py` file contains the `MainController` class, which is the entry point for the application. It coordinates between various subsystems and manages the overall state of the mower.

### Resource Manager

The `ResourceManager` class in `main_controller.py` manages hardware and software resources, ensuring proper initialization and cleanup.

### Navigation

The navigation module provides path planning and movement control:

- `PathPlanner`: Generates mowing paths based on different patterns
- `NavigationController`: Controls the mower's movement

### Obstacle Detection

The obstacle detection module provides capabilities for detecting and avoiding obstacles:

- `AvoidanceAlgorithm`: Implements obstacle avoidance strategies
- `detect_obstacle`: Function to detect obstacles using camera

### Hardware Interfaces

The hardware module provides interfaces to physical components:

- `BladeController`: Controls the cutting blade
- `RoboHATDriver`: Controls the drive motors
- `BNO085Sensor`: Provides orientation and acceleration data
- `VL53L0XSensors`: Provides distance measurements

### Simulation

The simulation module provides capabilities for testing without physical hardware:

- `VirtualWorld`: Simulates the environment
- `SimulatedSensor`: Base class for simulated sensors
- `SimulatedActuator`: Base class for simulated actuators

## Development Workflow

### Branching Strategy

- `main`: Stable production code
- `improvements`: Development branch for new features and improvements
- Feature branches: Created for specific features or bug fixes

### Making Changes

1. Create a new branch from `improvements`:

   ```bash
   git checkout improvements
   git pull
   git checkout -b feature/your-feature-name
   ```

2. Make your changes, following the coding standards

3. Run tests to ensure your changes don't break existing functionality:

   ```bash
   pytest
   ```

4. Commit your changes with a descriptive message:

   ```bash
   git add .
   git commit -m "Add feature: your feature description"
   ```

5. Push your branch to the remote repository:

   ```bash
   git push -u origin feature/your-feature-name
   ```

6. Create a pull request to merge your changes into the `improvements` branch

### Coding Standards

- Follow PEP 8 for code style
- Use type hints for all functions and methods
- Write docstrings for all modules, classes, and functions
- Keep functions and methods small and focused
- Write unit tests for all new functionality
- Use meaningful variable and function names

## Docstring Focus Areas

Critical modules requiring comprehensive docstrings and comments:

- `src/mower/main_controller.py` (flow and state transitions)
- `src/mower/hardware/sensor_interface.py` (I²C initialization and error handling)
- `src/mower/hardware/imu.py` (calibration and data interpretation)
- `src/mower/hardware/tof.py` (address management and read logic)

Refer to [`.roo/dev-instructions.md`](.roo/dev-instructions.md:1) for docstring standards.

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit
pytest tests/integration
pytest tests/simulation

# Run tests with coverage
pytest --cov=mower

# Run tests with verbose output
pytest -v
```

### Writing Tests

- Place tests in the appropriate directory based on the type of test
- Name test files with the prefix `test_`
- Name test functions with the prefix `test_`
- Use fixtures for common setup and teardown
- Use mocks for external dependencies
- Use parameterized tests for testing multiple inputs

### Simulation Testing

For testing without physical hardware, use the simulation capabilities:

```python
from mower.simulation import enable_simulation
from mower.simulation.world_model import get_world_instance, Vector2D

# Enable simulation mode
enable_simulation()

# Get the virtual world instance
world = get_world_instance()

# Set up the virtual world
world.set_robot_position(Vector2D(10.0, 10.0), 0.0)
world.add_obstacle(Vector2D(15.0, 10.0), 1.0)

# Run your tests using the simulated environment
```

## Documentation

### System Architecture

See [System Architecture](system_architecture.md) for a high-level overview of the project's components and their interactions.

For a detailed explanation of the sensor data flow, see [Sensor Data Flow](sensor_data_flow.md).

### API Documentation

The API documentation is available in the `docs/api` directory. It provides detailed information about each module, including classes, methods, and functions.

### User Guides

User guides are available in the `docs/user_guides` directory. They provide step-by-step instructions for common tasks and scenarios.

### Troubleshooting Guides

Troubleshooting guides are available in the `docs/troubleshooting` directory. They provide guidance on identifying and resolving common issues.

### Updating Documentation

When making changes to the codebase, update the relevant documentation:

- Update API documentation when changing interfaces
- Update user guides when changing user-facing functionality
- Update troubleshooting guides when fixing issues

## Contributing

### Reporting Issues

If you find a bug or have a suggestion for improvement, please create an issue in the issue tracker. Include as much detail as possible:

- Steps to reproduce the issue
- Expected behavior
- Actual behavior
- Error messages or logs
- Screenshots or videos (if applicable)

### Pull Requests

When submitting a pull request, please:

- Reference the issue that the pull request addresses
- Provide a clear description of the changes
- Include any necessary documentation updates
- Ensure all tests pass
- Follow the coding standards

### Code Review

All pull requests will be reviewed by at least one maintainer. The review process ensures:

- Code quality and adherence to standards
- Proper test coverage
- Documentation updates
- No regressions or new bugs

## Resources

- [API Documentation](api/index.md)
- [User Guides](user_guides/index.md)
- [Troubleshooting Guides](troubleshooting/index.md)
- [GitHub Repository](https://github.com/yourusername/autonomous_mower)
- [Issue Tracker](https://github.com/yourusername/autonomous_mower/issues)
