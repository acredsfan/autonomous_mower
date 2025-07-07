"""
Shared sensor data manager for inter-process communication.

This module provides a thread-safe way to share sensor data between
the main controller process and the web UI process, avoiding the
multiprocessing limitations that prevent direct resource sharing.

Key features:
- Atomic file writes to prevent corruption
- Timestamp-based staleness detection  
- Fallback to safe defaults
- Minimal latency impact on main process
"""
import json
import time
import threading
import tempfile
import os
from typing import Dict, Any, Optional
from pathlib import Path

from mower.utilities.logger_config import LoggerConfigInfo

logger = LoggerConfigInfo.get_logger(__name__)

# Shared data file location
SHARED_DATA_PATH = Path("/tmp/mower_sensor_data.json")
SHARED_DATA_MAX_AGE = 10.0  # seconds - consider data stale after this

class SharedSensorDataManager:
    """
    Manages shared sensor data between processes.
    
    The main process writes real sensor data to a shared file,
    and the web process reads from it to display real data
    instead of dummy/random values.
    """
    
    def __init__(self):
        self.logger = LoggerConfigInfo.get_logger(__name__)
        self._write_lock = threading.Lock()
        
    def write_sensor_data(self, sensor_data: Dict[str, Any]) -> bool:
        """
        Write sensor data to shared storage (main process).
        
        Args:
            sensor_data: Dictionary containing sensor readings
            
        Returns:
            bool: True if write was successful
        """
        try:
            # Add timestamp for staleness detection
            data_with_timestamp = {
                "timestamp": time.time(),
                "data": sensor_data
            }
            
            # Atomic write using temporary file + rename
            with self._write_lock:
                # Write to temporary file first
                temp_path = SHARED_DATA_PATH.with_suffix('.tmp')
                with open(temp_path, 'w') as f:
                    json.dump(data_with_timestamp, f, indent=2)
                
                # Atomic rename to final location
                temp_path.rename(SHARED_DATA_PATH)
                
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write shared sensor data: {e}")
            return False
    
    def read_sensor_data(self) -> Optional[Dict[str, Any]]:
        """
        Read sensor data from shared storage (web process).
        
        Returns:
            dict: Sensor data if available and fresh, None otherwise
        """
        try:
            if not SHARED_DATA_PATH.exists():
                return None
                
            with open(SHARED_DATA_PATH, 'r') as f:
                data_with_timestamp = json.load(f)
            
            # Check if data is fresh
            timestamp = data_with_timestamp.get("timestamp", 0)
            age = time.time() - timestamp
            
            if age > SHARED_DATA_MAX_AGE:
                self.logger.warning(f"Shared sensor data is stale ({age:.1f}s old)")
                return None
                
            return data_with_timestamp.get("data")
            
        except Exception as e:
            self.logger.debug(f"Failed to read shared sensor data: {e}")
            return None
    
    def is_data_fresh(self) -> bool:
        """
        Check if shared data exists and is fresh.
        
        Returns:
            bool: True if data exists and is recent
        """
        try:
            if not SHARED_DATA_PATH.exists():
                return False
                
            with open(SHARED_DATA_PATH, 'r') as f:
                data_with_timestamp = json.load(f)
            
            timestamp = data_with_timestamp.get("timestamp", 0)
            age = time.time() - timestamp
            
            return age <= SHARED_DATA_MAX_AGE
            
        except Exception:
            return False
    
    def get_fallback_sensor_data(self) -> Dict[str, Any]:
        """
        Get safe fallback sensor data when real data is unavailable.
        
        Returns:
            dict: Safe default sensor values
        """
        return {
            "imu": {
                "heading": 0.0,
                "roll": 0.0,
                "pitch": 0.0,
                "safety_status": {"is_safe": True}
            },
            "environment": {
                "temperature": 20.0,
                "humidity": 50.0,
                "pressure": 1013.25
            },
            "tof": {
                "left": 150.0,
                "right": 150.0,
                "front": 150.0
            },
            "power": {
                "voltage": 12.0,
                "current": 1.0,
                "power": 12.0,
                "percentage": 75
            },
            "gps": {
                "latitude": 0.000000,
                "longitude": 0.000000,
                "fix": False,
                "fix_quality": "no_fix",
                "status": "no_fix",
                "satellites": 0,
                "hdop": 99.9,
                "altitude": 0.0,
                "speed": 0.0
            }
        }

# Global instance for shared use
_shared_manager = None

def get_shared_sensor_manager() -> SharedSensorDataManager:
    """Get the global shared sensor data manager instance."""
    global _shared_manager
    if _shared_manager is None:
        _shared_manager = SharedSensorDataManager()
    return _shared_manager
