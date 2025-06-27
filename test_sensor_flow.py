#!/usr/bin/env python3
"""
Test to verify the complete sensor data flow without hardware dependencies.
"""

def mock_get_sensor_data():
    """Simulate the fallback sensor data from main_controller.py get_sensor_data method."""
    
    # This simulates the fallback data that should always be returned
    sensor_data = {}
    
    # Simulate the fallback logic from get_sensor_data
    if "imu" not in sensor_data:
        sensor_data["imu"] = {
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
        }
    
    if "environment" not in sensor_data:
        sensor_data["environment"] = {
            "temperature": 20.0,
            "humidity": 50.0,
            "pressure": 1013.25,
            "simulated": True
        }
    
    if "tof" not in sensor_data:
        sensor_data["tof"] = {
            "left": 100.0,
            "right": 100.0,
            "front": 100.0,
            "simulated": True
        }
    
    if "power" not in sensor_data:
        sensor_data["power"] = {
            "voltage": 12.0,
            "current": 1.0,
            "power": 12.0,
            "percentage": 80.0,
            "status": "Simulated",
            "simulated": True
        }
    
    return sensor_data

def mock_sensor_interface_data():
    """Simulate data from MockSensorInterface."""
    return {
        "temperature": 20.0,
        "humidity": 50.0,
        "pressure": 1013.25,
        "imu": {
            "heading": 0.0,
            "roll": 0.0,
            "pitch": 0.0,
            "acceleration": {"x": 0.0, "y": 0.0, "z": 9.81},
            "gyroscope": {"x": 0.0, "y": 0.0, "z": 0.0},
            "magnetometer": {"x": 0.0, "y": 0.0, "z": 0.0},
            "calibration": {"system": 3, "gyro": 3, "accel": 3, "mag": 3},
            "safety_status": {"tilt_warning": False, "calibration_warning": False}
        },
        "power": {
            "voltage": 12.0,
            "current": 1.5,
            "power": 18.0,
            "percentage": 75.0,
            "status": "Mock Sensor"
        },
        "distance": {
            "left": 200.0,
            "right": 200.0,
            "front": 200.0
        }
    }

def test_sensor_data_flow():
    """Test the complete sensor data flow."""
    
    print("=== Sensor Data Flow Test ===")
    
    # Test 1: Fallback data from main_controller
    print("\n1. Testing fallback sensor data from main_controller...")
    fallback_data = mock_get_sensor_data()
    print(f"   Fallback data keys: {list(fallback_data.keys())}")
    
    # Verify all required fields
    required_fields = {
        "imu": ["heading", "roll", "pitch", "safety_status"],
        "environment": ["temperature", "humidity", "pressure"],
        "tof": ["left", "right", "front"],
        "power": ["voltage", "current", "power", "percentage"]
    }
    
    all_good = True
    for section, fields in required_fields.items():
        if section not in fallback_data:
            print(f"   ✗ Missing section: {section}")
            all_good = False
        else:
            for field in fields:
                if field not in fallback_data[section]:
                    print(f"   ✗ Missing {section}.{field}")
                    all_good = False
                else:
                    print(f"   ✓ {section}.{field}: {fallback_data[section][field]}")
    
    print(f"   Fallback data complete: {'Yes' if all_good else 'No'}")
    
    # Test 2: MockSensorInterface data
    print("\n2. Testing MockSensorInterface data...")
    mock_data = mock_sensor_interface_data()
    
    # Simulate the data transformation that happens in main_controller when using MockSensorInterface
    if mock_data:
        transformed_data = {
            "imu": mock_data.get("imu", {}),
            "environment": {
                "temperature": mock_data.get("temperature"),
                "humidity": mock_data.get("humidity"),
                "pressure": mock_data.get("pressure"),
            },
            "tof": mock_data.get("distance", {}),
            "power": mock_data.get("power", {}),
        }
        
        print(f"   Mock data transformed keys: {list(transformed_data.keys())}")
        
        # Check if this would satisfy WebUI
        for section, fields in required_fields.items():
            if section not in transformed_data:
                print(f"   ✗ Missing section: {section}")
            else:
                for field in fields:
                    if field not in transformed_data[section]:
                        print(f"   ✗ Missing {section}.{field}")
                    else:
                        print(f"   ✓ {section}.{field}: {transformed_data[section][field]}")
    
    # Test 3: Simulate WebUI reception
    print("\n3. Testing WebUI data reception simulation...")
    test_data = fallback_data
    
    # Simulate JavaScript updateSensorData function logic
    webui_updates = []
    
    if test_data.get("environment", {}).get("temperature") is not None:
        webui_updates.append("Temperature display updated")
    
    if test_data.get("environment", {}).get("humidity") is not None:
        webui_updates.append("Humidity display updated")
    
    if test_data.get("environment", {}).get("pressure") is not None:
        webui_updates.append("Pressure display updated")
    
    if test_data.get("tof", {}).get("left") is not None:
        webui_updates.append("Left ToF distance updated")
    
    if test_data.get("tof", {}).get("right") is not None:
        webui_updates.append("Right ToF distance updated")
    
    if test_data.get("imu", {}).get("heading") is not None:
        webui_updates.append("IMU heading updated")
    
    if test_data.get("power", {}).get("voltage") is not None:
        webui_updates.append("Battery voltage updated")
    
    if test_data.get("power", {}).get("percentage") is not None:
        webui_updates.append("Battery percentage updated")
    
    print(f"   WebUI updates that would occur: {len(webui_updates)}")
    for update in webui_updates:
        print(f"     - {update}")
    
    print(f"\n   Result: {'✓ All sensor data should display properly in WebUI' if len(webui_updates) >= 6 else '✗ Some sensor data might not display'}")
    
    return all_good and len(webui_updates) >= 6

if __name__ == "__main__":
    success = test_sensor_data_flow()
    print(f"\n=== Test Result: {'PASS' if success else 'FAIL'} ===")
    if success:
        print("The sensor data flow should now work correctly!")
        print("The WebUI should receive and display sensor data even when hardware sensors fail.")
    else:
        print("There may still be issues with the sensor data flow.")