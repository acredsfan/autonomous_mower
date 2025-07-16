# Testing Documentation

This document covers the testing strategies and tools available for the Autonomous Mower project, including unit tests with mocks, integration tests, and hardware reliability testing.

## Unit Testing with Mocks

Unit tests should avoid interacting with real hardware by using mocks and fakes.

## Strategies

1. Use `unittest.mock.patch` to replace hardware interfaces:

   ```python
   from unittest.mock import patch

   with patch('mower.hardware.sensor_interface.I2CInterface') as mock_i2c:
       mock_i2c.return_value.read.return_value = 42
       # test code here
   ```

2. Provide fake sensor classes in `tests/hardware_fixtures.py`:

   - `FakeIMU`, `FakeToF` simulate sensor behavior
   - Register fixtures in `conftest.py` for reuse

3. Use dependency injection:

   - Accept interfaces as constructor parameters
   - Pass mock implementations during tests for isolation

4. Share common mock utilities in `tests/mocks/`:
   - Centralize creation of mock responses
   - Ensure consistent mocking across the test suite

## Example

```python
def test_path_planner_with_mocked_gps(gps_mock):
    gps_mock.get_position.return_value = (10.0,  5.0)
    planner = PathPlanner(gps=gps_mock)
    path = planner.generate_path()
    assert path is not None
```

## Best Practices

- Reset mocks between tests to avoid state leakage
- Use descriptive fixture names for clarity
- Avoid broad patch targets; patch the interface, not the full module
- Document mock usage in test file docstrings and comments

## Hardware Reliability Testing

### Sensor Reliability Test

The project includes a comprehensive sensor reliability test (`test_sensor_reliability.py`) that evaluates the consistency and performance of hardware sensors in real-world conditions.

#### Features

- **Comprehensive Statistics**: Tracks success rates, value ranges, and operational status for all sensors
- **Real-time Monitoring**: Displays live sensor data with success rate calculations
- **Automatic Timeout**: Runs for 30 seconds with automatic termination
- **Detailed Reporting**: Provides final assessment of sensor reliability
- **Status Tracking**: Monitors sensor operational states and error counts

#### Usage

```bash
# Run the sensor reliability test
python3 test_sensor_reliability.py
```

#### Output Example

```
=== Sensor Reliability Test ===
Testing improved sensor implementation...
AsyncSensorManager started successfully!

[ 1] ToF: L= 245mm R= 312mm | Success: L= 100.0% R= 100.0% | Op: 5
[ 2] ToF: L= 248mm R= 315mm | Success: L= 100.0% R= 100.0% | Op: 5
...
[10]     === Status Report ===
       tof_left    : operational  (errors:  0, hw: True)
       tof_right   : operational  (errors:  0, hw: True)
       imu         : operational  (errors:  0, hw: True)
       Left ToF    : avg= 246.3mm, range=245-250mm
       Right ToF   : avg= 314.1mm, range=312-318mm

=== FINAL RELIABILITY REPORT ===
Maximum operational sensors: 5
Left ToF sensor: 25/25 valid readings (100.0% success rate)
  Range: 245-250mm, Average: 246.3mm
Right ToF sensor: 25/25 valid readings (100.0% success rate)
  Range: 312-318mm, Average: 314.1mm

RELIABILITY ASSESSMENT:
✅ EXCELLENT - Both sensors >80% reliability
```

#### Reliability Assessment Criteria

- **EXCELLENT**: Both sensors >80% success rate
- **GOOD**: Both sensors >60% success rate  
- **FAIR**: Both sensors >40% success rate
- **POOR**: One or both sensors <40% success rate

### Other Diagnostic Tools

#### Basic Sensor Test

Located in `tools/test_sensors.py`, this tool provides a simple real-time display of sensor data:

```bash
# Run basic sensor test
python3 tools/test_sensors.py
```

Features:
- Real-time sensor data display
- IMU orientation data (heading, roll, pitch)
- ToF distance measurements
- Environmental data (if available)
- Safety status indicators

#### Hardware Diagnostic Test

For comprehensive hardware validation:

```bash
# Run hardware diagnostics
python3 -m mower.diagnostics.hardware_test --non-interactive --verbose
```

## Integration Testing

### Test Categories

The project includes several categories of integration tests:

- **Hardware Integration** (`tests/hardware_integration/`): Tests hardware component interactions
- **Service Integration** (`tests/integration/`): Tests service startup and component coordination
- **Navigation Integration**: Tests path planning with obstacle avoidance
- **Sensor Integration**: Tests sensor data flow and decision making

### Running Integration Tests

```bash
# Run all integration tests
pytest tests/integration/ tests/hardware_integration/

# Run specific integration test categories
pytest tests/integration/test_sensor_decision_making.py
pytest tests/hardware_integration/test_enhanced_tof_reliability.py
```

## Performance Testing

### Benchmarks

Performance benchmarks are available in `tests/benchmarks/`:

```bash
# Run performance benchmarks
pytest tests/benchmarks/ -v

# Run specific benchmark
pytest tests/benchmarks/test_avoidance_algorithm_benchmarks.py
```

### Profiling

For detailed performance analysis:

```bash
# Run with profiling
python3 -m mower.diagnostics.performance_profiler
```

## Regression Testing

Regression tests ensure that bug fixes remain effective:

```bash
# Run regression test suite
pytest tests/regression/
```

Key regression test areas:
- Camera initialization issues
- Service startup failures
- Sensor communication problems

## Simulation Testing

For testing without physical hardware:

```bash
# Run simulation tests
pytest tests/simulation/

# Enable simulation mode for development
export USE_SIMULATION=True
python3 -m mower.main_controller
```

## Test Coverage

### Running Coverage Analysis

```bash
# Run tests with coverage
pytest --cov=src/mower --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Coverage Targets

- **Unit Tests**: >90% line coverage
- **Integration Tests**: >80% branch coverage
- **Critical Paths**: 100% coverage for safety-critical code

## Continuous Integration

### Pre-commit Hooks

```bash
# Install pre-commit hooks
pre-commit install

# Run hooks manually
pre-commit run --all-files
```

### Test Automation

Tests are automatically run on:
- Pull request creation
- Commits to main branches
- Scheduled nightly runs

## Troubleshooting Tests

### Common Issues

1. **Hardware Not Available**: Tests will automatically use simulation mode
2. **Permission Errors**: Ensure proper GPIO/I2C permissions
3. **Timeout Issues**: Increase timeout values for slower hardware

### Debug Mode

```bash
# Run tests with debug output
pytest -v -s --log-cli-level=DEBUG
```
