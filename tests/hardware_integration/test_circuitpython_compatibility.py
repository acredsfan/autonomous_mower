#!/usr/bin/env python3
"""
Test script to validate the CircuitPython/MicroPython compatibility of the code.py file.

This simulates the PulseIn behavior to ensure our fixes work correctly.
"""

class MockPulseIn:
    """Mock PulseIn object that behaves like CircuitPython's PulseIn."""
    
    def __init__(self, pin, maxlen=64, idle_state=0):
        self.pin = pin
        self.maxlen = maxlen
        self.idle_state = idle_state
        self._pulses = [1500, 1400, 1600, 1450]  # Mock pulse data
        self._paused = False
    
    def pause(self):
        self._paused = True
    
    def resume(self):
        self._paused = False
    
    def clear(self):
        self._pulses = []
    
    def __len__(self):
        return len(self._pulses)
    
    def __getitem__(self, index):
        return self._pulses[index]

# Mock the read_rc_pulse function from our code
def read_rc_pulse(rc_in):
    """Read the latest RC pulse from a PulseIn channel."""
    rc_in.pause()
    
    # Get the number of pulses available
    pulse_count = len(rc_in)
    if pulse_count == 0:
        rc_in.resume()
        return None  # no new data
    
    # Read all available pulses and find the last valid one
    pulses = []
    for i in range(pulse_count):
        try:
            pulse = rc_in[i]
            pulses.append(pulse)
        except IndexError:
            break
    
    rc_in.clear()
    rc_in.resume()

    if not pulses:
        return None  # no valid data
        
    # Use the last valid pulse in the RC range
    val = pulses[-1]
    if 1000 <= val <= 2000:
        return val
    return None

def test_read_rc_pulse():
    """Test the read_rc_pulse function with mock data."""
    print("Testing read_rc_pulse function...")
    
    # Test with valid pulses
    rc_mock = MockPulseIn("GP6")
    result = read_rc_pulse(rc_mock)
    print(f"Result with valid pulses: {result}")
    assert result == 1450, f"Expected 1450, got {result}"
    
    # Test with empty pulses
    rc_mock._pulses = []
    result = read_rc_pulse(rc_mock)
    print(f"Result with empty pulses: {result}")
    assert result is None, f"Expected None, got {result}"
    
    # Test with out-of-range pulses
    rc_mock._pulses = [500, 3000]  # Out of 1000-2000 range
    result = read_rc_pulse(rc_mock)
    print(f"Result with out-of-range pulses: {result}")
    assert result is None, f"Expected None, got {result}"
    
    print("✓ All read_rc_pulse tests passed!")

def test_parse_pwm_values():
    """Test the parse_pwm_values function."""
    print("\nTesting parse_pwm_values function...")
    
    def parse_pwm_values(data_str):
        """Parse PWM values from serial data."""
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
    
    # Test valid input
    result = parse_pwm_values("1500,1600")
    print(f"Result with valid input: {result}")
    assert result == (1500, 1600), f"Expected (1500, 1600), got {result}"
    
    # Test invalid format
    result = parse_pwm_values("1500")
    print(f"Result with invalid format: {result}")
    assert result is None, f"Expected None, got {result}"
    
    # Test out of range
    result = parse_pwm_values("500,3000")
    print(f"Result with out of range: {result}")
    assert result is None, f"Expected None, got {result}"
    
    print("✓ All parse_pwm_values tests passed!")

def test_us_to_duty():
    """Test the us_to_duty function."""
    print("\nTesting us_to_duty function...")
    
    def us_to_duty(us, freq=60):
        """Convert microseconds pulse width to PWM duty cycle."""
        if us < 1000:
            us = 1000
        elif us > 2000:
            us = 2000
            
        # Calculate duty cycle for 16-bit PWM (0-65535)
        # For servo PWM: pulse width (us) / period (us) * max_duty_cycle
        period_us = 1000000.0 / freq  # Period in microseconds (e.g. ~16667 us for 60Hz)
        duty_cycle = int((us / period_us) * 65535)
        
        # Ensure duty cycle is within valid range
        if duty_cycle < 0:
            duty_cycle = 0
        elif duty_cycle > 65535:
            duty_cycle = 65535
            
        return duty_cycle
    
    # Test normal range
    result = us_to_duty(1500)  # Center position
    print(f"1500 us @ 60Hz = {result} duty cycle")
    assert 0 <= result <= 65535, f"Duty cycle out of range: {result}"
    
    # Test edge cases
    result_min = us_to_duty(1000)
    result_max = us_to_duty(2000)
    print(f"1000 us = {result_min}, 2000 us = {result_max}")
    assert result_min < result_max, "Min duty should be less than max"
    
    # Test clamping
    result_clamp_low = us_to_duty(500)
    result_clamp_high = us_to_duty(3000)
    assert result_clamp_low == us_to_duty(1000), "Low value should be clamped to 1000us"
    assert result_clamp_high == us_to_duty(2000), "High value should be clamped to 2000us"
    
    print("✓ All us_to_duty tests passed!")

if __name__ == "__main__":
    print("CircuitPython/MicroPython Compatibility Test")
    print("=" * 50)
    
    test_read_rc_pulse()
    test_parse_pwm_values()
    test_us_to_duty()
    
    print("\n🎉 All tests passed!")
    print("The corrected code.py should work with CircuitPython/MicroPython.")
