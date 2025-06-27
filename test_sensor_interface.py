#!/usr/bin/env python3
"""
Test script to isolate sensor interface initialization issues.
"""

import os
import sys
import logging
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mower.hardware.sensor_interface import get_sensor_interface
from mower.utilities.logger_config import LoggerConfigInfo

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = LoggerConfigInfo.get_logger(__name__)

def test_sensor_interface():
    """Test sensor interface initialization."""
    print("=== Sensor Interface Test ===")
    
    # Check current working directory
    print(f"Current working directory: {os.getcwd()}")
    
    # Check if .env file exists
    env_file = Path(".env")
    print(f".env file exists: {env_file.exists()}")
    if env_file.exists():
        print(f".env file path: {env_file.absolute()}")
    
    # Check some environment variables
    print(f"USE_SIMULATION: {os.getenv('USE_SIMULATION', 'not set')}")
    print(f"LOG_LEVEL: {os.getenv('LOG_LEVEL', 'not set')}")
    
    print("\n--- Attempting to create sensor interface ---")
    try:
        sensor_interface = get_sensor_interface()
        if sensor_interface:
            print(f"SUCCESS: Sensor interface created: {sensor_interface}")
            
            # Try to get sensor data
            print("\n--- Testing sensor data retrieval ---")
            try:
                sensor_data = sensor_interface.get_sensor_data()
                print(f"Sensor data: {sensor_data}")
            except Exception as e:
                print(f"Error getting sensor data: {e}")
                
        else:
            print("FAILED: Sensor interface returned None")
            
    except Exception as e:
        print(f"EXCEPTION: Failed to create sensor interface: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_sensor_interface()