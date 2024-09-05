
import logging
from adafruit_bme280 import basic as adafruit_bme280

def init_bme280(i2c):
    try:
        sensor = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=0x76)
        logging.info("BME280 initialized successfully.")
        return sensor
    except Exception as e:
        logging.error(f"Error initializing BME280: {e}")
        return None

def read_bme280(sensor):
    """Read BME280 sensor data."""
    try:
        temperature_f = sensor.temperature * 9 / 5 + 32
        return {
            'temperature_c': round(sensor.temperature, 1),
            'temperature_f': round(temperature_f, 1),
            'humidity': round(sensor.humidity, 1),
            'pressure': round(sensor.pressure, 1)
        }
    except Exception as e:
        logging.error(f"Error reading BME280 data: {e}")
        return {}
