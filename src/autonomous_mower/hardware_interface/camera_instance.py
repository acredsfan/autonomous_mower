import os
import socket
import threading

import cv2
from dotenv import load_dotenv
from picamera2 import Picamera2  # type: ignore

from src.autonomous_mower.utilities import LoggerConfigInfo as LoggerConfig

# Load environment variables
load_dotenv()

# Initialize logger
logging = LoggerConfig.get_logger(__name__)

FPS = int(os.getenv('STREAMING_FPS', 15))
STREAMING_RESOLUTION = os.getenv('STREAMING_RESOLUTION', '640x480')
WIDTH, HEIGHT = map(int, STREAMING_RESOLUTION.split('x'))


def get_device_ip():
    """
    Get the IP address of the device on the local network.
    This function uses a UDP socket to determine the device's IP
    without sending any actual data.
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


# Get the device's IP dynamically
DEVICE_IP = get_device_ip()

# Initialize Picamera2 instance and configure camera settings
camera = Picamera2()

# Set the camera resolution to 1280x720
camera_config = camera.create_video_configuration({"size": (WIDTH, HEIGHT)})
camera.configure(camera_config)

# Set up the encoder with a bitrate of 1 Mbps
frame_lock = threading.Lock()
latest_frame = None


def start_server_thread():
    """
    Start the server thread for streaming.
    This function starts the camera recording and sends the
    stream to the designated IP and port.
    """
    try:
        camera.start()
        logging.info(
            f"Camera started with resolution {WIDTH}x{HEIGHT} at {FPS} FPS"
        )
    except Exception as e:
        logging.error(f"Error starting camera: {e}")


def capture_frame():
    """Capture the latest frame from the camera and convert to JPEG."""
    global latest_frame
    with frame_lock:
        try:
            frame = camera.capture_array()
            if frame is not None:
                _, buffer = cv2.imencode('.jpg', frame)
                latest_frame = buffer.tobytes()
                # logging.info("Captured frame successfully")
            else:
                logging.warning("No frame captured")
        except Exception as e:
            logging.error(f"Error capturing frame: {e}")
    return latest_frame


def get_camera_instance():
    """
    Get the camera instance and start the server thread.
    This function returns the initialized Picamera2 instance
    and also starts the UDP streaming process.
    """
    start_server_thread()
    capture_frame()
    return camera
