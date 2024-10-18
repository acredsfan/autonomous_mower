import io
import os
import threading
import time
from threading import Condition

import cv2
import numpy as np
import requests
import tflite_runtime.interpreter as tflite  # type: ignore
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

from hardware_interface.camera_instance import (
    capture_frame,
    get_camera_instance
    )
from autonomous_mower.utilities import LoggerConfigInfo as LoggerConfig

# Initialize logger
logging = LoggerConfig.get_logger(__name__)

# Load environment variables from .env file
load_dotenv()
PATH_TO_OBJECT_DETECTION_MODEL = os.getenv("OBSTACLE_MODEL_PATH")
PI5_IP = os.getenv("OBJECT_DETECTION_IP")  # IP address for remote detection
LABEL_MAP_PATH = os.getenv("LABEL_MAP_PATH")  # Path to label map file
MIN_CONF_THRESHOLD = float(os.getenv('MIN_CONF_THRESHOLD', '0.5'))
USE_REMOTE_DETECTION = os.getenv('USE_REMOTE_DETECTION', 'False').lower() == \
    'true'

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
    del labels[0]

# Get the camera instance
camera = get_camera_instance()

# A flag to indicate whether to use remote detection (default to True)
use_remote_detection = USE_REMOTE_DETECTION

# Condition variable for thread synchronization
frame_condition = Condition()
frame = None
frame_lock = threading.Lock()


def capture_frames():
    """
    Capture frames from Picamera2 and process them.
    This function runs continuously and calls the `process_frame`
    function on each captured frame.
    """
    while True:
        frame = capture_frame()
        processed_frame = process_frame(frame)
        with frame_lock:
            saved_frame = processed_frame.copy()
        img = Image.fromarray(saved_frame)
        buf = io.BytesIO()
        """ Ensure all images are properly converted
            before saving to prevent errors """
        img = img.convert('RGB')
        img.save(buf, format='JPEG')


def detect_obstacles_local(image):
    """
    Perform local image classification using TFLite.
    Args:
        image: The image to perform obstacle detection on.
    Returns:
        A list of detected objects, each containing the name and score.
    """
    image_resized = image.resize((width, height))
    input_data = np.expand_dims(image_resized, axis=0)
    if len(input_data.shape) == 4 and input_data.shape[-1] != 3:
        input_data = input_data[:, :, :, :3]
    if floating_model:
        input_data = (np.float32(input_data) - input_mean) / input_std
    else:
        input_data = np.uint8(input_data)
    interpreter.set_tensor(input_details[0]['index'], input_data)
    interpreter.invoke()

    output_data = interpreter.get_tensor(output_details[0]['index'])[0]
    top_k = 1  # Top prediction
    top_indices = np.argsort(-output_data)[:top_k]
    detected_objects = []
    for idx in top_indices:
        class_name = labels[idx]
        score = output_data[idx]
        if score >= MIN_CONF_THRESHOLD:
            detected_objects.append({'name': class_name, 'score': score})
    return detected_objects


def detect_drops_local(image):
    """
    Use OpenCV to detect drops in the yard.
    Args:
        image: The image to perform drop detection on.
    Returns:
        A boolean indicating if a drop was detected.
    """
    image_resized = cv2.resize(image, (width, height))
    edges = cv2.Canny(image_resized, 100, 200)
    contours, _ = cv2.findContours(edges,
                                   cv2.RETR_TREE,
                                   cv2.CHAIN_APPROX_SIMPLE)
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > 1000:
            return True
    return False


def detect_obstacles_remote(image):
    """
    Send the image to Pi 5 for remote detection.
    Args:
        image: The image to send for remote detection.
    Returns:
        A boolean indicating if an obstacle was detected.
    """
    try:
        img_byte_arr = io.BytesIO()
        image = image.convert('RGB')
        image.save(img_byte_arr, format='JPEG')
        img_bytes = img_byte_arr.getvalue()

        response = requests.post(f'http://{PI5_IP}:5000/detect',
                                 files={'image': ('image.jpg', img_bytes,
                                                  'image/jpeg')},
                                 timeout=1)
        if response.status_code == 200:
            result = response.json()
            return result.get('obstacle_detected', False)
        else:
            logging.warning("Failed to get a valid response from Pi 5.")
            return False
    except (requests.ConnectionError, requests.Timeout):
        logging.warning("Pi 5 not reachable. Retrying before"
                        "falling back to local detection.")
        global use_remote_detection
        use_remote_detection = False
        return False


