# Regression Tests

This directory contains regression tests for known issues in the autonomous mower project. These tests verify that issues that have been fixed in the past don't reoccur in future versions of the code.

## What are Regression Tests?

Regression tests are a type of software testing that verifies that previously fixed issues remain fixed after changes to the codebase. They help ensure that new changes don't inadvertently reintroduce old bugs.

## Test Categories

The regression tests in this directory are organized by the type of issue they test:

### Service Startup Issues

Tests in `test_service_startup.py` verify that common service startup issues are properly handled:

- Log directory permissions issues
- Service logs creation
- Python environment issues

These tests are based on the troubleshooting section "Service Won't Start" in the README.md file.

### Camera Issues

Tests in `test_camera_issues.py` verify that common camera issues are properly handled:

- Camera connection and enable problems
- Camera device detection issues
- Camera permissions problems

These tests are based on the troubleshooting section "Camera Issues" in the README.md file.

## Running the Tests

To run all regression tests:

```bash
pytest tests/regression
```

To run a specific category of regression tests:

```bash
pytest tests/regression/test_service_startup.py
pytest tests/regression/test_camera_issues.py
```

To run a specific test:

```bash
pytest tests/regression/test_service_startup.py::TestServiceStartupIssues::test_log_directory_creation
```

## Adding New Regression Tests

When fixing a bug, consider adding a regression test to ensure it doesn't reoccur:

1. Identify the issue being fixed
2. Create a test that would fail if the issue were present
3. Verify that the test passes with the fix applied
4. Add the test to the appropriate file in the regression tests directory
5. Document the test with a reference to the original issue

## Test Coverage

Regression tests contribute to the overall test coverage of the project. To see how much of the code is covered by regression tests:

```bash
pytest tests/regression --cov=mower --cov-report=term
```

For more information on test coverage reporting, see the [Test Coverage Documentation](../../docs/test_coverage.md).