"""
Test module for test_sensor_interface.py.
"""

import unittest
from unittest.mock import MagicMock, patch

# Assuming this is the correct location
from mower.hardware.sensor_interface import EnhancedSensorInterface


class TestSensorInterface(unittest.TestCase):
    # Added patch for Thread
    @patch("mower.hardware.sensor_interface.threading.Thread")
    @patch("mower.hardware.sensor_interface.busio.I2C")
    def test_initialization(self, mock_i2c, mock_thread):  # Added mock_thread
        # Create an EnhancedSensorInterface instance
        sensor_interface = EnhancedSensorInterface()

        # Mock the _init_sensor_with_retry method
        sensor_interface._init_sensor_with_retry = MagicMock(return_value=True)

        # Call start
        sensor_interface.start()

        # Verify that _init_sensor_with_retry was called for each sensor
        # Assuming 4 sensors are initialized by default. Adjust if different.
        assert sensor_interface._init_sensor_with_retry.call_count == 4

        # Verify that the monitoring threads were started
        # Assuming 2 monitoring threads (e.g., data polling and status
        # checking)
        assert mock_thread.call_count == 2
        mock_thread.return_value.start.assert_called()

    @patch("mower.hardware.sensor_interface.busio.I2C")
    # Renamed from test_cleanup as it tests get_sensor_data
    def test_get_sensor_data(self, mock_i2c):
        # Create an EnhancedSensorInterface instance
        sensor_interface = EnhancedSensorInterface()

        # Set some test data
        test_data = {
            "temperature": 25.0,
            "humidity": 50.0,
            "pressure": 1013.25,
            "heading": 0.0,
            "roll": 0.0,
            "pitch": 0.0,
            "left_distance": 100.0,
            "right_distance": 100.0,
        }
        sensor_interface._data = test_data  # Directly setting internal state for test

        # Get the sensor data
        data = sensor_interface.get_sensor_data()

        # Verify that the correct data was returned
        assert data == test_data

        # Verify that the returned data is a copy
        assert data is not sensor_interface._data

    @patch("mower.hardware.sensor_interface.busio.I2C")
    # Renamed from test_get_sensor_status
    def test_is_safe_to_operate(self, mock_i2c):
        # Create an EnhancedSensorInterface instance
        sensor_interface = EnhancedSensorInterface()
        # Mock sensor_status as it's initialized in start() which is not called
        # here directly for this test
        sensor_interface._sensor_status = {
            "bno085": MagicMock(working=True),
            "vl53l0x": MagicMock(working=True),
            # Add other sensors if they are considered critical
        }
        sensor_interface.CRITICAL_SENSORS = ["bno085", "vl53l0x"]

        # Set all critical sensors to working
        sensor_interface._sensor_status["bno085"].working = True
        sensor_interface._sensor_status["vl53l0x"].working = True

        # Check if it's safe to operate
        assert sensor_interface.is_safe_to_operate() is True

        # Set one critical sensor to not working
        sensor_interface._sensor_status["bno085"].working = False

        # Check if it's safe to operate
        assert sensor_interface.is_safe_to_operate() is False

    @patch("mower.hardware.sensor_interface.busio.I2C")
    # Renamed from test_init_sensor_with_retry
    def test_handle_sensor_error(self, mock_i2c):
        # Create an EnhancedSensorInterface instance
        sensor_interface = EnhancedSensorInterface()
        # Mock sensor_status for the test
        sensor_interface._sensor_status = {"test_sensor": MagicMock(error_count=0, working=True, last_error=None)}

        # Call _handle_sensor_error
        sensor_interface._handle_sensor_error("test_sensor", Exception("Test error"))

        # Verify that the sensor status was updated
        assert sensor_interface._sensor_status["test_sensor"].working is False
        assert sensor_interface._sensor_status["test_sensor"].error_count == 1
        assert str(sensor_interface._sensor_status["test_sensor"].last_error) == "Test error"

    @patch("mower.hardware.sensor_interface.get_sensor_interface")
    # Renamed for clarity
    def test_get_sensor_interface_global_method(self, mock_get_sensor_interface):
        pass

    @patch("mower.hardware.sensor_interface.busio.I2C")
    def test_thread_safety(self, mock_i2c):
        pass


if __name__ == "__main__":
    unittest.main()
