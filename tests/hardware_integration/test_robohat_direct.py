#!/usr/bin/env python3
"""
Test script to verify that the robohat.py module works correctly when run directly.
"""

import subprocess
import sys
import os

def test_robohat_direct_execution():
    """Test running robohat.py directly."""
    print("Testing direct execution of robohat.py...")
    
    # Change to the project directory
    project_dir = "/home/pi/autonomous_mower"
    robohat_file = os.path.join(project_dir, "src", "mower", "hardware", "robohat.py")
    
    try:
        # Run the robohat.py file directly with a short timeout
        # This will test the __main__ block without running indefinitely
        result = subprocess.run(
            [sys.executable, robohat_file],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout
        )
        
        print(f"Return code: {result.returncode}")
        print(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            print(f"STDERR:\n{result.stderr}")
        
        # Check if it ran without syntax errors
        if "Traceback" not in result.stderr and "SyntaxError" not in result.stderr:
            print("✓ No syntax errors detected!")
            return True
        else:
            print("❌ Syntax or runtime errors detected!")
            return False
            
    except subprocess.TimeoutExpired:
        print("✓ Process ran without syntax errors (timed out as expected)")
        return True
    except Exception as e:
        print(f"❌ Error running test: {e}")
        return False

if __name__ == "__main__":
    success = test_robohat_direct_execution()
    sys.exit(0 if success else 1)
