#!/usr/bin/env python3
"""
Hardware integration test for the blade controller.

This test interacts with the actual hardware (IBT-4 driver via GPIO24 and GPIO25)
to verify that the blade controller works correctly with the physical hardware.

⚠️  WARNING: This test controls real hardware! Only run when:
1. The IBT-4 driver is properly connected to GPIO24 and GPIO25
2. The blade motor is safely disconnected or secured
3. You are prepared for actual motor movement

@hardware_interface IBT-4 motor driver
@gpio_pin_usage 24 (BCM) - IBT-4 IN1 input
@gpio_pin_usage 25 (BCM) - IBT-4 IN2 input
"""

import time
import logging
from mower.hardware.blade_controller import BladeController

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_blade_controller_hardware_basic():
    """Test basic blade controller hardware functionality."""
    logger.info("=== Starting Blade Controller Hardware Test ===")
    logger.info("⚠️  WARNING: This test controls real hardware!")
    logger.info("Make sure the blade motor is safely disconnected!")
    
    # Wait a few seconds to allow cancellation if needed
    logger.info("Starting test in 3 seconds... (Press Ctrl+C to abort)")
    time.sleep(3)
    
    blade_controller = None
    try:
        # Initialize blade controller
        logger.info("Initializing blade controller...")
        blade_controller = BladeController()
        logger.info("✓ Blade controller initialized successfully")
        
        # Test initial state
        state = blade_controller.get_state()
        logger.info(f"Initial state: {state}")
        assert not blade_controller.is_enabled(), "Blade should be disabled initially"
        assert not blade_controller.is_running(), "Blade should not be running initially"
        assert blade_controller.get_speed() == 0.0, "Initial speed should be 0"
        
        # Test enable/disable
        logger.info("Testing enable/disable...")
        assert blade_controller.enable(), "Enable should succeed"
        assert blade_controller.is_enabled(), "Blade should be enabled"
        logger.info("✓ Enable/disable test passed")
        
        # Test forward direction at low speed (10%)
        logger.info("Testing forward direction at 10% speed for 2 seconds...")
        assert blade_controller.set_direction(0), "Set forward direction should succeed"
        assert blade_controller.set_speed(0.1), "Set 10% speed should succeed"
        assert blade_controller.is_running(), "Blade should be running"
        assert blade_controller.get_speed() == 0.1, "Speed should be 0.1"
        time.sleep(2)
        logger.info("✓ Forward direction test completed")
        
        # Stop blade
        logger.info("Stopping blade...")
        assert blade_controller.set_speed(0.0), "Stop should succeed"
        assert not blade_controller.is_running(), "Blade should not be running after stop"
        time.sleep(1)
        logger.info("✓ Stop test passed")
        
        # Test reverse direction at low speed (10%)
        logger.info("Testing reverse direction at 10% speed for 2 seconds...")
        assert blade_controller.set_direction(1), "Set reverse direction should succeed"
        assert blade_controller.set_speed(0.1), "Set 10% speed should succeed"
        assert blade_controller.is_running(), "Blade should be running"
        time.sleep(2)
        logger.info("✓ Reverse direction test completed")
        
        # Stop blade
        logger.info("Stopping blade...")
        assert blade_controller.set_speed(0.0), "Stop should succeed"
        time.sleep(1)
        
        # Test convenience methods
        logger.info("Testing convenience methods...")
        assert blade_controller.start(0.15), "start() method should succeed"
        assert blade_controller.is_running(), "Blade should be running after start()"
        time.sleep(1)
        assert blade_controller.stop(), "stop() method should succeed"
        assert not blade_controller.is_running(), "Blade should not be running after stop()"
        logger.info("✓ Convenience methods test passed")
        
        # Test disable
        logger.info("Testing disable...")
        assert blade_controller.disable(), "Disable should succeed"
        assert not blade_controller.is_enabled(), "Blade should be disabled"
        logger.info("✓ Disable test passed")
        
        logger.info("=== All tests passed! ===")
        
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        raise
    finally:
        # Cleanup
        if blade_controller:
            logger.info("Cleaning up...")
            blade_controller.cleanup()
            logger.info("✓ Cleanup completed")


def test_blade_controller_safety():
    """Test blade controller safety features."""
    logger.info("=== Testing Blade Controller Safety Features ===")
    
    blade_controller = None
    try:
        blade_controller = BladeController()
        
        # Test that speed cannot be set when disabled
        logger.info("Testing safety: speed setting when disabled...")
        assert not blade_controller.is_enabled(), "Should start disabled"
        assert not blade_controller.set_speed(0.5), "Should not allow speed > 0 when disabled"
        assert blade_controller.get_speed() == 0.0, "Speed should remain 0"
        logger.info("✓ Safety test passed: cannot set speed when disabled")
        
        # Test invalid speed values
        logger.info("Testing invalid speed values...")
        blade_controller.enable()
        assert not blade_controller.set_speed(-0.1), "Should reject negative speed"
        assert not blade_controller.set_speed(1.1), "Should reject speed > 1.0"
        assert blade_controller.get_speed() == 0.0, "Speed should remain 0 after invalid inputs"
        logger.info("✓ Invalid speed test passed")
        
        # Test invalid direction values
        logger.info("Testing invalid direction values...")
        assert not blade_controller.set_direction(2), "Should reject invalid direction"
        assert not blade_controller.set_direction(-1), "Should reject negative direction"
        assert blade_controller.get_direction() == 0, "Direction should remain 0"
        logger.info("✓ Invalid direction test passed")
        
        logger.info("=== Safety tests passed! ===")
        
    except Exception as e:
        logger.error(f"Safety test failed with error: {e}")
        raise
    finally:
        if blade_controller:
            blade_controller.cleanup()


if __name__ == "__main__":
    print("IBT-4 Blade Controller Hardware Integration Test")
    print("=" * 50)
    print("This test will control actual hardware connected to GPIO pins 24 and 25.")
    print("Make sure the IBT-4 driver is connected and the blade motor is safely secured.")
    print()
    
    response = input("Do you want to continue? (yes/no): ").lower().strip()
    if response in ['yes', 'y']:
        test_blade_controller_hardware_basic()
        test_blade_controller_safety()
        print("\n✓ All hardware integration tests completed successfully!")
    else:
        print("Test cancelled by user.")
