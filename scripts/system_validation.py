#!/usr/bin/env python3
"""
System Validation Script

This script performs comprehensive validation of the autonomous mower system
after deployment. It checks hardware connectivity, software configuration,
and system functionality.

Usage:
    python3 scripts/system_validation.py [--verbose] [--config CONFIG_FILE]

Options:
    --verbose       Show detailed validation information
    --config        Specify configuration file path
"""

import os
import sys
import json
import time
import argparse
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from src.core.logger import get_logger
except ImportError:
    # Set up basic logging if logger module is not available
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("system_validation")
else:
    logger = get_logger("system_validation")


class SystemValidator:
    """System validation for the autonomous mower."""
    
    def __init__(self, config_path: Optional[str] = None, verbose: bool = False):
        """
        Initialize the system validator.
        
        Args:
            config_path: Path to configuration file
            verbose: Whether to show detailed validation information
        """
        self.config_path = config_path or "config/main_config.json"
        self.verbose = verbose
        self.config = self._load_config()
        self.validation_results = {
            "hardware": {},
            "software": {},
            "configuration": {},
            "functionality": {},
            "overall": {
                "status": "pending",
                "message": "Validation not started"
            }
        }
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file.
        
        Returns:
            Configuration dictionary
        """
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            logger.info(f"Loaded configuration from {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return {}
    
    def validate_hardware(self) -> bool:
        """
        Validate hardware components.
        
        Returns:
            True if all hardware checks pass, False otherwise
        """
        logger.info("Validating hardware components...")
        
        # Check Raspberry Pi model
        try:
            with open("/proc/cpuinfo", 'r') as f:
                cpuinfo = f.read()
            
            if "Raspberry Pi" in cpuinfo:
                model = next((line.split(": ")[1] for line in cpuinfo.split("\n") 
                             if "Model" in line), "Unknown")
                self.validation_results["hardware"]["raspberry_pi"] = {
                    "status": "pass",
                    "message": f"Detected {model}"
                }
            else:
                self.validation_results["hardware"]["raspberry_pi"] = {
                    "status": "fail",
                    "message": "Not running on Raspberry Pi"
                }
                return False
        except Exception as e:
            self.validation_results["hardware"]["raspberry_pi"] = {
                "status": "error",
                "message": f"Error detecting Raspberry Pi: {e}"
            }
            return False
        
        # Check I2C devices
        try:
            i2c_devices = subprocess.check_output(["i2cdetect", "-y", "1"]).decode()
            
            # Check for expected I2C devices
            expected_devices = {
                "0x40": "INA3221",
                "0x68": "MPU6050",
                "0x29": "VL53L0X"
            }
            
            found_devices = []
            for addr, name in expected_devices.items():
                if addr in i2c_devices:
                    found_devices.append(name)
                    self.validation_results["hardware"][name.lower()] = {
                        "status": "pass",
                        "message": f"Found {name} at {addr}"
                    }
                else:
                    self.validation_results["hardware"][name.lower()] = {
                        "status": "fail",
                        "message": f"{name} not found at {addr}"
                    }
            
            if not found_devices:
                logger.warning("No expected I2C devices found")
                return False
            
            logger.info(f"Found I2C devices: {', '.join(found_devices)}")
        except Exception as e:
            logger.error(f"Error checking I2C devices: {e}")
            self.validation_results["hardware"]["i2c_devices"] = {
                "status": "error",
                "message": f"Error checking I2C devices: {e}"
            }
            return False
        
        # Check camera
        try:
            camera_result = subprocess.run(
                ["vcgencmd", "get_camera"],
                capture_output=True,
                text=True
            )
            if "detected=1" in camera_result.stdout:
                self.validation_results["hardware"]["camera"] = {
                    "status": "pass",
                    "message": "Camera detected"
                }
                logger.info("Camera detected")
            else:
                self.validation_results["hardware"]["camera"] = {
                    "status": "fail",
                    "message": "Camera not detected"
                }
                logger.warning("Camera not detected")
        except Exception as e:
            logger.error(f"Error checking camera: {e}")
            self.validation_results["hardware"]["camera"] = {
                "status": "error",
                "message": f"Error checking camera: {e}"
            }
        
        # Check Coral TPU if enabled
        if self.config.get("hardware", {}).get("coral_enabled", False):
            try:
                # Try to import Edge TPU module
                import importlib
                edgetpu_spec = importlib.util.find_spec("tflite_runtime.interpreter")
                
                if edgetpu_spec:
                    # Try to list Edge TPU devices
                    from tflite_runtime.interpreter import load_delegate
                    try:
                        load_delegate("libedgetpu.so.1")
                        self.validation_results["hardware"]["coral_tpu"] = {
                            "status": "pass",
                            "message": "Coral TPU detected and library loaded"
                        }
                        logger.info("Coral TPU detected and library loaded")
                    except Exception as e:
                        self.validation_results["hardware"]["coral_tpu"] = {
                            "status": "fail",
                            "message": f"Coral TPU library error: {e}"
                        }
                        logger.warning(f"Coral TPU library error: {e}")
                else:
                    self.validation_results["hardware"]["coral_tpu"] = {
                        "status": "fail",
                        "message": "Edge TPU runtime not installed"
                    }
                    logger.warning("Edge TPU runtime not installed")
            except Exception as e:
                logger.error(f"Error checking Coral TPU: {e}")
                self.validation_results["hardware"]["coral_tpu"] = {
                    "status": "error",
                    "message": f"Error checking Coral TPU: {e}"
                }
        
        # Check GPIO access
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            # Test a safe GPIO pin (adjust as needed)
            test_pin = 4
            GPIO.setup(test_pin, GPIO.OUT)
            GPIO.output(test_pin, GPIO.HIGH)
            time.sleep(0.1)
            GPIO.output(test_pin, GPIO.LOW)
            GPIO.cleanup(test_pin)
            
            self.validation_results["hardware"]["gpio"] = {
                "status": "pass",
                "message": "GPIO access working"
            }
            logger.info("GPIO access working")
        except Exception as e:
            logger.error(f"Error accessing GPIO: {e}")
            self.validation_results["hardware"]["gpio"] = {
                "status": "error",
                "message": f"Error accessing GPIO: {e}"
            }
        
        # Overall hardware validation result
        hardware_statuses = [
            result["status"] for result in self.validation_results["hardware"].values()
        ]
        
        if "fail" in hardware_statuses:
            logger.warning("Hardware validation failed")
            return False
        elif "error" in hardware_statuses:
            logger.warning("Hardware validation encountered errors")
            return False
        else:
            logger.info("Hardware validation passed")
            return True
    
    def validate_software(self) -> bool:
        """
        Validate software components.
        
        Returns:
            True if all software checks pass, False otherwise
        """
        logger.info("Validating software components...")
        
        # Check Python version
        try:
            python_version = sys.version.split()[0]
            major, minor, _ = python_version.split(".")
            
            if int(major) >= 3 and int(minor) >= 9:
                self.validation_results["software"]["python"] = {
                    "status": "pass",
                    "message": f"Python {python_version} (required: 3.9+)"
                }
                logger.info(f"Python version: {python_version}")
            else:
                self.validation_results["software"]["python"] = {
                    "status": "fail",
                    "message": f"Python {python_version} (required: 3.9+)"
                }
                logger.warning(f"Python version {python_version} is below required 3.9+")
                return False
        except Exception as e:
            logger.error(f"Error checking Python version: {e}")
            self.validation_results["software"]["python"] = {
                "status": "error",
                "message": f"Error checking Python version: {e}"
            }
            return False
        
        # Check required Python packages
        required_packages = [
            "numpy",
            "opencv-python",
            "flask",
            "RPi.GPIO",
            "smbus2",
            "psutil"
        ]
        
        missing_packages = []
        for package in required_packages:
            try:
                __import__(package.replace("-", "_"))
                self.validation_results["software"][package] = {
                    "status": "pass",
                    "message": f"{package} installed"
                }
            except ImportError:
                missing_packages.append(package)
                self.validation_results["software"][package] = {
                    "status": "fail",
                    "message": f"{package} not installed"
                }
        
        if missing_packages:
            logger.warning(f"Missing required packages: {', '.join(missing_packages)}")
            return False
        
        # Check ML models
        model_files = [
            "models/coral_model_quantized_int8.tflite",
            "models/labels.txt"
        ]
        
        missing_models = []
        for model_file in model_files:
            if os.path.exists(model_file):
                self.validation_results["software"][os.path.basename(model_file)] = {
                    "status": "pass",
                    "message": f"{model_file} exists"
                }
            else:
                missing_models.append(model_file)
                self.validation_results["software"][os.path.basename(model_file)] = {
                    "status": "fail",
                    "message": f"{model_file} not found"
                }
        
        if missing_models:
            logger.warning(f"Missing model files: {', '.join(missing_models)}")
        
        # Check systemd service files
        service_files = [
            "/etc/systemd/system/mower.service",
            "/etc/systemd/system/ntrip-client.service"
        ]
        
        missing_services = []
        for service_file in service_files:
            if os.path.exists(service_file):
                self.validation_results["software"][os.path.basename(service_file)] = {
                    "status": "pass",
                    "message": f"{service_file} exists"
                }
            else:
                missing_services.append(service_file)
                self.validation_results["software"][os.path.basename(service_file)] = {
                    "status": "fail",
                    "message": f"{service_file} not found"
                }
        
        if missing_services:
            logger.warning(f"Missing service files: {', '.join(missing_services)}")
            return False
        
        # Overall software validation result
        software_statuses = [
            result["status"] for result in self.validation_results["software"].values()
        ]
        
        if "fail" in software_statuses:
            logger.warning("Software validation failed")
            return False
        elif "error" in software_statuses:
            logger.warning("Software validation encountered errors")
            return False
        else:
            logger.info("Software validation passed")
            return True
    
    def validate_configuration(self) -> bool:
        """
        Validate configuration files.
        
        Returns:
            True if all configuration checks pass, False otherwise
        """
        logger.info("Validating configuration files...")
        
        # Check main configuration file
        if not self.config:
            self.validation_results["configuration"]["main_config"] = {
                "status": "fail",
                "message": f"Failed to load {self.config_path}"
            }
            logger.warning(f"Failed to load {self.config_path}")
            return False
        
        # Check required configuration sections
        required_sections = ["system", "hardware", "navigation", "safety"]
        missing_sections = []
        
        for section in required_sections:
            if section in self.config:
                self.validation_results["configuration"][section] = {
                    "status": "pass",
                    "message": f"{section} section exists"
                }
            else:
                missing_sections.append(section)
                self.validation_results["configuration"][section] = {
                    "status": "fail",
                    "message": f"{section} section missing"
                }
        
        if missing_sections:
            logger.warning(f"Missing configuration sections: {', '.join(missing_sections)}")
            return False
        
        # Check other configuration files
        config_files = [
            "config/components.json",
            "config/home_location.json",
            "config/user_polygon.json"
        ]
        
        for config_file in config_files:
            try:
                if os.path.exists(config_file):
                    with open(config_file, 'r') as f:
                        json.load(f)
                    self.validation_results["configuration"][os.path.basename(config_file)] = {
                        "status": "pass",
                        "message": f"{config_file} exists and is valid JSON"
                    }
                else:
                    self.validation_results["configuration"][os.path.basename(config_file)] = {
                        "status": "warning",
                        "message": f"{config_file} not found"
                    }
                    logger.warning(f"{config_file} not found")
            except json.JSONDecodeError:
                self.validation_results["configuration"][os.path.basename(config_file)] = {
                    "status": "fail",
                    "message": f"{config_file} contains invalid JSON"
                }
                logger.warning(f"{config_file} contains invalid JSON")
                return False
            except Exception as e:
                self.validation_results["configuration"][os.path.basename(config_file)] = {
                    "status": "error",
                    "message": f"Error checking {config_file}: {e}"
                }
                logger.error(f"Error checking {config_file}: {e}")
        
        # Overall configuration validation result
        config_statuses = [
            result["status"] for result in self.validation_results["configuration"].values()
        ]
        
        if "fail" in config_statuses:
            logger.warning("Configuration validation failed")
            return False
        elif "error" in config_statuses:
            logger.warning("Configuration validation encountered errors")
            return False
        else:
            logger.info("Configuration validation passed")
            return True
    
    def validate_functionality(self) -> bool:
        """
        Validate system functionality.
        
        Returns:
            True if all functionality checks pass, False otherwise
        """
        logger.info("Validating system functionality...")
        
        # Check if services are running
        services = ["mower.service", "ntrip-client.service"]
        
        for service in services:
            try:
                result = subprocess.run(
                    ["systemctl", "is-active", service],
                    capture_output=True,
                    text=True
                )
                
                if result.stdout.strip() == "active":
                    self.validation_results["functionality"][service] = {
                        "status": "pass",
                        "message": f"{service} is running"
                    }
                    logger.info(f"{service} is running")
                else:
                    self.validation_results["functionality"][service] = {
                        "status": "fail",
                        "message": f"{service} is not running"
                    }
                    logger.warning(f"{service} is not running")
                    return False
            except Exception as e:
                logger.error(f"Error checking {service}: {e}")
                self.validation_results["functionality"][service] = {
                    "status": "error",
                    "message": f"Error checking {service}: {e}"
                }
                return False
        
        # Check web interface
        try:
            import socket
            
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            result = s.connect_ex(('localhost', 5000))
            s.close()
            
            if result == 0:
                self.validation_results["functionality"]["web_interface"] = {
                    "status": "pass",
                    "message": "Web interface is responding on port 5000"
                }
                logger.info("Web interface is responding on port 5000")
            else:
                self.validation_results["functionality"]["web_interface"] = {
                    "status": "fail",
                    "message": "Web interface is not responding on port 5000"
                }
                logger.warning("Web interface is not responding on port 5000")
                return False
        except Exception as e:
            logger.error(f"Error checking web interface: {e}")
            self.validation_results["functionality"]["web_interface"] = {
                "status": "error",
                "message": f"Error checking web interface: {e}"
            }
            return False
        
        # Check log file
        log_file = "/var/log/autonomous-mower/mower.log"
        
        try:
            if os.path.exists(log_file):
                # Check if log file is being written to
                mtime = os.path.getmtime(log_file)
                if time.time() - mtime < 300:  # Modified in the last 5 minutes
                    self.validation_results["functionality"]["log_file"] = {
                        "status": "pass",
                        "message": f"{log_file} exists and is being updated"
                    }
                    logger.info(f"{log_file} exists and is being updated")
                else:
                    self.validation_results["functionality"]["log_file"] = {
                        "status": "warning",
                        "message": f"{log_file} exists but hasn't been updated recently"
                    }
                    logger.warning(f"{log_file} exists but hasn't been updated recently")
            else:
                self.validation_results["functionality"]["log_file"] = {
                    "status": "fail",
                    "message": f"{log_file} does not exist"
                }
                logger.warning(f"{log_file} does not exist")
                return False
        except Exception as e:
            logger.error(f"Error checking log file: {e}")
            self.validation_results["functionality"]["log_file"] = {
                "status": "error",
                "message": f"Error checking log file: {e}"
            }
        
        # Overall functionality validation result
        functionality_statuses = [
            result["status"] for result in self.validation_results["functionality"].values()
        ]
        
        if "fail" in functionality_statuses:
            logger.warning("Functionality validation failed")
            return False
        elif "error" in functionality_statuses:
            logger.warning("Functionality validation encountered errors")
            return False
        else:
            logger.info("Functionality validation passed")
            return True
    
    def validate_all(self) -> bool:
        """
        Run all validation checks.
        
        Returns:
            True if all checks pass, False otherwise
        """
        logger.info("Starting system validation...")
        
        # Run all validation checks
        hardware_valid = self.validate_hardware()
        software_valid = self.validate_software()
        config_valid = self.validate_configuration()
        functionality_valid = self.validate_functionality()
        
        # Set overall validation result
        if hardware_valid and software_valid and config_valid and functionality_valid:
            self.validation_results["overall"] = {
                "status": "pass",
                "message": "All validation checks passed"
            }
            logger.info("All validation checks passed")
            return True
        else:
            failed_components = []
            if not hardware_valid:
                failed_components.append("hardware")
            if not software_valid:
                failed_components.append("software")
            if not config_valid:
                failed_components.append("configuration")
            if not functionality_valid:
                failed_components.append("functionality")
            
            self.validation_results["overall"] = {
                "status": "fail",
                "message": f"Validation failed for: {', '.join(failed_components)}"
            }
            logger.warning(f"Validation failed for: {', '.join(failed_components)}")
            return False
    
    def print_results(self) -> None:
        """Print validation results to console."""
        print("\n" + "=" * 80)
        print("SYSTEM VALIDATION RESULTS")
        print("=" * 80)
        
        # Print overall result
        overall_status = self.validation_results["overall"]["status"]
        overall_message = self.validation_results["overall"]["message"]
        
        if overall_status == "pass":
            print(f"\n✅ OVERALL: {overall_message}")
        else:
            print(f"\n❌ OVERALL: {overall_message}")
        
        # Print detailed results if verbose
        if self.verbose:
            for category, results in self.validation_results.items():
                if category == "overall":
                    continue
                
                print(f"\n{category.upper()}:")
                print("-" * 40)
                
                for component, result in results.items():
                    status = result["status"]
                    message = result["message"]
                    
                    if status == "pass":
                        print(f"✅ {component}: {message}")
                    elif status == "fail":
                        print(f"❌ {component}: {message}")
                    elif status == "warning":
                        print(f"⚠️ {component}: {message}")
                    else:
                        print(f"❓ {component}: {message}")
        
        print("\n" + "=" * 80)
    
    def save_results(self, output_file: str) -> None:
        """
        Save validation results to a file.
        
        Args:
            output_file: Path to output file
        """
        try:
            with open(output_file, 'w') as f:
                json.dump(self.validation_results, f, indent=2)
            logger.info(f"Validation results saved to {output_file}")
        except Exception as e:
            logger.error(f"Error saving validation results: {e}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="System Validation Script")
    parser.add_argument("--verbose", action="store_true", help="Show detailed validation information")
    parser.add_argument("--config", type=str, help="Specify configuration file path")
    parser.add_argument("--output", type=str, help="Save validation results to file")
    args = parser.parse_args()
    
    # Create validator
    validator = SystemValidator(config_path=args.config, verbose=args.verbose)
    
    # Run validation
    result = validator.validate_all()
    
    # Print results
    validator.print_results()
    
    # Save results if output file specified
    if args.output:
        validator.save_results(args.output)
    
    # Return exit code
    return 0 if result else 1


if __name__ == "__main__":
    sys.exit(main())