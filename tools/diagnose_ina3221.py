#!/usr/bin/env python3

"""
INA3221 Diagnostic Tool for Autonomous Mower

This tool helps diagnose INA3221 power monitoring issues by:
1. Testing sensor connectivity
2. Reading all channels
3. Providing wiring guidance
4. Showing I2C bus status
"""

import sys
import os
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_i2c_devices():
    """Test I2C devices on the bus"""
    print("I2C Bus Scan:")
    print("-" * 40)
    try:
        import board
        import busio
        i2c = busio.I2C(board.SCL, board.SDA)
        
        # Scan for devices
        devices = []
        for addr in range(0x08, 0x78):  # Typical I2C address range
            try:
                i2c.try_lock()
                if i2c.scan()[0:] and addr in i2c.scan():
                    devices.append(f"0x{addr:02x}")
            except:
                pass
            finally:
                try:
                    i2c.unlock()
                except:
                    pass
        
        if devices:
            print(f"Found I2C devices at addresses: {', '.join(devices)}")
            if '0x40' in devices:
                print("✓ INA3221 detected at address 0x40")
            else:
                print("⚠ INA3221 not found at expected address 0x40")
        else:
            print("No I2C devices found")
            
    except Exception as e:
        print(f"Error scanning I2C bus: {e}")

def test_ina3221_sensor():
    """Test the INA3221 sensor specifically"""
    print("\nINA3221 Sensor Test:")
    print("-" * 40)
    
    try:
        from mower.hardware.ina3221 import INA3221Sensor
        
        # Initialize sensor
        print("Initializing INA3221...")
        sensor = INA3221Sensor.init_ina3221()
        
        if not sensor:
            print("✗ Failed to initialize INA3221 sensor")
            return
            
        print("✓ INA3221 sensor initialized successfully")
        print(f"  Sensor type: {type(sensor)}")
        
        # Test all channels multiple times
        print("\nReading all channels (3 samples each):")
        
        for sample in range(3):
            print(f"\nSample {sample + 1}:")
            all_zero = True
            
            for channel in [1, 2, 3]:
                data = INA3221Sensor.read_ina3221(sensor, channel)
                if data:
                    voltage = data.get('bus_voltage', 0)
                    current = data.get('current', 0)
                    shunt_v = data.get('shunt_voltage', 0)
                    
                    print(f"  Channel {channel}: {voltage:6.3f}V  {current:8.3f}A  {shunt_v:8.3f}mV")
                    
                    if voltage > 0.1 or abs(current) > 0.01:
                        all_zero = False
                else:
                    print(f"  Channel {channel}: Error reading data")
            
            if sample == 0:
                if all_zero:
                    print("  ⚠ All channels reading zero - likely no power connections")
                else:
                    print("  ✓ Power detected on at least one channel")
                    
            time.sleep(0.5)
            
    except Exception as e:
        print(f"Error testing INA3221: {e}")
        import traceback
        traceback.print_exc()

def show_wiring_guidance():
    """Show wiring guidance for INA3221"""
    print("\nINA3221 Wiring Guidance:")
    print("=" * 40)
    print("""
The INA3221 has 3 channels, each requiring connections:

Channel 1 (typically main battery):
  • V+ (pin 1) → Battery positive terminal
  • V- (pin 2) → Between battery and load
  • IN+ (pin 3) → Battery positive terminal  
  • IN- (pin 4) → Between battery and load

Channel 2 (typically motor power):
  • V+ (pin 5) → Motor power positive
  • V- (pin 6) → Between motor supply and motors
  • IN+ (pin 7) → Motor power positive
  • IN- (pin 8) → Between motor supply and motors

Channel 3 (typically electronics):
  • V+ (pin 9) → Electronics power positive
  • V- (pin 10) → Between electronics supply and electronics
  • IN+ (pin 11) → Electronics power positive
  • IN- (pin 12) → Between electronics supply and electronics

Common connections:
  • VCC → 3.3V or 5V
  • GND → Ground
  • SDA → GPIO 2 (I2C data)
  • SCL → GPIO 3 (I2C clock)

Expected I2C address: 0x40 (default)
""")

def show_troubleshooting():
    """Show troubleshooting steps"""
    print("\nTroubleshooting Steps:")
    print("=" * 40)
    print("""
1. If no I2C devices found:
   • Check SDA/SCL connections to GPIO 2/3
   • Verify INA3221 power (VCC to 3.3V/5V, GND to ground)
   • Check I2C pullup resistors (usually built into Pi)

2. If INA3221 found but reading zero:
   • Verify power connections to V+/V- pins for each channel
   • Check that IN+/IN- pins are in the current path
   • Ensure the power source is actually on
   • Check for loose connections

3. If readings are unstable:
   • Check for proper ground connections
   • Verify shunt resistor connections
   • Check for electromagnetic interference

4. If only some channels work:
   • Check individual channel wiring
   • Verify the specific power rail is active
   • Check channel enable configuration
""")

def main():
    """Main diagnostic function"""
    print("INA3221 Power Monitor Diagnostic Tool")
    print("=" * 50)
    
    # Test I2C bus
    test_i2c_devices()
    
    # Test INA3221 specifically  
    test_ina3221_sensor()
    
    # Show guidance
    show_wiring_guidance()
    show_troubleshooting()

if __name__ == "__main__":
    main()
