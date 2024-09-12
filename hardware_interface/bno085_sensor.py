
from adafruit_bno08x.i2c import BNO08X_I2C
from adafruit_bno08x import (
    BNO_REPORT_ACCELEROMETER,
    BNO_REPORT_GYROSCOPE,
    BNO_REPORT_MAGNETOMETER,
    BNO_REPORT_ROTATION_VECTOR,
)
import time
import math
from utils import LoggerConfig

# Initialize logger
logging = LoggerConfig.get_logger(__name__)


class BNO085Sensor:
    """Class to handle BNO085 sensor"""

    @staticmethod
    def init_bno085(i2c):
        try:
            sensor = BNO08X_I2C(i2c, address=0x4B)
            sensor.enable_feature(BNO_REPORT_ACCELEROMETER)
            sensor.enable_feature(BNO_REPORT_GYROSCOPE)
            sensor.enable_feature(BNO_REPORT_MAGNETOMETER)
            sensor.enable_feature(BNO_REPORT_ROTATION_VECTOR)
            logging.info("BNO085 initialized with all features enabled.")
            return sensor
        except Exception as e:
            logging.error(f"Error initializing BNO085: {e}")
            return None

    @staticmethod
    def validate_sensor(sensor):
        """Validates the sensor object."""
        if sensor is None:
            logging.error("BNO085 sensor is not initialized or failed to initialize.")
            return False
        return True
    
    @staticmethod
    def calibrate_sensor(sensor):
        """Calibrate BNO085 sensor."""
        if not BNO085Sensor.validate_sensor(sensor):
            return {}
        
        try:
            sensor.calibrate()
            logging.info("BNO085 sensor calibrated successfully.")
        except Exception as e:
            logging.error(f"Error calibrating BNO085 sensor: {e}")
            return
        
    @staticmethod
    def reset_bno085(sensor):
        """Reset BNO085 sensor."""
        if not BNO085Sensor.validate_sensor(sensor):
            return {}
        
        try:
            sensor.soft_reset()
            logging.info("BNO085 sensor reset successfully.")
        except Exception as e:
            logging.error(f"Error resetting BNO085 sensor: {e}")
            return

    @staticmethod
    def read_bno085_accel(sensor):
        """Read BNO085 accelerometer data."""
        if not BNO085Sensor.validate_sensor(sensor):
            return {}

        try:
            accel_x, accel_y, accel_z = sensor.acceleration
            return {'x': accel_x, 'y': accel_y, 'z': accel_z}
        except Exception as e:
            logging.error(f"Error reading BNO085 accelerometer: {e}")
            return {}

    @staticmethod
    def read_bno085_gyro(sensor):
        """Read BNO085 gyroscope data."""
        if not BNO085Sensor.validate_sensor(sensor):
            return {}

        try:
            gyro_x, gyro_y, gyro_z = sensor.gyro
            return {'x': gyro_x, 'y': gyro_y, 'z': gyro_z}
        except Exception as e:
            logging.error(f"Error reading BNO085 gyroscope: {e}")
            return {}

    @staticmethod
    def read_bno085_magnetometer(sensor):
        """Read BNO085 magnetometer data."""
        if not BNO085Sensor.validate_sensor(sensor):
            return {}

        try:
            mag_x, mag_y, mag_z = sensor.magnetic
            return {'x': mag_x, 'y': mag_y, 'z': mag_z}
        except Exception as e:
            logging.error(f"Error reading BNO085 magnetometer: {e}")
            return {}

    @staticmethod
    def read_bno085_quaternion(sensor):
        """Read BNO085 rotation vector quaternion data."""
        if not BNO085Sensor.validate_sensor(sensor):
            return {}

        try:
            quat_i, quat_j, quat_k, quat_real = sensor.quaternion
            return {'i': quat_i, 'j': quat_j, 'k': quat_k, 'real': quat_real}
        except Exception as e:
            logging.error(f"Error reading BNO085 quaternion: {e}")
            return {}
    
    @staticmethod
    def calculate_speed(sensor):
        """Calculate speed in feet per second based on accelerometer data."""
        if not BNO085Sensor.validate_sensor(sensor):
            return 0
        
        try:
            accel_x, accel_y, accel_z = sensor.acceleration
            return round((accel_x**2 + accel_y**2 + accel_z**2)**0.5, 2)
        except Exception as e:
            logging.error(f"Error calculating speed: {e}")
            return 0
        
    @staticmethod
    def calculate_heading(sensor):
        """Calculate heading based on magnetometer data."""
        if not BNO085Sensor.validate_sensor(sensor):
            return 0
        
        try:
            mag_x, mag_y, mag_z = sensor.magnetic
            heading = 180 * math.atan2(mag_y, mag_x) / math.pi
            return round(heading, 2)
        except Exception as e:
            logging.error(f"Error calculating heading: {e}")
            return 0
        
    @staticmethod
    def calculate_pitch(sensor):
        """Calculate pitch based on accelerometer data."""
        if not BNO085Sensor.validate_sensor(sensor):
            return 0
        
        try:
            accel_x, accel_y, accel_z = sensor.acceleration
            pitch = math.atan2(accel_x, (accel_y**2 + accel_z**2)**0.5) * 180 / math.pi
            return round(pitch, 2)
        except Exception as e:
            logging.error(f"Error calculating pitch: {e}")
            return 0