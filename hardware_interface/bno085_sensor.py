import logging
from adafruit_bno08x import (
    BNO_REPORT_ACCELEROMETER,
    BNO_REPORT_GYROSCOPE,
    BNO_REPORT_MAGNETOMETER,
    BNO_REPORT_ROTATION_VECTOR,
)
from adafruit_bno08x.i2c import BNO08X_I2C

class BNO085Sensor:

    def init_bno085(i2c):
        try:
            bno085 = BNO08X_I2C(i2c, address=0x4B)
            bno085.enable_feature(BNO_REPORT_ACCELEROMETER)
            bno085.enable_feature(BNO_REPORT_GYROSCOPE)
            bno085.enable_feature(BNO_REPORT_MAGNETOMETER)
            bno085.enable_feature(BNO_REPORT_ROTATION_VECTOR)
            logging.info("BNO085 initialized with all features enabled.")
            return bno085
        except Exception as e:
            logging.error(f"Error initializing BNO085: {e}")
            return None

    def read_bno085_accel(sensor):
        try:
            accel_x, accel_y, accel_z = sensor.acceleration
            return {'x': accel_x, 'y': accel_y, 'z': accel_z}
        except Exception as e:
            logging.error(f"Error reading BNO085 accelerometer: {e}")
            return {}

    def read_bno085_gyro(sensor):
        try:
            gyro_x, gyro_y, gyro_z = sensor.gyro
            return {'x': gyro_x, 'y': gyro_y, 'z': gyro_z}
        except Exception as e:
            logging.error(f"Error reading BNO085 gyroscope: {e}")
            return {}

    def read_bno085_compass(sensor):
        try:
            mag_x, mag_y, mag_z = sensor.magnetic
            return {'x': mag_x, 'y': mag_y, 'z': mag_z}
        except Exception as e:
            logging.error(f"Error reading BNO085 magnetometer: {e}")
            return {}

    def read_bno085_quaternion(sensor):
        try:
            quat_i, quat_j, quat_k, quat_real = sensor.quaternion
            return {'i': quat_i, 'j': quat_j, 'k': quat_k, 'real': quat_real}
        except Exception as e:
            logging.error(f"Error reading BNO085 quaternion: {e}")
            return {}