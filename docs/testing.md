# Testing with Mocks

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
