import platform
import random
import time
import os
from dotenv import load_dotenv

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


# Load environment variables from .env file
load_dotenv()


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

        # Fetch XSHUT and interrupt pin assignments from .env
        self.left_xshut_pin = int(os.getenv("LEFT_TOF_XSHUT", 22))
        self.right_xshut_pin = int(os.getenv("RIGHT_TOF_XSHUT", 23))
        self.left_interrupt_pin = int(os.getenv("LEFT_TOF_INTERRUPT", 6))
        self.right_interrupt_pin = int(os.getenv("RIGHT_TOF_INTERRUPT", 12))

        if platform.system() == "Linux":
            try:
                import board  # board is specific to __init__ context for I2C

                # Check if essential libraries were imported
                if adafruit_vl53l0x is None or digitalio is None:
                    raise ImportError("VL53L0X or digitalio lib failed to import.")

                self.i2c = board.I2C()

                # Initialize XSHUT pins using environment variables
                self.xshut_left = digitalio.DigitalInOut(getattr(board, f"D{self.left_xshut_pin}"))
                self.xshut_right = digitalio.DigitalInOut(getattr(board, f"D{self.right_xshut_pin}"))

                # Initialize sensors
                self.left_sensor, self.right_sensor = self.init_vl53l0x_sensors(
                    self.i2c,
                    self.xshut_left,
                    self.xshut_right,
                    left_target_addr=_LEFT_SENSOR_TARGET_ADDRESS,
                    right_target_addr=_RIGHT_SENSOR_TARGET_ADDRESS,
                )

                # Log initialization status
                status_messages = []
                if self.left_sensor:
                    addr = hex(self.left_sensor._device.device_address)
                    status_messages.append(f"Left ToF sensor OK (Addr: {addr})")
                else:
                    status_messages.append("Left ToF sensor FAILED")

                if self.right_sensor:
                    addr = hex(self.right_sensor._device.device_address)
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

    def setup_interrupt_pins(self):
        """Set up interrupt pins for event-driven functionality."""
        if platform.system() == "Linux":
            try:
                self.left_interrupt = digitalio.DigitalInOut(getattr(board, f"D{self.left_interrupt_pin}"))
                self.right_interrupt = digitalio.DigitalInOut(getattr(board, f"D{self.right_interrupt_pin}"))

                self.left_interrupt.direction = digitalio.Direction.INPUT
                self.right_interrupt.direction = digitalio.Direction.INPUT

                logging.info("Interrupt pins initialized for ToF sensors.")
            except Exception as e:
                logging.error(f"Failed to initialize interrupt pins: {e}")
        else:
            logging.info("Interrupt pins not supported on non-Linux platforms.")

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
    def read_vl53l0x(sensor, sensor_name="Unknown", max_range=2000, min_range=10):
        """Read VL53L0X ToF sensor data with improved error handling and filtering."""
        if sensor is None:
            return -1  # Return error value if sensor is None

        try:
            # Add a small delay before reading to avoid I/O errors
            time.sleep(0.02)  # Increased delay for stability

            # Multiple attempts with I2C locking
            distance = None
            for attempt in range(3):  # Try up to 3 times
                try:
                    # Check if sensor has proper I2C connection
                    if hasattr(sensor, '_device') and hasattr(sensor._device, '_i2c'):
                        try:
                            # Try to acquire I2C lock
                            if sensor._device._i2c.try_lock():
                                distance = sensor.range
                                sensor._device._i2c.unlock()
                                break
                            else:
                                # Wait and try again if lock failed
                                time.sleep(0.01)
                                continue
                        except Exception as lock_error:
                            logging.debug(f"I2C lock failed for {sensor_name}: {lock_error}")
                            # Try without lock as fallback
                            distance = sensor.range
                            break
                    else:
                        # Direct read without locking
                        distance = sensor.range
                        break
                        
                except OSError as e:
                    if attempt < 2:  # Retry on I/O error
                        logging.debug(f"I/O error reading {sensor_name}, attempt {attempt + 1}: {e}")
                        time.sleep(0.05)
                        continue
                    else:
                        raise e

            if distance is None:
                logging.warning(f"Failed to read distance from {sensor_name} after 3 attempts")
                return -1

            # Validate and filter the reading
            if distance <= 0:
                logging.debug(f"{sensor_name} returned non-positive distance: {distance}")
                return -1
            
            # Filter out obviously bad readings (outliers)
            if distance > max_range:
                logging.debug(f"{sensor_name} reading {distance}mm exceeds max range {max_range}mm")
                return -1
                
            if distance < min_range:
                logging.debug(f"{sensor_name} reading {distance}mm below min range {min_range}mm")
                return -1

            return round(distance)  # Return rounded integer value
            
        except OSError as e:
            # More specific error handling for I/O errors
            if "Input/output error" in str(e):
                logging.debug(f"I/O error reading {sensor_name}: {e}. Common with concurrent access.")
            else:
                logging.error(f"OSError reading {sensor_name} data: {e}")
            return -1
        except Exception as e:
            logging.error(f"Unexpected error reading {sensor_name} data: {e}")
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
        
        # Reset both sensors to ensure clean state
        VL53L0XSensors.reset_sensor(xshut_left_pin)
        VL53L0XSensors.reset_sensor(xshut_right_pin)
        
        # Keep left sensor off, right sensor on
        xshut_left_pin.value = False
        time.sleep(0.1)  # Allow boot time for right sensor

        temp_sensor = VL53L0XSensors.init_vl53l0x(i2c, _DEFAULT_I2C_ADDRESS, "Right Sensor (default addr)")
        if temp_sensor:
            if right_target_addr != _DEFAULT_I2C_ADDRESS:
                try:
                    # Verify sensor is responsive before changing address
                    test_range = temp_sensor.range
                    logging.debug(f"Right sensor test reading: {test_range}mm")
                    
                    temp_sensor.set_address(right_target_addr)
                    time.sleep(0.05)  # Allow address change to settle
                    
                    # Verify the address change worked
                    verify_sensor = VL53L0XSensors.init_vl53l0x(i2c, right_target_addr, "Right Sensor (new addr)")
                    if verify_sensor:
                        right_sensor_obj = verify_sensor
                        logging.info(f"Right sensor addr changed to {hex(right_target_addr)} successfully.")
                    else:
                        logging.error(f"Right sensor not responding at new address {hex(right_target_addr)}")
                        xshut_right_pin.value = False
                        temp_sensor = None
                        
                except Exception as e:
                    logging.error(
                        f"Failed to change Right sensor addr to "
                        f"{hex(right_target_addr)}: {e}. Disabling sensor."
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
        if right_sensor_obj and right_sensor_obj._device.device_address == _DEFAULT_I2C_ADDRESS:
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
        distances = {"left": -1, "right": -1}

        if self.is_hardware_available:
            # Read from real sensors if available
            if self.left_sensor:
                distances["left"] = self.read_vl53l0x(self.left_sensor, "Left ToF")

            if self.right_sensor:
                distances["right"] = self.read_vl53l0x(self.right_sensor, "Right ToF")
                
            # Log occasional debug info for troubleshooting
            if hasattr(self, '_debug_counter'):
                self._debug_counter += 1
            else:
                self._debug_counter = 1
                
            if self._debug_counter % 50 == 0:  # Every 50 readings
                logging.debug(f"ToF sensors status - Left: {'OK' if self.left_sensor else 'FAIL'}, "
                             f"Right: {'OK' if self.right_sensor else 'FAIL'}")
                if distances["left"] == -1 and self.left_sensor:
                    logging.warning("Left ToF sensor returning error readings consistently")
                if distances["right"] == -1 and self.right_sensor:
                    logging.warning("Right ToF sensor returning error readings consistently")
        else:
            # Return simulated values for testing
            distances["left"] = random.uniform(50, 300)
            distances["right"] = random.uniform(50, 300)

        return distances

    def diagnose_sensors(self):
        """
        Diagnose ToF sensor issues and attempt recovery.
        Returns a dictionary with diagnostic information.
        """
        diagnosis = {
            "left_sensor": {"present": False, "responsive": False, "address": None},
            "right_sensor": {"present": False, "responsive": False, "address": None},
            "recommendations": []
        }
        
        if not self.is_hardware_available:
            diagnosis["recommendations"].append("Hardware not available - check platform and libraries")
            return diagnosis
            
        # Check left sensor
        if self.left_sensor:
            diagnosis["left_sensor"]["present"] = True
            try:
                diagnosis["left_sensor"]["address"] = hex(self.left_sensor._device.device_address)
                test_reading = self.read_vl53l0x(self.left_sensor, "Left ToF (Diagnostic)")
                diagnosis["left_sensor"]["responsive"] = test_reading != -1
                if not diagnosis["left_sensor"]["responsive"]:
                    diagnosis["recommendations"].append("Left sensor present but not responsive - check wiring/power")
            except Exception as e:
                diagnosis["recommendations"].append(f"Left sensor error: {e}")
        else:
            diagnosis["recommendations"].append("Left sensor not detected - check I2C connection")
            
        # Check right sensor  
        if self.right_sensor:
            diagnosis["right_sensor"]["present"] = True
            try:
                diagnosis["right_sensor"]["address"] = hex(self.right_sensor._device.device_address)
                test_reading = self.read_vl53l0x(self.right_sensor, "Right ToF (Diagnostic)")
                diagnosis["right_sensor"]["responsive"] = test_reading != -1
                if not diagnosis["right_sensor"]["responsive"]:
                    diagnosis["recommendations"].append("Right sensor present but not responsive - check wiring/power")
            except Exception as e:
                diagnosis["recommendations"].append(f"Right sensor error: {e}")
        else:
            diagnosis["recommendations"].append("Right sensor not detected - check I2C connection and address assignment")
            
        return diagnosis
    
    def attempt_sensor_recovery(self):
        """
        Attempt to recover failed sensors by reinitializing them.
        Returns True if any sensors were recovered.
        """
        if not self.is_hardware_available:
            logging.warning("Cannot attempt sensor recovery - hardware not available")
            return False
            
        logging.info("Attempting ToF sensor recovery...")
        
        # Store current sensor states
        left_was_working = self.left_sensor is not None
        right_was_working = self.right_sensor is not None
        
        try:
            # Re-initialize sensors
            self.left_sensor, self.right_sensor = self.init_vl53l0x_sensors(
                self.i2c,
                self.xshut_left,
                self.xshut_right,
                left_target_addr=_LEFT_SENSOR_TARGET_ADDRESS,
                right_target_addr=_RIGHT_SENSOR_TARGET_ADDRESS,
            )
            
            # Check if we recovered any sensors
            left_recovered = not left_was_working and self.left_sensor is not None
            right_recovered = not right_was_working and self.right_sensor is not None
            
            if left_recovered:
                logging.info("Left ToF sensor recovered successfully")
            if right_recovered:
                logging.info("Right ToF sensor recovered successfully")
                
            return left_recovered or right_recovered
            
        except Exception as e:
            logging.error(f"Sensor recovery failed: {e}")
            return False

if __name__ == "__main__":
    # Example of how to use this class
    print("Initializing VL53L0X sensors...")
    tof = VL53L0XSensors()
    
    # Run initial diagnostics
    print("\nRunning sensor diagnostics...")
    diagnosis = tof.diagnose_sensors()
    print(f"Diagnostic results: {diagnosis}")
    
    # If sensors have issues, attempt recovery
    if not (diagnosis["left_sensor"]["responsive"] and diagnosis["right_sensor"]["responsive"]):
        print("\nAttempting sensor recovery...")
        recovery_success = tof.attempt_sensor_recovery()
        print(f"Recovery {'successful' if recovery_success else 'failed'}")

    # Read distances repeatedly with better error tracking
    error_counts = {"left": 0, "right": 0}
    total_readings = 0
    
    try:
        while True:
            distances = tof.get_distances()
            total_readings += 1
            
            # Track error rates
            if distances["left"] == -1:
                error_counts["left"] += 1
            if distances["right"] == -1:
                error_counts["right"] += 1
                
            print(f"Left: {distances['left']} mm, Right: {distances['right']} mm")
            
            # Print error statistics every 20 readings
            if total_readings % 20 == 0:
                left_error_rate = (error_counts["left"] / total_readings) * 100
                right_error_rate = (error_counts["right"] / total_readings) * 100
                print(f"Error rates - Left: {left_error_rate:.1f}%, Right: {right_error_rate:.1f}%")
                
                # Attempt recovery if error rate is high
                if left_error_rate > 50 or right_error_rate > 50:
                    print("High error rate detected, attempting recovery...")
                    tof.attempt_sensor_recovery()
                    
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopped by user")
