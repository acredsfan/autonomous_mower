import time
import platform
import random

# Only import hardware-specific modules on Linux platforms
if platform.system() == "Linux":
    try:
        import adafruit_vl53l0x
    except ImportError:
        pass

from mower.utilities.logger_config import LoggerConfigInfo as LoggerConfig

# Initialize logger
logging = LoggerConfig.get_logger(__name__)


class VL53L0XSensors:
    def __init__(self):
        """Initialize the VL53L0X sensor interface.

        The mower has two ToF sensors located on the front:
        - Left front sensor
        - Right front sensor
        """
        self.left_sensor = None
        self.right_sensor = None
        self.is_hardware_available = False

        # Only try to import hardware-specific modules on Linux platforms (e.g., Raspberry Pi)
        if platform.system() == "Linux":
            try:
                import board
                import digitalio

                # Create I2C interface
                self.i2c = board.I2C()

                # Setup XSHUT pins for the two front-mounted ToF sensors
                self.xshut_left = digitalio.DigitalInOut(board.D17)  # GPIO17
                self.xshut_left.direction = digitalio.Direction.OUTPUT
                self.xshut_right = digitalio.DigitalInOut(board.D27)  # GPIO27
                self.xshut_right.direction = digitalio.Direction.OUTPUT

                # Initialize sensors
                shutdown_lines = [self.xshut_left, self.xshut_right]
                self.left_sensor, self.right_sensor = self.init_vl53l0x_sensors(
                    self.i2c, shutdown_lines
                )

                self.is_hardware_available = (
                    self.left_sensor is not None and self.right_sensor is not None
                )

                if self.is_hardware_available:
                    logging.info("ToF sensors initialized successfully")
                else:
                    logging.warning("Some ToF sensors failed to initialize")

            except ImportError as e:
                logging.warning(f"Hardware libraries not available: {e}")
            except Exception as e:
                logging.error(f"Error initializing ToF sensors: {e}")
        else:
            logging.info(
                "Running on non-Linux platform, ToF sensors will return simulated values"
            )

    @staticmethod
    def init_vl53l0x(i2c, address):
        """Initialize a VL53L0X sensor at the specified address."""
        try:
            sensor = adafruit_vl53l0x.VL53L0X(i2c, address=address)
            logging.info(f"VL53L0X initialized at address {hex(address)}.")
            return sensor
        except Exception as e:
            logging.error(f"Error initializing VL53L0X at address {hex(address)}: {e}")
            return None

    @staticmethod
    def reset_sensor(line):
        """Resets a VL53L0X sensor by toggling its XSHUT line."""
        line.value = False
        time.sleep(0.1)
        line.value = True
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
        This assumes one sensor is reset to 0x29 and the other is assigned to 0x30.
        """
        # Reset both sensors by setting XSHUT pins low then high
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

    def get_distances(self):
        """
        Get distances from the two ToF sensors on the front of the mower.
        Returns a dictionary with left and right distances.
        """
        distances = {"left": 0, "right": 0}

        if self.is_hardware_available:
            # Read from real sensors if available
            if self.left_sensor:
                distances["left"] = self.read_vl53l0x(self.left_sensor)

            if self.right_sensor:
                distances["right"] = self.read_vl53l0x(self.right_sensor)
        else:
            # Return simulated values for testing
            distances["left"] = random.uniform(50, 300)
            distances["right"] = random.uniform(50, 300)

        return distances


if __name__ == "__main__":
    # Example of how to use this class
    print("Initializing VL53L0X sensors...")
    tof = VL53L0XSensors()

    # Read distances repeatedly
    try:
        while True:
            distances = tof.get_distances()
            print(f"Left: {distances['left']} mm, Right: {distances['right']} mm")
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopped by user")
