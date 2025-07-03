#!/usr/bin/env python3
"""
CI verification script to ensure NumPy version compatibility with TFLite runtime.

This script ensures that NumPy is pinned below version 2.0 to maintain
compatibility with tflite_runtime which was built for NumPy 1.x.

@hardware_interface: None (CI verification only)
"""

import sys
from importlib.metadata import version


def verify_numpy_version() -> bool:
    """
    Verify that NumPy version is below 2.0 for tflite_runtime compatibility.
    
    Returns:
        bool: True if NumPy version is compatible, False otherwise.
        
    Raises:
        ImportError: If NumPy is not installed.
        SystemExit: If version check fails.
    """
    try:
        numpy_version = version("numpy")
        print(f"NumPy version detected: {numpy_version}")
        
        # Check if version is below 2.0
        major_version = int(numpy_version.split('.')[0])
        
        if major_version >= 2:
            print(f"ERROR: NumPy {numpy_version} is >= 2.0")
            print("tflite_runtime requires NumPy < 2.0 due to _ARRAY_API compatibility")
            print("Please ensure numpy is pinned to '>=1.24,<1.27' in pyproject.toml")
            return False
            
        print(f"✓ NumPy {numpy_version} is compatible with tflite_runtime")
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to check NumPy version: {e}")
        return False


def main():
    """Main entry point for CI verification."""
    if not verify_numpy_version():
        sys.exit(1)
    
    print("NumPy version verification passed")


if __name__ == "__main__":
    main()
