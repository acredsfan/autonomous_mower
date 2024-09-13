import time
import adafruit_vl53l0x
from utils import LoggerConfig

# Initialize logger
logging = LoggerConfig.get_logger(__name__)


class VL53L0XSensors:

    @staticmethod
    def init_vl53l0x(i2c, address):
        try:
            sensor = adafruit_vl53l0x.VL53L0X(i2c, address=address)
            logging.info(f"VL53L0X initialized at address {hex(address)}.")
            return sensor
        except Exception as e:
            logging.error(
                f"Error initializing VL53L0X at address {hex(address)}: {e}")
            return None

    @staticmethod
    def reset_sensor(line):
        """
        Resets a VL53L0X sensor by toggling its XSHUT line.
        """
        line.set_value(0)
        time.sleep(0.1)
        line.set_value(1)
        time.sleep(0.1)

    @staticmethod
    def read_vl53l0x(sensor):
        """Read VL53L0X ToF sensor data."""
        try:
            distance = sensor.range
            if distance > 0:
                return distance
            else:
                return -1  # Error value
        except Exception as e:
            logging.error(f"Error reading VL53L0X data: {e}")
            return -1

    @staticmethod
    def init_vl53l0x_sensors(i2c, shutdown_lines):
        """
        Initializes both VL53L0X sensors, setting their addresses correctly.
        This assumes one sensor is reset to 0x29
        and the other is assigned to 0x30.
        """
        # Reset both sensors to ensure they start at the default address
        VL53L0XSensors.reset_sensor(shutdown_lines[0])  # Left sensor
        time.sleep(0.1)
        VL53L0XSensors.reset_sensor(shutdown_lines[1])  # Right sensor
        time.sleep(0.1)

        # Initialize the right sensor first at the default address 0x29
        right_sensor = VL53L0XSensors.init_vl53l0x(i2c, 0x29)
        if right_sensor:
            # Reassign the right sensor to 0x30 to avoid conflict
            right_sensor.set_address(0x30)
            logging.info("Right VL53L0X sensor address updated to 0x30.")

        # Reset and Initialize the left sensor at the default address 0x29
        VL53L0XSensors.reset_sensor(shutdown_lines[0])
        left_sensor = VL53L0XSensors.init_vl53l0x(i2c, 0x29)

        return left_sensor, right_sensor
