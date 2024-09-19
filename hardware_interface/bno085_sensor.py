from adafruit_bno08x import (
    BNO_REPORT_ACCELEROMETER,
    BNO_REPORT_GYROSCOPE,
    BNO_REPORT_MAGNETOMETER,
    BNO_REPORT_ROTATION_VECTOR,
)
from utilities import LoggerConfigInfo as LoggerConfig
from .gpio_manager import GPIOManager
import math

# Initialize logger
logging = LoggerConfig.get_logger(__name__)


class BNO085Sensor:
    """Class to handle BNO085 sensor interaction"""

    @staticmethod
    def enable_features(sensor):
        """Enable BNO085 sensor features."""
        try:
            sensor.enable_feature(BNO_REPORT_ACCELEROMETER)
            sensor.enable_feature(BNO_REPORT_GYROSCOPE)
            sensor.enable_feature(BNO_REPORT_MAGNETOMETER)
            sensor.enable_feature(BNO_REPORT_ROTATION_VECTOR)
            logging.info("BNO085 features enabled.")
        except Exception as e:
            logging.error(f"Error enabling features on BNO085: {e}")

    @staticmethod
    def read_bno085_accel(sensor):
        """Read BNO085 accelerometer data."""
        try:
            accel_x, accel_y, accel_z = sensor.acceleration
            return {'x': accel_x, 'y': accel_y, 'z': accel_z}
        except Exception as e:
            logging.error(f"Error reading BNO085 accelerometer: {e}")
            return {}

    @staticmethod
    def read_bno085_gyro(sensor):
        """Read BNO085 gyroscope data."""
        try:
            gyro_x, gyro_y, gyro_z = sensor.gyro
            return {'x': gyro_x, 'y': gyro_y, 'z': gyro_z}
        except Exception as e:
            logging.error(f"Error reading BNO085 gyroscope: {e}")
            return {}

    @staticmethod
    def read_bno085_magnetometer(sensor):
        """Read BNO085 magnetometer data."""
        try:
            mag_x, mag_y, mag_z = sensor.magnetic
            return {'x': mag_x, 'y': mag_y, 'z': mag_z}
        except Exception as e:
            logging.error(f"Error reading BNO085 magnetometer: {e}")
            return {}

    @staticmethod
    def read_bno085_quaternion(sensor):
        """Read BNO085 rotation vector quaternion data."""
        try:
            quat_i, quat_j, quat_k, quat_real = sensor.quaternion
            return {'i': quat_i, 'j': quat_j, 'k': quat_k, 'real': quat_real}
        except Exception as e:
            logging.error(f"Error reading BNO085 quaternion: {e}")
            return {}

    @staticmethod
    def calculate_heading(sensor):
        """Calculate heading from BNO085 sensor data."""
        try:
            x, y, z = sensor.magnetic
            heading = math.degrees(math.atan2(y, x))
            if heading < 0:
                heading += 360
            return heading
        except Exception as e:
            logging.error(f"Error calculating heading: {e}")
            return -1
    
    @staticmethod
    def calculate_pitch(sensor):
        """Calculate pitch from BNO085 sensor data."""
        try:
            x, y, z = sensor.acceleration
            pitch = math.degrees(math.asin(-x))
            return pitch
        except Exception as e:
            logging.error(f"Error calculating pitch: {e}")
            return -1
        
    @staticmethod
    def calculate_roll(sensor):
        """Calculate roll from BNO085 sensor data."""
        try:
            x, y, z = sensor.acceleration
            roll = math.degrees(math.asin(y))
            return roll
        except Exception as e:
            logging.error(f"Error calculating roll: {e}")
            return -1
        
    @staticmethod
    def calculate_speed(sensor):
        """Calculate speed from BNO085 sensor data."""
        try:
            x, y, z = sensor.acceleration
            speed = math.sqrt(x**2 + y**2 + z**2)
            return speed
        except Exception as e:
            logging.error(f"Error calculating speed: {e}")
            return -1

    @staticmethod
    def cleanup():
        """Cleanup GPIO pins when done."""
        GPIOManager.clean()
