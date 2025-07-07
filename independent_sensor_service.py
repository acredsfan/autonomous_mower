#!/usr/bin/env python3
"""
Independent sensor service for autonomous mower.

This service provides a backup mechanism for sensor data collection
that operates independently of the main ResourceManager. It directly
initializes sensors without the complex ResourceManager context.

@author: GitHub Copilot
@date: 2025-01-07
"""

import json
import signal
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

# Add src to path for imports
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root / "src"))

from mower.hardware.sensor_interface import EnhancedSensorInterface
from mower.utilities.logger_config import LoggerConfigInfo

# Initialize logger
logger = LoggerConfigInfo.get_logger(__name__)


class IndependentSensorService:
    """
    Independent sensor data collection service.
    
    This service bypasses the ResourceManager complexity and directly
    initializes sensors for data collection. Useful when the main
    controller has initialization issues.
    """
    
    def __init__(self):
        """Initialize the independent sensor service."""
        self.sensor_interface: Optional[EnhancedSensorInterface] = None
        self.running = False
        self.shared_data_file = Path("/tmp/mower_sensor_data.json")
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _signal_handler(self, signum: int, frame) -> None:
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        
    def initialize_sensors(self) -> bool:
        """
        Initialize sensors directly without ResourceManager.
        
        Returns:
            bool: True if sensors initialized successfully
        """
        try:
            logger.info("Initializing sensor interface...")
            
            # Set timeout for sensor initialization
            def timeout_handler(signum, frame):
                raise TimeoutError("Sensor initialization timed out")
                
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(30)  # 30-second timeout
            
            try:
                # Create sensor interface directly
                self.sensor_interface = EnhancedSensorInterface()
                
                # Test sensor access
                logger.info("Testing sensor interface...")
                sensor_data = self.sensor_interface.get_sensor_data()
                
                if sensor_data:
                    logger.info("Sensor interface initialized successfully")
                    logger.info(f"Available sensors: {list(sensor_data.keys())}")
                    return True
                else:
                    logger.error("Sensor interface returned no data")
                    return False
                    
            except Exception as e:
                logger.error(f"Sensor initialization failed: {e}")
                return False
            finally:
                signal.alarm(0)  # Cancel timeout
                
        except TimeoutError:
            logger.error("Sensor initialization timed out after 30 seconds")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during sensor initialization: {e}")
            return False
            
    def collect_and_share_data(self) -> None:
        """
        Main data collection loop.
        
        Collects sensor data and writes to shared file for web UI.
        """
        if not self.sensor_interface:
            logger.error("Sensor interface not initialized")
            return
            
        logger.info("Starting sensor data collection loop...")
        self.running = True
        
        while self.running:
            try:
                # Collect sensor data
                sensor_data = self.sensor_interface.get_sensor_data()
                
                if sensor_data:
                    # Add timestamp
                    sensor_data['timestamp'] = time.time()
                    
                    # Write to shared file atomically
                    temp_file = self.shared_data_file.with_suffix('.tmp')
                    with temp_file.open('w') as f:
                        json.dump(sensor_data, f, indent=2)
                    temp_file.replace(self.shared_data_file)
                    
                    logger.debug(f"Updated sensor data: {len(sensor_data)} keys")
                else:
                    logger.warning("No sensor data available")
                    
            except Exception as e:
                logger.error(f"Error collecting sensor data: {e}")
                
            # Sleep for 2 seconds between collections
            time.sleep(2.0)
            
        logger.info("Sensor data collection stopped")
        
    def cleanup(self) -> None:
        """Clean up resources."""
        logger.info("Cleaning up independent sensor service...")
        
        if self.sensor_interface:
            try:
                # Sensor interface cleanup if needed
                pass
            except Exception as e:
                logger.error(f"Error cleaning up sensor interface: {e}")
                
        logger.info("Independent sensor service cleanup complete")
        
    def run(self) -> int:
        """
        Run the independent sensor service.
        
        Returns:
            int: Exit code (0 for success)
        """
        logger.info("Starting independent sensor service...")
        
        try:
            # Initialize sensors
            if not self.initialize_sensors():
                logger.error("Failed to initialize sensors")
                return 1
                
            # Start data collection
            self.collect_and_share_data()
            
        except KeyboardInterrupt:
            logger.info("Service interrupted by user")
        except Exception as e:
            logger.error(f"Unexpected error in service: {e}")
            return 1
        finally:
            self.cleanup()
            
        logger.info("Independent sensor service finished")
        return 0


def main() -> int:
    """Main entry point."""
    service = IndependentSensorService()
    return service.run()


if __name__ == "__main__":
    # Set up timeout for script execution
    def timeout_handler(signum, frame):
        print("Script timed out after 30 seconds")
        sys.exit(0)
        
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(30)
    
    try:
        exit_code = main()
        sys.exit(exit_code)
    finally:
        signal.alarm(0)
