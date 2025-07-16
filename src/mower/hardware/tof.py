"""
Time-of-Flight (ToF) sensor module for the autonomous mower.

This module implements VL53L0X sensors following the official CircuitPython
documentation for multiple sensors on the same I2C bus with continuous mode.
Based on: https://docs.circuitpython.org/projects/vl53l0x/en/latest/examples.html#multiple-vl53l0x-on-same-i2c-bus-and-with-continuous-mode
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
        from digitalio import DigitalInOut, Direction
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
        @property
        def direction(self): return None
        @direction.setter
        def direction(self, val): pass
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
    class Direction:
        OUTPUT = "output"
    board = None
    busio = None

from mower.utilities.logger_config import LoggerConfigInfo

# --- Configuration ---
load_dotenv()
logger = LoggerConfigInfo.get_logger(__name__)

try:
    SENSOR_CONFIG = [
        {
            "name": "right", 
            "xshut_pin": int(os.getenv("RIGHT_TOF_XSHUT", "23")), 
            "interrupt_pin": int(os.getenv("RIGHT_TOF_INTERRUPT", "12")),
            "address": 0x30  # First sensor gets changed address
        },
        {
            "name": "left", 
            "xshut_pin": int(os.getenv("LEFT_TOF_XSHUT", "22")), 
            "interrupt_pin": int(os.getenv("LEFT_TOF_INTERRUPT", "6")),
            "address": 0x29  # Last sensor keeps default address
        },
    ]
    logger.info(f"ToF config loaded: Right XSHUT={SENSOR_CONFIG[0]['xshut_pin']}, INT={SENSOR_CONFIG[0]['interrupt_pin']}")
    logger.info(f"ToF config loaded: Left XSHUT={SENSOR_CONFIG[1]['xshut_pin']}, INT={SENSOR_CONFIG[1]['interrupt_pin']}")
except (ValueError, TypeError) as e:
    logger.error(f"Invalid pin value in .env file: {e}")
    SENSOR_CONFIG = [
        {"name": "right", "xshut_pin": 23, "interrupt_pin": 12, "address": 0x30},
        {"name": "left", "xshut_pin": 22, "interrupt_pin": 6, "address": 0x29},
    ]
    logger.warning("Using default ToF pin configuration.")


class VL53L0XSensors:
    """
    Manages multiple VL53L0X sensors following CircuitPython documentation.
    
    This implementation follows the official pattern from:
    https://docs.circuitpython.org/projects/vl53l0x/en/latest/examples.html#multiple-vl53l0x-on-same-i2c-bus-and-with-continuous-mode
    """

    def __init__(self, i2c_bus=None, simulate: bool = False):
        self.is_hardware_available = False
        self._sensors: dict[str, VL53L0X | None] = {}
        self._xshut_pins: dict[str, DigitalInOut | None] = {}
        self._interrupt_pins: dict[str, DigitalInOut | None] = {}
        self._i2c = i2c_bus
        self._owns_i2c = False

        if simulate or not HARDWARE_AVAILABLE:
            logger.info("ToF: Using simulated data.")
            return

        try:
            # Use provided I2C bus or create our own
            if self._i2c is None:
                self._i2c = busio.I2C(board.SCL, board.SDA)
                self._owns_i2c = True
                logger.info("ToF: Created own I2C bus")
            else:
                logger.info("ToF: Using shared I2C bus")
            
            self._initialize_sensors()
            if any(self._sensors.values()):
                self.is_hardware_available = True
                logger.info(f"ToF: {len([s for s in self._sensors.values() if s])} sensors initialized successfully")
        except Exception as e:
            logger.error(f"ToF: Critical failure during sensor initialization: {e}", exc_info=True)
            self.is_hardware_available = False

    def _get_board_pin(self, pin_number: int):
        """Get the board pin object for a given pin number."""
        pin_map = {
            6: board.D6,   # Left interrupt pin
            12: board.D12, # Right interrupt pin
            17: board.D17,
            22: board.D22, # Left XSHUT pin
            23: board.D23, # Right XSHUT pin
            27: board.D27
        }
        return pin_map.get(pin_number)

    def _initialize_sensors(self):
        """
        Initialize sensors following the CircuitPython documentation pattern.
        """
        logger.info("ToF: Starting sensor initialization sequence...")

        # Step 1: Set up XSHUT and interrupt pins, disable all sensors
        for config in SENSOR_CONFIG:
            name = config["name"]
            xshut_pin_number = config["xshut_pin"]
            interrupt_pin_number = config["interrupt_pin"]
            
            # Configure XSHUT pin
            board_pin = self._get_board_pin(xshut_pin_number)
            if board_pin is None:
                logger.error(f"ToF: Unsupported XSHUT pin {xshut_pin_number} for sensor '{name}'")
                self._xshut_pins[name] = None
            else:
                try:
                    xshut_pin = DigitalInOut(board_pin)
                    xshut_pin.direction = Direction.OUTPUT
                    xshut_pin.value = False  # Disable sensor initially
                    self._xshut_pins[name] = xshut_pin
                    logger.debug(f"ToF: Configured XSHUT pin {xshut_pin_number} for sensor '{name}'")
                except Exception as e:
                    logger.error(f"ToF: Failed to configure XSHUT pin {xshut_pin_number}: {e}")
                    self._xshut_pins[name] = None
            
            # Configure interrupt pin (input with pull-up)
            interrupt_board_pin = self._get_board_pin(interrupt_pin_number)
            if interrupt_board_pin is None:
                logger.error(f"ToF: Unsupported interrupt pin {interrupt_pin_number} for sensor '{name}'")
                self._interrupt_pins[name] = None
            else:
                try:
                    interrupt_pin = DigitalInOut(interrupt_board_pin)
                    interrupt_pin.direction = Direction.INPUT
                    # Note: CircuitPython doesn't have built-in pull-up for DigitalInOut
                    # The VL53L0X interrupt is active low, so we'll read it directly
                    self._interrupt_pins[name] = interrupt_pin
                    logger.debug(f"ToF: Configured interrupt pin {interrupt_pin_number} for sensor '{name}'")
                except Exception as e:
                    logger.error(f"ToF: Failed to configure interrupt pin {interrupt_pin_number}: {e}")
                    self._interrupt_pins[name] = None

        # Step 2: Wait for all sensors to be disabled
        time.sleep(0.1)

        # Step 3: Initialize sensors one by one
        for i, config in enumerate(SENSOR_CONFIG):
            name = config["name"]
            target_address = config["address"]
            xshut_pin = self._xshut_pins.get(name)

            logger.info(f"ToF: Processing sensor {i+1}/{len(SENSOR_CONFIG)}: '{name}'")

            if xshut_pin is None:
                logger.warning(f"ToF: Skipping sensor '{name}' - XSHUT pin not available")
                self._sensors[name] = None
                continue

            try:
                # Enable this sensor
                logger.info(f"ToF: Enabling sensor '{name}' on pin {config['xshut_pin']}")
                xshut_pin.value = True
                time.sleep(0.1)  # Increased wait time for sensor to boot

                # Create sensor instance at default address (0x29)
                logger.debug(f"ToF: Creating VL53L0X instance for '{name}'")
                sensor = VL53L0X(self._i2c)
                
                # Change address for all sensors except the last one
                # The last sensor can keep the default address (0x29)
                if i < len(SENSOR_CONFIG) - 1:
                    logger.info(f"ToF: Changing address of '{name}' from 0x29 to {hex(target_address)}")
                    sensor.set_address(target_address)
                    time.sleep(0.1)  # Increased wait after address change
                    logger.info(f"ToF: Address change complete for '{name}'")
                else:
                    logger.info(f"ToF: Sensor '{name}' keeping default address 0x29")
                    # Update target_address for logging consistency
                    target_address = 0x29

                # Configure sensor for optimal continuous mode
                logger.debug(f"ToF: Configuring continuous mode for '{name}'")
                
                # Set a shorter timing budget for faster, more frequent readings
                sensor.measurement_timing_budget = 100000  # 100ms timing budget (faster)
                
                # Start continuous mode
                sensor.start_continuous()
                
                # Wait longer for continuous mode to stabilize
                time.sleep(0.5)  # Increased wait time for sensor stabilization
                
                # Test the sensor with a few readings to ensure it's working
                test_readings = 0
                for test_attempt in range(5):
                    try:
                        test_distance = sensor.range
                        if test_distance > 0 and test_distance < 8190:
                            test_readings += 1
                        time.sleep(0.05)
                    except:
                        pass
                
                if test_readings < 2:
                    logger.warning(f"ToF: Sensor '{name}' failed initial test readings ({test_readings}/5)")
                else:
                    logger.debug(f"ToF: Sensor '{name}' passed initial test ({test_readings}/5 valid readings)")
                
                self._sensors[name] = sensor
                logger.info(f"ToF: Successfully initialized sensor '{name}' at address {hex(target_address)}")

            except Exception as e:
                logger.error(f"ToF: Failed to initialize sensor '{name}': {e}", exc_info=True)
                self._sensors[name] = None
                # Disable the failed sensor
                if xshut_pin:
                    xshut_pin.value = False

        logger.info("ToF: Sensor initialization sequence complete")

    def get_distances(self) -> dict[str, int]:
        """
        Get distance readings from all sensors with enhanced reliability and health monitoring.
        
        Returns:
            dict: Dictionary with sensor names as keys and distances in mm as values.
                  Returns -1 for sensors that are not ready or failed.
        """
        if not self.is_hardware_available:
            return {"left": -1, "right": -1}

        readings = {}
        for name, sensor in self._sensors.items():
            if sensor is None:
                readings[name] = -1
                continue
            
            # Initialize sensor health tracking if not exists
            if not hasattr(self, '_sensor_health'):
                self._sensor_health = {}
            if name not in self._sensor_health:
                self._sensor_health[name] = {
                    'consecutive_failures': 0,
                    'total_attempts': 0,
                    'successful_reads': 0,
                    'last_valid_reading': None,
                    'last_recovery_attempt': 0
                }
            
            health = self._sensor_health[name]
            health['total_attempts'] += 1
            
            # Try multiple reading strategies for reliability
            distance = self._read_sensor_with_strategies(name, sensor, health)
            readings[name] = distance
            
            # Update health statistics
            if distance > 0:
                health['successful_reads'] += 1
                health['consecutive_failures'] = 0
                health['last_valid_reading'] = distance
            else:
                health['consecutive_failures'] += 1
                
                # Attempt recovery for persistently failing sensors
                if (health['consecutive_failures'] >= 10 and 
                    time.time() - health['last_recovery_attempt'] > 30):
                    logger.warning(f"ToF: Attempting recovery for sensor '{name}' after {health['consecutive_failures']} failures")
                    self._attempt_sensor_recovery(name, sensor)
                    health['last_recovery_attempt'] = time.time()
        
        return readings
    
    def _read_sensor_with_strategies(self, name: str, sensor, health: dict) -> int:
        """
        Try multiple reading strategies for a sensor to improve reliability.
        
        Args:
            name: Sensor name
            sensor: VL53L0X sensor object
            health: Health tracking dictionary
            
        Returns:
            int: Distance in mm, or -1 if failed
        """
        # Strategy 1: Quick read (normal case)
        try:
            distance = sensor.range
            if self._is_valid_reading(distance):
                return distance
        except Exception as e:
            logger.debug(f"ToF: Strategy 1 failed for '{name}': {e}")
        
        # Strategy 2: Multiple attempts with small delays
        for attempt in range(3):
            try:
                time.sleep(0.02)  # Small delay
                distance = sensor.range
                if self._is_valid_reading(distance):
                    return distance
            except Exception as e:
                logger.debug(f"ToF: Strategy 2 attempt {attempt + 1} failed for '{name}': {e}")
        
        # Strategy 3: Use last known good reading if recent failures are low
        if (health['last_valid_reading'] is not None and 
            health['consecutive_failures'] < 5 and
            health['successful_reads'] > health['total_attempts'] * 0.3):  # At least 30% success rate
            logger.debug(f"ToF: Using last valid reading for '{name}': {health['last_valid_reading']}mm")
            return health['last_valid_reading']
        
        # All strategies failed
        return -1
    
    def _is_valid_reading(self, distance: int) -> bool:
        """Check if a distance reading is valid."""
        return distance > 0 and distance < 8190
    
    def _attempt_sensor_recovery(self, name: str, sensor):
        """
        Attempt to recover a failing sensor by restarting continuous mode.
        
        Args:
            name: Sensor name
            sensor: VL53L0X sensor object
        """
        try:
            logger.info(f"ToF: Attempting recovery for sensor '{name}'")
            
            # Stop and restart continuous mode
            sensor.stop_continuous()
            time.sleep(0.1)
            
            # Reconfigure and restart
            sensor.measurement_timing_budget = 100000  # 100ms timing budget
            sensor.start_continuous()
            time.sleep(0.2)  # Wait for stabilization
            
            # Test the recovery
            test_distance = sensor.range
            if self._is_valid_reading(test_distance):
                logger.info(f"ToF: Recovery successful for sensor '{name}', test reading: {test_distance}mm")
            else:
                logger.warning(f"ToF: Recovery may have failed for sensor '{name}', test reading: {test_distance}")
                
        except Exception as e:
            logger.error(f"ToF: Recovery attempt failed for sensor '{name}': {e}")

    def get_distances_blocking(self, timeout_ms: int = 1000) -> dict[str, int]:
        """
        Get distance readings with blocking wait for data ready.
        
        Args:
            timeout_ms: Maximum time to wait for readings in milliseconds
            
        Returns:
            dict: Dictionary with sensor names as keys and distances in mm as values
        """
        if not self.is_hardware_available:
            return {"left": -1, "right": -1}

        readings = {}
        start_time = time.time()
        timeout_s = timeout_ms / 1000.0

        for name, sensor in self._sensors.items():
            try:
                if sensor is None:
                    readings[name] = -1
                    continue

                # In continuous mode, just read the range directly
                distance = sensor.range
                
                if distance >= 8190:
                    readings[name] = -1  # Out of range
                else:
                    readings[name] = distance

            except Exception as e:
                logger.debug(f"ToF: Error reading sensor '{name}': {e}")
                readings[name] = -1

        return readings

    def cleanup(self):
        """Clean up sensor resources."""
        logger.debug("ToF: Cleaning up sensors...")
        
        # Stop continuous mode on all sensors
        if hasattr(self, '_sensors'):
            for name, sensor in self._sensors.items():
                if sensor:
                    try:
                        sensor.stop_continuous()
                        logger.debug(f"ToF: Stopped continuous mode for sensor '{name}'")
                    except Exception as e:
                        logger.debug(f"ToF: Error stopping sensor '{name}': {e}")
        
        # Disable all XSHUT pins
        if hasattr(self, '_xshut_pins'):
            for name, pin in self._xshut_pins.items():
                if pin:
                    try:
                        pin.value = False
                        logger.debug(f"ToF: Disabled XSHUT pin for sensor '{name}'")
                    except Exception as e:
                        logger.debug(f"ToF: Error disabling XSHUT pin for sensor '{name}': {e}")

        # Clean up I2C bus if we own it
        if self._owns_i2c and self._i2c:
            try:
                self._i2c.deinit()
                logger.debug("ToF: Deinitialized I2C bus")
            except Exception as e:
                logger.debug(f"ToF: Error deinitializing I2C bus: {e}")

        logger.info("ToF: Cleanup complete")

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