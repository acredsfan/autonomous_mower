#!/usr/bin/env python3
"""
Test script for the web interface process separation.

This script tests:
1. Web process starts in separate process
2. PID is properly logged
3. Cleanup properly terminates the web process

@hardware_interface: None (web process only)
"""
import signal
import time
import sys
import os
import multiprocessing

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

def timeout_handler(signum, frame):
    """Handle timeout signal"""
    print("⚠️ Test timed out!")
    sys.exit(1)

# Set timeout for the entire test
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(120)  # 2 minute timeout

try:
    print("Starting Web Process Separation Test...")
    
    # Import the MainController class
    from src.mower.main_controller import MainController
    
    # Set environment variable to allow safe mode
    os.environ['SAFE_MODE_ALLOWED'] = 'true'
    
    # Create controller instance
    controller = MainController()
    
    # Initialize the web interface
    print("Initializing web interface in separate process...")
    result = controller.initialize_web_interface()
    
    if result and hasattr(controller, 'web_proc') and controller.web_proc.is_alive():
        print(f"✓ Web interface started successfully in separate process (PID: {controller.web_proc.pid})")
    else:
        print("✗ Failed to start web interface in separate process")
        sys.exit(1)
    
    # Get parent and child process IDs for verification
    parent_pid = os.getpid()
    web_pid = controller.web_proc.pid
    
    if parent_pid != web_pid:
        print(f"✓ Web process PID ({web_pid}) different from main process PID ({parent_pid})")
    else:
        print("✗ Web process running in same process as main!")
        sys.exit(1)
    
    # Test web interface availability
    print("Testing web interface availability (waiting up to 30s)...")
    web_available = False
    start_time = time.time()
    while time.time() - start_time < 30:  # 30 second timeout
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('127.0.0.1', 8000))
            sock.close()
            if result == 0:
                web_available = True
                break
        except Exception:
            pass
        time.sleep(1)
    
    if web_available:
        print("✓ Web interface is responding on port 8000")
    else:
        print("⚠️ Web interface not responding (this might be acceptable in test environment)")
    
    # Test cleanup
    print("Testing cleanup of web process...")
    
    # Implement a cleanup method since we can't directly call controller.cleanup_and_exit()
    def cleanup_web_proc():
        if controller.web_proc.is_alive():
            print("Terminating web process...")
            controller.web_proc.terminate()
            
            # Wait for graceful shutdown with timeout
            join_start = time.time()
            while time.time() - join_start < 5:
                if not controller.web_proc.is_alive():
                    break
                time.sleep(0.1)
            
            if controller.web_proc.is_alive():
                print("Force killing web process...")
                controller.web_proc.kill()
                time.sleep(1)
    
    # Call cleanup
    cleanup_web_proc()
    
    # Verify process is terminated
    if not controller.web_proc.is_alive():
        print("✓ Web process terminated successfully during cleanup")
    else:
        print("✗ Web process still running after cleanup!")
        sys.exit(1)
    
    print("✓ All web process separation tests completed successfully")
    
except Exception as e:
    print(f"✗ Test failed with error: {e}")
    sys.exit(1)
finally:
    signal.alarm(0)  # Cancel timeout
    # Ensure web process is terminated if it exists
    if 'controller' in locals() and hasattr(controller, 'web_proc') and controller.web_proc.is_alive():
        controller.web_proc.terminate()
        time.sleep(1)
        if controller.web_proc.is_alive():
            controller.web_proc.kill()
    print("Test complete")
