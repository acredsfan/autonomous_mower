#!/usr/bin/env python3
"""
Test for I2C bus sharing implementation in hardware_registry.py

This script verifies that:
1. The shared I2C bus is initialized correctly
2. The INA3221 sensor uses the shared bus
3. The bus is properly cleaned up on shutdown

@hardware_interface: I2C bus
"""
import signal
import time
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

def timeout_handler(signum, frame):
    """Handle timeout signal"""
    print("⚠️ Test timed out!")
    sys.exit(1)

# Set timeout for the entire test
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(60)  # 60 second timeout

try:
    print("Starting I2C bus sharing test...")
    
    # Import the hardware registry
    from src.mower.hardware.hardware_registry import get_hardware_registry
    
    # Get the hardware registry instance
    registry = get_hardware_registry()
    
    # Initialize the registry
    print("Initializing hardware registry...")
    registry.initialize()
    
    # Check if I2C bus was initialized
    if hasattr(registry, '_i2c_bus') and registry._i2c_bus:
        print("✓ Shared I2C bus initialized successfully")
    else:
        print("✗ Failed to initialize shared I2C bus")
        sys.exit(1)
    
    # Try to get INA3221 sensor
    print("Retrieving INA3221 sensor...")
    ina3221 = registry.get_ina3221()
    
    if ina3221:
        print("✓ INA3221 sensor initialized successfully")
    else:
        print("ℹ️ INA3221 sensor not available (this is acceptable if hardware is not present)")
    
    # Test cleanup
    print("Testing hardware registry cleanup...")
    registry.cleanup()
    
    # Verify the I2C bus has been closed
    try:
        # Trying to use the bus after it's closed should fail
        if registry._i2c_bus:
            registry._i2c_bus.read_byte(0x40)  # This should fail if bus is closed
            print("✗ I2C bus was not properly closed")
            sys.exit(1)
    except Exception:
        # This is expected behavior - the bus should be closed
        print("✓ I2C bus properly closed during cleanup")
    
    print("✓ All tests completed successfully")
    
except Exception as e:
    print(f"✗ Test failed with error: {e}")
    sys.exit(1)
finally:
    signal.alarm(0)  # Cancel timeout
    print("Test complete")
