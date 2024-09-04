import smbus2
import time

# Create an instance of the I2C bus
bus = smbus2.SMBus(1)  # Use the appropriate bus number (usually 1 for Raspberry Pi)

def scan_i2c_bus():
    print("Scanning I2C bus for devices...")
    devices = []
    for address in range(0x03, 0x78):  # Scan all valid I2C addresses
        try:
            bus.write_quick(address)
            print(f"Device found at address: {hex(address)}")
            devices.append(address)
        except Exception:
            pass  # No device at this address
    if not devices:
        print("No I2C devices found.")
    return devices

# Perform the scan
scan_i2c_bus()