#!/usr/bin/env python3
"""
Minimal test script for sensor data display in the autonomous mower.
"""

import sys
import os
import platform

# Add the project's src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

print("=== Autonomous Mower Sensor Test ===")
print(f"Platform: {platform.system()}")
print(f"Python version: {sys.version}")
print(f"Python path: {sys.path}")

try:
    print("\nImporting sensors...")
    from mower.hardware.tof import VL53L0XSensors
    from mower.hardware.imu import BNO085Sensor

    print("\nInitializing sensors...")
    tof_sensor = VL53L0XSensors()
    imu_sensor = BNO085Sensor()
    print("\nHardware detection:")
    hw_tof = "Available" if tof_sensor.is_hardware_available else "Simulated"
    hw_imu = "Available" if imu_sensor.is_hardware_available else "Simulated"
    print(f"ToF sensors: {hw_tof}")
    print(f"IMU sensor:  {hw_imu}")

    print("\nGetting sensor data...")
    tof_data = tof_sensor.get_distances()
    print(f"ToF distances: {tof_data}")

    heading = imu_sensor.get_heading()
    roll = imu_sensor.get_roll()
    pitch = imu_sensor.get_pitch()

    print(f"IMU heading: {heading:.1f}°")
    print(f"IMU roll: {roll:.1f}°")
    print(f"IMU pitch: {pitch:.1f}°")

    print("\nGetting safety status...")
    safety = imu_sensor.get_safety_status()
    print(f"Safety status: {safety}")

    print("\nTest completed successfully.")
except Exception as e:
    print(f"\nError: {e}")
    import traceback

    traceback.print_exc()
    print("\nTest failed.")
