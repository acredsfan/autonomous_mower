"""
Unit tests for hardware manager.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock

from mower.core.hal.hardware_manager import (
    HardwareManager, MotorController, SensorManager, SafetyController,
    HardwareError, SafetyViolationError
)
from mower.config.settings import SystemConfig


@pytest.mark.unit
class TestMotorController:
    """Test motor controller functionality."""
    
    def test_initialization_simulation(self, test_config):
        """Test motor controller initialization in simulation mode."""
        controller = MotorController(test_config, simulation=True)
        
        assert controller.initialize() == True
        assert controller.is_healthy() == True
        assert controller._initialized == True
        
        status = controller.get_status()
        assert status["simulation"] == True
        assert status["initialized"] == True
        
        controller.cleanup()
        assert controller._initialized == False
    
    @patch('serial.Serial')
    def test_initialization_hardware(self, mock_serial, test_config):
        """Test motor controller initialization with hardware."""
        mock_serial_instance = Mock()
        mock_serial_instance.is_open = True
        mock_serial_instance.write = Mock()
        mock_serial_instance.flush = Mock()
        mock_serial.return_value = mock_serial_instance
        
        controller = MotorController(test_config, simulation=False)
        
        assert controller.initialize() == True
        assert controller.is_healthy() == True
        
        # Verify serial connection was created
        mock_serial.assert_called_once_with(
            port=test_config.hardware.robohat_port,
            baudrate=test_config.hardware.robohat_baudrate,
            timeout=test_config.hardware.robohat_timeout
        )
        
        controller.cleanup()
    
    def test_motor_command_validation(self, test_config):
        """Test motor command validation."""
        controller = MotorController(test_config, simulation=True)
        controller.initialize()
        
        # Valid commands
        assert controller.set_motors(0, 0, 0) == True
        assert controller.set_motors(25, 15, 30) == True
        assert controller.set_motors(-25, -15, 0) == True
        
        # Invalid steering
        with pytest.raises(SafetyViolationError):
            controller.set_motors(100, 0, 0)  # Outside range
        
        # Invalid throttle
        with pytest.raises(SafetyViolationError):
            controller.set_motors(0, 50, 0)  # Exceeds max_speed
        
        # Invalid blade
        with pytest.raises(SafetyViolationError):
            controller.set_motors(0, 0, 100)  # Outside range
        
        controller.cleanup()
    
    def test_motor_state_tracking(self, test_config):
        """Test motor state tracking."""
        controller = MotorController(test_config, simulation=True)
        controller.initialize()
        
        # Initial state
        status = controller.get_status()
        assert status["steering"] == 0
        assert status["throttle"] == 0
        assert status["blade"] == 0
        assert status["motors_enabled"] == False
        
        # Set motors
        controller.set_motors(10, 5, 20)
        
        status = controller.get_status()
        assert status["steering"] == 10
        assert status["throttle"] == 5
        assert status["blade"] == 20
        assert status["motors_enabled"] == True
        
        # Stop motors
        controller.stop_all_motors()
        
        status = controller.get_status()
        assert status["steering"] == 0
        assert status["throttle"] == 0
        assert status["blade"] == 0
        assert status["motors_enabled"] == False
        
        controller.cleanup()
    
    def test_blade_control(self, test_config):
        """Test blade control functions."""
        controller = MotorController(test_config, simulation=True)
        controller.initialize()
        
        # Enable blade
        assert controller.enable_blade(30) == True
        status = controller.get_status()
        assert status["blade"] == 30
        
        # Disable blade
        assert controller.disable_blade() == True
        status = controller.get_status()
        assert status["blade"] == 0
        
        # Invalid blade speed
        with pytest.raises(SafetyViolationError):
            controller.enable_blade(200)
        
        controller.cleanup()
    
    def test_command_timing(self, test_config):
        """Test command timing tracking."""
        controller = MotorController(test_config, simulation=True)
        controller.initialize()
        
        start_time = time.time()
        controller.set_motors(10, 5, 0)
        
        status = controller.get_status()
        assert status["last_command_time"] >= start_time
        assert status["last_command_time"] <= time.time()
        
        controller.cleanup()


@pytest.mark.unit
class TestSensorManager:
    """Test sensor manager functionality."""
    
    def test_initialization_simulation(self, test_config):
        """Test sensor manager initialization in simulation mode."""
        manager = SensorManager(test_config, simulation=True)
        
        assert manager.initialize() == True
        assert manager.is_healthy() == True
        assert manager._initialized == True
        
        status = manager.get_status()
        assert status["simulation"] == True
        assert status["initialized"] == True
        
        manager.cleanup()
        assert manager._initialized == False
    
    def test_sensor_status(self, test_config):
        """Test sensor status reporting."""
        manager = SensorManager(test_config, simulation=True)
        manager.initialize()
        
        status = manager.get_status()
        assert "sensor_count" in status
        assert "healthy" in status
        assert status["healthy"] == True
        
        manager.cleanup()


@pytest.mark.unit
class TestSafetyController:
    """Test safety controller functionality."""
    
    def test_initialization_simulation(self, test_config):
        """Test safety controller initialization in simulation mode."""
        controller = SafetyController(test_config, simulation=True)
        
        assert controller.initialize() == True
        assert controller.is_healthy() == True
        assert controller._initialized == True
        
        status = controller.get_status()
        assert status["simulation"] == True
        assert status["initialized"] == True
        assert status["emergency_stop_active"] == False
        
        controller.cleanup()
        assert controller._initialized == False
    
    def test_emergency_stop_simulation(self, test_config):
        """Test emergency stop in simulation mode."""
        controller = SafetyController(test_config, simulation=True)
        controller.initialize()
        
        # Initially not active
        assert controller.is_emergency_stop_active() == False
        
        # Trigger emergency stop
        controller.trigger_emergency_stop()
        assert controller.is_emergency_stop_active() == True
        
        status = controller.get_status()
        assert status["emergency_stop_active"] == True
        
        controller.cleanup()


@pytest.mark.unit
class TestHardwareManager:
    """Test hardware manager functionality."""
    
    def test_singleton_behavior(self, test_config):
        """Test that hardware manager is a singleton."""
        # Reset singleton before test
        HardwareManager.reset_instance()
        
        manager1 = HardwareManager(test_config, simulation=True)
        manager2 = HardwareManager()
        
        assert manager1 is manager2
        
        HardwareManager.reset_instance()
    
    def test_initialization_all_components(self, test_config):
        """Test initialization of all components."""
        HardwareManager.reset_instance()
        
        manager = HardwareManager(test_config, simulation=True)
        
        assert manager.initialize_all() == True
        assert manager.is_system_healthy() == True
        
        # Check individual components
        assert manager.motor_controller.is_healthy() == True
        assert manager.sensor_manager.is_healthy() == True
        assert manager.safety_controller.is_healthy() == True
        
        manager.cleanup_all()
        HardwareManager.reset_instance()
    
    def test_system_status(self, test_config):
        """Test system status reporting."""
        HardwareManager.reset_instance()
        
        manager = HardwareManager(test_config, simulation=True)
        manager.initialize_all()
        
        status = manager.get_system_status()
        
        assert "simulation" in status
        assert "healthy" in status
        assert "components" in status
        assert status["simulation"] == True
        assert status["healthy"] == True
        
        # Check component statuses
        components = status["components"]
        assert "MotorController" in components
        assert "SensorManager" in components
        assert "SafetyController" in components
        
        for component_status in components.values():
            assert component_status["healthy"] == True
        
        manager.cleanup_all()
        HardwareManager.reset_instance()
    
    def test_safe_operation_context(self, test_config):
        """Test safe operation context manager."""
        HardwareManager.reset_instance()
        
        manager = HardwareManager(test_config, simulation=True)
        manager.initialize_all()
        
        # Normal operation should work
        with manager.safe_operation():
            manager.motor_controller.set_motors(10, 5, 0)
        
        # Emergency stop should prevent operation
        manager.safety_controller.trigger_emergency_stop()
        
        with pytest.raises(SafetyViolationError):
            with manager.safe_operation():
                manager.motor_controller.set_motors(10, 5, 0)
        
        manager.cleanup_all()
        HardwareManager.reset_instance()
    
    def test_cleanup_all_components(self, test_config):
        """Test cleanup of all components."""
        HardwareManager.reset_instance()
        
        manager = HardwareManager(test_config, simulation=True)
        manager.initialize_all()
        
        # Verify components are initialized
        assert manager.motor_controller._initialized == True
        assert manager.sensor_manager._initialized == True
        assert manager.safety_controller._initialized == True
        
        # Cleanup
        manager.cleanup_all()
        
        # Verify components are cleaned up
        assert manager.motor_controller._initialized == False
        assert manager.sensor_manager._initialized == False
        assert manager.safety_controller._initialized == False
        
        HardwareManager.reset_instance()


@pytest.mark.unit
def test_hardware_error_inheritance():
    """Test hardware error exception hierarchy."""
    # Test that SafetyViolationError is a subclass of HardwareError
    assert issubclass(SafetyViolationError, HardwareError)
    
    # Test creating exceptions
    hardware_error = HardwareError("Generic hardware error")
    safety_error = SafetyViolationError("Safety violation")
    
    assert str(hardware_error) == "Generic hardware error"
    assert str(safety_error) == "Safety violation"
    
    # Test catching with base class
    try:
        raise SafetyViolationError("Test safety error")
    except HardwareError as e:
        assert str(e) == "Test safety error"


@pytest.mark.integration
def test_hardware_manager_integration(hardware_manager):
    """Test hardware manager integration."""
    # This test uses the hardware_manager fixture which provides
    # a fully initialized hardware manager in simulation mode
    
    assert hardware_manager.is_system_healthy() == True
    
    # Test motor control
    with hardware_manager.safe_operation():
        success = hardware_manager.motor_controller.set_motors(10, 5, 20)
        assert success == True
    
    # Test system status
    status = hardware_manager.get_system_status()
    assert status["healthy"] == True
    assert status["simulation"] == True
