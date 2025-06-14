#!/usr/bin/env python3
"""
Test script for RoboHAT MM1 communication after firmware update.
This script tests the Donkeycar-based firmware communication protocol.
"""

import serial
import time
import sys

def test_robohat_communication():
    """Test communication with the updated RoboHAT MM1 firmware."""
    print("=== RoboHAT MM1 Firmware Communication Test ===")
    print("Testing updated Donkeycar-based firmware...")
    
    try:
        with serial.Serial('/dev/ttyACM1', 115200, timeout=3) as ser:
            print("✓ Connected to /dev/ttyACM1")
            
            # Clear buffers
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            time.sleep(1)
            
            # Test 1: Send status command
            print("\n1. Testing status command...")
            ser.write(b'status\r')
            time.sleep(0.5)
            
            if ser.in_waiting:
                response = ser.read(ser.in_waiting)
                print(f"   Response: {response.decode('utf-8', errors='ignore')}")
            else:
                print("   No response to status command")
            
            # Test 2: Disable RC control
            print("\n2. Testing RC disable...")
            ser.write(b'rc=disable\r')
            time.sleep(0.5)
            
            if ser.in_waiting:
                response = ser.read(ser.in_waiting)
                print(f"   Response: {response.decode('utf-8', errors='ignore')}")
            else:
                print("   No response to rc=disable")
            
            # Test 3: Send PWM commands
            print("\n3. Testing PWM commands...")
            test_commands = [
                (b'1500,1500\r', "Neutral position"),
                (b'1600,1500\r', "Turn right"),
                (b'1500,1600\r', "Move forward"),
                (b'1400,1500\r', "Turn left"),
                (b'1500,1400\r', "Move backward"),
                (b'1500,1500\r', "Return to neutral")
            ]
            
            for cmd, description in test_commands:
                print(f"   Sending: {cmd.decode()} - {description}")
                ser.write(cmd)
                time.sleep(1)
                
                if ser.in_waiting:
                    response = ser.read(ser.in_waiting)
                    print(f"   Response: {response.decode('utf-8', errors='ignore')}")
            
            # Test 4: Re-enable RC control
            print("\n4. Re-enabling RC control...")
            ser.write(b'rc=enable\r')
            time.sleep(0.5)
            
            if ser.in_waiting:
                response = ser.read(ser.in_waiting)
                print(f"   Response: {response.decode('utf-8', errors='ignore')}")
            
            print("\n✓ Communication test completed successfully!")
            print("\nIf you saw responses above, the firmware is working correctly.")
            print("If no responses, the firmware may need to be updated manually.")
            
            return True
            
    except serial.SerialException as e:
        print(f"❌ Serial communication error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_robohat_communication()
    sys.exit(0 if success else 1)
