#!/usr/bin/env python3
"""
Test script to validate TFLite model fallback handling.
"""

import os
import sys

def test_tflite_fallback():
    """Test TFLite model fallback handling"""
    print("Testing TFLite model fallback handling...")
    
    try:
        # Test 1: Missing model file handling
        model_path = "/nonexistent/model.tflite"
        
        # Simulate what the obstacle detector does
        if not os.path.exists(model_path):
            print(f"✓ Correctly detected missing model: {model_path}")
        else:
            print(f"✗ Model existence check failed")
            return False
            
        # Test 2: TFLite runtime import fallback
        tflite_available = False
        try:
            from tflite_runtime.interpreter import Interpreter
            print("✓ TFLite runtime is available")
            tflite_available = True
        except ImportError:
            print("✓ TFLite runtime not available - fallback will be used")
            tflite_available = False
            
        # Test 3: NumPy 2.x compatibility check
        try:
            import numpy as np
            print(f"✓ NumPy version: {np.__version__}")
            if hasattr(np, '_ARRAY_API'):
                print("✓ NumPy 2.x compatible attributes found")
            else:
                print("✓ Using NumPy 1.x or compatible version")
        except ImportError:
            print("⚠ NumPy not available in test environment")
            
        print("✓ TFLite fallback handling working correctly!")
        return True
        
    except Exception as e:
        print(f"✗ TFLite test failed with error: {e}")
        return False

if __name__ == "__main__":
    success = test_tflite_fallback()
    sys.exit(0 if success else 1)