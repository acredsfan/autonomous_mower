import os
import socket
import threading
import time
import cv2
from dotenv import load_dotenv
import io
import queue
from picamera2 import Picamera2  # type: ignore

from mower.utilities.logger_config import (
    LoggerConfigDebug as LoggerConfig
)

# Load environment variables
load_dotenv()

# Initialize logger
logging = LoggerConfig.get_logger(__name__)

# Camera configuration from environment variables
FPS = int(os.getenv('STREAMING_FPS', 15))
STREAMING_RESOLUTION = os.getenv('STREAMING_RESOLUTION', '640x480')
WIDTH, HEIGHT = map(int, STREAMING_RESOLUTION.split('x'))
BUFFER_SIZE = int(os.getenv('FRAME_BUFFER_SIZE', 5))  # Number of frames to keep in buffer

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
    Singleton class to manage camera access for both streaming and object detection.
    
    This class provides a central point for accessing the camera, ensuring that
    multiple components can use the camera simultaneously without conflicts.
    It maintains a frame buffer that can be accessed by both the streaming server
    and the object detection module.
    
    The class supports:
    - Frame capture at a configurable FPS
    - Frame buffering for efficient access
    - MJPEG streaming for the web UI
    - On-demand frame access for object detection
    
    Thread Safety:
        All camera access is protected by locks to ensure thread-safe operation
        when accessed by multiple components simultaneously.
    """
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """Implement singleton pattern for camera access"""
        if cls._instance is None:
            cls._instance = super(CameraInstance, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the camera instance with required resources"""
        if self._initialized:
            return
            
        self.device_ip = get_device_ip()
        self.camera = None
        self.running = False
        self.frame_buffer = queue.Queue(maxsize=BUFFER_SIZE)
        self.frame_lock = threading.Lock()
        self.latest_frame = None
        self.capture_thread = None
        
        # Attempt to initialize the camera
        try:
            self.camera = Picamera2()
            # Set the camera resolution
            camera_config = self.camera.create_video_configuration({"size": (WIDTH, HEIGHT)})
            self.camera.configure(camera_config)
            logging.info(f"Camera initialized with resolution {WIDTH}x{HEIGHT}")
        except Exception as e:
            logging.error(f"Failed to initialize camera: {e}")
            self.camera = None
            
        self._initialized = True
    
    def start(self):
        """
        Start the camera and frame capture thread.
        
        This starts both the camera and a background thread that captures
        frames at the configured FPS rate, maintaining a buffer of recent frames
        that can be accessed by both streaming and object detection components.
        
        Returns:
            bool: True if successfully started, False otherwise
        """
        if self.running:
            return True
            
        if self.camera is None:
            logging.error("Cannot start camera - not initialized")
            return False
            
        try:
            self.camera.start()
            self.running = True
            
            # Start background thread for frame capture
            self.capture_thread = threading.Thread(target=self._capture_loop)
            self.capture_thread.daemon = True
            self.capture_thread.start()
            
            logging.info(f"Camera started with resolution {WIDTH}x{HEIGHT} at {FPS} FPS")
            return True
        except Exception as e:
            logging.error(f"Error starting camera: {e}")
            return False
    
    def _capture_loop(self):
        """Background thread loop to capture frames at the specified FPS"""
        interval = 1.0 / FPS
        while self.running:
            try:
                # Capture frame
                frame = self.camera.capture_array()
                
                # Update latest frame with lock protection
                with self.frame_lock:
                    self.latest_frame = frame
                    
                    # Add to buffer, removing oldest if full
                    if self.frame_buffer.full():
                        try:
                            self.frame_buffer.get_nowait()  # Remove oldest frame
                        except queue.Empty:
                            pass  # Buffer was emptied by another thread
                    
                    try:
                        self.frame_buffer.put_nowait(frame)
                    except queue.Full:
                        pass  # Someone else filled the buffer
                
                # Sleep to maintain desired FPS
                time.sleep(interval)
            except Exception as e:
                logging.error(f"Error in camera capture loop: {e}")
                time.sleep(1)  # Prevent tight error loops
    
    def capture_frame(self):
        """
        Capture the latest frame from the camera.
        
        This method returns the most recent frame captured by the camera.
        If the camera is not available or an error occurs, it returns None.
        
        Returns:
            numpy.ndarray or None: The captured frame as a numpy array, or None on failure
        """
        if not self.running:
            if not self.start():
                return None
        
        with self.frame_lock:
            if self.latest_frame is not None:
                return self.latest_frame.copy()  # Return a copy to prevent modification
        
        return None
    
    def get_jpeg_frame(self):
        """
        Get the latest frame as a JPEG-encoded byte array.
        
        This is useful for web streaming and API endpoints that need
        JPEG format images rather than raw numpy arrays.
        
        Returns:
            bytes or None: JPEG-encoded image data, or None on failure
        """
        frame = self.capture_frame()
        if frame is None:
            return None
            
        try:
            _, buffer = cv2.imencode('.jpg', frame)
            return buffer.tobytes()
        except Exception as e:
            logging.error(f"Error encoding frame to JPEG: {e}")
            return None
    
    def stop(self):
        """
        Stop the camera and release resources.
        
        This stops the frame capture thread and camera hardware,
        releasing all associated resources.
        
        Returns:
            bool: True if successfully stopped, False otherwise
        """
        if not self.running:
            return True
            
        try:
            self.running = False
            
            # Stop the capture thread
            if self.capture_thread and self.capture_thread.is_alive():
                self.capture_thread.join(timeout=3.0)
                if self.capture_thread.is_alive():
                    logging.warning("Camera capture thread did not terminate cleanly")
            
            # Stop the camera
            if self.camera:
                self.camera.stop()
                
            # Clear buffer
            with self.frame_lock:
                self.latest_frame = None
                while not self.frame_buffer.empty():
                    try:
                        self.frame_buffer.get_nowait()
                    except queue.Empty:
                        break
            
            logging.info("Camera stopped")
            return True
        except Exception as e:
            logging.error(f"Error stopping camera: {e}")
            return False
    
    def __del__(self):
        """Ensure camera resources are cleaned up on object destruction"""
        self.stop()


# Module-level singleton instance and accessor functions
_camera_instance = None

def get_camera_instance():
    """
    Get the camera instance singleton.
    
    This function provides access to the camera singleton instance,
    ensuring that all components access the same camera resource.
    
    Returns:
        CameraInstance: The singleton camera instance
    """
    global _camera_instance
    if _camera_instance is None:
        _camera_instance = CameraInstance()
        _camera_instance.start()
    return _camera_instance

def capture_frame():
    """
    Capture a frame from the camera.
    
    This is a convenience function for getting a single frame from the camera.
    
    Returns:
        numpy.ndarray or None: The captured frame, or None if unavailable
    """
    camera = get_camera_instance()
    return camera.capture_frame()

def get_jpeg_frame():
    """
    Get a JPEG-encoded frame from the camera.
    
    This is a convenience function for getting a JPEG-encoded frame.
    
    Returns:
        bytes or None: JPEG-encoded image data, or None if unavailable
    """
    camera = get_camera_instance()
    return camera.get_jpeg_frame()

def start_server_thread():
    """
    Start the camera server thread.
    
    This function starts the camera and ensures it's capturing frames.
    It's used for initializing the camera system when the web UI starts.
    
    Returns:
        bool: True if camera started successfully, False otherwise
    """
    camera = get_camera_instance()
    return camera.start()
