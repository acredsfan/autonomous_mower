#!/usr/bin/env python3
"""
Single Instance Protection for Autonomous Mower

This module provides a PID file-based mechanism to ensure only one instance
of the mower application runs at a time, preventing hardware resource conflicts.
"""

import os
import psutil
import signal
import atexit
import time
from pathlib import Path
from typing import Optional

from mower.utilities.logger_config import LoggerConfigInfo
logger = LoggerConfigInfo.get_logger(__name__)

class SingleInstanceLock:
    """
    Ensures only one instance of the application runs at a time using PID files.
    
    This prevents hardware resource conflicts when multiple processes try to
    access I2C, GPIO, camera, and other hardware simultaneously.
    """
    
    def __init__(self, pid_file: str = "/tmp/autonomous_mower.pid"):
        """
        Initialize single instance lock.
        
        Args:
            pid_file: Path to PID file for tracking running instance
        """
        self.pid_file = Path(pid_file)
        self.logger = logger
        self._locked = False
        
    def acquire(self, force_cleanup: bool = False) -> bool:
        """
        Acquire single instance lock.
        
        Args:
            force_cleanup: If True, forcefully clean up stale processes
            
        Returns:
            True if lock acquired successfully, False if another instance is running
        """
        # Check if PID file exists
        if self.pid_file.exists():
            try:
                with open(self.pid_file, 'r') as f:
                    existing_pid = int(f.read().strip())
                
                # Check if process is actually running
                if self._is_process_running(existing_pid):
                    if force_cleanup:
                        self.logger.warning(f"Force cleanup: Terminating existing process PID {existing_pid}")
                        try:
                            os.kill(existing_pid, signal.SIGTERM)
                            time.sleep(2)  # Give it time to cleanup
                            if self._is_process_running(existing_pid):
                                self.logger.warning(f"Force cleanup: Killing stubborn process PID {existing_pid}")
                                os.kill(existing_pid, signal.SIGKILL)
                                time.sleep(1)
                        except (OSError, ProcessLookupError):
                            pass  # Process already gone
                    else:
                        self.logger.error(f"Another mower instance is already running (PID: {existing_pid})")
                        self.logger.error("Use --force-cleanup flag or kill the existing process manually")
                        return False
                else:
                    # Stale PID file - clean it up
                    self.logger.warning(f"Cleaning up stale PID file (process {existing_pid} not running)")
                    self._cleanup_pid_file()
                    
            except (ValueError, FileNotFoundError, PermissionError) as e:
                self.logger.warning(f"Error reading PID file: {e}, cleaning up")
                self._cleanup_pid_file()
        
        # Create new PID file
        try:
            current_pid = os.getpid()
            with open(self.pid_file, 'w') as f:
                f.write(str(current_pid))
            
            self.logger.info(f"Single instance lock acquired (PID: {current_pid})")
            self._locked = True
            
            # Register cleanup on exit
            atexit.register(self.release)
            
            return True
            
        except (OSError, PermissionError) as e:
            self.logger.error(f"Failed to create PID file: {e}")
            return False
    
    def release(self):
        """Release the single instance lock by removing PID file."""
        if self._locked:
            self._cleanup_pid_file()
            self._locked = False
            self.logger.info("Single instance lock released")
    
    def _is_process_running(self, pid: int) -> bool:
        """
        Check if a process with given PID is running and is a mower process.
        
        Args:
            pid: Process ID to check
            
        Returns:
            True if process is running and appears to be a mower process
        """
        try:
            process = psutil.Process(pid)
            if not process.is_running():
                return False
                
            # Check if it's actually a mower process
            cmdline = ' '.join(process.cmdline())
            if 'mower.main_controller' in cmdline or 'autonomous_mower' in cmdline:
                return True
            else:
                self.logger.warning(f"PID {pid} exists but doesn't appear to be a mower process: {cmdline}")
                return False
                
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return False
    
    def _cleanup_pid_file(self):
        """Remove PID file if it exists."""
        try:
            if self.pid_file.exists():
                self.pid_file.unlink()
        except (OSError, PermissionError) as e:
            self.logger.warning(f"Could not remove PID file: {e}")

def ensure_single_instance(force_cleanup: bool = False) -> bool:
    """
    Convenience function to ensure single instance.
    
    Args:
        force_cleanup: If True, forcefully terminate existing instances
        
    Returns:
        True if single instance protection is successful
    """
    lock = SingleInstanceLock()
    return lock.acquire(force_cleanup=force_cleanup)
