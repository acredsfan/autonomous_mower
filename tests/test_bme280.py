import board
import busio
from adafruit_bme280 import basic as adafruit_bme280

# Initialize I2C bus
i2c = busio.I2C(board.SCL, board.SDA)

# Initialize BME280 sensor
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=0x76)

# Read and print sensor values
print("Temperature: {:.1f} C".format(bme280.temperature))
print("Temperature: {:.1f} F".format(bme280.temperature * 9/5 + 32))
print("Humidity: {:.1f} %".format(bme280.humidity))
print("Pressure: {:.1f} hPa".format(bme280.pressure))