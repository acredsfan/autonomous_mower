"""
Obstacle detection module for autonomous mower.

This module provides comprehensive obstacle detection capabilities using:
1. TensorFlow Lite models for ML-based object detection
2. OpenCV for basic image processing and drop detection
3. Support for both local and remote (Pi 5) detection
4. Integration with Edge TPU when available
5. YOLOv8 models for improved detection performance
"""

import io
import os
import threading
import time
from threading import Condition
from typing import List, Tuple

import cv2
import numpy as np
import requests  # type: ignore
from dotenv import load_dotenv
from PIL import Image

from mower.hardware.hardware_registry import get_hardware_registry
from mower.obstacle_detection.sort import Sort  # Import SORT
from mower.utilities.logger_config import LoggerConfigInfo

# Initialize logger
logger = LoggerConfigInfo.get_logger(__name__)

# Load environment variables
load_dotenv()

# Define default paths relative to the project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DEFAULT_MODEL_DIR = os.path.join(PROJECT_ROOT, "models")
DEFAULT_LABEL_MAP_FILE = os.path.join(DEFAULT_MODEL_DIR, "labels.txt")
DEFAULT_YOLOV8_MODEL = os.path.join(DEFAULT_MODEL_DIR, "yolov8n_float32.tflite")

PI5_IP = os.getenv("OBJECT_DETECTION_IP")

LABEL_MAP_PATH = os.getenv("LABEL_MAP_PATH")
if not LABEL_MAP_PATH or not os.path.exists(LABEL_MAP_PATH):
    logger.warning(
        f"LABEL_MAP_PATH env var not set or path invalid: {LABEL_MAP_PATH}. "
        f"Falling back to default: {DEFAULT_LABEL_MAP_FILE}"
    )
    LABEL_MAP_PATH = DEFAULT_LABEL_MAP_FILE
    if not os.path.exists(LABEL_MAP_PATH):
        logger.error(f"Default label map not found: {DEFAULT_LABEL_MAP_FILE}")
        # Potentially disable detection or raise an error


MIN_CONF_THRESHOLD = float(os.getenv("MIN_CONF_THRESHOLD", "0.5"))
USE_REMOTE_DETECTION = os.getenv("USE_REMOTE_DETECTION", "False").lower() == "true"

# YOLOv8 specific environment variables
YOLOV8_MODEL_PATH = os.getenv("YOLOV8_MODEL_PATH")
if not YOLOV8_MODEL_PATH or not os.path.exists(YOLOV8_MODEL_PATH):
    logger.warning(
        f"YOLOV8_MODEL_PATH env var not set or path invalid: {YOLOV8_MODEL_PATH}. "
        f"Falling back to default: {DEFAULT_YOLOV8_MODEL}"
    )
    YOLOV8_MODEL_PATH = DEFAULT_YOLOV8_MODEL
    if not os.path.exists(YOLOV8_MODEL_PATH):
        logger.warning(f"Default YOLOv8 model not found: {DEFAULT_YOLOV8_MODEL}. YOLOv8 will be disabled.")
        # This will be handled by _initialize_yolov8 which checks USE_YOLOV8 and path existence

USE_YOLOV8 = os.getenv("USE_YOLOV8", "True").lower() == "true"

# Load labels if available
labels = []
if LABEL_MAP_PATH and os.path.exists(LABEL_MAP_PATH):
    try:
        with open(LABEL_MAP_PATH, "r", encoding="utf-8") as f:
            labels = [line.strip() for line in f.readlines()]
        if labels and labels[0] == "???":
            del labels[0]
        logger.info("Loaded %d labels from %s", len(labels), LABEL_MAP_PATH)
    except (IOError, UnicodeDecodeError) as e:
        logger.error("Error loading label map: %s", e)
else:
    logger.warning("Label map not found at %s", LABEL_MAP_PATH)


