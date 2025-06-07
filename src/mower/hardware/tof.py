import platform
import random
import time

from mower.utilities.logger_config import LoggerConfigInfo

# Only import hardware-specific modules on Linux platforms
digitalio = None  # Initialize to None
if platform.system() == "Linux":
    try:
        import adafruit_vl53l0x
        import digitalio  # Import digitalio here
    except ImportError:
        # This will be caught later if adafruit_vl53l0x or digitalio is None
        pass


# Initialize logger
logging = LoggerConfigInfo.get_logger(__name__)

_DEFAULT_I2C_ADDRESS = 0x29
_LEFT_SENSOR_TARGET_ADDRESS = 0x29
_RIGHT_SENSOR_TARGET_ADDRESS = 0x30


class VL53L0XSensors:
    def __init__(self):
        """Initialize the VL53L0X sensor interface.

        The mower has two ToF sensors located on the front:
        - Left front sensor (Target Address: 0x29)
        - Right front sensor (Target Address: 0x30)
        """
        self.left_sensor = None
        self.right_sensor = None
        self.is_hardware_available = False

        if platform.system() == "Linux":
            try:
                import board  # board is specific to __init__ context for I2C

                # Check if essential libraries were imported
                if adafruit_vl53l0x is None or digitalio is None:
                    raise ImportError("VL53L0X or digitalio lib failed to import.")

                self.i2c = board.I2C()

                self.xshut_left = digitalio.DigitalInOut(board.D17)  # GPIO17
                self.xshut_right = digitalio.DigitalInOut(board.D27)  # GPIO27

                self.left_sensor, self.right_sensor = self.init_vl53l0x_sensors(
                    self.i2c,
                    self.xshut_left,
                    self.xshut_right,
                    left_target_addr=_LEFT_SENSOR_TARGET_ADDRESS,
                    right_target_addr=_RIGHT_SENSOR_TARGET_ADDRESS,
                )

                status_messages = []
                if self.left_sensor:
                    addr = hex(self.left_sensor._address)  # Changed from device_address
                    status_messages.append(f"Left ToF sensor OK (Addr: {addr})")
                else:
                    status_messages.append("Left ToF sensor FAILED")

                if self.right_sensor:
                    addr = hex(self.right_sensor._address)  # Changed from device_address
                    status_messages.append(f"Right ToF sensor OK (Addr: {addr})")
                else:
                    status_messages.append("Right ToF sensor FAILED")

                logging.info("ToF Init: " + "; ".join(status_messages))

                self.is_hardware_available = self.left_sensor is not None or self.right_sensor is not None

                if self.is_hardware_available:
                    if self.left_sensor and self.right_sensor:
                        logging.info("All expected ToF sensors are operational.")
                    else:
                        logging.warning("One ToF sensor not operational. Using available sensor(s).")
                else:
                    logging.error("No ToF sensors operational. Readings unavailable.")

            except ImportError as e:
                logging.warning(f"HW libs (board/digitalio/vl53l0x) missing: {e}. Simulating.")
            except Exception as e:  # General exception for other init errors
                logging.error(f"Error initializing ToF sensors: {e}. Simulating.")
        else:
            logging.info("Non-Linux platform. ToF sensors will be simulated.")

    @staticmethod
    def init_vl53l0x(i2c, address, sensor_name="Sensor"):
        """Initialize a VL53L0X sensor at the specified address."""
        if adafruit_vl53l0x is None:
            logging.error(f"adafruit_vl53l0x lib not available. Cannot init {sensor_name}.")
            return None
        try:
            sensor = adafruit_vl53l0x.VL53L0X(i2c, address=address)
            logging.info(f"{sensor_name} VL53L0X initialized at address {hex(address)}.")
            return sensor
        except ValueError:  # Typically "No I2C device at address"
            logging.warning(f"No I2C device for {sensor_name} VL53L0X at address " f"{hex(address)}.")
            return None
        except Exception as e:
            logging.error(f"Error initializing {sensor_name} VL53L0X at {hex(address)}: {e}")
            return None

    @staticmethod
    def reset_sensor(line):
        """Resets a VL53L0X sensor by toggling its XSHUT line."""
        if digitalio is None:
            logging.error("digitalio library not available, cannot reset sensor.")
            return

        # Ensure direction is output
        if line.direction != digitalio.Direction.OUTPUT:
            line.direction = digitalio.Direction.OUTPUT
        line.value = False
        time.sleep(0.05)  # Reduced delay
        line.value = True
        time.sleep(0.05)  # Reduced delay

    @staticmethod
    def read_vl53l0x(sensor):
        """Read VL53L0X ToF sensor data."""
        try:
            distance = sensor.range
            if distance > 0:
                return distance
            else:
                # VL53L0X can return 0 for valid readings very close,
                # but often indicates an issue if consistently 0 or negative.
                # Library might return 0 for errors. Treat > 0 as valid.
                logging.debug(f"VL53L0X returned non-positive distance: {distance}")
                return -1  # Error value or out of range
        except Exception as e:
            logging.error(f"Error reading VL53L0X data: {e}")
            return -1

    @staticmethod
    def init_vl53l0x_sensors(
        i2c,
        xshut_left_pin,
        xshut_right_pin,
        left_target_addr,
        right_target_addr,
    ):
        """
        Initializes both VL53L0X sensors, setting their addresses robustly.
        Manages XSHUT lines to initialize sensors one by one.
        """
        left_sensor_obj = None
        right_sensor_obj = None

        if digitalio is None:
            logging.error("digitalio library not available for sensor init.")
            return None, None

        # Ensure pin directions are set
        if xshut_left_pin.direction != digitalio.Direction.OUTPUT:
            xshut_left_pin.direction = digitalio.Direction.OUTPUT
        if xshut_right_pin.direction != digitalio.Direction.OUTPUT:
            xshut_right_pin.direction = digitalio.Direction.OUTPUT

        # --- Initialize Right Sensor (typically the one that changes address) ---
        logging.info("Initializing Right ToF sensor...")
        # Keep left sensor in reset
        VL53L0XSensors.reset_sensor(xshut_left_pin)
        VL53L0XSensors.reset_sensor(xshut_right_pin)  # Reset right sensor
        time.sleep(0.1)  # Allow boot time

        temp_sensor = VL53L0XSensors.init_vl53l0x(i2c, _DEFAULT_I2C_ADDRESS, "Right Sensor (default addr)")
        if temp_sensor:
            if right_target_addr != _DEFAULT_I2C_ADDRESS:
                try:
                    temp_sensor.set_address(right_target_addr)
                    logging.info(f"Right sensor addr changed to {hex(right_target_addr)}.")
                    right_sensor_obj = temp_sensor
                except Exception as e:
                    logging.error(
                        f"Failed to change Right sensor addr to "
                        f"{hex(right_target_addr)}: {e}. Sensor may remain at "
                        f"{hex(_DEFAULT_I2C_ADDRESS)}."
                    )
                    xshut_right_pin.value = False  # Force off
                    temp_sensor = None
            else:
                right_sensor_obj = temp_sensor
                logging.info(f"Right sensor init at default addr " f"{hex(_DEFAULT_I2C_ADDRESS)}.")
        else:
            logging.warning("Right sensor failed to init at default address.")
            xshut_right_pin.value = False

        # --- Initialize Left Sensor ---
        logging.info("Initializing Left ToF sensor...")
        if right_sensor_obj and right_sensor_obj._address == _DEFAULT_I2C_ADDRESS:  # Changed from device_address
            # This case implies right_target_addr was default.
            # Or, address change failed and it's still at default.
            # We must reset the right sensor to free up the default address.
            logging.info(f"Right sensor at {hex(_DEFAULT_I2C_ADDRESS)}. Resetting for Left sensor.")
            xshut_right_pin.value = False
            time.sleep(0.05)

        VL53L0XSensors.reset_sensor(xshut_left_pin)  # Reset left sensor
        time.sleep(0.1)  # Allow boot time

        temp_sensor = VL53L0XSensors.init_vl53l0x(i2c, _DEFAULT_I2C_ADDRESS, "Left Sensor (default addr)")
        if temp_sensor:
            # Assuming left sensor stays at default address as per constants
            if left_target_addr == _DEFAULT_I2C_ADDRESS:
                left_sensor_obj = temp_sensor
                logging.info(f"Left sensor init at default addr {hex(_DEFAULT_I2C_ADDRESS)}.")
            else:  # Should not happen with current constants
                logging.error(f"Left sensor target addr " f"{hex(left_target_addr)} is not default!")
                try:
                    temp_sensor.set_address(left_target_addr)
                    logging.info(f"Left sensor addr changed to {hex(left_target_addr)}.")
                    left_sensor_obj = temp_sensor
                except Exception as e:
                    logging.error(f"Failed to change Left sensor addr: {e}.")
                    xshut_left_pin.value = False
                    temp_sensor = None
        else:
            logging.warning("Left sensor failed to init at default address.")
            xshut_left_pin.value = False

        # --- Finalize XSHUT states ---
        # Ensure XSHUT is low if sensor object is None.
        # reset_sensor leaves XSHUT high if successful.
        if not left_sensor_obj and xshut_left_pin.value:
            xshut_left_pin.value = False
        if not right_sensor_obj and xshut_right_pin.value:
            xshut_right_pin.value = False

        return left_sensor_obj, right_sensor_obj

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