def process_frame(frame):
    """
    Process frames for obstacle detection and annotate them.
    Args:
        frame: The captured frame to process.
    Returns:
        The annotated frame with detected objects.
    """
    if isinstance(frame, bytes):
        frame = np.frombuffer(frame, dtype=np.uint8)
        frame = frame.reshape((camera.height, camera.width, 3))

    image = Image.fromarray(frame)
    if use_remote_detection:
        detect_obstacles_remote(image)
    else:
        detected_objects = detect_obstacles_local(image)
        draw = ImageDraw.Draw(image)
        for obj in detected_objects:
            # Placeholder for bounding box drawing; adjust for your model
            label = f"{obj['name']}: {int(obj['score'] * 100)}%"
            try:
                font = ImageFont.truetype("arial.ttf", 15)
            except IOError:
                font = ImageFont.load_default()
            draw.text((10, 10), label, fill='red', font=font)
        len(detected_objects) > 0
    return np.array(image)


def start_processing():
    """
    Start the frame processing thread.
    """
    thread = threading.Thread(target=capture_frames)
    thread.start()


# Create Global Object Detected Flag
object_detected = False


def detect_obstacle():
    """
    Check if remote detection or local detection is enabled
    then check if an obstacle is detected on either detect_obstacles_remote
    or detect_obstacles_local.
    """
    global object_detected
    with frame_lock:
        frame = capture_frame()
    image = Image.fromarray(frame)
    if use_remote_detection:
        object_detected = detect_obstacles_remote(image)
    else:
        detected_objects = detect_obstacles_local(image)
        object_detected = len(detected_objects) > 0
    return object_detected


drop_detected = False


def detect_drop():
    """
    Check if detect_drops_local has detected a drop in the yard.
    Then update the global drop_detected flag.
    """
    global drop_detected
    with frame_lock:
        frame = capture_frame()
    image = Image.fromarray(frame)
    drop_detected = detect_drops_local(image)
    return drop_detected


def draw_object_boxes_local():
    """
    Draw bounding boxes around detected objects.
    """
    global object_detected
    with frame_lock:
        frame = capture_frame()
    image = Image.fromarray(frame)
    detected_objects = detect_obstacles_local(image)
    draw = ImageDraw.Draw(image)
    for obj in detected_objects:
        # Placeholder for bounding box drawing; adjust for your model
        label = f"{obj['name']}: {int(obj['score'] * 100)}%"
        try:
            font = ImageFont.truetype("arial.ttf", 15)
        except IOError:
            font = ImageFont.load_default()
        draw.text((10, 10), label, fill='red', font=font)
    return np.array(image)


def draw_object_boxes_remote():
    """
    Draw bounding boxes around detected objects.
    """
    global object_detected
    with frame_lock:
        frame = capture_frame()
    image = Image.fromarray(frame)
    object_detected = detect_obstacles_remote(image)
    return np.array(image)


def draw_drop_lines():
    """
    Draw lines around detected drops.
    """
    global drop_detected
    with frame_lock:
        frame = capture_frame()
    image = Image.fromarray(frame)
    drop_detected = detect_drops_local(image)
    return np.array(image)


def overlay_text(image, text):
    """
    Overlay text on the image.
    Args:
        image: The image to overlay text on.
        text: The text to overlay on the image.
    Returns:
        The image with the text overlay.
    """
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("arial.ttf", 15)
    except IOError:
        font = ImageFont.load_default()
    draw.text((10, 10), text, fill='red', font=font)
    return image


def stream_frame_with_overlays():
    """
    Stream frames with overlays for objects and drops.
    """
    global object_detected, drop_detected
    with frame_lock:
        frame = capture_frame()
    image = Image.fromarray(frame)
    if use_remote_detection:
        image = draw_object_boxes_remote()
    else:
        image = draw_object_boxes_local()
    if drop_detected:
        image = overlay_text(image, "Drop detected!")
    return image


if __name__ == "__main__":
    start_processing()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        camera.stop()
