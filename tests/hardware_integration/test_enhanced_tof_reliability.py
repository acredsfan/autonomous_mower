#!/usr/bin/env python3
"""
Enhanced ToF sensor reliability test script.

This script tests the improved ToF sensor reading reliability with:
- Enhanced retry mechanisms
- Exponential backoff
- I2C bus recovery
- Better error handling

Run for 60 seconds maximum with timeout safety.
"""

import signal
import sys
import time
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from mower.hardware.sensor_interface import EnhancedSensorInterface
from mower.utilities.logger_config import LoggerConfigInfo

# Initialize logger
logger = LoggerConfigInfo.get_logger(__name__)

def timeout_handler(signum, frame):
    """Handle timeout signal."""
    print("\nTest timed out after 60 seconds")
    print("=== Enhanced ToF Reliability Test Complete ===")
    sys.exit(0)

def test_enhanced_tof_reliability():
    """Test enhanced ToF sensor reliability improvements."""
    print("=== Enhanced ToF Sensor Reliability Test ===")
    print("Testing improved error handling, retry mechanisms, and recovery")
    print("Expected: Reduced error rates compared to basic implementation")
    print()
    
    # Setup timeout
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(60)  # 60-second timeout
    
    try:
        # Initialize enhanced sensor interface
        print("Initializing Enhanced Sensor Interface...")
        interface = EnhancedSensorInterface()
        
        # Check current environment variables
        max_retries = int(os.getenv("TOF_READ_RETRY_COUNT", 5))
        retry_delay = float(os.getenv("TOF_READ_RETRY_DELAY", 0.02))
        bus_recovery = os.getenv("TOF_BUS_RECOVERY_ENABLED", "True").lower() == "true"
        
        print(f"Current ToF reliability settings:")
        print(f"  TOF_READ_RETRY_COUNT: {max_retries}")
        print(f"  TOF_READ_RETRY_DELAY: {retry_delay}s") 
        print(f"  TOF_BUS_RECOVERY_ENABLED: {bus_recovery}")
        print()
        
        # Track detailed statistics
        total_readings = 0
        successful_readings = 0
        left_errors = 0
        right_errors = 0
        both_errors = 0
        recovery_attempts = 0
        
        print("Taking measurements with enhanced reliability (60 seconds max)...")
        print("Timestamp | Left (mm) | Right (mm) | Success Rate | Notes")
        print("-" * 70)
        
        start_time = time.time()
        last_stats_time = start_time
        
        while time.time() - start_time < 60:  # Run for max 60 seconds
            try:
                # Get sensor data using enhanced interface
                sensor_data = interface.get_sensor_data()
                total_readings += 1
                
                # Extract ToF data if available
                tof_data = sensor_data.get("tof", {})
                left_val = tof_data.get("left", "N/A")
                right_val = tof_data.get("right", "N/A")
                
                # Convert None to "ERR" for display
                left_str = f"{left_val:4d}" if left_val not in [None, "N/A"] else " ERR"
                right_str = f"{right_val:4d}" if right_val not in [None, "N/A"] else " ERR"
                
                # Track error statistics
                left_error = left_val in [None, "N/A"]
                right_error = right_val in [None, "N/A"]
                
                if left_error and right_error:
                    both_errors += 1
                elif left_error:
                    left_errors += 1
                elif right_error:
                    right_errors += 1
                else:
                    successful_readings += 1
                
                # Calculate success rate
                if total_readings > 0:
                    success_rate = (successful_readings / total_readings) * 100
                else:
                    success_rate = 0
                
                # Display current reading
                timestamp = time.strftime("%H:%M:%S")
                notes = []
                
                if left_val not in [None, "N/A"] and left_val > 2000:
                    notes.append(f"Left:{left_val}mm>2m")
                if right_val not in [None, "N/A"] and right_val > 2000:
                    notes.append(f"Right:{right_val}mm>2m")
                if left_error and right_error:
                    notes.append("Both failed")
                elif left_error or right_error:
                    notes.append("Partial success")
                
                note_str = " | ".join(notes) if notes else "OK"
                
                print(f"{timestamp} | {left_str:8s} | {right_str:9s} | {success_rate:6.1f}% | {note_str}")
                
                # Print detailed statistics every 15 seconds
                current_time = time.time()
                if current_time - last_stats_time >= 15:
                    print(f"\n--- Statistics after {total_readings} readings ---")
                    print(f"Successful readings: {successful_readings} ({success_rate:.1f}%)")
                    print(f"Left sensor errors: {left_errors}")
                    print(f"Right sensor errors: {right_errors}")
                    print(f"Both sensors failed: {both_errors}")
                    total_errors = left_errors + right_errors + (both_errors * 2)
                    if total_readings > 0:
                        error_rate = (total_errors / (total_readings * 2)) * 100
                        print(f"Overall error rate: {error_rate:.1f}%")
                    print()
                    last_stats_time = current_time
                
                time.sleep(1.0)  # Read every second
                
            except KeyboardInterrupt:
                raise
            except Exception as e:
                logger.error(f"Test iteration failed: {e}")
                total_readings += 1
                both_errors += 1
                
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        print(f"\nTest failed: {e}")
    finally:
        # Cancel timeout
        signal.alarm(0)
        
        # Final statistics
        print("\n=== Final Test Results ===")
        print(f"Total readings attempted: {total_readings}")
        print(f"Successful readings: {successful_readings}")
        print(f"Left sensor errors: {left_errors}")
        print(f"Right sensor errors: {right_errors}")
        print(f"Both sensors failed: {both_errors}")
        
        if total_readings > 0:
            success_rate = (successful_readings / total_readings) * 100
            total_errors = left_errors + right_errors + (both_errors * 2)
            error_rate = (total_errors / (total_readings * 2)) * 100
            
            print(f"\nOverall Statistics:")
            print(f"  Success rate: {success_rate:.1f}%")
            print(f"  Error rate: {error_rate:.1f}%")
            
            # Determine test result
            if success_rate >= 90:
                print("✓ EXCELLENT: >90% success rate achieved")
            elif success_rate >= 80:
                print("✓ GOOD: >80% success rate achieved")  
            elif success_rate >= 70:
                print("⚠ FAIR: >70% success rate, room for improvement")
            else:
                print("✗ POOR: <70% success rate, hardware issues likely")
                
            print(f"\nComparison to basic implementation:")
            print(f"  Previous error rate was ~50% (many ERR readings)")
            print(f"  Current error rate: {error_rate:.1f}%")
            if error_rate < 25:
                print("  ✓ Significant improvement achieved!")
            elif error_rate < 40:
                print("  ↗ Moderate improvement achieved")  
            else:
                print("  ↔ Limited improvement, check hardware")
        
        print("\nNext steps:")
        print("1. If error rate is still high, check I2C wiring and power")
        print("2. Consider adding pull-up resistors if not present")
        print("3. Verify sensor mounting and environmental conditions")
        print("4. Check for I2C address conflicts with other devices")

if __name__ == "__main__":
    test_enhanced_tof_reliability()
