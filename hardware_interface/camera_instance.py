from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput
import socket
from dotenv import load_dotenv
import os
from utilities import LoggerConfigInfo as LoggerConfig

# Initialize logger
logging = LoggerConfig.get_logger(__name__)

# Load environment variables from .env file (for configurable UDP port)
load_dotenv()

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
camera_config = camera.create_video_configuration({"size": (1280, 720)})
camera.configure(camera_config)

# Set up the encoder with a bitrate of 1 Mbps
encoder = H264Encoder(1000000)


def start_server_thread():
    """
    Start the server thread for streaming.
    This function starts the camera recording and sends the
    stream to the designated IP and port.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.connect((DEVICE_IP, 8080))
        stream = sock.makefile('wb')
        camera.start_recording(encoder, FileOutput(stream))


def get_camera_instance():
    """
    Get the camera instance and start the server thread.
    This function returns the initialized Picamera2 instance
    and also starts the UDP streaming process.
    """
    start_server_thread()
    return camera
