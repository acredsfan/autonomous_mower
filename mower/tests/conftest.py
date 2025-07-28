"""
Pytest configuration and fixtures for autonomous mower testing.

This module provides common fixtures and configuration for all tests,
including hardware simulation and mock objects.
"""

import pytest
import logging
import tempfile
from pathlib import Path
from typing import Generator, Dict, Any
from unittest.mock import Mock, MagicMock

from mower.config.settings import SystemConfig, HardwareConfig, SafetyConfig, ServicesConfig
from mower.core.hal.hardware_manager import HardwareManager
from mower.core.safety.safety_system import SafetySystem


# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)


@pytest.fixture
def test_config() -> SystemConfig:
    """Create test configuration with safe defaults."""
    return SystemConfig(
        hardware=HardwareConfig(
            robohat_port="/dev/null",
            robohat_baudrate=115200,
            robohat_timeout=1.0,
            steering_range=(-50, 50),
            throttle_range=(-30, 30),
            blade_range=(0, 50),
            max_speed=25,
            gps_port="/dev/null",
            gps_baudrate=9600,
            i2c_bus=1,
            emergency_stop_pin=21,
            status_led_pin=18
        ),
        safety=SafetyConfig(
            command_timeout=2.0,
            emergency_stop_debounce=0.05,
            boundary_buffer=0.5,
            max_tilt_angle=15.0,
            low_battery_threshold=11.0,
            motor_watchdog=1.0,
            sensor_watchdog=3.0,
            vision_watchdog=5.0
        ),
        services=ServicesConfig(
            redis_url="redis://localhost:6379",
            redis_db=1,  # Use different DB for testing
            log_level="DEBUG",
            web_host="127.0.0.1",
            web_port=8081,  # Different port for testing
            web_debug=True,
            health_check_interval=0.5,
            service_startup_timeout=10.0
        ),
        environment="test",
        simulation_mode=True,
        data_directory=str(tempfile.mkdtemp())
    )


@pytest.fixture
def hardware_manager(test_config: SystemConfig) -> Generator[HardwareManager, None, None]:
    """Create hardware manager in simulation mode."""
    # Reset singleton before test
    HardwareManager.reset_instance()
    
    hw_manager = HardwareManager(test_config, simulation=True)
    hw_manager.initialize_all()
    
    yield hw_manager
    
    # Cleanup after test
    hw_manager.cleanup_all()
    HardwareManager.reset_instance()


@pytest.fixture
def safety_system(test_config: SystemConfig) -> Generator[SafetySystem, None, None]:
    """Create safety system for testing."""
    safety = SafetySystem(test_config)
    safety.initialize()
    
    yield safety
    
    # Cleanup after test
    safety.shutdown()


@pytest.fixture
def mock_serial():
    """Create mock serial connection."""
    mock = Mock()
    mock.is_open = True
    mock.write = Mock()
    mock.flush = Mock()
    mock.close = Mock()
    mock.read = Mock(return_value=b"OK\r\n")
    return mock


@pytest.fixture
def mock_gpio():
    """Create mock GPIO interface."""
    mock = Mock()
    mock.setup = Mock()
    mock.input = Mock(return_value=False)  # Emergency stop not pressed
    mock.output = Mock()
    mock.cleanup = Mock()
    return mock


@pytest.fixture
def mock_i2c():
    """Create mock I2C interface."""
    mock = Mock()
    mock.read_byte_data = Mock(return_value=0x42)
    mock.write_byte_data = Mock()
    mock.read_i2c_block_data = Mock(return_value=[0x42, 0x24])
    mock.write_i2c_block_data = Mock()
    return mock


@pytest.fixture
def mock_sensor_data() -> Dict[str, Any]:
    """Create mock sensor data."""
    return {
        "gps": {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "altitude": 10.0,
            "fix_quality": 1,
            "satellites": 8
        },
        "imu": {
            "acceleration": {"x": 0.1, "y": 0.2, "z": 9.8},
            "gyroscope": {"x": 0.0, "y": 0.0, "z": 0.1},
            "magnetometer": {"x": 0.3, "y": 0.4, "z": -0.5}
        },
        "tof": {
            "distance_mm": 1500,
            "status": "valid"
        },
        "battery": {
            "voltage": 12.6,
            "current": 2.5,
            "percentage": 85
        }
    }


class MockHardwareInterface:
    """Mock hardware interface for testing."""
    
    def __init__(self):
        self.initialized = False
        self.healthy = True
        self.commands = []
    
    def initialize(self) -> bool:
        self.initialized = True
        return True
    
    def cleanup(self) -> None:
        self.initialized = False
    
    def is_healthy(self) -> bool:
        return self.healthy
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "initialized": self.initialized,
            "healthy": self.healthy,
            "commands_sent": len(self.commands)
        }
    
    def send_command(self, command: str) -> bool:
        self.commands.append(command)
        return True


@pytest.fixture
def mock_hardware_interface() -> MockHardwareInterface:
    """Create mock hardware interface."""
    return MockHardwareInterface()


# Test markers
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests that don't require hardware"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests with mock hardware"
    )
    config.addinivalue_line(
        "markers", "hardware: Tests that require actual hardware"
    )
    config.addinivalue_line(
        "markers", "slow: Slow tests that take more than 1 second"
    )
    config.addinivalue_line(
        "markers", "safety: Safety-critical tests"
    )


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances before each test."""
    # Reset hardware manager
    HardwareManager.reset_instance()
    
    # Reset global safety system
    import mower.core.safety.safety_system
    mower.core.safety.safety_system._safety_system = None
    
    yield
    
    # Cleanup after test
    HardwareManager.reset_instance()
    mower.core.safety.safety_system._safety_system = None


# Utility functions for tests
def assert_motor_command_safe(steering: int, throttle: int, blade: int = 0):
    """Assert that motor command values are within safe ranges."""
    assert -100 <= steering <= 100, f"Steering {steering} outside safe range"
    assert -100 <= throttle <= 100, f"Throttle {throttle} outside safe range"
    assert 0 <= blade <= 100, f"Blade {blade} outside safe range"
    assert abs(throttle) <= 50, f"Throttle {throttle} exceeds test speed limit"


def create_test_boundary_points():
    """Create test boundary points for testing."""
    return [
        (0.0, 0.0),
        (10.0, 0.0),
        (10.0, 10.0),
        (0.0, 10.0)
    ]
