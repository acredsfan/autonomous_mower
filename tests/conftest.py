"""
Test module for conftest.py.
"""


import pytest
from unittest.mock import MagicMock


# Test fixtures
@pytest.fixture
def mock_gpio():
    sensor = MagicMock()
    sensor.read.return_value = 0.5
    sensor.initialize.return_value = True
    return sensor


@pytest.fixture
def mock_imu_sensor():
    tof = MagicMock()
    tof.measure_distance.return_value = 100.0  # 100cm
    tof.is_object_detected.return_value = False
    return tof


@pytest.fixture
def mock_motor_controller():
    pass
