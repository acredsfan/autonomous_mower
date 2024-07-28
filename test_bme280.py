import unittest
import board
import busio
from adafruit_bme280 import basic as adafruit_bme280

class TestBME280Sensor(unittest.TestCase):
    def setUp(self):
        # Initialize I2C bus
        self.i2c = busio.I2C(board.SCL, board.SDA)
        # Initialize BME280 sensor
        self.bme280 = adafruit_bme280.Adafruit_BME280_I2C(self.i2c, address=0x76)
    
    def test_read_temperature(self):
        temperature = self.bme280.temperature
        self.assertIsInstance(temperature, float)
    
    def test_read_humidity(self):
        humidity = self.bme280.humidity
        self.assertIsInstance(humidity, float)
    
    def test_read_pressure(self):
        pressure = self.bme280.pressure
        self.assertIsInstance(pressure, float)

if __name__ == '__main__':
    unittest.main()
