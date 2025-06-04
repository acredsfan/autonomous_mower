"""
Test module for INA3221 sensor using adafruit-circuitpython-ina3221 library.
Tests power monitoring functionality across three channels.
"""

import sys
import unittest
from unittest.mock import MagicMock, patch

from mower.hardware.ina3221 import INA3221Sensor

# Mock hardware dependencies before importing our module
board_mock = MagicMock()
busio_mock = MagicMock()
adafruit_ina3221_mock = MagicMock()

sys.modules["board"] = board_mock
sys.modules["busio"] = busio_mock
sys.modules["adafruit_ina3221"] = adafruit_ina3221_mock


class TestINA3221Sensor(unittest.TestCase):
    """Test cases for INA3221 sensor functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.i2c_mock = MagicMock()
        self.sensor_mock = MagicMock()

    @patch("mower.hardware.ina3221.adafruit_ina3221.INA3221")
    @patch("mower.hardware.ina3221.busio.I2C")
    def test_init_ina3221_success(self, mock_i2c, mock_ina3221):
        """Test successful initialization of INA3221 sensor."""
        mock_i2c.return_value = self.i2c_mock
        mock_ina3221.return_value = self.sensor_mock

        sensor = INA3221Sensor.init_ina3221()

        self.assertIsNotNone(sensor)
        mock_i2c.assert_called_once()
        mock_ina3221.assert_called_once_with(self.i2c_mock)

    @patch("mower.hardware.ina3221.adafruit_ina3221.INA3221")
    @patch("mower.hardware.ina3221.busio.I2C")
    def test_init_ina3221_failure(self, mock_i2c, mock_ina3221):
        """Test INA3221 initialization failure handling."""
        mock_i2c.side_effect = OSError("I2C bus error")

        sensor = INA3221Sensor.init_ina3221()

        self.assertIsNone(sensor)

    def test_read_ina3221_valid_channels(self):
        """Test reading INA3221 sensor data from valid channels."""
        # Mock the sensor channel objects
        channel_mock = MagicMock()
        channel_mock.bus_voltage = 12.5
        channel_mock.shunt_voltage = 0.1
        channel_mock.current = 1.2

        self.sensor_mock.__getitem__.return_value = channel_mock

        # Test each valid channel
        for channel in [1, 2, 3]:
            data = INA3221Sensor.read_ina3221(self.sensor_mock, channel)

            expected_data = {
                "bus_voltage": 12.5,
                "shunt_voltage": 0.1,
                "current": 1.2,
            }
            self.assertEqual(data, expected_data)

    def test_read_ina3221_invalid_channel(self):
        """Test reading INA3221 sensor data from invalid channel."""
        data = INA3221Sensor.read_ina3221(self.sensor_mock, 4)
        self.assertEqual(data, {})

    def test_read_ina3221_none_sensor(self):
        """Test reading INA3221 with None sensor."""
        data = INA3221Sensor.read_ina3221(None, 1)
        self.assertEqual(data, {})

    def test_read_ina3221_io_error(self):
        """Test handling of I/O errors during sensor reading."""
        self.sensor_mock.__getitem__.side_effect = OSError("I2C communication error")

        data = INA3221Sensor.read_ina3221(self.sensor_mock, 1)
        self.assertEqual(data, {})

    def test_read_ina3221_attribute_error(self):
        """Test handling of attribute errors during sensor reading."""
        self.sensor_mock.__getitem__.side_effect = AttributeError("Invalid attribute")

        data = INA3221Sensor.read_ina3221(self.sensor_mock, 1)
        self.assertEqual(data, {})

    def test_read_ina3221_data_precision(self):
        """Test that sensor data is rounded to 2 decimal places."""
        channel_mock = MagicMock()
        channel_mock.bus_voltage = 12.567891
        channel_mock.shunt_voltage = 0.123456
        channel_mock.current = 1.234567

        self.sensor_mock.__getitem__.return_value = channel_mock

        data = INA3221Sensor.read_ina3221(self.sensor_mock, 1)

        expected_data = {
            "bus_voltage": 12.57,
            "shunt_voltage": 0.12,
            "current": 1.23,
        }
        self.assertEqual(data, expected_data)


if __name__ == "__main__":
    unittest.main()
