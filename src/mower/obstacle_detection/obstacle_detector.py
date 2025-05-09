"""
Obstacle detection module for autonomous mower.

This module provides comprehensive obstacle detection capabilities using:
1. TensorFlow Lite models for ML-based object detection
2. OpenCV for basic image processing and drop detection
3. Support for both local and remote (Pi 5) detection
4. Integration with Edge TPU when available
"""

import io
import os
import threading
import time
from threading import Condition
from typing import List, Tuple

import cv2
import numpy as np
import requests
from dotenv import load_dotenv
from PIL import Image

from mower.hardware.camera_instance import get_camera_instance, capture_frame
from mower.utilities.logger_config import LoggerConfig

# Initialize logger
logger = LoggerConfig.get_logger(__name__)

# Load environment variables
load_dotenv()
PATH_TO_OBJECT_DETECTION_MODEL = os.getenv("OBSTACLE_MODEL_PATH")
PI5_IP = os.getenv("OBJECT_DETECTION_IP")  # IP address for remote detection
LABEL_MAP_PATH = os.getenv("LABEL_MAP_PATH")  # Path to label map file
MIN_CONF_THRESHOLD = float(os.getenv('MIN_CONF_THRESHOLD', '0.5'))
USE_REMOTE_DETECTION = os.getenv(
    'USE_REMOTE_DETECTION',
    'False').lower() == 'true'

# Load labels if available
labels = []
if LABEL_MAP_PATH and os.path.exists(LABEL_MAP_PATH):
    try:
        with open(LABEL_MAP_PATH, 'r') as f:
            labels = [line.strip() for line in f.readlines()]
        if labels and labels[0] == '???':
            del labels[0]
        logger.info(f"Loaded {len(labels)} labels from {LABEL_MAP_PATH}")
    except Exception as e:
        logger.error(f"Error loading label map: {e}")
else:
    logger.warning(f"Label map not found at {LABEL_MAP_PATH}")


