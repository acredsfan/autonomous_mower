from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FfmpegOutput

# Initialize Picamera2 instance
camera = Picamera2()
camera_config = camera.create_video_configuration(main={"size": (1280, 720)})
camera.configure(camera_config)
encoder = H264Encoder(1000000)
# Set output of UDP stream to the Device's IP, Port 8000
output = FfmpegOutput("-f rtp udp://{}:8000")
camera.start()

def start_server_thread():
    """Start the server thread for streaming."""
    camera.start_recording(encoder, output)


def get_camera_instance():
    """Get the camera instance and start server thread."""
    start_server_thread()
    return camera
