import io
import os
import time
import threading
from threading import Condition
import numpy as np
import tflite_runtime.interpreter as tflite
from dotenv import load_dotenv
import requests
from PIL import Image, ImageDraw, ImageFont

from utilities import LoggerConfigInfo as LoggerConfig
from hardware_interface.camera_instance import get_camera_instance

# Initialize logger
logging = LoggerConfig.get_logger(__name__)

# Load environment variables from .env file
load_dotenv()
PATH_TO_OBJECT_DETECTION_MODEL = os.getenv("OBSTACLE_MODEL_PATH")
PI5_IP = os.getenv("OBJECT_DETECTION_IP")  # IP address of the Pi 5
LABEL_MAP_PATH = os.getenv("LABEL_MAP_PATH")  # Path to label map file
MIN_CONF_THRESHOLD = float(os.getenv('MIN_CONF_THRESHOLD', '0.5'))

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
with open(LABEL_MAP_PATH, 'r') as f:
    labels = [line.strip() for line in f.readlines()]
if labels[0] == '???':
    del(labels[0])

# Get the camera instance
camera = get_camera_instance()

# A flag to indicate whether to use remote detection
use_remote_detection = True

# Condition variable for thread synchronization
frame_condition = Condition()
frame = None


def capture_frames():
    """Capture frames from Picamera2 and process them."""
    while True:
        # Capture the frame
        frame = camera.capture_array()
        # Process the frame
        processed_frame = process_frame(frame)
        # Encode the frame as JPEG
        img = Image.fromarray(processed_frame)
        buf = io.BytesIO()
        img.save(buf, format='JPEG')


def detect_obstacles_local(image):
    """Perform local image classification using TFLite."""
    # Resize the image to the required input size
    image_resized = image.resize((width, height))
    input_data = np.expand_dims(image_resized, axis=0)
    if floating_model:
        input_data = (np.float32(input_data) - input_mean) / input_std
    else:
        input_data = np.uint8(input_data)
    interpreter.set_tensor(input_details[0]['index'], input_data)
    interpreter.invoke()
    # Get the output probabilities
    output_data = interpreter.get_tensor(output_details[0]['index'])[0]
    # Get the top predicted class index
    top_k = 1  # You can get more predictions by increasing this value
    top_indices = np.argsort(-output_data)[:top_k]
    detected_objects = []
    for idx in top_indices:
        class_name = labels[idx]
        score = output_data[idx]
        detected_objects.append({'name': class_name, 'score': score})
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

def process_frame(frame):
    """Process frames for obstacle detection and annotate them."""
    image = Image.fromarray(frame)
    if use_remote_detection:
        obstacle_detected = detect_obstacles_remote(image)
    else:
        detected_objects = detect_obstacles_local(image)
        # Draw bounding boxes on the image
        draw = ImageDraw.Draw(image)
        for obj in detected_objects:
            xmin, ymin, xmax, ymax = obj['box']
            draw.rectangle([xmin, ymin, xmax, ymax], outline='red', width=2)
            label = f"{obj['name']}: {int(obj['score'] * 100)}%"
            # Optional: Use a truetype font if available
            try:
                font = ImageFont.truetype("arial.ttf", 15)
            except IOError:
                font = ImageFont.load_default()
            text_size = draw.textsize(label, font=font)
            text_location = (xmin + 5, ymin + 5)
            draw.rectangle([xmin, ymin, xmin + text_size[0] + 10, ymin + text_size[1] + 10],
                           fill='red')
            draw.text(text_location, label, fill='white', font=font)
        obstacle_detected = len(detected_objects) > 0
    # You can use obstacle_detected flag in your robot control logic
    return np.array(image)

def start_processing():
    thread = threading.Thread(target=capture_frames)
    thread.daemon = True
    thread.start()


if __name__ == "__main__":
    start_processing()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        camera.stop()
