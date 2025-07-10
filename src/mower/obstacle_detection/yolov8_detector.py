"""
YOLOv8 TFLite model detector for autonomous mower obstacle detection.

This module provides YOLOv8 object detection capabilities
using TensorFlow Lite. It's optimized for Raspberry Pi and
works with both CPU and Coral TPU when available.
"""

import os
import time
from typing import Dict, List

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from mower.utilities.logger_config import LoggerConfigInfo

# Initialize logger
logger = LoggerConfigInfo.get_logger(__name__)


class YOLOv8TFLiteDetector:
    """
    YOLOv8 detector using TensorFlow Lite models.

    This class handles detection with YOLOv8 models that have been converted to TFLite
    format, making them suitable for running on Raspberry Pi and edge devices.
    """

    def __init__(self, model_path: str, label_path: str, conf_threshold: float = 0.5, use_coral: bool = False):
        """
        Initialize the YOLOv8 TFLite detector.

        Args:
            model_path: Path to the YOLOv8 TFLite model
            label_path: Path to the label map file
            conf_threshold: Confidence threshold for detections
            use_coral: Whether to use Coral Edge TPU if available
        """
        self.model_path = model_path
        self.label_path = label_path
        self.conf_threshold = conf_threshold
        self.use_coral = use_coral

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
                with open(self.label_path, "r", encoding="utf-8") as f:
                    labels = [line.strip() for line in f.readlines()]
                logger.info("Loaded %d labels from %s", len(labels), self.label_path)
            except (IOError, ValueError, UnicodeDecodeError) as e:
                logger.error("Error loading label file %s: %s", self.label_path, e)
        else:
            logger.warning("Label file not found at %s", self.label_path)

        return labels

    def _initialize_interpreter(self) -> bool:
        """Initialize the TensorFlow Lite interpreter."""
        try:
            # Import coral utils for interpreter creation
            from mower.obstacle_detection.coral_utils import get_interpreter_creator

            if not os.path.exists(self.model_path):
                logger.error("Model file not found at %s", self.model_path)
                return False

            # Get appropriate interpreter creator function
            interpreter_creator = get_interpreter_creator(use_coral=self.use_coral)
            
            # Load interpreter using coral utils
            self.interpreter = interpreter_creator(model_path=self.model_path)
            self.interpreter.allocate_tensors()

            # Get input and output details
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()

            # Get model shape
            self.input_height = self.input_details[0]["shape"][1]
            self.input_width = self.input_details[0]["shape"][2]

            # Check if floating point model
            self.floating_model = self.input_details[0]["dtype"] == np.float32

            # Detect output format - YOLOv8 TFLite has specific output shapes
            num_outputs = len(self.output_details)

            # Check output shapes to determine format
            # Standard YOLOv8 TFLite export often has one output tensor:
            # Shape [1, num_boxes, num_classes + 5] (x, y, w, h, conf, class_probs...)
            # Or sometimes [1, num_classes + 5, num_boxes]
            if num_outputs >= 1:
                output_shape = self.output_details[0]["shape"]
                # Check if the second-to-last dimension matches num_classes + 5
                # or if the last dimension matches num_classes + 5
                if len(output_shape) == 3 and (
                    output_shape[2] == len(self.labels) + 5 or output_shape[1] == len(self.labels) + 5
                ):
                    self.has_detect_output = True
                    logger.info("Detected YOLOv8 output format.")
                else:
                    logger.warning(
                        "Output tensor shape doesn't match expected YOLOv8 format. "
                        "Falling back to classification processing."
                    )
                    self.has_detect_output = False
                    logger.info(
                        "YOLOv8 TFLite detector initialized: " "input shape=%dx%d, " "floating_model=%s",
                        self.input_width,
                        self.input_height,
                        self.floating_model,
                    )
                return True

        except ImportError:
            logger.error("TFLite runtime not available. " "Install with 'pip install tflite-runtime'")
            return False
        except Exception as e:
            logger.error("Error initializing interpreter: %s", e)
            return False

    def preprocess_image(self, image) -> np.ndarray:
        """
        Preprocess image for the model.

        Args:
            image: PIL.Image or numpy array

        Returns:
            Preprocessed numpy array ready for inference
        """
        # Convert to PIL if numpy, ensuring RGB format
        if isinstance(image, np.ndarray):
            # Handle BGR (OpenCV) to RGB conversion if needed
            if len(image.shape) == 3 and image.shape[2] == 3:
                # Convert BGR to RGB for PIL
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            elif len(image.shape) == 3 and image.shape[2] == 4:
                # Convert BGRA to RGB
                image = cv2.cvtColor(image, cv2.COLOR_BGRA2RGB)
            image = Image.fromarray(image)
        elif isinstance(image, Image.Image):
            # Ensure PIL image is in RGB mode
            if image.mode != 'RGB':
                image = image.convert('RGB')

        # Resize to model input size
        image_resized = image.resize((self.input_width, self.input_height))

        # Convert to numpy array
        image_array = np.array(
            image_resized,
            dtype=np.float32 if self.floating_model else np.uint8,
        )

        # Ensure we have exactly 3 channels (RGB)
        if len(image_array.shape) == 3 and image_array.shape[2] != 3:
            logger.error(f"Image has {image_array.shape[2]} channels, expected 3 (RGB)")
            return None

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
        if self.input_details is None or self.interpreter is None:
            return []
        self.interpreter.set_tensor(self.input_details[0]["index"], input_data)

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

        # Apply Non-Max Suppression (NMS) to filter overlapping detections
        detections = non_max_suppression(detections, iou_threshold=0.5)
        # Log performance
        logger.debug(
            "YOLOv8 inference: %.2fs (%.1f FPS), %d detections",
            inference_time,
            1 / inference_time if inference_time > 0 else 0.0,
            len(detections),
        )
        return detections

    def _process_yolov8_output(self) -> List[Dict]:
        """
        Process YOLOv8 detection output format.
        Handles different possible output tensor layouts.
        """
        # Get output tensor - format depends on the model
        if self.interpreter is None or self.output_details is None:
            return []
        output_data = self.interpreter.get_tensor(self.output_details[0]["index"])[0]

        # Handle different output shapes
        # YOLOv8 can output either [1, num_boxes, num_features] or [1, num_features, num_boxes]
        if len(output_data.shape) == 2:
            # Output shape is [num_boxes, num_features] or [num_features, num_boxes]
            num_classes = len(self.labels)
            expected_features = num_classes + 5  # x, y, w, h, confidence + class probabilities
            
            # Check which dimension matches expected features
            if output_data.shape[1] == expected_features:
                # Shape is [num_boxes, num_features] - correct format
                pass
            elif output_data.shape[0] == expected_features:
                # Shape is [num_features, num_boxes] - need to transpose
                output_data = output_data.T
                logger.debug("Transposed YOLOv8 output from [%d, %d] to [%d, %d]", 
                           output_data.shape[1], output_data.shape[0], 
                           output_data.shape[0], output_data.shape[1])
            else:
                logger.warning("Unexpected YOLOv8 output shape: %s, expected features: %d", 
                             output_data.shape, expected_features)
                # Try to continue with current shape
        else:
            logger.warning("Unexpected YOLOv8 output tensor rank: %d", len(output_data.shape))
            return []

        # Get original image dimensions (use input size as reference)
        original_height, original_width = self.input_height, self.input_width

        detections = []
        num_boxes = output_data.shape[0]

        for i in range(num_boxes):
            # Extract values from each detection
            box_data = output_data[i]
            
            # Handle different YOLOv8 output formats:
            # Format 1: [x, y, w, h, objectness_confidence, class_prob1, class_prob2, ...]
            # Format 2: [x, y, w, h, class_prob1, class_prob2, ...] (no separate objectness)
            
            if len(box_data) >= 5:
                # Extract bounding box coordinates
                x, y, w, h = box_data[0:4]
                
                # Determine confidence and class scores based on format
                if len(box_data) == len(self.labels) + 5:
                    # Format 1: has objectness confidence
                    objectness = box_data[4] 
                    class_scores = box_data[5:]
                    class_id = np.argmax(class_scores)
                    class_confidence = class_scores[class_id]
                    # Final confidence is objectness * class confidence
                    final_confidence = objectness * class_confidence
                elif len(box_data) == len(self.labels) + 4:
                    # Format 2: no separate objectness, just class scores
                    class_scores = box_data[4:]
                    class_id = np.argmax(class_scores)
                    class_confidence = class_scores[class_id]
                    final_confidence = class_confidence
                else:
                    logger.warning("Unexpected box data length: %d", len(box_data))
                    continue
                
                # Skip low confidence detections
                if final_confidence < self.conf_threshold:
                    continue

                # Convert from center coords to [xmin, ymin, xmax, ymax] relative to input size
                xmin = int((x - w / 2) * original_width)
                ymin = int((y - h / 2) * original_height)
                xmax = int((x + w / 2) * original_width)
                ymax = int((y + h / 2) * original_height)

                # Clamp coordinates to image bounds
                xmin = max(0, xmin)
                ymin = max(0, ymin)
                xmax = min(original_width - 1, xmax)
                ymax = min(original_height - 1, ymax)

                # Get class name
                if class_id < len(self.labels):
                    class_name = self.labels[class_id]
                else:
                    class_name = f"Class {class_id}"

                # Create detection dict
                detections.append(
                    {
                        "class_name": class_name,
                        "confidence": float(final_confidence),
                        # Use xmin, ymin, xmax, ymax format
                        "box": [xmin, ymin, xmax, ymax],
                        "type": "yolov8_tflite",
                    }
                )

        return detections

    def _process_classification_output(self) -> List[Dict]:
        """Fallback for classification models."""
        # Get output tensor - for classification output is typically [1,
        # num_classes]
        if self.interpreter is None or self.output_details is None:
            return []
        output = self.interpreter.get_tensor(self.output_details[0]["index"])[0]

        # Get top predictions
        top_k = 3
        top_indices = np.argsort(-output)[:top_k]

        detections = []
        for idx in top_indices:
            score = float(output[idx])
            if score >= self.conf_threshold and idx < len(self.labels):
                detections.append(
                    {
                        "class_name": self.labels[idx],
                        "confidence": score,
                        "box": None,  # No bounding box for classification
                        "type": "classification_tflite",
                    }
                )

        return detections

    def draw_detections(self, image: np.ndarray, detections: List[Dict]) -> np.ndarray:
        """
        Draw detection boxes and labels on the image.

        Args:
            image: Source image as numpy array (BGR format expected by OpenCV)
            detections: List of detection dictionaries

        Returns:
            Image with detections drawn on it
        """
        # Make a copy of the image
        image_with_boxes = image.copy()
        height, width, _ = image_with_boxes.shape

        try:
            font = ImageFont.truetype("arial.ttf", 15)
        except IOError:
            font = ImageFont.load_default()

        # Convert to PIL Image for drawing text
        pil_image = Image.fromarray(cv2.cvtColor(image_with_boxes, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_image)

        # Draw each detection
        for detection in detections:
            box = detection.get("box")
            class_name = detection["class_name"]
            confidence = detection["confidence"]

            if box:
                xmin, ymin, xmax, ymax = map(int, box)

                # Draw rectangle
                draw.rectangle([(xmin, ymin), (xmax, ymax)], outline="red", width=2)

                # Draw label background
                label = f"{class_name}: {confidence:.2f}"
                # Use getbbox for compatibility with PIL >= 10.0
                bbox = font.getbbox(label)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                draw.rectangle(
                    [
                        (xmin, ymin - text_height - 2),
                        (xmin + text_width + 2, ymin),
                    ],
                    fill="red",
                )
                # Draw label text
                draw.text(
                    (xmin + 1, ymin - text_height - 1),
                    label,
                    fill="white",
                    font=font,
                )
            else:
                # Handle classification output (draw text somewhere)
                label = f"{class_name}: {confidence:.2f}"
                draw.text(
                    (10, 10 + detections.index(detection) * 20),
                    label,
                    fill="red",
                    font=font,
                )

        # Convert back to OpenCV format (BGR)
        image_with_boxes = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

        return image_with_boxes


# Helper function (consider moving to utils if needed elsewhere)
def non_max_suppression(detections: List[Dict], iou_threshold: float = 0.5) -> List[Dict]:
    """Apply Non-Maximum Suppression."""
    if not detections:
        return []

    # Sort by confidence score (descending)
    detections.sort(key=lambda x: x["confidence"], reverse=True)

    keep_detections = []
    while detections:
        best_detection = detections.pop(0)
        keep_detections.append(best_detection)

        # Remove overlapping boxes
        remaining_detections = []
        for det in detections:
            iou = calculate_iou(best_detection["box"], det["box"])
            if iou < iou_threshold:
                remaining_detections.append(det)
        detections = remaining_detections

    return keep_detections


def calculate_iou(box1, box2):
    """Calculate Intersection over Union."""
    xmin1, ymin1, xmax1, ymax1 = box1
    xmin2, ymin2, xmax2, ymax2 = box2

    inter_xmin = max(xmin1, xmin2)
    inter_ymin = max(ymin1, ymin2)
    inter_xmax = min(xmax1, xmax2)
    inter_ymax = min(ymax1, ymax2)

    inter_area = max(0, inter_xmax - inter_xmin) * max(0, inter_ymax - inter_ymin)
    area1 = (xmax1 - xmin1) * (ymax1 - ymin1)
    area2 = (xmax2 - xmin2) * (ymax2 - ymin2)
    union_area = area1 + area2 - inter_area

    if union_area == 0:
        return 0.0
    return inter_area / union_area
