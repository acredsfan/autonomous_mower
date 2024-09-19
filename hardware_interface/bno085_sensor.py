from adafruit_bno08x.i2c import BNO08X_I2C
from adafruit_bno08x import (
    BNO_REPORT_ACCELEROMETER,
    BNO_REPORT_GYROSCOPE,
    BNO_REPORT_MAGNETOMETER,
    BNO_REPORT_ROTATION_VECTOR,
)
from utilities import LoggerConfigInfo as LoggerConfig
from .gpio_manager import GPIOManager

# Initialize logger
logging = LoggerConfig.get_logger(__name__)

interrupt_pin = [8]  # GPIO line for interrupt
shutdown_pin = []  # No shutdown line needed
interrupt_lines, _ = GPIOManager.init_gpio(shutdown_pin, interrupt_pin)


class BNO085Sensor:
    """Class to handle BNO085 sensor"""

    def __init__(self, i2c):
        self.sensor = self.init_bno085(i2c)
        if self.sensor:
            # Add interrupt handler for INT pin
            GPIOManager.wait_for_interrupt(interrupt_lines,
                                           self.read_sensor_callback)

    def init_bno085(self, i2c):
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

    def read_sensor_callback(self, pin):
        """Callback to read sensor data when INT pin is triggered."""
        logging.info(f"Interrupt received on GPIO pin {pin}."
                     f" Reading sensor data...")
        try:
            # Read sensor data on interrupt trigger
            accel_data = self.read_bno085_accel(self.sensor)
            gyro_data = self.read_bno085_gyro(self.sensor)
            logging.info(f"Accelerometer data: {accel_data}")
            logging.info(f"Gyroscope data: {gyro_data}")
        except Exception as e:
            logging.error(f"Error in sensor callback: {e}")

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

    def cleanup(self):
        """Cleanup GPIO pins when done."""
        GPIOManager.clean()


if __name__ == "__main__":
    # Initialize the BNO085 sensor
    bno085_sensor = BNO085Sensor()
    try:
        while True:
            pass
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt: Stopping the application.")
    except Exception:
        logging.exception("An error occurred during the application.")
    finally:
        bno085_sensor.cleanup()
