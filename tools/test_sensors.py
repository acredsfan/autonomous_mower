#!/usr/bin/env python3
"""
Sensor Test Utility for Autonomous Mower

This script tests the sensor functionality without running the full mower system.
It helps verify that sensors are working correctly and displaying data as expected.
"""

import json
import os
import platform
import sys
import time

from src.mower.hardware.imu import BNO085Sensor
from src.mower.hardware.tof import VL53L0XSensors

# Add the project directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def print_sensor_data(sensor_data):
    """Print formatted sensor data."""
    print("\033[2J\033[H")  # Clear screen
    print("=== Autonomous Mower Sensor Test ===")
    print(f"Platform: {platform.system()}")
    # Check if running on hardware or simulation
    hw_check = platform.system() == "Linux"
    print(f"Running on hardware: {'Yes' if hw_check else 'No'}")

    print("\n--- IMU Data ---")
    if "heading" in sensor_data["imu"]:
        print(f"Heading: {sensor_data['imu']['heading']:.1f}°")
        print(f"Roll:    {sensor_data['imu']['roll']:.1f}°")
        print(f"Pitch:   {sensor_data['imu']['pitch']:.1f}°")
    else:
        print("IMU data not available")

    print("\n--- Distance Sensors ---")
    if "tof" in sensor_data and sensor_data["tof"]:
        tof = sensor_data["tof"]
        print(f"Left:  {tof.get('left', 'N/A'):.1f} mm")
        print(f"Right: {tof.get('right', 'N/A'):.1f} mm")
    else:
        print("Distance sensor data not available")

    print("\n--- Environment ---")
    if "environment" in sensor_data:
        env = sensor_data["environment"]
        print(f"Temperature: {env.get('temperature', 'N/A'):.1f}°C")
        print(f"Humidity:    {env.get('humidity', 'N/A'):.1f}%")
        print(f"Pressure:    {env.get('pressure', 'N/A'):.1f} hPa")
    else:
        print("Environmental data not available")

    print("\n--- Safety Status ---")
    if "safety_status" in sensor_data["imu"]:
        safety = sensor_data["imu"]["safety_status"]
        for status, value in safety.items():
            status_text = status.replace("_", " ").title()
            status_indicator = "⚠️ WARNING" if value else "✓ OK"
            print(f"{status_text}: {status_indicator}")
    else:
        print("Safety data not available")


def main():
    """Main function for testing sensors."""
    # Initialize sensors
    print("Initializing sensors...")
    tof_sensor = VL53L0XSensors()
    imu_sensor = BNO085Sensor()

    try:
        while True:
            # Get sensor data
            heading = imu_sensor.get_heading()
            roll = imu_sensor.get_roll()
            pitch = imu_sensor.get_pitch()
            safety_status = imu_sensor.get_safety_status()
            distances = tof_sensor.get_distances()

            # Create data structure
            sensor_data = {
                "imu": {
                    "heading": heading,
                    "roll": roll,
                    "pitch": pitch,
                    "safety_status": safety_status,
                },
                "tof": distances,
                "environment": {
                    "temperature": 22.5,  # Simulated value
                    "humidity": 55.3,  # Simulated value
                    "pressure": 1013.2,  # Simulated value
                },
            }

            # Display data
            print_sensor_data(sensor_data)

            # Display raw JSON (for debugging)
            print("\n--- Raw JSON Data ---")
            print(json.dumps(sensor_data, indent=2))

            time.sleep(1)
    except KeyboardInterrupt:
        print("\nSensor test stopped")


if __name__ == "__main__":
    main()
