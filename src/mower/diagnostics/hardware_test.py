#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hardware test suite for the autonomous mower.

This module provides a comprehensive suite of tests for all hardware components
of the autonomous mower system. It can be run in interactive or non-interactive mode,
and can test individual components or the entire system.

Key features:
- Automated testing of all sensors and hardware interfaces
- Range validation to ensure sensor readings are within expected parameters
- Interactive testing for components that require user verification
- Detailed logging and reporting of test results
- Command-line interface for running full or targeted tests

Example usage:
    python -m mower.diagnostics.hardware_test  # Run all tests
    python -m mower.diagnostics.hardware_test --test imu  # Test only the IMU
    python -m mower.diagnostics.hardware_test --non-interactive  # Run without prompts
"""

import argparse
import logging
import sys
import time
import queue
from typing import Dict, List, Optional, Any, Tuple

# Configure logging
from mower.utilities.logger_config import LoggerConfigInfo as LoggerConfig
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

try:
    # Try to import the resource manager
    from mower.main_controller import ResourceManager
except ImportError:
    # If we can't import it, define a placeholder
    ResourceManager = None
    logging.warning("Could not import ResourceManager. Will create one dynamically.")

class HardwareTestSuite:
    """
    A suite of tests for hardware components of the autonomous mower.
    
    This class provides methods to test each hardware component individually,
    as well as a method to run all tests in sequence. It can be used interactively
    or non-interactively, and can be run from the command line or imported and used
    programmatically.
    
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
            resource_manager: An instance of ResourceManager. If None, a new one will be created.
        """
        self.resource_manager = resource_manager or ResourceManager()
        self.test_results = {}
        self.test_in_progress = False
        
    def run_all_tests(self, interactive: bool = True) -> Dict[str, bool]:
        """
        Run all hardware tests in sequence.
        
        Args:
            interactive: If True, prompt the user between tests.
                        If False, run all tests without prompting.
        
        Returns:
            Dict[str, bool]: A dictionary mapping test names to result (True=passed, False=failed)
        
        Note:
            Interactive mode is useful for manual testing where user interaction 
            may be required (e.g., confirming motor movement). Non-interactive mode
            is useful for automated testing and diagnostics.
        """
        self.test_results = {}
        
        # Find all test methods
        test_methods = [
            method_name for method_name in dir(self) 
            if method_name.startswith('test_') and callable(getattr(self, method_name))
        ]
        
        for method_name in test_methods:
            test_name = method_name[5:].replace('_', ' ')  # Remove 'test_' prefix and replace underscores
            
            if interactive:
                print("\n" + "="*50)
                print(f"RUNNING TEST: {test_name.upper()}")
                print("="*50)
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
                    if len(test_methods) > 1:  # Don't prompt after the last test
                        input("Press Enter to continue to the next test...")
            except Exception as e:
                # Handle any exceptions that weren't caught by the test method
                logging.error(f"Exception running test {test_name}: {e}")
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
        passed_tests = sum(1 for result in self.test_results.values() if result)
        
        print("\n" + "="*50)
        print(f"SUMMARY: {passed_tests}/{total_tests} tests passed")
        print("="*50)
        
        # Print individual test results
        for test, result in self.test_results.items():
            status = "PASSED" if result else "FAILED"
            print(f"{test}: {status}")
        print("="*50)
        
    def _check_sensor_ranges(self, sensor_name: str, reading: Dict[str, Any]) -> bool:
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
        # Here we do some minimal bounds checks to ensure the sensor is returning data
        if sensor_name.lower() == 'imu':
            # If IMU reading includes heading, pitch, roll
            if 'heading' in reading:
                if reading['heading'] < 0 or reading['heading'] > 360:
                    logging.warning(f"IMU heading out of range: {reading['heading']}")
                    return False
            if 'pitch' in reading:
                if reading['pitch'] < -90 or reading['pitch'] > 90:
                    logging.warning(f"IMU pitch out of range: {reading['pitch']}")
                    return False
            if 'roll' in reading:
                if reading['roll'] < -180 or reading['roll'] > 180:
                    logging.warning(f"IMU roll out of range: {reading['roll']}")
                    return False
        elif sensor_name.lower() == 'bme280':
            # Check for typical atmosphere
            if 'temperature' in reading and (reading['temperature'] < -40 or reading['temperature'] > 85):
                logging.warning(f"BME280 temperature out of range: {reading['temperature']}")
                return False
            if 'humidity' in reading and (reading['humidity'] < 0 or reading['humidity'] > 100):
                logging.warning(f"BME280 humidity out of range: {reading['humidity']}")
                return False
            if 'pressure' in reading and (reading['pressure'] < 300 or reading['pressure'] > 1100):
                logging.warning(f"BME280 pressure out of range: {reading['pressure']}")
                return False
        elif sensor_name.lower() == 'gps':
            # Basic checks for latitude/longitude
            if 'latitude' in reading and (reading['latitude'] < -90 or reading['latitude'] > 90):
                logging.warning(f"GPS latitude out of range: {reading['latitude']}")
                return False
            if 'longitude' in reading and (reading['longitude'] < -180 or reading['longitude'] > 180):
                logging.warning(f"GPS longitude out of range: {reading['longitude']}")
                return False
        elif sensor_name.lower() == 'power_monitor':
            # Check for reasonable voltage/current ranges
            if 'battery_voltage' in reading and (reading['battery_voltage'] < 0 or reading['battery_voltage'] > 30):
                logging.warning(f"Battery voltage out of range: {reading['battery_voltage']}")
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
            logging.info("Testing GPIO accessibility")
            # This just checks if we can access the GPIO library without errors
            import RPi.GPIO as GPIO
            
            # If we got here without an exception, consider it a basic success
            return True
        except Exception as e:
            logging.error(f"Error testing GPIO: {e}")
            return False
    
    def test_imu(self) -> bool:
        """
        Test the IMU sensor initialization and readings.

        This test will:
         1. Attempt to connect to the IMU sensor.
         2. Retrieve reading data such as heading, pitch, roll.
         3. Validate if the data is within a plausible range.

        Returns:
            True if the test passed, False otherwise.
        """
        try:
            imu = self.resource_manager.get_imu_sensor()
            if imu is None:
                logging.error("IMU sensor is None")
                return False
            
            # Read sensor data
            reading = imu.read()
            logging.info(f"IMU reading: {reading}")
            
            # Example of minimal check
            if not self._check_sensor_ranges('IMU', reading):
                logging.warning("IMU reading outside safe range guidelines.")
                return False
            
            # Additional validations
            if 'heading' not in reading or 'roll' not in reading or 'pitch' not in reading:
                logging.warning("IMU returned incomplete data")
                return False
            
            return True
        except Exception as e:
            logging.error(f"Error testing IMU: {e}")
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
                logging.error("BME280 sensor is None")
                return False
            
            # Read sensor data
            reading = bme280.read()
            logging.info(f"BME280 reading: {reading}")
            
            # Validate reading with range checks
            if not self._check_sensor_ranges('BME280', reading):
                logging.warning("BME280 reading outside safe range guidelines.")
                return False
            
            # Additional validations for required fields
            if 'temperature' not in reading or 'humidity' not in reading or 'pressure' not in reading:
                logging.warning("BME280 returned incomplete data")
                return False
            
            # Display readings for user
            print(f"Temperature: {reading.get('temperature', 'N/A')}°C")
            print(f"Humidity: {reading.get('humidity', 'N/A')}%")
            print(f"Pressure: {reading.get('pressure', 'N/A')} hPa")
            
            return True
        except Exception as e:
            logging.error(f"Error testing BME280: {e}")
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
            tof = self.resource_manager.get_tof_sensors()
            if tof is None:
                logging.error("ToF sensors are None")
                return False
            
            # Read sensor data
            readings = tof.read_all()
            logging.info(f"ToF sensor readings: {readings}")
            
            if not readings:
                logging.warning("No ToF sensor readings returned")
                return False
            
            # Check each sensor reading
            for i, distance in enumerate(readings):
                # Basic plausibility check - most ToF sensors have a range of 50mm to 4000mm
                if distance < 0 or distance > 5000:
                    logging.warning(f"ToF sensor {i+1} reading out of range: {distance} mm")
                    print(f"Sensor {i+1}: {distance} mm (OUT OF RANGE)")
                else:
                    print(f"Sensor {i+1}: {distance} mm")
            
            return True
        except Exception as e:
            logging.error(f"Error testing ToF sensors: {e}")
            return False
    
    def test_power_monitor(self) -> bool:
        """
        Test the power monitoring system (INA3221).
        
        This test will:
         1. Attempt to connect to the power monitoring sensor.
         2. Retrieve voltage and current readings for different channels.
         3. Validate if the data is within plausible ranges.

        Returns:
            True if the test passed, False otherwise.
        """
        try:
            power_monitor = self.resource_manager.get_ina3221_sensor()
            if power_monitor is None:
                logging.error("Power monitor is None")
                return False
            
            # Read sensor data
            reading = power_monitor.read()
            logging.info(f"Power monitor reading: {reading}")
            
            # Check if readings are within expected ranges
            if not self._check_sensor_ranges('power_monitor', reading):
                logging.warning("Power monitor readings outside safe range guidelines.")
                return False
            
            # Display readings for user
            print(f"Power monitor reading: {reading}")
            if 'battery_voltage' in reading:
                print(f"Battery voltage: {reading['battery_voltage']} V")
            if 'battery_current' in reading:
                print(f"Battery current: {reading['battery_current']} mA")
            if 'solar_voltage' in reading:
                print(f"Solar voltage: {reading['solar_voltage']} V")
            if 'solar_current' in reading:
                print(f"Solar current: {reading['solar_current']} mA")
            
            # Simple validation of reading
            if 'battery_voltage' not in reading:
                logging.warning("Power monitor returned incomplete data")
                return False
                
            return True
        except Exception as e:
            logging.error(f"Error testing power monitor: {e}")
            return False
    
    def test_gps(self) -> bool:
        """
        Test the GPS module.
        
        This test will:
         1. Attempt to connect to the GPS receiver.
         2. Wait for position data (with timeout).
         3. Validate if the data is within plausible ranges.
         4. Check for required data quality indicators.

        Returns:
            True if the test passed, False otherwise.
        """
        try:
            gps = self.resource_manager.get_gps_position()
            if gps is None:
                logging.error("GPS module is None")
                return False
            
            print("Waiting for GPS fix (up to 10 seconds)...")
            
            # Try to get a GPS fix for up to 10 seconds
            start_time = time.time()
            position = None
            
            while time.time() - start_time < 10:
                position = gps.get_position()
                if position and position.get('latitude') and position.get('longitude'):
                    break
                time.sleep(0.5)
            
            if not position:
                print("No GPS position available within timeout period.")
                return False
            
            logging.info(f"GPS position: {position}")
            
            # Check if position data is within plausible ranges
            if not self._check_sensor_ranges('GPS', position):
                logging.warning("GPS reading outside safe range guidelines.")
                return False
            
            # Display readings for user
            print(f"Latitude: {position.get('latitude', 'N/A')}")
            print(f"Longitude: {position.get('longitude', 'N/A')}")
            if 'altitude' in position:
                print(f"Altitude: {position.get('altitude')} m")
            if 'accuracy' in position:
                print(f"Accuracy: {position.get('accuracy')} m")
            if 'satellites' in position:
                print(f"Satellites: {position.get('satellites')}")
            if 'fix_quality' in position:
                print(f"Fix Quality: {position.get('fix_quality')}")
            
            # Validate GPS data completeness
            if ('latitude' not in position or 
                'longitude' not in position or 
                position.get('latitude') == 0 or 
                position.get('longitude') == 0):
                logging.warning("GPS returned invalid position data")
                return False
                
            return True
        except Exception as e:
            logging.error(f"Error testing GPS: {e}")
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
                logging.error("RoboHAT driver is None")
                return False
            
            print("Testing drive motors...")
            print("WARNING: The mower will move during this test!")
            print("Ensure the mower is elevated or has space to move safely.")
            input("Press Enter to continue or Ctrl+C to cancel...")
            
            # Test sequence: forward, stop, backward, stop, turn left, stop, turn right, stop
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
            logging.error(f"Error testing drive motors: {e}")
            # Ensure motors are stopped after exception
            try:
                self.resource_manager.get_robohat_driver().set_motors(0, 0)
            except:
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
                logging.error("Blade controller is None")
                return False
            
            print("Testing blade motor...")
            print("WARNING: The blade motor will run during this test!")
            print("Ensure the mower is in a safe position with no obstructions.")
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
            feedback = input("Did the blade motor work correctly at all speeds? (y/n): ")
            return feedback.lower().startswith('y')
        except Exception as e:
            logging.error(f"Error testing blade motor: {e}")
            # Ensure blade is stopped after exception
            try:
                self.resource_manager.get_blade_controller().set_speed(0)
            except:
                pass
            return False
    
    def test_camera(self) -> bool:
        """
        Test the camera module.
        
        This test will attempt to capture an image from the camera.
        
        Returns:
            True if the test passed, False otherwise.
        """
        try:
            camera = self.resource_manager.get_camera()
            if camera is None:
                logging.error("Camera is None")
                return False
            
            print("Testing camera...")
            
            # Capture a frame
            frame = camera.capture_frame()
            
            if frame is None or frame.size == 0:
                print("Failed to capture a valid frame")
                return False
            
            print(f"Successfully captured image: {frame.shape[0]}x{frame.shape[1]}")
            
            # Save the image for inspection
            import cv2
            test_image_path = "camera_test.jpg"
            cv2.imwrite(test_image_path, frame)
            
            print(f"Test image saved to {test_image_path}")
            
            return True
        except Exception as e:
            logging.error(f"Error testing camera: {e}")
            return False

def main():
    """
    Run the hardware test suite from the command line.
    
    This utility tests all major hardware components of the autonomous mower system:
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
    
    Usage examples:
        python -m mower.diagnostics.hardware_test  # Run all tests interactively
        python -m mower.diagnostics.hardware_test --test imu  # Test only the IMU
        python -m mower.diagnostics.hardware_test --non-interactive  # Run all tests without prompts
    
    Returns:
        System exit code: 0 if all tests pass, non-zero otherwise
    """
    parser = argparse.ArgumentParser(description='Run hardware tests for the autonomous mower')
    parser.add_argument('--non-interactive', action='store_true', help='Run tests without prompting')
    parser.add_argument('--test', type=str, help='Run only the specified test')
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("AUTONOMOUS MOWER HARDWARE TEST SUITE")
    print("=" * 50)
    print("This utility tests hardware functionality and sensor calibration.")
    print("For each sensor, readings are validated against plausible ranges.")
    print("=" * 50)
    
    # Create test suite
    test_suite = HardwareTestSuite()
    
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
                if attr.startswith('test_') and callable(getattr(test_suite, attr)):
                    test_name = attr[5:].replace('_', '-')
                    print(f"  - {test_name}")
            return 1
    else:
        # Run all tests
        test_results = test_suite.run_all_tests(interactive=not args.non_interactive)
        # Return exit code based on test results
        return 0 if all(test_results.values()) else 1

if __name__ == "__main__":
    sys.exit(main()) 