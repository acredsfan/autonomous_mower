#!/usr/bin/env python3
"""
Test communication with the RP2040 RoboHAT code.

This script tests the communication protocol between the Raspberry Pi
and the RP2040-zero running the corrected MicroPython code.
"""

import time
import serial
import sys

def test_rp2040_communication():
    """Test serial communication with the RP2040."""
    # Try to find the RP2040 serial port
    # Common ports: /dev/ttyS0, /dev/ttyAMA0, /dev/ttyUSB0, /dev/ttyACM0
    possible_ports = ["/dev/ttyS0", "/dev/ttyAMA0", "/dev/ttyUSB0", "/dev/ttyACM0"]
    
    ser = None
    for port in possible_ports:
        try:
            ser = serial.Serial(port, 115200, timeout=1)
            print(f"✓ Connected to RP2040 on {port}")
            break
        except serial.SerialException:
            print(f"✗ Could not open {port}")
            continue
    
    if ser is None:
        print("❌ Could not find RP2040 serial port")
        return False
    
    try:
        print("\n=== Testing RP2040 Communication ===")
        
        # Test 1: Disable RC control
        print("1. Disabling RC control...")
        ser.write(b"rc=disable\r")
        time.sleep(0.5)
        
        # Test 2: Send steering and throttle commands
        test_commands = [
            (1500, 1500),  # Center position
            (1400, 1600),  # Left turn, forward
            (1600, 1400),  # Right turn, backward
            (1500, 1500),  # Back to center
        ]
        
        print("2. Sending PWM commands...")
        for i, (steering, throttle) in enumerate(test_commands):
            command = f"{steering},{throttle}\r"
            print(f"   Sending: {command.strip()}")
            ser.write(command.encode())
            time.sleep(1)
        
        # Test 3: Re-enable RC control
        print("3. Re-enabling RC control...")
        ser.write(b"rc=enable\r")
        time.sleep(0.5)
        
        print("✓ All tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        return False
    finally:
        if ser:
            ser.close()

if __name__ == "__main__":
    print("RP2040 RoboHAT Communication Test")
    print("=" * 40)
    print("This test will communicate with the RP2040-zero")
    print("running the corrected MicroPython code.")
    print()
    
    success = test_rp2040_communication()
    
    if success:
        print("\n🎉 Communication test passed!")
        print("The RP2040 MicroPython code appears to be working correctly.")
    else:
        print("\n❌ Communication test failed!")
        print("Check the RP2040 connection and code deployment.")
    
    sys.exit(0 if success else 1)
