"""
Camera instance module for managing camera access.

This module provides a singleton pattern for camera access to ensure
only one instance of the camera is active at a time.
"""

import os
import socket
import threading
import cv2  # type:ignore
from dotenv import load_dotenv  # type:ignore
from typing import Optional, Union

from mower.utilities.logger_config import (
    LoggerConfigInfo as LoggerConfig
    )

# Load environment variables
load_dotenv()

# Initialize logger
logging = LoggerConfig.get_logger(__name__)

# Camera configuration from environment variables
FPS = int(os.getenv('STREAMING_FPS', 15))
STREAMING_RESOLUTION = os.getenv('STREAMING_RESOLUTION', '640x480')
WIDTH, HEIGHT = map(int, STREAMING_RESOLUTION.split('x'))
# Number of frames to keep in buffer
BUFFER_SIZE = int(os.getenv('FRAME_BUFFER_SIZE', 5))

# Try to import picamera2, but don't fail if not available
try:
    from picamera2 import Picamera2  # type: ignore
    PICAMERA_AVAILABLE = True
except ImportError:
    PICAMERA_AVAILABLE = False
    logging.warning(
        "picamera2 not available. Using OpenCV camera or simulation.")

# Global camera instance
_camera_instance = None
_camera_lock = threading.Lock()


def get_device_ip():
    """
    Get the IP address of the device on the local network.
    This function uses a UDP socket to determine the device's IP
    without sending any actual data.

    Returns:
        str: IP address of the device, or '127.0.0.1' if detection fails
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't need to connect, just open a socket to get the IP
        s.connect(('8.8.8.8', 80))  # Google's DNS server
        device_ip = s.getsockname()[0]
    except Exception as e:
        # Fallback if IP detection fails
        logging.error(f"Could not determine device IP: {e}")
        device_ip = '127.0.0.1'  # Default to localhost if detection fails
    finally:
        s.close()
    return device_ip


class CameraInstance:
    """
    Singleton class for managing camera access.

    This class ensures that only one instance of the camera is active
    at any time, preventing resource conflicts.
    """

    def __init__(self):
        """Initialize the camera instance."""
        self._camera = None
        self._is_picamera = False
        self._frame_width = 640
        self._frame_height = 480
        self._is_initialized = False
        self._last_frame = None
        self._frame_lock = threading.Lock()

    def initialize(self) -> bool:
        """
        Initialize the camera hardware.

        Returns:
            bool: True if initialization successful, False otherwise
        """
        if self._is_initialized:
            return True

        try:
            # Try picamera2 first if available
            if PICAMERA_AVAILABLE:
                try:
                    self._camera = Picamera2()
                    self._camera.configure(
                        self._camera.create_preview_configuration(
                            main={"size": (self._frame_width,
                                           self._frame_height)}
                            )
                        )
                    self._camera.start()
                    self._is_picamera = True
                    self._is_initialized = True
                    logging.info("Initialized PiCamera2")
                    return True
                except Exception as e:
                    logging.warning(f"Failed to initialize PiCamera2: {e}")

            # Fall back to OpenCV camera
            self._camera = cv2.VideoCapture(0)
            if not self._camera.isOpened():
                logging.warning("Failed to open OpenCV camera")
                return False

            self._camera.set(cv2.CAP_PROP_FRAME_WIDTH, self._frame_width)
            self._camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self._frame_height)
            self._is_picamera = False
            self._is_initialized = True
            logging.info("Initialized OpenCV camera")
            return True

        except Exception as e:
            logging.error(f"Camera initialization failed: {e}")
            return False

    def capture_frame(self) -> Optional[Union[bytes, None]]:
        """
        Capture a frame from the camera.

        Returns:
            Optional[bytes]: JPEG encoded frame data or None if capture fails
        """
        if not self._is_initialized:
            if not self.initialize():
                return None

        try:
            with self._frame_lock:
                if self._is_picamera:
                    frame = self._camera.capture_array()
                else:
                    ret, frame = self._camera.read()
                    if not ret:
                        return None

                # Convert to JPEG
                ret, jpeg = cv2.imencode('.jpg', frame)
                if not ret:
                    return None

                self._last_frame = jpeg.tobytes()
                return self._last_frame

        except Exception as e:
            logging.error(f"Frame capture failed: {e}")
            return None

    def get_last_frame(self) -> Optional[bytes]:
        """
        Get the last captured frame without capturing a new one.

        Returns:
            Optional[bytes]: Last captured frame data or None if no frame
            available
        """
        with self._frame_lock:
            return self._last_frame

    def release(self):
        """Release camera resources."""
        if self._is_initialized:
            try:
                if self._is_picamera:
                    self._camera.close()
                else:
                    self._camera.release()
            except Exception as e:
                logging.error(f"Error releasing camera: {e}")
            finally:
                self._is_initialized = False
                self._camera = None

    def cleanup(self):
        """Clean up resources used by the CameraInstance."""
        try:
            # Add specific cleanup logic here
            logging.info("CameraInstance cleaned up successfully.")
        except Exception as e:
            logging.error(f"Error cleaning up CameraInstance: {e}")


def get_camera_instance() -> CameraInstance:
    """
    Get the singleton camera instance.

    Returns:
        CameraInstance: The singleton camera instance
    """
    global _camera_instance
    with _camera_lock:
        if _camera_instance is None:
            _camera_instance = CameraInstance()
        return _camera_instance


def start_server_thread():
    """
    Start the camera server thread.

    This function starts the camera and ensures it's capturing frames.
    It's used for initializing the camera system when the web UI starts.

    Returns:
        bool: True if camera started successfully, False otherwise
    """
    camera = get_camera_instance()
    return camera.initialize()
