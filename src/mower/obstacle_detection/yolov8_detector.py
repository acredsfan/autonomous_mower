"""
YOLOv8 TFLite model detector for autonomous mower obstacle detection.

This module provides YOLOv8 object detection capabilities
using TensorFlow Lite. It's optimized for Raspberry Pi and
works with both CPU and Coral TPU when available.
"""

import os
import time
import numpy as np
import cv2
from typing import List, Dict

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
                logger.error(f"Error loading label file {self.label_path}: {e}")
        else:
            logger.warning(f"Label file not found at {self.label_path}")

        return labels

    def _initialize_interpreter(self) -> bool:
        """Initialize the TensorFlow Lite interpreter."""
        try:
            # Import TFLite interpreter
            from tflite_runtime.interpreter import Interpreter  # type: ignore

            # Check if model exists
            if not os.path.exists(self.model_path):
                logger.error(f"Model file not found at {self.model_path}")
                return False

            # Load interpreter
            self.interpreter = Interpreter(model_path=self.model_path)
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
                    output_shape[2] == len(self.labels) + 5
                    or output_shape[1] == len(self.labels) + 5
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
                f"YOLOv8 TFLite detector initialized: "
                f"input shape={self.input_width}x{self.input_height}, "
                f"floating_model={self.floating_model}"
            )
            return True

        except ImportError:
            logger.error(
                "TFLite runtime not available. "
                "Install with 'pip install tflite-runtime'"
            )
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
        image_array = np.array(
            image_resized,
            dtype=np.float32 if self.floating_model else np.uint8,
        )

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
            f"YOLOv8 inference: {inference_time:.2f}s "
            f"({1/inference_time:.1f} FPS), "
            f"{len(detections)} detections"
        )

        return detections

    def _process_yolov8_output(self) -> List[Dict]:
        """Process YOLOv8 detection output format."""
        # Get output tensor - format depends on the model
        # Shape [num_boxes, num_classes+5] or [num_classes+5, num_boxes]
        output_data = self.interpreter.get_tensor(self.output_details[0]["index"])[0]

        # Check if we need to transpose
        if output_data.shape[0] == len(self.labels) + 5:
            output_data = output_data.T  # Transpose to [num_boxes, num_classes+5]

        # Get original image dimensions (use input size as reference)
        original_height, original_width = self.input_height, self.input_width

        detections = []
        num_boxes = output_data.shape[0]

        for i in range(num_boxes):  # For each detection
            # Extract values [x, y, w, h, confidence, class_probs...]
            box_data = output_data[i]
            confidence = box_data[4]

            # Skip low confidence detections
            if confidence < self.conf_threshold:
                continue

            # Calculate class scores
            class_scores = box_data[5:]
            class_id = np.argmax(class_scores)
            class_score = class_scores[class_id] * confidence  # Combined score

            # Skip low class confidence
            if class_score < self.conf_threshold:
                continue

            # Calculate bounding box (center_x, center_y, width, height)
            x, y, w, h = box_data[0:4]

            # Convert from center coords to [xmin, ymin, xmax, ymax] relative
            # to input size
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
                    "confidence": float(class_score),
                    # Use xmin, ymin, xmax, ymax format
                    "box": [xmin, ymin, xmax, ymax],
                    "type": "yolov8_tflite",
                }
            )

        # TODO: Add Non-Max Suppression (NMS) if the exported model doesn't include it
        # detections = self.non_max_suppression(detections)

        return detections

    def _process_classification_output(self) -> List[Dict]:
        """Fallback for classification models."""
        # Get output tensor - for classification output is typically [1, num_classes]
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
            font = ImageFont.truetype("arial.ttf", 15)  # Or a default font
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

                # Scale box if needed (assuming box coords are relative to
                # model input size)
                # This might not be necessary if _process_yolov8_output already
                # scales them
                # xmin = int(xmin * width / self.input_width)
                # ymin = int(ymin * height / self.input_height)
                # xmax = int(xmax * width / self.input_width)
                # ymax = int(ymax * height / self.input_height)

                # Draw rectangle
                draw.rectangle([(xmin, ymin), (xmax, ymax)], outline="red", width=2)

                # Draw label background
                label = f"{class_name}: {confidence:.2f}"
                text_width, text_height = font.getsize(label)
                draw.rectangle(
                    [(xmin, ymin - text_height - 2), (xmin + text_width + 2, ymin)],
                    fill="red",
                )
                # Draw label text
                draw.text(
                    (xmin + 1, ymin - text_height - 1), label, fill="white", font=font
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
def non_max_suppression(
    detections: List[Dict], iou_threshold: float = 0.5
) -> List[Dict]:
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
