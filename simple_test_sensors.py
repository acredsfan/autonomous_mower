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

    print(
        f"\nHardware detection: ToF={tof_sensor.is_hardware_available}, IMU={imu_sensor.is_hardware_available}"
    )

    print("\nGetting sensor data...")
    tof_data = tof_sensor.get_distances()
    print(f"ToF distances: {tof_data}")

    heading = imu_sensor.get_heading()
    roll = imu_sensor.get_roll()
    pitch = imu_sensor.get_pitch()

    print(f"IMU heading: {heading:.1f}°")
    print(f"IMU roll: {roll:.1f}°")
    print(f"IMU pitch: {pitch:.1f}°")

except Exception as e:
    print(f"\nERROR: {e}")
    import traceback

    traceback.print_exc()
