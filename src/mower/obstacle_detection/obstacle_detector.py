"""
Obstacle detection module that leverages TensorFlow Lite models for visual object detection.

This module provides the ObstacleDetector class which is responsible for:
1. Processing camera frames to detect obstacles using machine learning
2. Supporting both CPU-based and Coral TPU-accelerated inference 
3. Providing a unified interface for the rest of the system

The detector automatically uses the Edge TPU accelerator when available,
falling back to CPU inference if not available or requested.
"""

import logging
import time
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os
import io
from dotenv import load_dotenv

# Import local modules
from mower.hardware.camera_instance import get_camera_instance, capture_frame
from mower.utilities.logger_config import LoggerConfigInfo as LoggerConfig
from mower.obstacle_detection.local_obstacle_detection import initialize_with_resource_manager

# Initialize logger
logging = LoggerConfig.get_logger(__name__)

# Load environment variables
load_dotenv()
LABEL_MAP_PATH = os.getenv('LABEL_MAP_PATH')
MIN_CONF_THRESHOLD = float(os.getenv('MIN_CONF_THRESHOLD', '0.5'))

# Load labels if available
labels = []
if LABEL_MAP_PATH and os.path.exists(LABEL_MAP_PATH):
    try:
        with open(LABEL_MAP_PATH, 'r') as f:
            labels = [line.strip() for line in f.readlines()]
        if labels and labels[0] == '???':
            del labels[0]
        logging.info(f"Loaded {len(labels)} labels from {LABEL_MAP_PATH}")
    except Exception as e:
        logging.error(f"Error loading label map: {e}")
else:
    logging.warning(f"Label map not found at {LABEL_MAP_PATH}")

