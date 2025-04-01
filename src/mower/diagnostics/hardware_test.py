"""
Hardware test module for comprehensive testing of all hardware components.

This module provides functions for testing all hardware components of the
autonomous mower system, including motors, sensors, and communication interfaces.
It can be run as a standalone script to perform a full system check or
individual test functions can be called for specific component testing.

Usage:
    python -m mower.diagnostics.hardware_test

Or import and use specific test functions:
    from mower.diagnostics.hardware_test import test_motors, test_sensors
"""

import time
import sys
import argparse
import threading
from typing import List, Dict, Any, Optional, Tuple, Callable

from mower.utilities.logger_config import LoggerConfigInfo as LoggerConfig
from mower.main_controller import ResourceManager

# Initialize logger
logging = LoggerConfig.get_logger(__name__)

class HardwareTestSuite:
    """
    Test suite for all hardware components of the autonomous mower.
    
    This class provides methods for testing individual components and a
    comprehensive test of all hardware systems. It relies on the ResourceManager
    for access to hardware components.
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
        Run all hardware tests sequentially.
        
        Args:
            interactive: If True, will prompt the user between tests.
            
        Returns:
            A dictionary with test names as keys and test results as values.
        """
        self.test_in_progress = True
        self.test_results = {}
        
        # Define test sequence
        tests = [
            ("GPIO", self.test_gpio),
            ("IMU Sensor", self.test_imu),
            ("BME280 Sensor", self.test_bme280),
            ("ToF Sensors", self.test_tof_sensors),
            ("Power Monitor", self.test_power_monitor),
            ("GPS", self.test_gps),
            ("Drive Motors", self.test_drive_motors),
            ("Blade Motor", self.test_blade_motor),
            ("Camera", self.test_camera)
        ]
        
        try:
            print("\n===== AUTONOMOUS MOWER HARDWARE TEST SUITE =====\n")
            
            for name, test_func in tests:
                if interactive:
                    input(f"\nPress Enter to test {name}...")
                
                print(f"\nTesting {name}...")
                try:
                    result = test_func()
                    self.test_results[name] = result
                    status = "PASSED" if result else "FAILED"
                    print(f"{name} test {status}")
                except Exception as e:
                    self.test_results[name] = False
                    print(f"{name} test FAILED: {e}")
                    logging.error(f"Error testing {name}: {e}")
            
            # Print summary
            self._print_summary()
            
        finally:
            self.test_in_progress = False
            
        return self.test_results
    
    def _print_summary(self):
        """Print a summary of all test results."""
        print("\n===== TEST SUMMARY =====")
        
        if not self.test_results:
            print("No tests were run.")
            return
        
        passed = sum(1 for result in self.test_results.values() if result)
        failed = sum(1 for result in self.test_results.values() if not result)
        
        for name, result in self.test_results.items():
            status = "PASSED" if result else "FAILED"
            print(f"{name}: {status}")
        
        print(f"\nTotal: {len(self.test_results)} | Passed: {passed} | Failed: {failed}")
        
        if failed == 0:
            print("\nAll hardware tests PASSED!")
        else:
            print(f"\nWARNING: {failed} hardware tests FAILED!")
    
    def test_gpio(self) -> bool:
        """
        Test the GPIO manager initialization and functionality.
        
        Returns:
            True if the test passed, False otherwise.
        """
        try:
            gpio_manager = self.resource_manager.get_gpio_manager()
            if gpio_manager is None:
                logging.error("GPIO manager is None")
                return False
            
            print("GPIO manager initialized successfully.")
            return True
        except Exception as e:
            logging.error(f"Error testing GPIO: {e}")
            return False
    
    def test_imu(self) -> bool:
        """
        Test the IMU sensor initialization and readings.
        
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
            
            print(f"IMU reading: {reading}")
            print(f"Heading: {reading.get('heading', 'N/A')}°")
            print(f"Roll: {reading.get('roll', 'N/A')}°")
            print(f"Pitch: {reading.get('pitch', 'N/A')}°")
            
            # Simple validation of reading
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
            
            print(f"BME280 reading: {reading}")
            print(f"Temperature: {reading.get('temperature', 'N/A')}°C")
            print(f"Humidity: {reading.get('humidity', 'N/A')}%")
            print(f"Pressure: {reading.get('pressure', 'N/A')} hPa")
            
            # Simple validation of reading
            if ('temperature' not in reading or 
                'humidity' not in reading or 
                'pressure' not in reading):
                logging.warning("BME280 returned incomplete data")
                return False
                
            return True
        except Exception as e:
            logging.error(f"Error testing BME280: {e}")
            return False
    
    def test_tof_sensors(self) -> bool:
        """
        Test the Time-of-Flight (ToF) distance sensors.
        
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
            
            if not readings:
                logging.warning("No ToF sensor readings returned")
                return False
            
            # Print readings
            print(f"ToF sensor readings:")
            for i, distance in enumerate(readings):
                print(f"Sensor {i+1}: {distance} mm")
            
            return True
        except Exception as e:
            logging.error(f"Error testing ToF sensors: {e}")
            return False
    
    def test_power_monitor(self) -> bool:
        """
        Test the power monitoring system (INA3221).
        
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
            
            print(f"GPS position: {position}")
            print(f"Latitude: {position.get('latitude', 'N/A')}")
            print(f"Longitude: {position.get('longitude', 'N/A')}")
            if 'altitude' in position:
                print(f"Altitude: {position.get('altitude')} m")
            if 'accuracy' in position:
                print(f"Accuracy: {position.get('accuracy')} m")
            if 'satellites' in position:
                print(f"Satellites: {position.get('satellites')}")
            
            # Validate GPS data
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
    
    Command-line arguments:
        --non-interactive: Run all tests without prompting between tests.
        --test <test_name>: Run only the specified test.
    """
    parser = argparse.ArgumentParser(description='Run hardware tests for the autonomous mower')
    parser.add_argument('--non-interactive', action='store_true', help='Run tests without prompting')
    parser.add_argument('--test', type=str, help='Run only the specified test')
    
    args = parser.parse_args()
    
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
        else:
            print(f"Error: Test '{args.test}' not found")
            print("Available tests:")
            for attr in dir(test_suite):
                if attr.startswith('test_') and callable(getattr(test_suite, attr)):
                    test_name = attr[5:].replace('_', '-')
                    print(f"  - {test_name}")
    else:
        # Run all tests
        test_suite.run_all_tests(interactive=not args.non_interactive)

if __name__ == "__main__":
    main() 