# Test Coverage Reporting

This document explains how to use the test coverage reporting features in the autonomous mower project.

## Overview

Test coverage reporting helps identify which parts of the codebase are being tested and which parts need more testing. It provides metrics on how much of the code is covered by tests and highlights specific lines that are not being tested.

## Running Tests with Coverage

To run tests with coverage reporting:

```bash
pytest
```

This will run all tests and generate coverage reports in both terminal and HTML formats.

To run tests for a specific module with coverage:

```bash
pytest tests/module_name --cov=mower.module_name
```

## Viewing Coverage Reports

### Terminal Report

The terminal report shows a summary of coverage for each module:

```
----------- coverage: platform win32, python 3.9.7-final-0 -----------
Name                                      Stmts   Miss  Cover
-------------------------------------------------------------
mower/__init__.py                            10      0   100%
mower/config_management/__init__.py          45      5    89%
mower/hardware/sensor_interface.py          120     25    79%
...
-------------------------------------------------------------
TOTAL                                      1250    320    74%
```

### HTML Report

For a more detailed view, open the HTML report:

```bash
# On Windows
start htmlcov\index.html

# On Linux
xdg-open htmlcov/index.html

# On macOS
open htmlcov/index.html
```

The HTML report provides:
- Overall coverage percentage
- File-by-file breakdown
- Line-by-line highlighting of covered and uncovered code
- Branch coverage information

## Interpreting Coverage Results

- **Green lines**: Executed during tests
- **Red lines**: Not executed during tests
- **Yellow lines**: Partially executed (e.g., only one branch of an if statement was tested)

## Coverage Targets

The project aims for:
- Overall coverage: At least 80%
- Critical components: At least 90%
- UI and non-critical components: At least 70%

## Improving Coverage

To improve coverage:
1. Focus on red lines in the HTML report
2. Add tests for uncovered functions and methods
3. Add test cases for uncovered branches
4. Consider if some uncovered code is actually unreachable or unnecessary

## Configuration

Coverage settings are configured in:
- `.coveragerc` in the project root
- `pytest.ini` in the tests directory

These files control:
- Which files to include/exclude from coverage
- Which lines to exclude from coverage reporting
- Output formats and locations

## Continuous Integration

Coverage reports are automatically generated during CI runs. The CI pipeline will:
1. Run all tests with coverage
2. Generate coverage reports
3. Upload coverage reports as artifacts
4. Fail the build if coverage drops below the minimum threshold

## Troubleshooting

If you encounter issues with coverage reporting:

1. Ensure pytest-cov is installed:
   ```bash
   pip install pytest-cov
   ```

2. Check that the `.coveragerc` file exists in the project root

3. Verify that the coverage configuration in `pytest.ini` is correct

4. Try running with explicit coverage options:
   ```bash
   pytest --cov=mower --cov-report=term --cov-report=html
   ```