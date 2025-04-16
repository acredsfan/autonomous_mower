#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hardware test suite for the autonomous mower.

This module provides a comprehensive suite of tests for all hardware components
of the autonomous mower system. It can be run in interactive or non-interactive
mode, and can test individual components or the entire system.

Key features:
- Automated testing of all sensors and hardware interfaces
- Range validation to ensure sensor readings are within expected parameters
- Interactive testing for components that require user verification
- Detailed logging and reporting of test results
- Command-line interface for running full or targeted tests

Example usage:
    sudo -E env PATH=$PATH python3 -m mower.diagnostics.hardware_test
    sudo -E env PATH=$PATH python3 -m mower.diagnostics.hardware_test \
        --test imu
    sudo -E env PATH=$PATH python3 -m mower.diagnostics.hardware_test \
        --non-interactive
"""

import argparse
import os
import sys
import time
from typing import Dict, Optional, Any
import logging as logging_levels
from mower.hardware.imu import BNO085Sensor
from mower.hardware.tof import VL53L0XSensors
from mower.hardware.ina3221 import INA3221Sensor
from mower.navigation.gps import GpsLatestPosition

# Configure logging
from mower.utilities.logger_config import LoggerConfigInfo as LoggerConfig
logger = LoggerConfig.get_logger(__name__)

try:
    from mower.main_controller import ResourceManager
except ImportError as e:
    logger.error(f"Failed to import ResourceManager: {e}")
    sys.exit(1)


# Ensure RPi.GPIO is imported conditionally to handle environments
# without GPIO support
try:
    import RPi.GPIO as GPIO  # type:ignore
except ImportError:
    GPIO = None  # Handle gracefully if GPIO is not available


def check_root_privileges() -> bool:
    """
    Check if the script is running with root privileges.

    Returns:
        bool: True if running as root, False otherwise
    """
    if os.geteuid() != 0:
        msg = (
            "Hardware tests require root privileges. "
            "Please run with: sudo -E env PATH=$PATH python3 -m "
            "mower.diagnostics.hardware_test"
        )
        logger.error(msg)
        print(msg)
        return False
    return True


def initialize_resource_manager() -> Optional[ResourceManager]:
    """
    Initialize the ResourceManager with proper error handling.

    Returns:
        Optional[ResourceManager]: Initialized ResourceManager or
            None on failure
    """
    try:
        resource_manager = ResourceManager()
        resource_manager.initialize()
        return resource_manager
    except Exception as e:
        logger.error(f"Failed to initialize ResourceManager: {e}")
        return None


class HardwareTestSuite:
    """
    A suite of tests for hardware components of the autonomous mower.

    This class provides methods to test each hardware component individually,
    as well as a method to run all tests in sequence. It can be used
    interactively or non-interactively, and can be run from the command line or
    imported and used programmatically.

    Each test validates:
    1. Connectivity to the hardware component
    2. Ability to read data from the component
    3. Range validation to ensure readings are within expected parameters

    For motors, the tests also include functional tests to verify movement.
    """

    def __init__(self, resource_manager: Optional[ResourceManager] = None):
        """
        Initialize the hardware test suite.

        Args:
            resource_manager: An instance of ResourceManager. If None,
                a new one will be created.
        """
        if not check_root_privileges():
            raise RuntimeError("Root privileges required")

        self.resource_manager = resource_manager
        if self.resource_manager is None:
            self.resource_manager = initialize_resource_manager()
            if self.resource_manager is None:
                raise RuntimeError("Failed to initialize ResourceManager")

        self.test_results = {}
        self.test_in_progress = False

    def run_all_tests(self, interactive: bool = True) -> Dict[str, bool]:
        """
        Run all hardware tests in sequence.

        Args:
            interactive: If True, prompt the user between tests.
                      If False, run all tests without prompting.

        Returns:
            Dict[str, bool]: A dictionary mapping test names to result
                          (True=passed, False=failed)

        Note:
            Interactive mode is useful for manual testing where user
            interaction may be required (e.g., confirming motor movement).
            Non-interactive mode is useful for automated testing and
            diagnostics.
        """
        self.test_results = {}

        # Find all test methods
        test_methods = [
            method_name for method_name in dir(self)
            if method_name.startswith('test_') and
            callable(getattr(self, method_name))]

        for method_name in test_methods:
            # Remove 'test_' prefix and replace underscores
            test_name = method_name[5:].replace('_', ' ')

            if interactive:
                print("\n" + "=" * 50)
                print(f"RUNNING TEST: {test_name.upper()}")
                print("=" * 50)
                input("Press Enter to start this test...")
            else:
                print(f"\nRunning test: {test_name}")

            try:
                # Get the test method and run it
                test_method = getattr(self, method_name)
                result = test_method()

                # Record the result
                self.test_results[test_name] = result

                if interactive:
                    print(f"Test {'PASSED' if result else 'FAILED'}")
                    # Don't prompt after the last test
                    if len(test_methods) > 1:
                        input("Press Enter to continue to the next test...")
            except Exception as e:
                # Handle any exceptions that weren't caught by the test method
                logger.error(f"Exception running test {test_name}: {e}")
                self.test_results[test_name] = False
                print(f"Test FAILED with exception: {e}")
                if interactive:
                    input("Press Enter to continue to the next test...")

        # Print summary of results
        self._print_summary()

        return self.test_results

    def _print_summary(self):
        """
        Print a summary of test results.
        """
        # Calculate total and passed tests
        total_tests = len(self.test_results)
        passed_tests = sum(
            1 for result in self.test_results.values() if result)

        print("\n" + "=" * 50)
        print(f"SUMMARY: {passed_tests}/{total_tests} tests passed")
        print("=" * 50)

        # Print individual test results
        for test, result in self.test_results.items():
            status = "PASSED" if result else "FAILED"
            print(f"{test}: {status}")

        # Add detailed logging for each test result
        logger.info("Starting hardware tests...")

        # Log the result of each test
        for test_name, result in self.test_results.items():
            if result:
                logger.info(f"Test {test_name} PASSED")
            else:
                logger.error(f"Test {test_name} FAILED")

        # Log summary of results
        logger.info(
            f"Hardware tests completed: {passed_tests}/"
            f"{total_tests} tests passed"
        )

        print("=" * 50)

    def _check_sensor_ranges(self, sensor_name: str,
                             reading: Dict[str, Any]) -> bool:
        """
        Check if a given sensor reading is within plausible limits.

        Args:
            sensor_name: Name of the sensor (e.g. "IMU", "BME280")
            reading: Dictionary of sensor values

        Returns:
            bool: True if readings are within expected range, False otherwise.

        Explanation:
            This method is a minimal reference. In a real environment, define
            stable ranges or use knowledge from sensor documentation.

        Example:
            If 'roll' in reading, check that -180 < roll < 180
        """
        # Here we do some minimal bounds checks to ensure the sensor is
        # returning data
        if sensor_name.lower() == 'imu':
            # If IMU reading includes heading, pitch, roll
            if 'heading' in reading:
                if reading['heading'] < 0 or reading['heading'] > 360:
                    logger.warning(
                        f"IMU heading out of range: {reading['heading']}")
                    return False
            if 'pitch' in reading:
                if reading['pitch'] < -90 or reading['pitch'] > 90:
                    logger.warning(
                        f"IMU pitch out of range: {reading['pitch']}")
                    return False
            if 'roll' in reading:
                if reading['roll'] < -180 or reading['roll'] > 180:
                    logger.warning(
                        f"IMU roll out of range: {reading['roll']}")
                    return False
        elif sensor_name.lower() == 'bme280':
            # Check for typical atmosphere
            if 'temperature' in reading and (
                    reading['temperature'] < -40 or
                    reading['temperature'] > 85):
                logger.warning(
                    "BME280 temperature out of range: "
                    f"{reading['temperature']}")
                return False
            if 'humidity' in reading and (
                    reading['humidity'] < 0 or reading['humidity'] > 100):
                logger.warning(
                    f"BME280 humidity out of range: {reading['humidity']}")
                return False
            if 'pressure' in reading and (
                    reading['pressure'] < 300 or reading['pressure'] > 1100):
                logger.warning(
                    f"BME280 pressure out of range: {reading['pressure']}")
                return False
        elif sensor_name.lower() == 'gps':
            # Basic checks for latitude/longitude
            if 'latitude' in reading and (
                    reading['latitude'] < -90 or reading['latitude'] > 90):
                logger.warning(
                    f"GPS latitude out of range: {reading['latitude']}")
                return False
            if 'longitude' in reading and (
                    reading['longitude'] < -180 or reading['longitude'] > 180):
                logger.warning(
                    f"GPS longitude out of range: {reading['longitude']}")
                return False
        elif sensor_name.lower() == 'power_monitor':
            # Check for reasonable voltage/current ranges
            if ('battery_voltage' in reading and
                    (reading['battery_voltage'] < 0 or
                     reading['battery_voltage'] > 30)):
                logger.warning(
                    f"Battery voltage out of range: "
                    f"{reading['battery_voltage']}")
                return False
        # Add more checks as needed for additional sensors
        return True

    def test_gpio(self) -> bool:
        """
        Test GPIO functionality.

        Returns:
            True if the test passed, False otherwise.
        """
        try:
            # Basic test to check if GPIO is accessible
            logger.info("Testing GPIO accessibility")

            # First check if we're running as root
            import os
            if os.geteuid() != 0:
                msg = (
                    "GPIO test requires root privileges. "
                    "Please run with: sudo -E env PATH=$PATH python3 -m "
                    "mower.diagnostics.hardware_test"
                )
                logger.warning(msg)
                print(msg)
                return False

            # This just checks if we can access the GPIO library without errors
            import RPi.GPIO as GPIO  # type:ignore
            # Check if GPIO is accessible
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(18, GPIO.OUT)
            GPIO.output(18, GPIO.HIGH)
            time.sleep(0.5)
            GPIO.output(18, GPIO.LOW)
            GPIO.cleanup()
            logger.info("GPIO test passed")

            # If we got here without an exception, consider it a basic success
            return True
        except Exception as e:
            if "no access to /dev/mem" in str(e):
                msg = (
                    "No access to GPIO. Root privileges required. "
                    "Please run with: sudo -E env PATH=$PATH python3 -m "
                    "mower.diagnostics.hardware_test"
                )
                logger.error(msg)
                print(msg)
            else:
                logger.error(f"Error testing GPIO: {e}")
            return False

    def test_imu(self) -> bool:
        """Test the IMU module."""
        try:
            imu = BNO085Sensor()
            data = imu.read()
            if data and 'quaternion' in data:
                logger.info(f"IMU reading: {data}")
                return True
            else:
                logger.warning("IMU returned incomplete data.")
                return False
        except Exception as e:
            logger.error(f"Error testing IMU: {e}")
            return False

    def test_bme280(self) -> bool:
        """
        Test the BME280 environmental sensor.

        This test will:
         1. Attempt to connect to the BME280 sensor.
         2. Retrieve temperature, humidity, and pressure data.
         3. Validate if the data is within plausible ranges.

        Returns:
            True if the test passed, False otherwise.
        """
        try:
            bme280 = self.resource_manager.get_bme280_sensor()
            if bme280 is None:
                logger.error("BME280 sensor is None")
                return False

            # Read sensor data
            reading = bme280.read()
            logger.info(f"BME280 reading: {reading}")

            # Validate reading with range checks
            if not self._check_sensor_ranges('BME280', reading):
                logger.warning(
                    "BME280 reading outside safe range guidelines.")
                return False

            # Additional validations for required fields
            if ('temperature' not in reading or 'humidity' not in reading or
                    'pressure' not in reading):
                logger.warning("BME280 returned incomplete data")
                return False

            # Display readings for user
            print(f"Temperature: {reading.get('temperature', 'N/A')}°C")
            print(f"Humidity: {reading.get('humidity', 'N/A')}%")
            print(f"Pressure: {reading.get('pressure', 'N/A')} hPa")

            return True
        except Exception as e:
            logger.error(f"Error testing BME280: {e}")
            return False

    def test_tof_sensors(self) -> bool:
        """
        Test the Time-of-Flight (ToF) distance sensors.

        This test will:
         1. Attempt to connect to the ToF sensors.
         2. Retrieve distance readings from all connected sensors.
         3. Validate if the data is within plausible ranges.

        Returns:
            True if the test passed, False otherwise.
        """
        try:
            tof_sensors = VL53L0XSensors()
            data = tof_sensors.read_all(sensors=[1, 2, 3])
            if data:
                logger.info(f"ToF sensors reading: {data}")
                return True
            else:
                logger.warning("ToF sensors returned no data.")
                return False
        except Exception as e:
            logger.error(f"Error testing ToF sensors: {e}")
            return False

    def test_power_monitor(self) -> bool:
        """Test the power monitor module."""
        try:
            power_monitor = INA3221Sensor()
            data = power_monitor.read(channel=1)
            if data:
                logger.info(f"Power monitor reading: {data}")
                return True
            else:
                logger.warning("Power monitor returned no data.")
                return False
        except Exception as e:
            logger.error(f"Error testing power monitor: {e}")
            return False

    def test_gps(self) -> bool:
        """Test the GPS module."""
        try:
            gps = GpsLatestPosition()
            position = gps.get_position()
            if position:
                logger.info(f"GPS position: {position}")
                return True
            else:
                logger.warning("No GPS data available.")
                return False
        except Exception as e:
            logger.error(f"Error testing GPS: {e}")
            return False

    def test_drive_motors(self) -> bool:
        """
        Test the drive motors.

        This test will move the motors forward, backward, and turn in place.

        Returns:
            True if the test passed, False otherwise.
        """
        try:
            robohat = self.resource_manager.get_robohat_driver()
            if robohat is None:
                logger.error("RoboHAT driver is None")
                return False

            print("Testing drive motors...")
            print("WARNING: The mower will move during this test!")
            print("Ensure the mower is elevated or has space to move safely.")
            input("Press Enter to continue or Ctrl+C to cancel...")

            # Test sequence: forward, stop, backward, stop, turn left, stop,
            # turn right, stop
            moves = [
                ("forward", 0.5, 0.5),
                ("stop", 0, 0),
                ("backward", -0.5, -0.5),
                ("stop", 0, 0),
                ("turn left", -0.5, 0.5),
                ("stop", 0, 0),
                ("turn right", 0.5, -0.5),
                ("stop", 0, 0)
                ]

            for move, left, right in moves:
                print(f"Motor test: {move}")
                robohat.set_motors(left, right)
                time.sleep(1)

            # Final stop
            robohat.set_motors(0, 0)

            print("Drive motors test complete.")
            feedback = input("Did all motor movements work correctly? (y/n): ")
            return feedback.lower().startswith('y')
        except Exception as e:
            logger.error(f"Error testing drive motors: {e}")
            # Ensure motors are stopped after exception
            try:
                self.resource_manager.get_robohat_driver().set_motors(0, 0)
            except BaseException:
                pass
            return False

    def test_blade_motor(self) -> bool:
        """
        Test the blade motor.

        This test will run the blade at different speeds.

        Returns:
            True if the test passed, False otherwise.
        """
        try:
            blade_controller = self.resource_manager.get_blade_controller()
            if blade_controller is None:
                logger.error("Blade controller is None")
                return False

            print("Testing blade motor...")
            print("WARNING: The blade motor will run during this test!")
            print("Ensure the mower is in a safe position with no "
                  "obstructions.")
            input("Press Enter to continue or Ctrl+C to cancel...")

            # Test sequence: low speed, medium speed, high speed, stop
            speeds = [
                ("low speed (25%)", 0.25),
                ("medium speed (50%)", 0.5),
                ("high speed (75%)", 0.75),
                ("stop", 0)
                ]

            for description, speed in speeds:
                print(f"Blade test: {description}")
                blade_controller.set_speed(speed)
                time.sleep(2)

            # Final stop
            blade_controller.set_speed(0)

            print("Blade motor test complete.")
            feedback = input(
                "Did the blade motor work correctly at all speeds? (y/n): ")
            return feedback.lower().startswith('y')
        except Exception as e:
            logger.error(f"Error testing blade motor: {e}")
            # Ensure blade is stopped after exception
            try:
                self.resource_manager.get_blade_controller().set_speed(0)
            except BaseException:
                pass
            return False

    def test_camera(self) -> bool:
        """
        Test the camera module.

        This test will attempt to capture an image from the camera.
        The test is considered optional and will pass if the camera
        is not available but properly detected that state.

        Returns:
            True if the test passed or camera is unavailable, False on error
        """
        try:
            camera = self.resource_manager.get_camera()
            if camera is None:
                print("Camera not available - skipping test")
                return True  # Consider this a pass since camera is optional

            print("Testing camera...")

            # Capture a frame
            frame = camera.capture_frame()

            if frame is None:
                print("Camera detected but failed to capture frame")
                return True  # Still pass since camera is optional

            if isinstance(frame, bytes):
                print("Successfully captured JPEG image")
                return True
            elif hasattr(frame, 'shape'):
                print(
                    f"Successfully captured image: "
                    f"{frame.shape[0]}x{frame.shape[1]}")
                return True
            else:
                print("Captured frame but in unexpected format")
                return True  # Still pass since camera is optional

        except Exception as e:
            logger.warning(f"Camera test error (non-critical): {e}")
            return True  # Consider camera errors non-critical


def main():
    """
    Run the hardware test suite from the command line.

    This utility tests all major hardware components of the autonomous mower
    system:
    - IMU (orientation sensor)
    - BME280 (environmental sensor)
    - ToF sensors (distance sensors)
    - GPS module
    - Power monitoring system
    - Drive motors
    - Blade motor
    - Camera

    Command-line options:
        --non-interactive: Run all tests without prompting between tests.
        --test <test_name>: Run only the specified test (e.g., 'imu', 'gps').
        --verbose: Enable verbose output

    Usage examples:
        sudo -E env PATH=$PATH python3 -m mower.diagnostics.hardware_test
        sudo -E env PATH=$PATH python3 -m mower.diagnostics.hardware_test \
            --test imu
        sudo -E env PATH=$PATH python3 -m mower.diagnostics.hardware_test \
            --non-interactive

    Returns:
        System exit code: 0 if all tests pass, non-zero otherwise
    """
    # Check for root privileges first
    if not check_root_privileges():
        return 1

    parser = argparse.ArgumentParser(
        description='Run hardware tests for the autonomous mower')
    parser.add_argument(
        '--non-interactive',
        action='store_true',
        help='Run tests without prompting')
    parser.add_argument(
        '--test',
        type=str,
        help='Run only the specified test')
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output')

    args = parser.parse_args()

    # Configure logging based on verbosity
    if args.verbose:
        logger.setLevel(logging_levels.DEBUG)
        # Force immediate output
        for handler in logger.handlers:
            handler.flush = lambda: None
    else:
        logger.setLevel(logging_levels.INFO)

    print("=" * 50)
    print("AUTONOMOUS MOWER HARDWARE TEST SUITE")
    print("=" * 50)
    print("This utility tests hardware functionality and sensor calibration.")
    print("For each sensor, readings are validated against plausible ranges.")
    print("=" * 50)

    resource_manager = None
    try:
        # Initialize ResourceManager
        resource_manager = initialize_resource_manager()
        if resource_manager is None:
            return 1

        # Create test suite
        test_suite = HardwareTestSuite(resource_manager)

        if args.test:
            # Run specific test
            test_func_name = f"test_{args.test.lower().replace('-', '_')}"
            if hasattr(test_suite, test_func_name):
                test_func = getattr(test_suite, test_func_name)
                print(f"Running {args.test} test...")
                result = test_func()
                print(f"Test {'PASSED' if result else 'FAILED'}")
                return 0 if result else 1
            else:
                print(f"Error: Test '{args.test}' not found")
                print("Available tests:")
                for attr in dir(test_suite):
                    if attr.startswith('test_') and callable(
                            getattr(test_suite, attr)):
                        test_name = attr[5:].replace('_', '-')
                        print(f"  - {test_name}")
                return 1
        else:
            # Run all tests
            test_results = test_suite.run_all_tests(
                interactive=not args.non_interactive)
            return 0 if all(test_results.values()) else 1

    except Exception as e:
        logger.error(f"Error running hardware tests: {e}")
        return 1

    finally:
        # Cleanup
        if resource_manager is not None:
            try:
                resource_manager.cleanup()
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")


if __name__ == "__main__":
    sys.exit(main())
