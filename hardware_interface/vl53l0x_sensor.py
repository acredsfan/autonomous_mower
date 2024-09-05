
import logging
import time
import adafruit_vl53l0x

def init_vl53l0x(i2c, address):
    try:
        sensor = adafruit_vl53l0x.VL53L0X(i2c, address=address)
        logging.info(f"VL53L0X initialized at address {hex(address)}.")
        return sensor
    except Exception as e:
        logging.error(f"Error initializing VL53L0X at address {hex(address)}: {e}")
        return None

def reset_sensor(line):
    """
    Resets a VL53L0X sensor by toggling its XSHUT line.
    """
    line.set_value(0)
    time.sleep(0.1)
    line.set_value(1)
    time.sleep(0.1)

def read_vl53l0x(sensor):
    """Read VL53L0X ToF sensor data."""
    try:
        distance = sensor.range
        if distance > 0:
            return distance
        else:
            return -1
    except Exception as e:
        logging.error(f"Error reading VL53L0X data: {e}")
        return -1
