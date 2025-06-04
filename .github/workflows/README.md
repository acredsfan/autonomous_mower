# CI/CD Pipeline

This directory contains the GitHub Actions workflows that make up the CI/CD pipeline for the autonomous mower project.

## Overview

The CI/CD pipeline is designed to automate testing, linting, and code quality checks for the autonomous mower codebase. It helps ensure that code changes meet quality standards and don't introduce regressions.

## Workflows

### CI Workflow (`ci.yml`)

The CI workflow runs on every push to the `main` and `improvements` branches, as well as on pull requests to the `main` branch. It consists of three jobs:

#### 1. Lint

This job runs linting and type checking on the codebase:
- **flake8**: Checks for syntax errors and enforces coding standards
- **black**: Verifies that code formatting meets the project's standards
- **mypy**: Performs static type checking

#### 2. Test

This job runs the test suite on multiple Python versions (3.9 and 3.10):
- **Unit tests**: Tests for individual components
- **Simulation tests**: Tests using the simulation capabilities
- **Navigation tests**: Tests for navigation algorithms
- **Obstacle detection tests**: Tests for obstacle detection algorithms
- **Benchmarks**: Performance benchmarks for critical operations
- **Coverage reporting**: Generates test coverage reports

The test coverage reports are uploaded as artifacts and to Codecov for visualization and tracking.

#### 3. Integration

This job runs integration tests after the lint and test jobs have completed successfully.

## Hardware Dependencies

Since the CI environment doesn't have access to the physical hardware that the autonomous mower code depends on, the workflow includes steps to mock hardware-specific dependencies like RPi.GPIO and smbus2. This allows the tests to run in the CI environment without requiring physical hardware.

## Test Coverage

The CI workflow generates test coverage reports using pytest-cov. These reports are uploaded as artifacts and to Codecov, where they can be visualized and tracked over time. This helps identify areas of the codebase that need more testing.

## Troubleshooting

If the CI workflow fails, check the following:

1. **Lint failures**: Make sure your code passes flake8, black, and mypy checks
2. **Test failures**: Check the test logs to see which tests failed and why
3. **Hardware dependencies**: If tests fail due to missing hardware dependencies, make sure the mocking is set up correctly
4. **Environment issues**: If tests fail due to environment issues, check the workflow logs for clues

## Local Testing

You can run the same checks locally before pushing your changes:

```bash
# Run linting checks
flake8 src tests
black --check src tests
mypy src

# Run tests
pytest tests/unit tests/utilities tests/config_management
pytest tests/simulation
pytest tests/navigation
pytest tests/obstacle_detection
pytest tests/benchmarks
pytest tests/integration

# Run tests with coverage
pytest --cov=mower
```

This helps catch issues before they reach the CI pipeline.
