"""
Local obstacle detection module.

This module provides functions for detecting obstacles and drops using the
camera.
"""

import io
import os
import threading
import time
from threading import Condition
from typing import Optional, Tuple

import cv2
import numpy as np
import requests
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

from mower.hardware.camera_instance import get_camera_instance
from mower.utilities.logger_config import LoggerConfigInfo as LoggerConfig

# Initialize logger
logger = LoggerConfig.get_logger(__name__)

# Load environment variables from .env file
load_dotenv()
PATH_TO_OBJECT_DETECTION_MODEL = os.getenv("OBSTACLE_MODEL_PATH")
PI5_IP = os.getenv("OBJECT_DETECTION_IP")  # IP address for remote detection
LABEL_MAP_PATH = os.getenv("LABEL_MAP_PATH")  # Path to label map file
MIN_CONF_THRESHOLD = float(os.getenv('MIN_CONF_THRESHOLD', '0.5'))
USE_REMOTE_DETECTION = os.getenv(
    'USE_REMOTE_DETECTION',
    'False').lower() == 'true'

# Global variables for resource management
_resource_manager = None
_interpreter = None
_input_details = None
_output_details = None
_height = 0
_width = 0
_floating_model = False
input_mean = 127.5
input_std = 127.5

# Load labels
with open(LABEL_MAP_PATH, 'r') as f:
    labels = [line.strip() for line in f.readlines()]
if labels[0] == '???':
    del labels[0]

# Get the camera instance
camera = get_camera_instance()

# A flag to indicate whether to use remote detection
use_remote_detection = USE_REMOTE_DETECTION

# Condition variable for thread synchronization
frame_condition = Condition()
frame = None
frame_lock = threading.Lock()


def initialize_with_resource_manager(resource_manager):
    """
    Initialize the obstacle detection module with a ResourceManager
    instance.

    This allows the detection to use an interpreter (CPU or Edge TPU)
    that's already been initialized by the ResourceManager.

    Args:
        resource_manager: The ResourceManager instance to use
    """
    global _resource_manager, _interpreter, _input_details
    global _output_details, _height, _width, _floating_model

    logger.info("Initializing obstacle detection with ResourceManager")
    _resource_manager = resource_manager

    # Get model details from ResourceManager
    _interpreter = _resource_manager.get_inference_interpreter()
    if _interpreter:
        _input_details = _resource_manager.get_model_input_details()
        _output_details = _resource_manager.get_model_output_details()
        _height, _width = _resource_manager.get_model_input_size()

        # Check if floating point model
        if _input_details and len(_input_details) > 0:
            _floating_model = (_input_details[0]['dtype'] == np.float32)

        interpreter_type = _resource_manager.get_interpreter_type()
        logger.info(
            f"Using {interpreter_type} for obstacle detection inference")
    else:
        # Fallback to direct initialization
        _initialize_local_interpreter()


def _initialize_local_interpreter():
    """
    Initialize the TFLite interpreter directly if ResourceManager is not
    available.

    This is a fallback method when the obstacle detection module is used
    as a standalone component without ResourceManager integration.
    """
    global _interpreter, _input_details, _output_details
    global _height, _width, _floating_model

    logger.info("Fallback: Initializing local TFLite interpreter directly")

    # Import tflite_runtime for direct initialization
    import tflite_runtime.interpreter as tflite

    try:
        # Initialize TFLite interpreter for local detection
        _interpreter = tflite.Interpreter(
            model_path=PATH_TO_OBJECT_DETECTION_MODEL)
        _interpreter.allocate_tensors()
        _input_details = _interpreter.get_input_details()
        _output_details = _interpreter.get_output_details()
        _height = _input_details[0]['shape'][1]
        _width = _input_details[0]['shape'][2]
        _floating_model = (_input_details[0]['dtype'] == np.float32)
        logger.info(
            f"TFLite model loaded with input size: {_height}x{_width}")
    except Exception as e:
        logger.error(f"Failed to initialize TFLite interpreter: {e}")
        _interpreter = None


def _ensure_interpreter():
    """
    Ensure that the interpreter is initialized.

    This function checks if the interpreter is initialized, and if not,
    attempts to initialize it using the fallback method.

    Returns:
        bool: True if interpreter is initialized, False otherwise
    """
    global _interpreter

    if _interpreter is not None:
        return True

    # Try to initialize if not already done
    if _resource_manager is not None:
        _interpreter = _resource_manager.get_inference_interpreter()
        return _interpreter is not None
    else:
        _initialize_local_interpreter()
        return _interpreter is not None


