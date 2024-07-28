import unittest
from hardware_interface.sensor_interface import SensorInterface

class TestBME280Sensor(unittest.TestCase):
    def setUp(self):
        self.sensor_interface = SensorInterface()

    def test_read_bme280(self):
        data = self.sensor_interface.read_bme280()
        self.assertIsInstance(data, dict)
        self.assertIn('temperature_c', data)
        self.assertIn('temperature_f', data)
        self.assertIn('humidity', data)
        self.assertIn('pressure', data)

if __name__ == '__main__':
    unittest.main()