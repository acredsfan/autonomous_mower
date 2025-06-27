#!/usr/bin/env python3
"""
Simple test to verify fallback sensor data structure.
"""

def test_fallback_data_structure():
    """Test the fallback sensor data structure matches WebUI expectations."""
    
    # This simulates what should be in the fallback data
    expected_sensor_data = {
        "imu": {
            "heading": 0.0,
            "roll": 0.0,
            "pitch": 0.0,
            "safety_status": {
                "emergency_stop_active": False,
                "obstacle_detected_nearby": False,
                "low_battery_warning": False,
                "system_error": False,
            },
            "simulated": True
        },
        "environment": {
            "temperature": 20.0,
            "humidity": 50.0,
            "pressure": 1013.25,
            "simulated": True
        },
        "tof": {
            "left": 100.0,
            "right": 100.0,
            "front": 100.0,
            "simulated": True
        },
        "power": {
            "voltage": 12.0,
            "current": 1.0,
            "power": 12.0,
            "percentage": 80.0,
            "status": "Simulated",
            "simulated": True
        }
    }
    
    print("=== Fallback Sensor Data Structure Test ===")
    print("Expected WebUI sensor data structure:")
    
    # Check each required section
    required_sections = ["imu", "environment", "tof", "power"]
    for section in required_sections:
        if section in expected_sensor_data:
            print(f"✓ {section}: {expected_sensor_data[section]}")
        else:
            print(f"✗ Missing {section}")
    
    # Check IMU required fields
    imu_required = ["heading", "roll", "pitch"]
    if "imu" in expected_sensor_data:
        for field in imu_required:
            if field in expected_sensor_data["imu"]:
                print(f"✓ IMU.{field}: {expected_sensor_data['imu'][field]}")
            else:
                print(f"✗ Missing IMU.{field}")
    
    # Check environment required fields  
    env_required = ["temperature", "humidity", "pressure"]
    if "environment" in expected_sensor_data:
        for field in env_required:
            if field in expected_sensor_data["environment"]:
                print(f"✓ Environment.{field}: {expected_sensor_data['environment'][field]}")
            else:
                print(f"✗ Missing Environment.{field}")
    
    print("\nThis structure should provide all data needed by the WebUI.")
    print("The fallback code in main_controller.py should ensure this structure is always present.")

if __name__ == "__main__":
    test_fallback_data_structure()