def detect_obstacles_local(image):
    """
    Perform local image classification using TFLite.
    Args:
        image: The image to perform obstacle detection on.
    Returns:
        A list of detected objects, each containing the name and score.
    """
    if not _ensure_interpreter():
        logger.error("TFLite interpreter not available for object detection")
        return []

    image_resized = image.resize((_width, _height))
    input_data = np.expand_dims(image_resized, axis=0)
    if len(input_data.shape) == 4 and input_data.shape[-1] != 3:
        input_data = input_data[:, :, :, :3]
    if _floating_model:
        input_data = (np.float32(input_data) - input_mean) / input_std
    else:
        input_data = np.uint8(input_data)
    _interpreter.set_tensor(_input_details[0]['index'], input_data)
    _interpreter.invoke()

    output_data = _interpreter.get_tensor(_output_details[0]['index'])[0]
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
    image_resized = cv2.resize(image, (_width, _height))
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

        response = requests.post(
            f'http://{PI5_IP}:5000/detect',
            files={'image': ('image.jpg', img_bytes, 'image/jpeg')},
            timeout=1
            )
        if response.status_code == 200:
            result = response.json()
            return result.get('obstacle_detected', False)
        else:
            logger.warning("Failed to get a valid response from Pi 5.")
            return False
    except (requests.ConnectionError, requests.Timeout):
        logger.warning("Pi 5 not reachable. Retrying before "
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


def detect_obstacle(frame: np.ndarray) -> Tuple[bool, Optional[np.ndarray]]:
    """
    Detect obstacles in the given frame.

    Args:
        frame: The input frame to process

    Returns:
        Tuple[bool, Optional[np.ndarray]]: (obstacle_detected,
                                           processed_frame)
    """
    if frame is None:
        return False, None

    try:
        # Convert to grayscale for processing
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Use Canny edge detection
        edges = cv2.Canny(blurred, 50, 150)

        # Find contours
        contours, _ = cv2.findContours(
            edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Filter contours by size
        min_area = 1000  # Minimum contour area to consider
        large_contours = [c for c in contours if cv2.contourArea(c) > min_area]

        # Draw contours on original frame
        frame_with_contours = frame.copy()
        cv2.drawContours(
            frame_with_contours, large_contours, -1, (0, 255, 0), 2)

        # Consider it an obstacle if we find any large contours
        return bool(large_contours), frame_with_contours

    except Exception as e:
        logger.error(f"Error in obstacle detection: {e}")
        return False, None


def detect_drop(frame: np.ndarray) -> Tuple[bool, Optional[np.ndarray]]:
    """
    Detect potential drops (cliffs) in the given frame.

    Args:
        frame: The input frame to process

    Returns:
        Tuple[bool, Optional[np.ndarray]]: (drop_detected,
                                           processed_frame)
    """
    if frame is None:
        return False, None

    try:
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Apply threshold to identify dark areas (potential drops)
        _, thresh = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY)

        # Find contours of dark areas
        contours, _ = cv2.findContours(
            thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Filter contours by size
        min_area = 2000  # Minimum area to consider as a drop
        large_contours = [c for c in contours if cv2.contourArea(c) > min_area]

        # Draw contours on original frame
        frame_with_contours = frame.copy()
        cv2.drawContours(
            frame_with_contours, large_contours, -1, (0, 0, 255), 2)

        # Consider it a drop if we find any large dark areas
        return bool(large_contours), frame_with_contours

    except Exception as e:
        logger.error(f"Error in drop detection: {e}")
        return False, None


def stream_frame_with_overlays() -> Optional[bytes]:
    """
    Get a frame with obstacle and drop detection overlays.

    Returns:
        Optional[bytes]: JPEG encoded frame with overlays or None if not
                        available
    """
    try:
        # Get camera instance
        camera = get_camera_instance()

        # Capture frame
        frame_data = camera.capture_frame()
        if frame_data is None:
            return None

        # Convert JPEG to numpy array
        frame = cv2.imdecode(
            np.frombuffer(
                frame_data,
                np.uint8),
            cv2.IMREAD_COLOR)
        if frame is None:
            return None

        # Run detections
        obstacle_detected, obstacle_frame = detect_obstacle(frame)
        drop_detected, drop_frame = detect_drop(
            frame if obstacle_frame is None else obstacle_frame)

        # Use the most processed frame available
        final_frame = drop_frame if drop_frame is not None else (
            obstacle_frame if obstacle_frame is not None else frame
            )

        # Add text overlays
        if obstacle_detected:
            cv2.putText(final_frame, "OBSTACLE DETECTED", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        if drop_detected:
            cv2.putText(final_frame, "DROP DETECTED", (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        # Convert back to JPEG
        _, jpeg_data = cv2.imencode('.jpg', final_frame)
        return jpeg_data.tobytes()

    except Exception as e:
        logger.error(f"Error in stream frame with overlays: {e}")
        return None


def capture_frames():
    """
    Capture frames from Picamera2 and process them.
    This function runs continuously and calls the `process_frame`
    function on each captured frame.
    """
    while True:
        frame = camera.capture_frame()
        processed_frame = process_frame(frame)
        with frame_lock:
            saved_frame = processed_frame.copy()
        img = Image.fromarray(saved_frame)
        buf = io.BytesIO()
        """ Ensure all images are properly converted
            before saving to prevent errors """
        img = img.convert('RGB')
        img.save(buf, format='JPEG')


if __name__ == "__main__":
    start_processing()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        camera.stop()
