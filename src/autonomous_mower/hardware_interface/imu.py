import math
import os
import time

import adafruit_bno08x
from adafruit_bno08x.uart import BNO08X_UART
from dotenv import load_dotenv
from autonomous_mower.utilities.logger_config import (
    LoggerConfigDebug as LoggerConfig
)
from autonomous_mower.hardware_interface.serial_port import SerialPort

# Initialize logger
logging = LoggerConfig.get_logger(__name__)

# Load environment variables
load_dotenv()
# Get the UART port from the environment variables
IMU_SERIAL_PORT = os.getenv('IMU_SERIAL_PORT', '/dev/ttyAMA2')
IMU_BAUDRATE = int(os.getenv('IMU_BAUD_RATE', '3000000'))

# Initialize SerialPort for IMU
imu_serial_port = SerialPort(port=IMU_SERIAL_PORT, baudrate=IMU_BAUDRATE)
try:
    imu_serial_port.start()
    print(f"IMU_SERIAL_PORT: {IMU_SERIAL_PORT}")
    print("Serial port initialized.")
    print("Initializing BNO085 sensor...")

    # Try for 30 seconds to initialize the BNO085 sensor
    sensor = None
    start_time = time.time()
    while time.time() - start_time < 5:
        try:
            sensor = BNO08X_UART(imu_serial_port.ser)
            print("BNO085 sensor initialized.")
            break
        except Exception as e:
            print(f"Error initializing BNO085 sensor: {e}")
            print("Retrying...")
            time.sleep(1)
    else:
        print("Failed to initialize BNO085 sensor.")
        raise Exception("Failed to initialize BNO085 sensor.")

    if sensor is not None:
        print("BNO085 sensor initialized.")

except Exception as e:
    logging.error(f"Failed to start IMU SerialPort: {e}")
finally:
    imu_serial_port.stop()
    print("IMU SerialPort stopped.")


class BNO085Sensor:
    """Class to handle BNO085 sensor interaction"""

    @staticmethod
    def enable_features(sensor):
        """Enable BNO085 sensor features."""
        try:
            sensor.enable_feature(adafruit_bno08x.BNO_REPORT_ACCELEROMETER)
            sensor.enable_feature(adafruit_bno08x.BNO_REPORT_GYROSCOPE)
            sensor.enable_feature(adafruit_bno08x.BNO_REPORT_MAGNETOMETER)
            sensor.enable_feature(adafruit_bno08x.BNO_REPORT_ROTATION_VECTOR)
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
    def calculate_quaternion(sensor):
        """Calculate Quaternion based on BNO085 rotation vector data."""
        try:
            q0, q1, q2, q3 = sensor.quaternion
            return {'q0': q0, 'q1': q1, 'q2': q2, 'q3': q3}
        except Exception as e:
            logging.error(f"Error calculating Quaternion: {e}")

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
            x = max(min(x, 1.0), -1.0)  # Clamp x to the range [-1, 1]
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
            y = max(min(y, 1.0), -1.0)  # Clamp y to the range [-1, 1]
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
    def cleanup(sensor):
        """Cleanup BNO085 sensor resources."""
        try:
            sensor.deinit()
            logging.info("BNO085 sensor deinitialized.")
        except Exception as e:
            logging.error(f"Error deinitializing BNO085 sensor: {e}")


if __name__ == '__main__':
    try:
        imu_serial_port.start()
        sensor = BNO08X_UART(imu_serial_port.ser)
        BNO085Sensor.enable_features(sensor)
        while True:
            accel_data = BNO085Sensor.read_bno085_accel(sensor)
            gyro_data = BNO085Sensor.read_bno085_gyro(sensor)
            mag_data = BNO085Sensor.read_bno085_magnetometer(sensor)
            quaternion = BNO085Sensor.calculate_quaternion(sensor)
            heading = BNO085Sensor.calculate_heading(sensor)
            pitch = BNO085Sensor.calculate_pitch(sensor)
            roll = BNO085Sensor.calculate_roll(sensor)
            speed = BNO085Sensor.calculate_speed(sensor)
            print(f"Accelerometer: {accel_data}")
            print(f"Gyroscope: {gyro_data}")
            print(f"Magnetometer: {mag_data}")
            print(f"Quaternion: {quaternion}")
            print(f"Heading: {heading}")
            print(f"Pitch: {pitch}")
            print(f"Roll: {roll}")
            print(f"Speed: {speed}")
            time.sleep(1)
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        BNO085Sensor.cleanup(sensor)
        imu_serial_port.stop()
        print("IMU SerialPort stopped.")
