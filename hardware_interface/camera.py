import io
import os
import time
import threading
from threading import Condition
from http import server
from picamera2 import PiCamera2 as PiCamera
import numpy as np
import tflite_runtime.interpreter as tflite
from dotenv import load_dotenv
import requests
import logging
from utilities import LoggerConfigInfo as LoggerConfig

# Initialize logger
logging = LoggerConfig.get_logger(__name__)

# Load environment variables from .env file
load_dotenv()
PATH_TO_OBJECT_DETECTION_MODEL = os.getenv("OBSTACLE_MODEL_PATH")
PI5_IP = os.getenv("OBJECT_DETECTION_IP")  # IP address of the Pi 5

# Initialize TFLite interpreter for local detection
interpreter = tflite.Interpreter(model_path=PATH_TO_OBJECT_DETECTION_MODEL)
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()
height = input_details[0]['shape'][1]
width = input_details[0]['shape'][2]
floating_model = (input_details[0]['dtype'] == np.float32)
input_mean = 127.5
input_std = 127.5

# Load labels
LABEL_MAP_PATH = os.getenv("LABEL_MAP_PATH")  # Add this to your .env
with open(LABEL_MAP_PATH, 'r') as f:
    labels = [line.strip() for line in f.readlines()]
if labels[0] == '???':
    del(labels[0])

# Camera settings
camera = PiCamera()
camera.resolution = (640, 480)
camera.framerate = 24
output = None

# A flag to indicate whether to use remote detection
use_remote_detection = True

# Condition variable for thread synchronization
frame_condition = Condition()
frame = None

class StreamingOutput(object):
    def __init__(self):
        self.frame = None
        self.buffer = io.BytesIO()
        self.condition = Condition()
        self.running = True

    def write(self, buf):
        if buf.startswith(b'\xff\xd8'):
            # New frame, copy the existing buffer's content and notify all clients it's available
            self.buffer.truncate()
            with self.condition:
                self.frame = self.buffer.getvalue()
                self.condition.notify_all()
            self.buffer.seek(0)
        return self.buffer.write(buf)

output = StreamingOutput()
camera.start_recording(output, format='mjpeg')

def detect_obstacles_local(image):
    """Perform local TFLite detection on the image."""
    frame_rgb = np.array(image)
    frame_resized = cv2.resize(frame_rgb, (width, height))
    input_data = np.expand_dims(frame_resized, axis=0)
    if floating_model:
        input_data = (np.float32(input_data) - input_mean) / input_std
    interpreter.set_tensor(input_details[0]['index'], input_data)
    interpreter.invoke()
    boxes = interpreter.get_tensor(output_details[0]['index'])[0]  # Bounding box coordinates
    classes = interpreter.get_tensor(output_details[1]['index'])[0]  # Class index
    scores = interpreter.get_tensor(output_details[2]['index'])[0]  # Confidence scores
    min_conf_threshold = float(os.getenv('MIN_CONF_THRESHOLD', '0.5'))
    detected_objects = []
    for i in range(len(scores)):
        if ((scores[i] > min_conf_threshold) and (scores[i] <= 1.0)):
            object_name = labels[int(classes[i])]
            detected_objects.append({'name': object_name, 'score': scores[i]})
    return detected_objects

def detect_obstacles_remote(image):
    """Send the image to Pi 5 for remote detection."""
    try:
        # Convert image to bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG')
        img_bytes = img_byte_arr.getvalue()

        response = requests.post(f'http://{PI5_IP}:5000/detect',
                                 files={'image': ('image.jpg', img_bytes, 'image/jpeg')},
                                 timeout=1)
        if response.status_code == 200:
            result = response.json()
            return result.get('obstacle_detected', False)
        else:
            logging.warning("Failed to get a valid response from Pi 5.")
            return False
    except (requests.ConnectionError, requests.Timeout):
        logging.warning("Pi 5 not reachable. Falling back to local detection.")
        global use_remote_detection
        use_remote_detection = False
        return False

def process_frame():
    """Process frames for obstacle detection."""
    while True:
        with output.condition:
            output.condition.wait()
            frame = output.frame
        image = Image.open(io.BytesIO(frame))
        if use_remote_detection:
            obstacle_detected = detect_obstacles_remote(image)
        else:
            obstacle_detected = detect_obstacles_local(image)
        # Use obstacle_detected flag in your robot control logic

def start_processing():
    thread = threading.Thread(target=process_frame)
    thread.daemon = True
    thread.start()

class StreamingHandler(server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/video_feed':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    with output.condition:
                        output.condition.wait()
                        frame = output.frame
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
            except Exception as e:
                logging.warning('Removed streaming client %s: %s', self.client_address, str(e))
        else:
            self.send_error(404)
            self.end_headers()

def start_streaming_server():
    address = ('', 8000)
    server_instance = server.ThreadingHTTPServer(address, StreamingHandler)
    server_thread = threading.Thread(target=server_instance.serve_forever)
    server_thread.daemon = True
    server_thread.start()

if __name__ == "__main__":
    start_processing()
    start_streaming_server()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        camera.stop_recording()
