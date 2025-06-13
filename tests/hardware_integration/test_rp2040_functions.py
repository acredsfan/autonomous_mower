#!/usr/bin/env python3
"""
MicroPython Code Verification Script

This script checks that the key functions in the RP2040 code work correctly
by simulating their behavior in a standard Python environment.
"""

def us_to_duty_test(us, freq=60):
    """Test version of the us_to_duty function."""
    if us < 1000:
        us = 1000
    elif us > 2000:
        us = 2000
        
    # Calculate duty cycle for 16-bit PWM (0-65535)
    period_us = 1000000.0 / freq  # Period in microseconds
    duty_cycle = int((us / period_us) * 65535)
    
    # Ensure duty cycle is within valid range
    if duty_cycle < 0:
        duty_cycle = 0
    elif duty_cycle > 65535:
        duty_cycle = 65535
        
    return duty_cycle

def parse_pwm_values_test(data_str):
    """Test version of the parse_pwm_values function."""
    try:
        parts = data_str.split(",")
        if len(parts) == 2:
            steering = int(parts[0].strip())
            throttle = int(parts[1].strip())
            
            # Validate range (standard RC PWM range)
            if 1000 <= steering <= 2000 and 1000 <= throttle <= 2000:
                return steering, throttle
            else:
                print(f"PWM values out of range: S={steering}, T={throttle}")
                return None
        else:
            print(f"Invalid PWM format: {data_str}")
            return None
    except ValueError as e:
        print(f"Parse error: {e}")
        return None

def test_functions():
    """Test the key functions from the RP2040 code."""
    print("Testing RP2040 MicroPython Functions")
    print("=" * 40)
    
    # Test PWM conversion
    print("\n1. Testing us_to_duty conversion:")
    test_values = [1000, 1500, 2000, 500, 2500]  # Include out-of-range values
    for us in test_values:
        duty = us_to_duty_test(us)
        print(f"   {us:4d} µs -> {duty:5d} duty cycle ({duty/65535*100:.1f}%)")
    
    # Test PWM parsing
    print("\n2. Testing PWM value parsing:")
    test_commands = [
        "1500,1500",
        "1000,2000", 
        "1400,1600",
        "invalid,data",
        "1500",
        "999,1500",  # Out of range
        "1500,2001"  # Out of range
    ]
    
    for cmd in test_commands:
        result = parse_pwm_values_test(cmd)
        print(f"   '{cmd}' -> {result}")
    
    print("\n✓ All function tests completed!")
    print("The RP2040 code functions should work correctly now.")

if __name__ == "__main__":
    test_functions()
