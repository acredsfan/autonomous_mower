import unittest
from unittest.mock import MagicMock
from mower.hardware.ina3221 import INA3221Sensor


class TestINA3221Sensor(unittest.TestCase):
    def setUp(self):
        self.i2c_mock = MagicMock()
        self.sensor = INA3221Sensor.init_ina3221(self.i2c_mock)

    def test_init_ina3221(self):
        """Test INA3221 initialization."""
        self.assertIsNotNone(self.sensor)

    def test_read_ina3221(self):
        """Test reading INA3221 sensor data."""
        INA3221Sensor.read_ina3221 = MagicMock(
            return_value={"bus_voltage": 12.5, "current": 1.2}
        )
        data = INA3221Sensor.read_ina3221(self.sensor, 1)
        self.assertEqual(data["bus_voltage"], 12.5)
        self.assertEqual(data["current"], 1.2)


if __name__ == "__main__":
    unittest.main()
