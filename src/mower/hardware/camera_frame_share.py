"""
Camera frame sharing mechanism between main and web processes.

This module provides a way for the main process to share camera frames
with the web process without both processes trying to access the camera
hardware directly.
"""

import os
import time
import threading
import json
from typing import Optional, Dict, Any
from mower.utilities.logger_config import LoggerConfigInfo

logger = LoggerConfigInfo.get_logger(__name__)


class CameraFrameSharer:
    """
    Manages sharing of camera frames between processes via the filesystem.
    
    The main process writes frames to a shared location, and the web process
    reads them. This avoids camera hardware conflicts.
    """
    
    def __init__(self, share_dir: str = "/tmp/mower_camera_share"):
        """
        Initialize the frame sharer.
        
        Args:
            share_dir: Directory to use for sharing frames
        """
        self.share_dir = share_dir
        self.frame_path = os.path.join(share_dir, "current_frame.jpg")
        self.metadata_path = os.path.join(share_dir, "frame_metadata.json")
        self.lock_path = os.path.join(share_dir, "frame.lock")
        
        # Ensure share directory exists
        os.makedirs(share_dir, exist_ok=True)
        
        # Initialize metadata
        self.frame_count = 0
        self.last_update = 0
        
        logger.info(f"CameraFrameSharer initialized with share_dir: {share_dir}")
    
    def write_frame(self, frame_bytes: bytes) -> bool:
        """
        Write a frame to the shared location (called by main process).
        
        Args:
            frame_bytes: JPEG encoded frame data
            
        Returns:
            bool: True if frame was written successfully
        """
        try:
            # Use a lock file to prevent reading while writing
            with open(self.lock_path, 'w') as lock_file:
                lock_file.write(str(os.getpid()))
                
                # Write the frame
                with open(self.frame_path, 'wb') as f:
                    f.write(frame_bytes)
                
                # Update metadata
                self.frame_count += 1
                self.last_update = time.time()
                
                metadata = {
                    'frame_count': self.frame_count,
                    'timestamp': self.last_update,
                    'size': len(frame_bytes),
                    'writer_pid': os.getpid()
                }
                
                with open(self.metadata_path, 'w') as f:
                    json.dump(metadata, f)
            
            # Remove lock file
            if os.path.exists(self.lock_path):
                os.remove(self.lock_path)
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to write frame: {e}")
            # Clean up lock file on error
            if os.path.exists(self.lock_path):
                try:
                    os.remove(self.lock_path)
                except:
                    pass
            return False
    
    def read_frame(self, timeout: float = 1.0) -> Optional[bytes]:
        """
        Read the latest frame from the shared location (called by web process).
        
        Args:
            timeout: Maximum time to wait for a frame
            
        Returns:
            Optional[bytes]: JPEG encoded frame data or None if not available
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Check if lock file exists (main process is writing)
                if os.path.exists(self.lock_path):
                    time.sleep(0.01)  # Wait a bit and try again
                    continue
                
                # Check if frame file exists
                if not os.path.exists(self.frame_path):
                    time.sleep(0.1)
                    continue
                
                # Read metadata to check if frame is fresh
                if os.path.exists(self.metadata_path):
                    try:
                        with open(self.metadata_path, 'r') as f:
                            metadata = json.load(f)
                        
                        # Check if frame is too old (more than 5 seconds)
                        if time.time() - metadata.get('timestamp', 0) > 5.0:
                            logger.debug("Shared frame is too old, skipping")
                            time.sleep(0.1)
                            continue
                            
                    except (json.JSONDecodeError, IOError):
                        # If metadata is corrupted, still try to read the frame
                        pass
                
                # Read the frame
                with open(self.frame_path, 'rb') as f:
                    frame_data = f.read()
                
                if len(frame_data) > 0:
                    logger.debug(f"Read shared frame: {len(frame_data)} bytes")
                    return frame_data
                    
            except Exception as e:
                logger.debug(f"Error reading shared frame: {e}")
                
            time.sleep(0.05)  # Small delay before retry
        
        logger.debug("No valid shared frame available within timeout")
        return None
    
    def get_metadata(self) -> Optional[Dict[str, Any]]:
        """
        Get metadata about the current shared frame.
        
        Returns:
            Optional[Dict]: Metadata dictionary or None if not available
        """
        try:
            if os.path.exists(self.metadata_path):
                with open(self.metadata_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.debug(f"Error reading metadata: {e}")
        
        return None
    
    def is_frame_available(self) -> bool:
        """
        Check if a current frame is available.
        
        Returns:
            bool: True if a frame is available and recent
        """
        metadata = self.get_metadata()
        if not metadata:
            return False
        
        # Check if frame is recent (within last 2 seconds)
        age = time.time() - metadata.get('timestamp', 0)
        return age < 2.0 and os.path.exists(self.frame_path)
    
    def cleanup(self):
        """Clean up shared files."""
        try:
            for path in [self.frame_path, self.metadata_path, self.lock_path]:
                if os.path.exists(path):
                    os.remove(path)
            logger.info("Cleaned up shared camera files")
        except Exception as e:
            logger.error(f"Error cleaning up shared files: {e}")


# Global instance for sharing frames
_frame_sharer: Optional[CameraFrameSharer] = None
_frame_sharer_lock = threading.Lock()


def get_frame_sharer() -> CameraFrameSharer:
    """
    Get the global frame sharer instance.
    
    Returns:
        CameraFrameSharer: The global frame sharer instance
    """
    global _frame_sharer
    with _frame_sharer_lock:
        if _frame_sharer is None:
            _frame_sharer = CameraFrameSharer()
        return _frame_sharer
