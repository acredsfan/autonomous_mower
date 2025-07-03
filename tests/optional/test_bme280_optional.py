"""
Test BME280 as optional sensor - ensure startup continues when BME280 fails.

This test verifies that the sensor interface and resource manager can handle
BME280 sensor failures gracefully without affecting system initialization.

@hardware_interface: Mock testing (no actual hardware)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import logging

from mower.hardware.sensor_interface import EnhancedSensorInterface, SENSOR_DEFS


class TestBME280Optional:
    """Test class for BME280 optional sensor handling."""

    def test_sensor_defs_has_bme280_optional(self):
        """Test that BME280 is marked as optional in sensor definitions."""
        assert "bme280" in SENSOR_DEFS
        assert SENSOR_DEFS["bme280"]["optional"] is True

    @patch('mower.hardware.sensor_interface.get_hardware_registry')
    @patch('mower.hardware.sensor_interface.board')
    @patch('mower.hardware.sensor_interface.busio')
    def test_bme280_failure_does_not_crash_init(self, mock_busio, mock_board, mock_hardware_registry):
        """Test that BME280 failure doesn't crash sensor interface initialization."""
        # Setup mocks
        mock_board.SCL = Mock()
        mock_board.SDA = Mock()
        mock_busio.I2C.return_value = Mock()
        
        # Mock hardware registry to simulate BME280 failure
        mock_registry = Mock()
        mock_registry.get_bme280.side_effect = Exception("BME280 not found")
        mock_registry.get_bno085.return_value = Mock()
        mock_registry.get_ina3221.return_value = Mock()
        mock_registry.get_vl53l0x.return_value = Mock()
        mock_hardware_registry.return_value = mock_registry
        
        # Create sensor interface - should not raise exception
        try:
            sensor_interface = EnhancedSensorInterface()
            assert sensor_interface is not None
            assert sensor_interface._sensors["bme280"] is None
            print("✓ BME280 failure handled gracefully")
        except Exception as e:
            pytest.fail(f"EnhancedSensorInterface initialization failed with BME280 error: {e}")

    @patch('mower.hardware.sensor_interface.get_hardware_registry')
    @patch('mower.hardware.sensor_interface.board')
    @patch('mower.hardware.sensor_interface.busio')
    def test_bme280_optional_logging_level(self, mock_busio, mock_board, mock_hardware_registry, caplog):
        """Test that BME280 failures are logged at INFO level, not WARNING/ERROR."""
        # Setup mocks
        mock_board.SCL = Mock()
        mock_board.SDA = Mock()
        mock_busio.I2C.return_value = Mock()
        
        # Mock hardware registry to simulate BME280 failure
        mock_registry = Mock()
        mock_registry.get_bme280.side_effect = Exception("BME280 sensor not connected")
        mock_registry.get_bno085.return_value = Mock()
        mock_registry.get_ina3221.return_value = Mock()
        mock_registry.get_vl53l0x.return_value = Mock()
        mock_hardware_registry.return_value = mock_registry
        
        # Capture logs
        with caplog.at_level(logging.INFO):
            sensor_interface = EnhancedSensorInterface()
            
        # Check that BME280 failure is logged at INFO level
        bme280_logs = [record for record in caplog.records if "bme280" in record.message.lower()]
        assert len(bme280_logs) > 0, "Expected BME280 log messages"
        
        # Verify log level is INFO, not WARNING or ERROR
        for log_record in bme280_logs:
            assert log_record.levelno <= logging.INFO, f"BME280 log should be INFO level, got {log_record.levelname}: {log_record.message}"
        
        print("✓ BME280 failures logged at appropriate INFO level")

    @patch('mower.hardware.sensor_interface.get_hardware_registry')
    @patch('mower.hardware.sensor_interface.board')
    @patch('mower.hardware.sensor_interface.busio')
    def test_init_all_resources_continues_without_bme280(self, mock_busio, mock_board, mock_hardware_registry):
        """Test that resource initialization continues when BME280 is unavailable."""
        # Setup mocks
        mock_board.SCL = Mock()
        mock_board.SDA = Mock()
        mock_busio.I2C.return_value = Mock()
        
        # Mock hardware registry with BME280 failure but other sensors working
        mock_registry = Mock()
        mock_registry.get_bme280.return_value = None  # BME280 not available
        mock_registry.get_bno085.return_value = Mock()
        mock_registry.get_ina3221.return_value = Mock()
        mock_registry.get_vl53l0x.return_value = Mock()
        mock_hardware_registry.return_value = mock_registry
        
        # Create sensor interface
        sensor_interface = EnhancedSensorInterface()
        
        # Verify initialization completed
        assert sensor_interface is not None
        assert sensor_interface._sensors["bme280"] is None
        assert sensor_interface._sensors["bno085"] is not None
        
        # Verify sensor data can be read without BME280
        sensor_data = sensor_interface.get_sensor_data()
        assert isinstance(sensor_data, dict)
        
        print("✓ Sensor interface works without BME280")

    @patch('mower.hardware.sensor_interface.get_hardware_registry')
    @patch('mower.hardware.sensor_interface.board')
    @patch('mower.hardware.sensor_interface.busio')
    def test_sensor_interface_healthy_without_bme280(self, mock_busio, mock_board, mock_hardware_registry):
        """Test that sensor interface doesn't mark itself as unhealthy when BME280 is missing."""
        # Setup mocks
        mock_board.SCL = Mock()
        mock_board.SDA = Mock()
        mock_busio.I2C.return_value = Mock()
        
        # Mock hardware registry with BME280 failure
        mock_registry = Mock()
        mock_registry.get_bme280.return_value = None
        mock_registry.get_bno085.return_value = Mock()
        mock_registry.get_ina3221.return_value = Mock()
        mock_registry.get_vl53l0x.return_value = Mock()
        mock_hardware_registry.return_value = mock_registry
        
        # Create sensor interface
        sensor_interface = EnhancedSensorInterface()
        
        # Check sensor status
        sensor_status = sensor_interface.get_sensor_status()
        
        # BME280 should be marked as not working, but this shouldn't affect overall health
        assert "bme280" in sensor_status
        # The sensor interface itself should still be functional
        assert sensor_interface._sensors is not None
        
        print("✓ Sensor interface remains healthy without BME280")


if __name__ == "__main__":
    # Run tests directly
    test_class = TestBME280Optional()
    
    try:
        test_class.test_sensor_defs_has_bme280_optional()
        print("✓ SENSOR_DEFS test passed")
    except Exception as e:
        print(f"✗ SENSOR_DEFS test failed: {e}")
        
    # Note: The other tests require pytest to run properly due to mocking
    print("\nTo run all tests with mocking, use:")
    print("pytest tests/optional/test_bme280_optional.py -v")