class ObstacleDetector:
    """
    Unified obstacle detection class combining ML and traditional methods.

    This class provides:
    1. ML-based object detection using TensorFlow Lite
    2. Basic obstacle detection using OpenCV
    3. Drop detection for safety
    4. Remote detection capability with Pi 5
    5. Support for Edge TPU acceleration
    6. YOLOv8 model support for improved detection
    """

    def __init__(self, resource_manager=None):
        """Initialize the obstacle detector."""
        self.resource_manager = resource_manager

        # Get camera instance
        self.camera = get_hardware_registry().get_camera()

        # Remote detection settings
        self.use_remote_detection = USE_REMOTE_DETECTION

        # YOLOv8 detector (primary ML detection method)
        self.yolov8_detector = None
        self.use_yolov8 = USE_YOLOV8

        # Thread synchronization
        self.frame_condition = Condition()
        self.frame = None
        self.frame_lock = threading.Lock()

        # Initialize tracker
        self.tracker = Sort()

        # Initialize frame sharer for web interface
        self._frame_sharer = None
        try:
            from mower.hardware.camera_frame_share import CameraFrameSharer
            self._frame_sharer = CameraFrameSharer()
            logger.info("Frame sharer initialized for web interface")
        except ImportError as e:
            logger.debug(f"Frame sharing not available: {e}")

        # Initialize YOLOv8 detector (only ML detector needed)
        self.yolov8_detector = self._initialize_yolov8()

        logger.info(
            "ObstacleDetector initialized with %s",
            "YOLOv8 enabled" if self.yolov8_detector else "YOLOv8 disabled - using OpenCV only",
        )

    def _initialize_yolov8(self):
        """
        Initialize the YOLOv8 detector, dynamically selecting CPU or Coral Edge TPU
        based on environment variables.
        """
        if not self.use_yolov8:
            logger.info("YOLOv8 detector disabled")
            return None

        try:
            # Import YOLOv8 detector class and check Coral availability
            from mower.obstacle_detection.yolov8_detector import YOLOv8TFLiteDetector
            from mower.obstacle_detection.coral_utils import is_coral_detected

            model_path_to_use = ""
            use_coral_flag = False

            # Get environment variables
            USE_CORAL_ACCELERATOR = os.getenv("USE_CORAL_ACCELERATOR", "True").lower() == "true"
            EDGE_TPU_MODEL_PATH = os.getenv("EDGE_TPU_MODEL_PATH")
            YOLOV8_CPU_MODEL_PATH = YOLOV8_MODEL_PATH

            # Check if Coral is actually available before attempting to use it
            coral_available = is_coral_detected() if USE_CORAL_ACCELERATOR else False



            if USE_CORAL_ACCELERATOR and coral_available:
                if EDGE_TPU_MODEL_PATH and os.path.exists(EDGE_TPU_MODEL_PATH):
                    model_path_to_use = EDGE_TPU_MODEL_PATH
                    use_coral_flag = True
                    logger.info("🟢 Coral accelerator is available. Using Edge TPU model: %s", model_path_to_use)
                else:
                    logger.warning("USE_CORAL_ACCELERATOR is True and Coral detected, but Edge TPU model not found at: %s", EDGE_TPU_MODEL_PATH)
                    logger.warning("Falling back to CPU model at: %s", YOLOV8_CPU_MODEL_PATH)
                    model_path_to_use = YOLOV8_CPU_MODEL_PATH
                    use_coral_flag = False
            elif USE_CORAL_ACCELERATOR and not coral_available:
                logger.warning("🟡 USE_CORAL_ACCELERATOR is True, but Coral TPU not detected or libraries unavailable")
                logger.warning("Falling back to CPU model at: %s", YOLOV8_CPU_MODEL_PATH)
                model_path_to_use = YOLOV8_CPU_MODEL_PATH
                use_coral_flag = False
            else:
                logger.info("🔵 Using CPU for inference with model: %s", YOLOV8_CPU_MODEL_PATH)
                model_path_to_use = YOLOV8_CPU_MODEL_PATH
                use_coral_flag = False

            # Check if model exists
            if not os.path.exists(model_path_to_use):
                logger.warning("YOLOv8 model not found at %s, skipping", model_path_to_use)
                return None

            logger.info("🎯 FINAL DECISION - YOLOv8 model path: %s, use_coral: %s", model_path_to_use, use_coral_flag)

            # Initialize detector
            detector = YOLOv8TFLiteDetector(
                model_path=model_path_to_use,
                label_path=LABEL_MAP_PATH,
                conf_threshold=MIN_CONF_THRESHOLD,
                use_coral=use_coral_flag,
            )
            logger.info("YOLOv8 detector initialized successfully with %s", 
                       "Coral Edge TPU" if use_coral_flag else "CPU")
            return detector
            
        except ImportError:
            logger.error("Failed to import YOLOv8TFLiteDetector class")
            return None
        except (IOError, ValueError, RuntimeError) as e:
            logger.error("Failed to initialize YOLOv8 detector: %s", e)
            return None

    def detect_obstacles(self, frame=None) -> List[dict]:
        """
        Detect obstacles using all available methods.

        Args:
            frame: Optional frame to process. If None, captures from camera.

        Returns:
            List of detected objects with name, confidence, and position.
        """
        if frame is None:
            frame = self.camera.get_frame()
            if frame is None:
                return []
            
            # Share frame with web process if we captured it
            if hasattr(self, '_frame_sharer') and self._frame_sharer is not None:
                try:
                    # Convert frame to JPEG bytes for frame sharing
                    success, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    if success:
                        jpeg_bytes = buffer.tobytes()
                        self._frame_sharer.write_frame(jpeg_bytes)
                except Exception as e:
                    logger.debug(f"Failed to share frame in detect_obstacles: {e}")

        detected_objects = []

        # Try remote detection first if enabled
        if self.use_remote_detection:
            try:
                remote_objects = self._detect_obstacles_remote(frame)
                if remote_objects:
                    detected_objects.extend(remote_objects)
                    return detected_objects
            except (ConnectionError, requests.RequestException, IOError, ValueError) as e:
                logger.warning("Remote detection failed, falling back to local: %s", e)
                self.use_remote_detection = False

        # YOLOv8-based detection (preferred if available)
        if self.yolov8_detector:
            try:
                yolo_objects = self.yolov8_detector.detect(frame)
                if yolo_objects:
                    detected_objects.extend(yolo_objects)

                    # Apply tracking
                    if len(yolo_objects) > 0:
                        # Extract bounding boxes and confidences for tracker
                        detections_np = np.array(
                            [
                                [d["box"][0], d["box"][1], d["box"][2], d["box"][3], d["confidence"]]
                                for d in yolo_objects
                            ]
                        )

                        # Update tracker and get tracked objects
                        tracked_objects = self.tracker.update(detections_np)

                        # Add track IDs to detections
                        for i, obj in enumerate(yolo_objects):
                            obj["track_id"] = int(tracked_objects[i, 4])

                    if len(detected_objects) > 0:
                        return detected_objects
            except (ValueError, RuntimeError, IOError) as e:
                logger.warning("YOLOv8 detection failed, falling back: %s", e)

        # OpenCV-based detection (always run as backup/supplement)
        cv_objects = self._detect_obstacles_opencv(frame)
        detected_objects.extend(cv_objects)

        return detected_objects

    def _detect_obstacles_opencv(self, frame) -> List[dict]:
        """Perform basic obstacle detection using OpenCV."""
        try:
            # Check if frame is valid
            if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
                logger.warning("Invalid frame provided to OpenCV detector")
                return []

            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Apply Gaussian blur
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)

            # Edge detection
            edges = cv2.Canny(blurred, 50, 150)

            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # Filter contours by size
            detected_objects = []
            min_area = 1000

            for contour in contours:
                area = cv2.contourArea(contour)
                if area > min_area:
                    # Calculate bounding box
                    x, y, w, h = cv2.boundingRect(contour)

                    detected_objects.append(
                        {
                            "name": "obstacle",
                            "score": min(1.0, area / 10000),  # Normalize score
                            "type": "opencv",
                            "box": [x, y, w, h],
                        }
                    )

            return detected_objects

        except (ValueError, cv2.error, TypeError) as e:
            logger.error("Error in OpenCV detection: %s", e)
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
            image = image.convert("RGB")
            image.save(img_byte_arr, format="JPEG")
            img_bytes = img_byte_arr.getvalue()

            # Send to Pi 5
            response = requests.post(
                f"http://{PI5_IP}:5000/detect",
                files={"image": ("image.jpg", img_bytes, "image/jpeg")},
                timeout=1,
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("detections"):
                    return [
                        {
                            "name": det["class"],
                            "score": det["confidence"],
                            "type": "remote",
                            "box": det.get("box"),
                        }
                        for det in result["detections"]
                    ]

            return []

        except (ConnectionError, TimeoutError) as e:
            logger.error("Error connecting to remote detection service: %s", e)
            raise
        except (ValueError, TypeError) as e:
            logger.error("Error parsing remote detection result: %s", e)
            raise
        except (IOError, RuntimeError) as e:
            logger.error("Error in remote detection: %s", e)
            raise

    def detect_drops(self, frame=None) -> List[dict]:
        """
        Detect potential drops/cliffs in the frame.

        Args:
            frame: Optional frame to process. If None, captures from camera.

        Returns:
            List of detected drops with position and confidence.
        """
        if frame is None:
            frame = self.camera.get_frame()
            if frame is None:
                return []
            
            # Share frame with web process if we captured it
            if hasattr(self, '_frame_sharer') and self._frame_sharer is not None:
                try:
                    self._frame_sharer.write_frame(frame)
                except Exception as e:
                    logger.debug(f"Failed to share frame in detect_drops: {e}")

        try:
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Apply Gaussian blur to reduce noise
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)

            # Use Canny edge detection to find edges
            edges = cv2.Canny(blurred, 50, 150)

            # Find contours from edges
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            drops = []

            for contour in contours:
                # Approximate the contour to reduce complexity
                epsilon = 0.02 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)

                # Calculate bounding box and area
                x, y, w, h = cv2.boundingRect(approx)
                area = cv2.contourArea(contour)

                # Heuristic: Consider as drop if area is large and aspect ratio
                # is unusual
                aspect_ratio = w / float(h)
                if area > 500 and (aspect_ratio < 0.5 or aspect_ratio > 2.0):
                    drops.append(
                        {
                            "position": (x, y, w, h),
                            "confidence": 0.8,  # Placeholder confidence value
                            "type": "drop",
                        }
                    )

            return drops

        except (ValueError, cv2.error, TypeError) as e:
            logger.error("Error detecting drops: %s", e)
            return []

    def draw_detections(self, frame, detections: List[dict]) -> np.ndarray:
        """Draw detection results on frame."""
        try:
            # Use YOLOv8 detector's draw function for YOLOv8 detections
            yolo_detections = [d for d in detections if d.get("type") == "yolov8"]
            if self.yolov8_detector and yolo_detections:
                frame = self.yolov8_detector.draw_detections(frame, yolo_detections)
                # Filter out YOLOv8 detections since they're already drawn
                detections = [d for d in detections if d.get("type") != "yolov8"]

            # Continue with normal drawing for other detection types
            frame_with_detections = frame.copy()

            for detection in detections:
                # Get detection info
                name = detection["name"]
                score = detection["score"]
                box = detection.get("box")
                det_type = detection.get("type", "unknown")

                # Choose color based on type
                if det_type == "ml":
                    color = (0, 255, 0)  # Green for ML detections
                elif det_type == "opencv":
                    color = (255, 0, 0)  # Blue for OpenCV detections
                elif det_type == "remote":
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
                        2,
                    )

                # Draw label
                label = f"{name}: {int(score * 100)}%"
                if box:
                    if "track_id" in detection:
                        label = f"{label} (ID: {detection['track_id']})"
                    cv2.putText(
                        frame_with_detections,
                        label,
                        (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        color,
                        2,
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
                        2,
                    )

            return frame_with_detections

        except (ValueError, cv2.error, TypeError, IndexError) as e:
            logger.error("Error drawing detections: %s", e)
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
            frame = self.camera.get_frame()
            if frame is None:
                return None, []
            
            # Share frame with web process if we captured it
            if hasattr(self, '_frame_sharer') and self._frame_sharer is not None:
                try:
                    self._frame_sharer.write_frame(frame)
                except Exception as e:
                    logger.debug(f"Failed to share frame in process_frame: {e}")

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
        self.processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
        self.processing_thread.start()

    def _processing_loop(self):
        """Main processing loop for continuous detection."""
        # Initialize frame sharer for web interface
        frame_sharer = None
        try:
            from mower.hardware.camera_frame_share import CameraFrameSharer
            frame_sharer = CameraFrameSharer()
            logger.info("Frame sharing initialized for web interface")
        except ImportError as e:
            logger.debug(f"Frame sharing not available: {e}")
        
        while True:
            try:
                # Capture and process frame
                frame = self.camera.get_frame()
                if frame is not None:
                    # Share frame with web process if available
                    if frame_sharer is not None:
                        try:
                            frame_sharer.write_frame(frame)
                        except Exception as e:
                            logger.debug(f"Failed to share frame: {e}")
                    
                    processed_frame, detections = self.process_frame(frame)

                    # Store latest results
                    with self.frame_lock:
                        self.frame = processed_frame
                        self.latest_detections = detections

                # Small delay to prevent CPU overload
                time.sleep(0.1)

            except (ValueError, RuntimeError, cv2.error, TypeError) as e:
                logger.error("Error in processing loop: %s", e)
                time.sleep(1)  # Longer delay on error


# Singleton instance
_obstacle_detector = None


def get_obstacle_detector(resource_manager=None):
    """Get or create singleton instance of ObstacleDetector."""
    global _obstacle_detector

    if _obstacle_detector is None:
        _obstacle_detector = ObstacleDetector(resource_manager)

    return _obstacle_detector