class ObstacleDetector:
    """
    Class for detecting obstacles using TensorFlow Lite models.
    
    This class provides methods for:
    1. Detecting obstacles in camera frames
    2. Classifying detected objects
    3. Drawing detection visualizations for debugging
    
    It supports both CPU and Edge TPU (Coral) inference based on
    the configuration in the ResourceManager.
    """
    
    def __init__(self, resource_manager):
        """
        Initialize the detector with a ResourceManager instance.
        
        Args:
            resource_manager: The ResourceManager providing access to the
                              TensorFlow Lite interpreter and configuration.
        
        The detector will use the interpreter provided by the ResourceManager,
        which may be either CPU-based or Edge TPU accelerated.
        """
        self.resource_manager = resource_manager
        self.interpreter = self.resource_manager.get_inference_interpreter()
        self.interpreter_type = self.resource_manager.get_interpreter_type()
        self.input_details = self.resource_manager.get_model_input_details()
        self.output_details = self.resource_manager.get_model_output_details()
        
        # Get input size from the model
        self.input_height, self.input_width = self.resource_manager.get_model_input_size()
        
        # Check if we're using a floating point model
        self.floating_model = False
        if self.input_details and len(self.input_details) > 0:
            self.floating_model = (self.input_details[0]['dtype'] == np.float32)
        
        # Constants for preprocessing
        self.input_mean = 127.5
        self.input_std = 127.5
        
        # Get camera instance
        self.camera = get_camera_instance()
        
        # Initialize the legacy detection module with our resource manager
        # This allows backwards compatibility with existing code
        initialize_with_resource_manager(resource_manager)
        
        logging.info(f"ObstacleDetector initialized with {self.interpreter_type} interpreter")
        logging.info(f"Model input size: {self.input_width}x{self.input_height}")
    
    def detect(self, frame):
        """
        Performs obstacle detection on a single frame.
        
        Args:
            frame: The image frame to analyze (numpy array)
            
        Returns:
            List of detected objects, each containing:
            - name: Class name of the detected object
            - score: Confidence score (0.0-1.0)
            - box: Bounding box coordinates [x, y, w, h] if available
        """
        if self.interpreter is None:
            logging.error("Interpreter not available for detection")
            return []
        
        # Convert numpy array to PIL Image for consistent processing
        if isinstance(frame, np.ndarray):
            image = Image.fromarray(frame)
        else:
            image = frame
            
        # Preprocess the image
        image_resized = image.resize((self.input_width, self.input_height))
        input_data = np.expand_dims(image_resized, axis=0)
        
        # Handle different channel formats
        if len(input_data.shape) == 4 and input_data.shape[-1] != 3:
            input_data = input_data[:, :, :, :3]  # Keep only RGB channels
            
        # Normalize pixel values
        if self.floating_model:
            input_data = (np.float32(input_data) - self.input_mean) / self.input_std
        else:
            input_data = np.uint8(input_data)
            
        # Run inference
        try:
            self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
            start_time = time.time()
            self.interpreter.invoke()
            inference_time = time.time() - start_time
            
            # Get prediction results
            output_data = self.interpreter.get_tensor(self.output_details[0]['index'])[0]
            
            # Process results based on model format
            # This implementation assumes a classification model returning class scores
            # Adjust for detection models that return bounding boxes
            top_k = 3  # Get top 3 predictions
            top_indices = np.argsort(-output_data)[:top_k]
            
            detected_objects = []
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
                        'box': None  # Placeholder for bounding box if available
                    })
            
            # Log performance metrics
            logging.debug(f"Inference time: {inference_time:.2f}s ({1/inference_time:.1f} FPS)")
            if detected_objects:
                logging.info(f"Detected objects: {[obj['name'] for obj in detected_objects]}")
                
            return detected_objects
            
        except Exception as e:
            logging.error(f"Error during inference: {e}")
            return []
    
    def detect_from_camera(self):
        """
        Captures a frame from the camera and performs detection.
        
        Returns:
            List of detected objects (same format as detect())
        """
        frame = capture_frame()
        if frame is None:
            logging.warning("Failed to capture frame from camera")
            return []
            
        return self.detect(frame)
    
    def is_obstacle_detected(self):
        """
        Check if any obstacles are detected in the current camera view.
        
        Returns:
            bool: True if obstacles are detected, False otherwise
        """
        detections = self.detect_from_camera()
        return len(detections) > 0
    
    def draw_detections(self, frame, detections):
        """
        Draw detection results on an image for visualization.
        
        Args:
            frame: The image frame to annotate
            detections: List of detected objects from the detect() method
            
        Returns:
            Annotated image with detection results drawn on it
        """
        # Convert numpy array to PIL Image for drawing
        if isinstance(frame, np.ndarray):
            image = Image.fromarray(frame)
        else:
            image = frame
            
        draw = ImageDraw.Draw(image)
        
        # Try to load a font, fall back to default if not available
        try:
            font = ImageFont.truetype("arial.ttf", 15)
        except IOError:
            font = ImageFont.load_default()
            
        # Draw each detection
        for i, obj in enumerate(detections):
            label = f"{obj['name']}: {int(obj['score'] * 100)}%"
            
            # Position text at top left for now (adjust if we have bounding boxes)
            text_position = (10, 10 + (i * 20))
            draw.text(text_position, label, fill='red', font=font)
            
            # Draw bounding box if available
            if obj.get('box'):
                x, y, w, h = obj['box']
                draw.rectangle([(x, y), (x+w, y+h)], outline='red', width=2)
                
        return np.array(image)

    def _draw_detections(self, image, boxes, classes, scores):
        """
        Draw bounding boxes and labels for detected objects.
        
        Args:
            image: The image to draw on
            boxes: Bounding box coordinates (normalized)
            classes: Class indices of detected objects
            scores: Confidence scores for detections
            
        Returns:
            Image with detection visualizations
        """
        try:
            h, w, _ = image.shape
            for i in range(len(scores)):
                if scores[i] >= self.min_confidence:
                    # Get bounding box coordinates
                    ymin = int(max(1, (boxes[i][0] * h)))
                    xmin = int(max(1, (boxes[i][1] * w)))
                    ymax = int(min(h, (boxes[i][2] * h)))
                    xmax = int(min(w, (boxes[i][3] * w)))
                    
                    # Get class label
                    class_id = int(classes[i])
                    label = self.labels[class_id] if class_id < len(self.labels) else f"Class {class_id}"
                    
                    # Draw bounding box
                    cv2.rectangle(image, (xmin, ymin), (xmax, ymax), (10, 255, 0), 2)
                    
                    # Draw label
                    label_text = f"{label}: {int(scores[i] * 100)}%"
                    label_background_color = (10, 255, 0)
                    label_text_color = (0, 0, 0)
                    
                    # Ensure the label fits in the image
                    label_size = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
                    if ymin - label_size[1] - 10 < 0:
                        label_ymin = ymin + label_size[1] + 10
                    else:
                        label_ymin = ymin - 10
                        
                    cv2.rectangle(image, (xmin, label_ymin - label_size[1] - 10),
                                (xmin + label_size[0], label_ymin + 10), label_background_color, -1)
                    cv2.putText(image, label_text, (xmin, label_ymin),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, label_text_color, 1)
            
            return image
        except Exception as e:
            logger.error(f"Error drawing detections: {e}")
            return image

# Singleton instance
_obstacle_detector = None

def get_obstacle_detector(resource_manager):
    """
    Get or create a singleton instance of the ObstacleDetector.
    
    This factory function ensures only one instance of ObstacleDetector
    is created, preventing multiple initializations of the ML model
    and camera resources.
    
    Args:
        resource_manager: The ResourceManager instance for accessing
                          inference engine and system resources
                          
    Returns:
        ObstacleDetector: A singleton instance of ObstacleDetector
    """
    global _obstacle_detector
    
    if _obstacle_detector is None:
        _obstacle_detector = ObstacleDetector(resource_manager)
        
    return _obstacle_detector 