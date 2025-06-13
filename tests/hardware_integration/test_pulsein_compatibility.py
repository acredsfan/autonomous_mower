#!/usr/bin/env python3
"""
Test PulseIn compatibility and iteration handling for RP2040 MicroPython code.

This test specifically addresses the TypeError: 'PulseIn' object is not iterable
issue by creating mock PulseIn objects and testing various access patterns.
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Import the RP2040 code functions
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'mower', 'robohat_files'))

try:
    from code import read_rc_pulse, parse_pwm_values, us_to_duty
except ImportError as e:
    print(f"Error importing RP2040 code: {e}")
    sys.exit(1)


class MockPulseIn:
    """Mock PulseIn class that simulates CircuitPython/MicroPython PulseIn behavior."""
    
    def __init__(self, pulse_data=None):
        self.pulse_data = pulse_data or []
        self.paused = False
    
    def __len__(self):
        return len(self.pulse_data)
    
    def __getitem__(self, index):
        if index >= len(self.pulse_data):
            raise IndexError("Index out of range")
        return self.pulse_data[index]
    
    def __iter__(self):
        # This should NOT be used in the corrected code
        # If code tries to iterate directly, it should fail in actual hardware
        raise TypeError("'PulseIn' object is not iterable")
    
    def pause(self):
        self.paused = True
    
    def resume(self):
        self.paused = False
    
    def clear(self):
        self.pulse_data.clear()


def test_pulsein_direct_iteration():
    """Test that our code doesn't try to iterate PulseIn directly."""
    print("Testing PulseIn direct iteration handling...")
    
    # This should fail if code tries: [p for p in rc_in]
    mock_pulse = MockPulseIn([1500, 1600, 1400])
    
    try:
        # This would fail if code.py had: [p for p in rc_in]
        list(mock_pulse)  # Direct iteration attempt
        print("ERROR: MockPulseIn allowed direct iteration (this shouldn't happen)")
        return False
    except TypeError as e:
        print(f"✓ Direct iteration correctly fails: {e}")
    
    # But our corrected code should work fine
    try:
        result = read_rc_pulse(mock_pulse)
        print(f"✓ read_rc_pulse works correctly: {result}")
        return True
    except Exception as e:
        print(f"ERROR: read_rc_pulse failed: {e}")
        return False


def test_pulsein_index_access():
    """Test that our code uses index access correctly."""
    print("\nTesting PulseIn index access...")
    
    # Test with valid pulse data
    mock_pulse = MockPulseIn([900, 1500, 1600, 2100])  # Mix of valid/invalid
    
    try:
        result = read_rc_pulse(mock_pulse)
        print(f"✓ Index access works: {result}")
        
        # Should return the last valid pulse (1600)
        if result == 1600:
            print("✓ Correctly returned last valid pulse")
            return True
        else:
            print(f"ERROR: Expected 1600, got {result}")
            return False
    except Exception as e:
        print(f"ERROR: Index access failed: {e}")
        return False


def test_empty_pulsein():
    """Test handling of empty PulseIn."""
    print("\nTesting empty PulseIn handling...")
    
    mock_pulse = MockPulseIn([])
    
    try:
        result = read_rc_pulse(mock_pulse)
        if result is None:
            print("✓ Empty PulseIn correctly returns None")
            return True
        else:
            print(f"ERROR: Expected None, got {result}")
            return False
    except Exception as e:
        print(f"ERROR: Empty PulseIn handling failed: {e}")
        return False


def test_all_invalid_pulses():
    """Test handling of all invalid pulses."""
    print("\nTesting all invalid pulses...")
    
    mock_pulse = MockPulseIn([500, 2500, 3000])  # All out of range
    
    try:
        result = read_rc_pulse(mock_pulse)
        if result is None:
            print("✓ All invalid pulses correctly returns None")
            return True
        else:
            print(f"ERROR: Expected None, got {result}")
            return False
    except Exception as e:
        print(f"ERROR: Invalid pulses handling failed: {e}")
        return False


def main():
    """Run all PulseIn compatibility tests."""
    print("PulseIn Compatibility Test for RP2040 Code")
    print("=" * 50)
    
    tests = [
        test_pulsein_direct_iteration,
        test_pulsein_index_access,
        test_empty_pulsein,
        test_all_invalid_pulses,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"ERROR in {test.__name__}: {e}")
    
    print(f"\n{'='*50}")
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All PulseIn compatibility tests passed!")
        print("The code correctly handles PulseIn objects without direct iteration.")
        return True
    else:
        print("❌ Some tests failed!")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
