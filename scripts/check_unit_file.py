#!/usr/bin/env python3
"""
CI script to validate systemd unit file configuration.

Ensures that mower.service has proper restart backoff settings
to prevent endless restart loops.

@hardware_interface: None (CI validation only)
"""

import re
import sys
import signal
import time
from pathlib import Path


def timeout_handler(signum, frame):
    """Handle timeout signal for file operations."""
    print("ERROR: Unit file validation timed out")
    raise TimeoutError("Unit file validation timed out")


def check_unit_file(file_path: str) -> bool:
    """
    Validate systemd unit file has proper restart configuration.
    
    Args:
        file_path: Path to the systemd unit file
        
    Returns:
        bool: True if configuration is valid, False otherwise
    """
    # Set timeout for file operations
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(30)  # 30 second timeout
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        signal.alarm(0)  # Cancel timeout after successful read
        
        # Check for RestartSec >= 10
        restart_sec_match = re.search(r'RestartSec=(\d+)', content)
        if not restart_sec_match:
            print("ERROR: RestartSec not found in unit file")
            return False
            
        restart_sec = int(restart_sec_match.group(1))
        if restart_sec < 10:
            print(f"ERROR: RestartSec={restart_sec} is too low (minimum: 10)")
            return False
            
        print(f"✓ RestartSec={restart_sec} meets minimum requirement")
        
        # Check for StartLimitInterval
        if 'StartLimitInterval=' not in content:
            print("WARNING: StartLimitInterval not set")
        else:
            print("✓ StartLimitInterval configured")
            
        # Check for StartLimitBurst
        if 'StartLimitBurst=' not in content:
            print("WARNING: StartLimitBurst not set")
        else:
            print("✓ StartLimitBurst configured")
            
        return True
        
    except TimeoutError:
        print("ERROR: File read operation timed out")
        return False
    except Exception as e:
        print(f"ERROR: Failed to check unit file: {e}")
        return False
    finally:
        signal.alarm(0)  # Ensure timeout is cancelled


def main():
    """Main entry point for CI validation."""
    unit_file = Path("deployment/mower.service")
    
    if not unit_file.exists():
        print(f"ERROR: Unit file not found: {unit_file}")
        sys.exit(1)
        
    if not check_unit_file(str(unit_file)):
        sys.exit(1)
        
    print("Unit file validation passed")


if __name__ == "__main__":
    main()
