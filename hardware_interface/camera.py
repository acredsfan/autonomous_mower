import numpy as np
import threading
from queue import Queue, Empty
import tflite_runtime.interpreter as tflite
from picamera2 import Picamera2
from dotenv import load_dotenv
import os
import cv2
from utilities import LoggerConfigInfo as LoggerConfig
import socket
import requests
from flask import Flask, Response

# Initialize logger
logging = LoggerConfig.get_logger(__name__)

# Load environment variables from .env file
load_dotenv()

# Retrieve the path to the object detection model from the .env file
PATH_TO_OBJECT_DETECTION_MODEL = os.getenv("OBSTACLE_MODEL_PATH")

# Flask app for video stream
app = Flask(__name__)


class SingletonCamera:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SingletonCamera, cls).__new__(cls)
                cls._instance.init_camera()
        return cls._instance

    def init_camera(self):
        """Initialize the camera using Picamera2 and start the update thread."""
        self.frame_queue = Queue(maxsize=1)
        self.picam2 = Picamera2()
        self.picam2.configure(self.picam2.create_video_configuration(main={"size": (640, 480)}))
        self.picam2.start()
        self.running = True
        self.read_thread = threading.Thread(target=self.update, daemon=True)
        self.read_thread.start()
        self.queue_lock = threading.Lock()

    def update(self):
        """Capture frames from the camera."""
        while self.running:
            frame = self.picam2.capture_array()
            if frame is None:
                logging.warning("Failed to read frame from camera. Attempting reinitialization.")
                self.reinitialize_camera()
                continue

            with self.queue_lock:
                if not self.frame_queue.empty():
                    try:
                        self.frame_queue.get_nowait()
                    except Empty:
                        pass
                self.frame_queue.put(frame)

    def get_frame(self):
        """Get the latest frame from the camera."""
        with self.queue_lock:
            try:
                return self.frame_queue.get_nowait()
            except Empty:
                return None

    def stream_video(self):
        while True:
            frame = self.picam2.capture_array()
            _, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

    def detect_obstacle(self):
        """Attempt to detect obstacles via Pi 5. Fallback to local detection if necessary."""
        frame = self.get_frame()
        if frame is None:
            logging.warning("No frame available for detection.")
            return False

        try:
            # Try sending frame to Pi 5 for remote obstacle detection
            response = requests.post('http://<PI5_IP>:5000/detect', files={'image': frame})
            if response.status_code == 200:
                logging.info(f"Obstacle detected remotely: {response.json()}")
                return response.json().get('obstacle_detected', False)
        except requests.ConnectionError:
            logging.warning("Pi 5 not reachable. Falling back to local detection.")

        # Fallback to local obstacle detection using TFLite
        return self.local_obstacle_detection(frame)

    def local_obstacle_detection(self, frame):
        """Run obstacle detection locally using TFLite model."""
        # Add code here to run detection with TFLite interpreter on the Pi 4
        results = self.detect_objects(frame)
        if results:
            logging.info(f"Local obstacle detected: {results}")
            return True
        else:
            logging.info("No local obstacles detected.")
            return False

    def detect_objects(self, image):
        """Run inference with TFLite and detect objects."""
        # You can use the existing TFLite detection code here
        detected_objects = []
        # Add logic for TFLite model inference and returning results
        return detected_objects


    def object_detected_flag(self):
        ''' Check if either remote or local obstacle detection has detected an obstacle and
        return a flag that avoidance algorithm can use to avoid the obstacle'''
        # Check if obstacle is detected by either remote or local detection
        if self.detect_obstacle():
            return True
        return False


# Singleton accessor function
camera_instance = SingletonCamera()


def get_camera_instance():
    """Accessor function to get the SingletonCamera instance."""
    return camera_instance

# Flask route to serve the video stream
@app.route('/video_feed')
def video_feed():
    return Response(camera_instance.stream_video(), mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == "__main__":
    # Start Flask server for video streaming
    app.run(host='0.0.0.0', port=8000)