class ObstacleDetector:
    """
    Unified obstacle detection class combining ML and traditional methods.

    This class provides:
    1. ML-based object detection using TensorFlow Lite
    2. Basic obstacle detection using OpenCV
    3. Drop detection for safety
    4. Remote detection capability with Pi 5
    5. Support for Edge TPU acceleration
    """

    def __init__(self, resource_manager=None):
        """Initialize the obstacle detector."""
        self.resource_manager = resource_manager

        # Initialize ML components
        self.interpreter = None
        self.interpreter_type = None
        self.input_details = None
        self.output_details = None
        self.input_height = 0
        self.input_width = 0
        self.floating_model = False

        # Constants for preprocessing
        self.input_mean = 127.5
        self.input_std = 127.5

        # Get camera instance
        self.camera = get_camera_instance()

        # Remote detection settings
        self.use_remote_detection = USE_REMOTE_DETECTION

        # Thread synchronization
        self.frame_condition = Condition()
        self.frame = None
        self.frame_lock = threading.Lock()

        # Initialize interpreter
        self._initialize_interpreter()

        logger.info(
            f"ObstacleDetector initialized with {self.interpreter_type} "
            "interpreter"
        )

    def _initialize_interpreter(self):
        """Initialize the TensorFlow Lite interpreter."""
        try:
            if self.resource_manager:
                # Try to get interpreter from resource manager
                self.interpreter = (
                    self.resource_manager.get_inference_interpreter()
                )
                if self.interpreter:
                    self.interpreter_type = (
                        self.resource_manager.get_interpreter_type()
                    )
                    self.input_details = (
                        self.resource_manager.get_model_input_details()
                    )
                    self.output_details = (
                        self.resource_manager.get_model_output_details()
                    )
                    self.input_height, self.input_width = (
                        self.resource_manager.get_model_input_size()
                    )

                    if self.input_details and len(self.input_details) > 0:
                        self.floating_model = (
                            self.input_details[0]['dtype'] == np.float32
                        )
                    return

            # Fallback to direct initialization
            import tflite_runtime.interpreter as tflite

            self.interpreter = tflite.Interpreter(
                model_path=PATH_TO_OBJECT_DETECTION_MODEL
            )
            self.interpreter.allocate_tensors()
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()
            self.input_height = self.input_details[0]['shape'][1]
            self.input_width = self.input_details[0]['shape'][2]
            self.floating_model = (
                self.input_details[0]['dtype'] == np.float32
            )
            self.interpreter_type = "CPU"

            logger.info(
                f"TFLite model loaded with input size: "
                f"{self.input_height}x{self.input_width}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize interpreter: {e}")
            self.interpreter = None

    def detect_obstacles(self, frame=None) -> List[dict]:
        """
        Detect obstacles using all available methods.

        Args:
            frame: Optional frame to process. If None, captures from camera.

        Returns:
            List of detected objects with name, confidence, and position.
        """
        if frame is None:
            frame = capture_frame()
            if frame is None:
                return []

        detected_objects = []

        # Try remote detection first if enabled
        if self.use_remote_detection:
            try:
                remote_objects = self._detect_obstacles_remote(frame)
                if remote_objects:
                    detected_objects.extend(remote_objects)
                    return detected_objects
            except Exception as e:
                logger.warning(
                    f"Remote detection failed, falling back to local: {e}"
                )
                self.use_remote_detection = False

        # Local ML-based detection
        if self.interpreter:
            ml_objects = self._detect_obstacles_ml(frame)
            detected_objects.extend(ml_objects)

        # OpenCV-based detection
        cv_objects = self._detect_obstacles_opencv(frame)
        detected_objects.extend(cv_objects)

        return detected_objects

    def _detect_obstacles_ml(self, frame) -> List[dict]:
        """Perform ML-based object detection."""
        try:
            # Convert frame to PIL Image
            if isinstance(frame, np.ndarray):
                image = Image.fromarray(frame)
            else:
                image = frame

            # Preprocess image
            image_resized = image.resize(
                (self.input_width, self.input_height)
            )
            input_data = np.expand_dims(image_resized, axis=0)

            # Handle different channel formats
            if len(input_data.shape) == 4 and input_data.shape[-1] != 3:
                input_data = input_data[:, :, :, :3]

            # Normalize pixel values
            if self.floating_model:
                input_data = (
                    (np.float32(input_data) - self.input_mean) /
                    self.input_std
                )
            else:
                input_data = np.uint8(input_data)

            # Run inference
            self.interpreter.set_tensor(
                self.input_details[0]['index'],
                input_data
            )
            start_time = time.time()
            self.interpreter.invoke()
            inference_time = time.time() - start_time

            # Get prediction results
            output_data = self.interpreter.get_tensor(
                self.output_details[0]['index']
            )[0]

            # Process results
            detected_objects = []
            top_k = 3  # Get top 3 predictions
            top_indices = np.argsort(-output_data)[:top_k]

            for idx in top_indices:
                if idx < len(labels):
                    class_name = labels[idx]
                else:
                    class_name = f"Class {idx}"

                score = float(output_data[idx])
                if score >= MIN_CONF_THRESHOLD:
                    detected_objects.append({
                        'name': class_name,
                        'score': score,
                        'type': 'ml',
                        'box': None  # Add bounding box if available
                    })

            # Log performance
            logger.debug(
                f"ML inference: {inference_time:.2f}s "
                f"({1 / inference_time:.1f} FPS)"
            )

            return detected_objects

        except Exception as e:
            logger.error(f"Error in ML detection: {e}")
            return []

    def _detect_obstacles_opencv(self, frame) -> List[dict]:
        """Perform basic obstacle detection using OpenCV."""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Apply Gaussian blur
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)

            # Edge detection
            edges = cv2.Canny(blurred, 50, 150)

            # Find contours
            contours, _ = cv2.findContours(
                edges,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE
            )

            # Filter contours by size
            detected_objects = []
            min_area = 1000

            for contour in contours:
                area = cv2.contourArea(contour)
                if area > min_area:
                    # Calculate bounding box
                    x, y, w, h = cv2.boundingRect(contour)

                    detected_objects.append({
                        'name': 'obstacle',
                        'score': min(1.0, area / 10000),  # Normalize score
                        'type': 'opencv',
                        'box': [x, y, w, h]
                    })

            return detected_objects

        except Exception as e:
            logger.error(f"Error in OpenCV detection: {e}")
            return []

    def _detect_obstacles_remote(self, frame) -> List[dict]:
        """Send frame to Pi 5 for remote detection."""
        try:
            # Convert frame to JPEG
            if isinstance(frame, np.ndarray):
                image = Image.fromarray(frame)
            else:
                image = frame

            img_byte_arr = io.BytesIO()
            image = image.convert('RGB')
            image.save(img_byte_arr, format='JPEG')
            img_bytes = img_byte_arr.getvalue()

            # Send to Pi 5
            response = requests.post(
                f'http://{PI5_IP}:5000/detect',
                files={'image': ('image.jpg', img_bytes, 'image/jpeg')},
                timeout=1
            )

            if response.status_code == 200:
                result = response.json()
                if result.get('detections'):
                    return [
                        {
                            'name': det['class'],
                            'score': det['confidence'],
                            'type': 'remote',
                            'box': det.get('box')
                        }
                        for det in result['detections']
                    ]

            return []

        except Exception as e:
            logger.error(f"Error in remote detection: {e}")
            raise

    def detect_drops(self, frame=None) -> List[dict]:
        """Detect potential drops/cliffs in the frame."""
        if frame is None:
            frame = capture_frame()
            if frame is None:
                return []

        try:
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Apply threshold for dark areas
            _, thresh = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY)

            # Find contours
            contours, _ = cv2.findContours(
                thresh,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE
            )

            # Filter and process contours
            detected_drops = []
            min_area = 2000

            for contour in contours:
                area = cv2.contourArea(contour)
                if area > min_area:
                    x, y, w, h = cv2.boundingRect(contour)
                    detected_drops.append({
                        'name': 'drop',
                        'score': min(1.0, area / 5000),
                        'type': 'opencv',
                        'box': [x, y, w, h]
                    })

            return detected_drops

        except Exception as e:
            logger.error(f"Error detecting drops: {e}")
            return []

    def draw_detections(
        self,
        frame,
        detections: List[dict]
    ) -> np.ndarray:
        """Draw detection results on frame."""
        try:
            frame_with_detections = frame.copy()

            for detection in detections:
                # Get detection info
                name = detection['name']
                score = detection['score']
                box = detection.get('box')
                det_type = detection.get('type', 'unknown')

                # Choose color based on type
                if det_type == 'ml':
                    color = (0, 255, 0)  # Green for ML detections
                elif det_type == 'opencv':
                    color = (255, 0, 0)  # Blue for OpenCV detections
                elif det_type == 'remote':
                    color = (0, 0, 255)  # Red for remote detections
                else:
                    color = (255, 255, 0)  # Yellow for unknown

                # Draw bounding box if available
                if box:
                    x, y, w, h = box
                    cv2.rectangle(
                        frame_with_detections,
                        (x, y),
                        (x + w, y + h),
                        color,
                        2
                    )

                # Draw label
                label = f"{name}: {int(score * 100)}%"
                if box:
                    cv2.putText(
                        frame_with_detections,
                        label,
                        (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        color,
                        2
                    )
                else:
                    # If no box, draw at top
                    y_pos = 30 + detections.index(detection) * 30
                    cv2.putText(
                        frame_with_detections,
                        label,
                        (10, y_pos),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        color,
                        2
                    )

            return frame_with_detections

        except Exception as e:
            logger.error(f"Error drawing detections: {e}")
            return frame

    def process_frame(self, frame=None) -> Tuple[np.ndarray, List[dict]]:
        """
        Process a frame for all types of detections.

        Args:
            frame: Optional frame to process. If None, captures from camera.

        Returns:
            Tuple of (annotated frame, list of detections)
        """
        if frame is None:
            frame = capture_frame()
            if frame is None:
                return None, []

        # Detect obstacles and drops
        obstacles = self.detect_obstacles(frame)
        drops = self.detect_drops(frame)

        # Combine detections
        all_detections = obstacles + drops

        # Draw detections on frame
        annotated_frame = self.draw_detections(frame, all_detections)

        return annotated_frame, all_detections

    def start_processing(self):
        """Start continuous frame processing in background thread."""
        self.processing_thread = threading.Thread(
            target=self._processing_loop,
            daemon=True
        )
        self.processing_thread.start()

    def _processing_loop(self):
        """Main processing loop for continuous detection."""
        while True:
            try:
                # Capture and process frame
                frame = capture_frame()
                if frame is not None:
                    processed_frame, detections = self.process_frame(frame)

                    # Store latest results
                    with self.frame_lock:
                        self.frame = processed_frame
                        self.latest_detections = detections

                # Small delay to prevent CPU overload
                time.sleep(0.1)

            except Exception as e:
                logger.error(f"Error in processing loop: {e}")
                time.sleep(1)  # Longer delay on error


# Singleton instance
_obstacle_detector = None


def get_obstacle_detector(resource_manager=None):
    """Get or create singleton instance of ObstacleDetector."""
    global _obstacle_detector

    if _obstacle_detector is None:
        _obstacle_detector = ObstacleDetector(resource_manager)

    return _obstacle_detector
