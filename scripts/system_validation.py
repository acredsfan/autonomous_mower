#!/usr/bin/env python3
"""
Final system validation with comprehensive timeout protection.
This script performs:
1. Service status check
2. Log file validation
3. CI script validation
4. Optional sensor handling verification
5. Web interface verification
"""
import subprocess
import time
import signal
import sys
import os

def timeout_handler(signum, frame):
    """Handle timeout signal"""
    print("⚠️  Validation script timed out")
    sys.exit(1)

# Set overall timeout for validation
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(300)  # 5 minute total timeout

def run_command(cmd, timeout_sec=30, shell=False):
    """Run a command with timeout and return result"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, 
                             timeout=timeout_sec, shell=shell)
        return result.returncode == 0, result.stdout
    except subprocess.TimeoutExpired:
        print(f"Command timed out after {timeout_sec} seconds: {cmd}")
        return False, f"TIMEOUT: {cmd}"
    except Exception as e:
        print(f"Error running command: {e}")
        return False, f"ERROR: {str(e)}"

def check_service_status():
    """Check if mower service is active"""
    print("Checking service status...")
    success, output = run_command(['systemctl', 'is-active', 'mower.service'], timeout_sec=5)
    if success:
        print("✓ Service is active")
        return True
    else:
        print(f"✗ Service is not active: {output}")
        return False

def copy_and_check_logs():
    """Copy logs and check for critical errors"""
    print("Copying logs for analysis...")
    success, _ = run_command(['python3', '/home/pi/autonomous_mower/copy_logs.py'], timeout_sec=60)
    if not success:
        print("✗ Failed to copy logs")
        return False
    
    print("Checking for critical errors in logs...")
    success, output = run_command('grep -E "(CRITICAL|ERROR.*Failed)" copied_mower.log | tail -10', 
                               timeout_sec=10, shell=True)
    if success:
        print(f"⚠️  Found critical errors in logs:\n{output}")
        return False
    else:
        print("✓ No critical errors found in recent logs")
        return True

def check_unit_file():
    """Run the unit file validation script"""
    print("Validating systemd unit file configuration...")
    success, output = run_command(['python3', '/home/pi/autonomous_mower/scripts/check_unit_file.py'], 
                               timeout_sec=30)
    if success:
        print("✓ Unit file validation passed")
        return True
    else:
        print(f"✗ Unit file validation failed:\n{output}")
        return False

def check_numpy_version():
    """Run the NumPy version verification script"""
    print("Validating NumPy version...")
    success, output = run_command(['python3', '/home/pi/autonomous_mower/tests/ci/verify_numpy_version.py'], 
                               timeout_sec=30)
    if success:
        print("✓ NumPy version validation passed")
        return True
    else:
        print(f"✗ NumPy version validation failed:\n{output}")
        return False

def check_web_interface():
    """Check if the web interface is responding"""
    print("Checking web interface...")
    
    # First check if a process is running with 'flask' or 'web' in its name
    success, output = run_command(['ps', 'aux'], timeout_sec=10)
    if not success:
        print("✗ Failed to check process list")
        return False
    
    web_process_found = False
    for line in output.splitlines():
        if 'flask' in line.lower() or 'web_process' in line.lower():
            if 'grep' not in line.lower():  # Exclude the grep process itself
                web_process_found = True
                print(f"✓ Web process found: {line.strip()}")
                break
    
    if not web_process_found:
        print("✗ No web interface process found")
        return False
    
    # Try to connect to the web interface
    success, _ = run_command(['curl', '-s', '-m', '10', 'http://localhost:8000'], timeout_sec=15)
    if success:
        print("✓ Web interface is responding")
        return True
    else:
        print("✗ Web interface not responding")
        return False

def check_optional_sensors():
    """Check if optional sensors are properly handled"""
    print("Checking optional sensor handling...")
    
    # Copy logs first if they haven't been copied yet
    if not os.path.exists('copied_mower.log'):
        run_command(['python3', '/home/pi/autonomous_mower/copy_logs.py'], timeout_sec=60)
    
    # Check if BME280 sensor messages are in logs (whether present or not)
    success, output = run_command('grep -i "bme280" copied_mower.log | tail -5', 
                               timeout_sec=10, shell=True)
    if success:
        print(f"✓ BME280 sensor handling detected:\n{output.strip()}")
    else:
        print("ℹ️ No BME280 sensor messages found in logs")
    
    # Check if INA3221 sensor messages are in logs (whether present or not)
    success, output = run_command('grep -i "ina3221" copied_mower.log | tail -5', 
                               timeout_sec=10, shell=True)
    if success:
        print(f"✓ INA3221 sensor handling detected:\n{output.strip()}")
    else:
        print("ℹ️ No INA3221 sensor messages found in logs")
    
    # Check if any error messages indicate failure to handle missing sensors
    success, output = run_command('grep -E "(ERROR.*sensor|sensor.*Failed)" copied_mower.log | tail -5', 
                               timeout_sec=10, shell=True)
    if success:
        print(f"⚠️ Possible sensor handling issues detected:\n{output.strip()}")
        return False
    else:
        print("✓ No critical sensor handling issues detected")
        return True

def run_validation_tests():
    """Run all validation tests"""
    print("\n=== AUTONOMOUS MOWER SYSTEM VALIDATION ===")
    print(f"Starting validation at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {
        "Service Status": check_service_status(),
        "Log Analysis": copy_and_check_logs(),
        "Unit File Validation": check_unit_file(),
        "NumPy Version": check_numpy_version(),
        "Optional Sensors": check_optional_sensors(),
        "Web Interface": check_web_interface()
    }
    
    print("\n=== VALIDATION RESULTS SUMMARY ===")
    all_passed = True
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        if not passed:
            all_passed = False
        print(f"{test_name}: {status}")
    
    print("\n=== FINAL RESULT ===")
    if all_passed:
        print("✅ ALL VALIDATION TESTS PASSED")
        return 0
    else:
        print("❌ SOME VALIDATION TESTS FAILED")
        return 1

if __name__ == "__main__":
    try:
        exit_code = run_validation_tests()
        print(f"\nValidation completed at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        sys.exit(exit_code)
    except Exception as e:
        print(f"✗ Validation script failed with error: {e}")
        sys.exit(1)
    finally:
        signal.alarm(0)  # Cancel timeout
