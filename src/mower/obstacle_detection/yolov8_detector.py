"""
YOLOv8 TFLite model detector for autonomous mower obstacle detection.

This module provides YOLOv8 object detection capabilities using TensorFlow Lite.
It's optimized for Raspberry Pi and works with both CPU and Coral TPU when available.
"""

import os
import time
import numpy as np
from typing import List, Tuple, Dict, Optional, Union

from PIL import Image
import cv2

from mower.utilities.logger_config import LoggerConfigInfo as LoggerConfig

# Initialize logger
logger = LoggerConfigInfo.get_logger(__name__)


class YOLOv8TFLiteDetector:
    """
    YOLOv8 detector using TensorFlow Lite models.
    
    This class handles detection with YOLOv8 models that have been converted to TFLite
    format, making them suitable for running on Raspberry Pi and edge devices.
    """
    
    def __init__(self, model_path: str, label_path: str, conf_threshold: float = 0.5):
        """
        Initialize the YOLOv8 TFLite detector.
        
        Args:
            model_path: Path to the YOLOv8 TFLite model
            label_path: Path to the label map file
            conf_threshold: Confidence threshold for detections
        """
        self.model_path = model_path
        self.label_path = label_path
        self.conf_threshold = conf_threshold
        
        # Interpreter
        self.interpreter = None
        self.input_details = None
        self.output_details = None
        self.input_height = 0
        self.input_width = 0
        self.floating_model = False
        self.has_detect_output = False  # True if model has detection output format
        
        # Load labels
        self.labels = self._load_labels()
        
        # Initialize interpreter
        self._initialize_interpreter()
    
    def _load_labels(self) -> List[str]:
        """Load labels from file."""
        labels = []
        if os.path.exists(self.label_path):
            try:
                with open(self.label_path, "r") as f:
                    labels = [line.strip() for line in f.readlines()]
                logger.info(f"Loaded {len(labels)} labels from {self.label_path}")
            except Exception as e:
                logger.error(f"Error loading labels: {e}")
        else:
            logger.warning(f"Label file not found at {self.label_path}")
        
        return labels
    
    def _initialize_interpreter(self) -> bool:
        """Initialize the TensorFlow Lite interpreter."""
        try:
            # Import TFLite interpreter
            from tflite_runtime.interpreter import Interpreter
            
            # Check if model exists
            if not os.path.exists(self.model_path):
                logger.error(f"Model not found at {self.model_path}")
                return False
            
            # Load interpreter
            self.interpreter = Interpreter(model_path=self.model_path)
            self.interpreter.allocate_tensors()
            
            # Get input and output details
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()
            
            # Get model shape
            self.input_height = self.input_details[0]['shape'][1]
            self.input_width = self.input_details[0]['shape'][2]
            
            # Check if floating point model
            self.floating_model = (self.input_details[0]['dtype'] == np.float32)
            
            # Detect output format - YOLOv8 TFLite has specific output shapes
            num_outputs = len(self.output_details)
            
            # Check output shapes to determine format
            if num_outputs >= 1:
                # YOLOv8 TFLite detection format
                if len(self.output_details[0]['shape']) == 3 and self.output_details[0]['shape'][2] > 5:
                    # Shape is [1, num_detections, 5+num_classes] or similar
                    self.has_detect_output = True
                    logger.info("YOLOv8 detection output format detected")
            
            logger.info(
                f"YOLOv8 TFLite detector initialized: "
                f"input shape={self.input_width}x{self.input_height}, "
                f"floating_model={self.floating_model}"
            )
            return True
            
        except ImportError:
            logger.error("TFLite runtime not available. Install with 'pip install tflite-runtime'")
            return False
        except Exception as e:
            logger.error(f"Error initializing interpreter: {e}")
            return False
    
    def preprocess_image(self, image) -> np.ndarray:
        """
        Preprocess image for the model.
        
        Args:
            image: PIL.Image or numpy array
            
        Returns:
            Preprocessed numpy array ready for inference
        """
        # Convert to PIL if numpy
        if isinstance(image, np.ndarray):
            image = Image.fromarray(image)
        
        # Resize to model input size
        image_resized = image.resize((self.input_width, self.input_height))
        
        # Convert to numpy array
        image_array = np.array(image_resized, dtype=np.float32 if self.floating_model else np.uint8)
        
        # Normalization
        if self.floating_model:
            image_array = image_array / 255.0
        
        # Add batch dimension
        input_data = np.expand_dims(image_array, axis=0)
        
        return input_data
    
    def detect(self, image) -> List[Dict]:
        """
        Detect objects in an image.
        
        Args:
            image: PIL.Image or numpy array
        
        Returns:
            List of detection dictionaries with class, confidence, and bounding box
        """
        if self.interpreter is None:
            return []
        
        # Preprocess image
        input_data = self.preprocess_image(image)
        
        # Set input tensor
        self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
        
        # Run inference
        start_time = time.time()
        self.interpreter.invoke()
        inference_time = time.time() - start_time
        
        # Get results based on output format
        if self.has_detect_output:
            detections = self._process_yolov8_output()
        else:
            # Fallback for classification models
            detections = self._process_classification_output()
        
        # Log performance
        logger.debug(
            f"YOLOv8 inference: {inference_time:.2f}s "
            f"({1/inference_time:.1f} FPS), "
            f"{len(detections)} detections"
        )
        
        return detections
    
    def _process_yolov8_output(self) -> List[Dict]:
        """Process YOLOv8 detection output format."""
        # Get output tensor - format depends on the model
        # For YOLOv8 TFLite, output tensor has shape [1, num_boxes, num_classes+5]
        # where 5 represents [x, y, w, h, confidence]
        output = self.interpreter.get_tensor(self.output_details[0]['index'])
        
        # Get original image dimensions
        original_height, original_width = 0, 0
        if len(self.input_details[0]['shape']) == 4:
            original_height, original_width = self.input_height, self.input_width
        
        detections = []
        for i in range(output.shape[1]):  # For each detection
            # Extract values
            confidence = output[0, i, 4]
            
            # Skip low confidence detections
            if confidence < self.conf_threshold:
                continue
            
            # Calculate class scores
            class_scores = output[0, i, 5:]
            class_id = np.argmax(class_scores)
            class_score = class_scores[class_id]
            
            # Skip low class confidence
            if class_score < self.conf_threshold:
                continue
            
            # Calculate bounding box
            x, y, w, h = output[0, i, 0:4]
            
            # Convert to [0, 1] range and then to pixel values
            xmin = max(0.0, x - w/2) * original_width
            ymin = max(0.0, y - h/2) * original_height
            xmax = min(1.0, x + w/2) * original_width  
            ymax = min(1.0, y + h/2) * original_height
            
            # Get class name
            if class_id < len(self.labels):
                class_name = self.labels[class_id]
            else:
                class_name = f"Class {class_id}"
            
            # Create detection dict
            detections.append({
                'name': class_name,
                'class_id': int(class_id),
                'score': float(class_score),
                'confidence': float(confidence),
                'box': [float(xmin), float(ymin), float(xmax-xmin), float(ymax-ymin)],
                'type': 'yolov8'
            })
        
        return detections
    
    def _process_classification_output(self) -> List[Dict]:
        """Fallback for classification models."""
        # Get output tensor - for classification output is typically [1, num_classes]
        output = self.interpreter.get_tensor(self.output_details[0]['index'])[0]
        
        # Get top predictions
        top_k = 3
        top_indices = np.argsort(-output)[:top_k]
        
        detections = []
        for idx in top_indices:
            score = float(output[idx])
            if score < self.conf_threshold:
                continue
                
            if idx < len(self.labels):
                class_name = self.labels[idx]
            else:
                class_name = f"Class {idx}"
                
            detections.append({
                'name': class_name,
                'class_id': int(idx),
                'score': score,
                'confidence': score,
                'box': None,  # No bounding box for classification
                'type': 'yolov8-class'
            })
            
        return detections
    
    def draw_detections(self, image: np.ndarray, detections: List[Dict]) -> np.ndarray:
        """
        Draw detection boxes and labels on the image.
        
        Args:
            image: Source image as numpy array
            detections: List of detection dictionaries
            
        Returns:
            Image with detections drawn on it
        """
        # Make a copy of the image
        image_with_boxes = image.copy()
        
        # Draw each detection
        for detection in detections:
            # Extract info
            name = detection['name']
            score = detection['score']
            box = detection.get('box')
            
            # Skip if no box
            if box is None:
                continue
                
            # Convert to integers
            x, y, w, h = [int(v) for v in box]
            
            # Draw box
            cv2.rectangle(image_with_boxes, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            # Draw label background
            label = f"{name}: {int(score * 100)}%"
            (label_w, label_h), baseline = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2
            )
            cv2.rectangle(
                image_with_boxes, 
                (x, y - label_h - 5), 
                (x + label_w, y), 
                (0, 255, 0), 
                -1
            )
            
            # Draw label text
            cv2.putText(
                image_with_boxes,
                label,
                (x, y - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 0),
                2
            )
            
        return image_with_boxes