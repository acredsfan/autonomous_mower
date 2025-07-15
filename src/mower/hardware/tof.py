"""
Time-of-Flight (ToF) sensor module for the autonomous mower.

This module has been completely rewritten for maximum stability, mirroring the
official Adafruit library examples for multi-sensor setups. It uses direct
'digitalio' control for precise timing and explicit I2C bus management to
prevent state conflicts and ensure reliable readings.
"""

import time
import platform
import logging
import os
from dotenv import load_dotenv

# Conditional hardware imports
if platform.system() == "Linux":
    try:
        import board
        import busio
        from adafruit_vl53l0x import VL53L0X
        from digitalio import DigitalInOut
        HARDWARE_AVAILABLE = True
    except (ImportError, RuntimeError) as e:
        logging.getLogger(__name__).warning(f"ToF hardware library not found: {e}. ToF will be disabled.")
        HARDWARE_AVAILABLE = False
else:
    HARDWARE_AVAILABLE = False

# Fallback classes for non-Linux environments
if not HARDWARE_AVAILABLE:
    class DigitalInOut:
        def __init__(self, pin): self.pin = pin
        def switch_to_output(self, value=False): pass
        @property
        def value(self): return False
        @value.setter
        def value(self, val): pass
    class VL53L0X:
        def __init__(self, i2c, address=0x29): pass
        def set_address(self, address): pass
        def start_continuous(self): pass
        def stop_continuous(self): pass
        @property
        def range(self): return 0
        @property
        def data_ready(self): return True
        def clear_interrupt(self): pass
        @property
        def measurement_timing_budget(self): return 200000
        @measurement_timing_budget.setter
        def measurement_timing_budget(self, val): pass
    board = None
    busio = None

from mower.utilities.logger_config import LoggerConfigInfo

# --- Configuration ---
load_dotenv()
logger = LoggerConfigInfo.get_logger(__name__)

try:
    SENSOR_CONFIG = [
        {"name": "right", "xshut_pin": int(os.getenv("RIGHT_TOF_XSHUT", "27")), "address": 0x30},
        {"name": "left",  "xshut_pin": int(os.getenv("LEFT_TOF_XSHUT", "17")), "address": 0x29},
    ]
    logger.info(f"ToF config loaded: Right XSHUT={SENSOR_CONFIG[0]['xshut_pin']}, Left XSHUT={SENSOR_CONFIG[1]['xshut_pin']}")
except (ValueError, TypeError) as e:
    logger.error(f"Invalid XSHUT pin value in .env file: {e}")
    SENSOR_CONFIG = [
        {"name": "right", "xshut_pin": 27, "address": 0x30},
        {"name": "left",  "xshut_pin": 17, "address": 0x29},
    ]
    logger.warning("Using default ToF pin configuration.")


class VL53L0XSensors:
    """
    Manages VL53L0X sensors using a hardened initialization sequence.
    """

    def __init__(self, simulate: bool = False):
        self.is_hardware_available = False
        self._sensors: dict[str, VL53L0X | None] = {}
        self._xshut_pins: dict[str, DigitalInOut | None] = {}
        self._i2c = None

        if simulate or not HARDWARE_AVAILABLE:
            logger.info("ToF: Using simulated data.")
            return

        try:
            # Initialize I2C bus once
            self._i2c = busio.I2C(board.SCL, board.SDA)
            self._initialize_all()
            if any(self._sensors.values()):
                self.is_hardware_available = True
        except Exception as e:
            logger.error(f"ToF: Critical failure during sensor initialization: {e}", exc_info=True)
            self.is_hardware_available = False

    def _initialize_all(self):
        """
        Initializes each ToF sensor sequentially with deliberate timing
        and explicit I2C bus locking for maximum stability.
        """
        logger.info("ToF: Starting hardened initialization sequence...")

        board_pins = {"17": board.D17, "27": board.D27, "22": board.D22, "23": board.D23}
        for config in SENSOR_CONFIG:
            name = config["name"]
            pin_num_str = str(config["xshut_pin"])
            if pin_num_str in board_pins:
                 self._xshut_pins[name] = DigitalInOut(board_pins[pin_num_str])
            else:
                 logger.error(f"Pin {pin_num_str} not defined in board_pins mapping.")
                 self._xshut_pins[name] = None
                 continue
            
            self._xshut_pins[name].switch_to_output(value=False)

        time.sleep(0.1)  # Delay after setting all pins low

        # Explicitly lock the I2C bus during the entire initialization
        while not self._i2c.try_lock():
            logger.warning("ToF: Waiting to acquire I2C bus lock...")
            time.sleep(0.1)
        
        logger.info("ToF: I2C bus lock acquired.")
        try:
            for config in SENSOR_CONFIG:
                name = config["name"]
                target_address = config["address"]
                xshut_pin_obj = self._xshut_pins.get(name)

                if not xshut_pin_obj:
                    continue
                
                # Enable one sensor
                logger.debug(f"ToF: Enabling sensor '{name}' on pin {config['xshut_pin']}.")
                xshut_pin_obj.value = True
                time.sleep(0.1) # Crucial delay to allow sensor to boot

                try:
                    # Initialize sensor at default address
                    sensor = VL53L0X(self._i2c)
                    
                    if name != SENSOR_CONFIG[-1]["name"]:
                        logger.info(f"ToF: Changing address of '{name}' to {hex(target_address)}")
                        sensor.set_address(target_address)
                    
                    # Set a stable timing budget and start continuous mode
                    sensor.measurement_timing_budget = 200000 # 200ms budget
                    sensor.start_continuous()
                    
                    self._sensors[name] = sensor
                    logger.info(f"ToF: Successfully initialized '{name}'.")

                except Exception as e:
                    self._sensors[name] = None
                    logger.error(f"ToF: Failed to initialize '{name}'. Disabling. Error: {e}")
                    xshut_pin_obj.value = False # Ensure failed sensor is off

        finally:
            self._i2c.unlock()
            logger.info("ToF: I2C bus lock released.")


    def get_distances(self) -> dict[str, int]:
        if not self.is_hardware_available:
            return {"left": -1, "right": -1}

        readings = {}
        for name, sensor in self._sensors.items():
            try:
                if sensor:
                    # The `data_ready` and `clear_interrupt` pattern is key for continuous mode
                    if sensor.data_ready:
                        readings[name] = sensor.range
                        sensor.clear_interrupt()
                    else:
                        # Data is not ready yet, return -1 to indicate this
                        readings[name] = -1
                else:
                    readings[name] = -1 # Sensor not initialized
            except Exception:
                readings[name] = -1
        
        return readings

    def cleanup(self):
        if hasattr(self, '_sensors'):
             for sensor in self._sensors.values():
                 if sensor:
                     try:
                         sensor.stop_continuous()
                     except Exception:
                         pass
        
        if hasattr(self, '_xshut_pins'):
             for pin in self._xshut_pins.values():
                 if pin:
                     pin.value = False

# Standalone test
if __name__ == "__main__":
    if HARDWARE_AVAILABLE:
        print("--- ToF Sensor Test ---")
        tof_instance = None
        try:
            tof_instance = VL53L0XSensors()

            if not tof_instance.is_hardware_available:
                print("No ToF sensors were initialized. Exiting.")
            else:
                print("Reading distances for 20 seconds... Press Ctrl+C to stop.")
                for _ in range(40):
                    print(f"Readings: {tof_instance.get_distances()}")
                    time.sleep(0.5)
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            if tof_instance:
                tof_instance.cleanup()
            print("\nTest finished.")
    else:
        print("Hardware libraries not available.")