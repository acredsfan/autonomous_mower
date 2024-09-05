
import logging
from adafruit_bno08x import (
    BNO_REPORT_ACCELEROMETER,
    BNO_REPORT_GYROSCOPE,
    BNO_REPORT_MAGNETOMETER,
    BNO_REPORT_ROTATION_VECTOR,
)
from adafruit_bno08x.i2c import BNO08X_I2C

def init_bno085(i2c):
    try:
        sensor = BNO08X_I2C(i2c, address=0x4B)
        sensor.enable_feature(BNO_REPORT_ACCELEROMETER)
        sensor.enable_feature(BNO_REPORT_GYROSCOPE)
        sensor.enable_feature(BNO_REPORT_MAGNETOMETER)
        sensor.enable_feature(BNO_REPORT_ROTATION_VECTOR)
        logging.info("BNO085 initialized and features enabled.")
        return sensor
    except Exception as e:
        logging.error(f"Error initializing BNO085: {e}")
        return None

def read_bno085_accel(sensor):
    try:
        accel_x, accel_y, accel_z = sensor.acceleration
        return {'x': accel_x, 'y': accel_y, 'z': accel_z}
    except Exception as e:
        logging.error(f"Error reading BNO085 accelerometer data: {e}")
        return {}
