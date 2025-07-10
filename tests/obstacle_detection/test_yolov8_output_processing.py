"""Test YOLOv8 output processing for different tensor layouts."""

import unittest.mock as mock
import pytest
import numpy as np
from PIL import Image


@pytest.fixture
def mock_labels_file(tmp_path):
    """Create a temporary labels file."""
    labels_file = tmp_path / "labels.txt"
    labels = ["person", "bicycle", "car"]
    labels_file.write_text("\n".join(labels))
    return str(labels_file)


@pytest.fixture
def mock_model_file(tmp_path):
    """Create a temporary model file."""
    model_file = tmp_path / "test_model.tflite"
    model_file.write_bytes(b"TFL3fake_model_content")
    return str(model_file)


def create_mock_interpreter_with_output_shape(output_shape, output_data):
    """Create mock interpreter with specific output shape."""
    interpreter = mock.Mock()
    
    # Mock input details
    interpreter.get_input_details.return_value = [
        {
            'index': 0,
            'shape': [1, 640, 640, 3],
            'dtype': np.float32
        }
    ]
    
    # Mock output details with specified shape
    interpreter.get_output_details.return_value = [
        {
            'index': 0,
            'shape': output_shape
        }
    ]
    
    # Mock inference output
    interpreter.get_tensor.return_value = output_data
    
    return interpreter


def test_yolov8_output_processing_standard_layout():
    """Test output processing with standard [num_boxes, num_features] layout."""
    from mower.obstacle_detection.yolov8_detector import YOLOv8TFLiteDetector
    
    # Create test data in standard format [num_boxes, num_features]
    # Format: [x, y, w, h, objectness, class1, class2, class3]
    output_data = np.zeros((100, 8))  # 100 boxes, 8 features (4 bbox + 1 objectness + 3 classes)
    
    # Add one valid detection
    output_data[0] = [0.5, 0.5, 0.2, 0.3, 0.8, 0.1, 0.1, 0.9]  # High confidence car detection
    
    # Wrap in batch dimension
    output_data = np.expand_dims(output_data, axis=0)
    
    with mock.patch('mower.obstacle_detection.yolov8_detector.get_interpreter_creator') as mock_creator:
        mock_interpreter = create_mock_interpreter_with_output_shape([1, 100, 8], output_data)
        mock_creator.return_value = lambda model_path: mock_interpreter
        
        # Create detector
        detector = YOLOv8TFLiteDetector(
            model_path="fake_model.tflite",
            label_path="fake_labels.txt",
            conf_threshold=0.5,
            use_coral=False
        )
        
        # Mock labels
        detector.labels = ["person", "bicycle", "car"]
        detector.has_detect_output = True
        
        # Test output processing
        detections = detector._process_yolov8_output()
        
        # Verify detection
        assert len(detections) == 1
        detection = detections[0]
        assert detection['class_name'] == 'car'
        assert detection['confidence'] > 0.5


def test_yolov8_output_processing_transposed_layout():
    """Test output processing with transposed [num_features, num_boxes] layout."""
    from mower.obstacle_detection.yolov8_detector import YOLOv8TFLiteDetector
    
    # Create test data in transposed format [num_features, num_boxes]
    output_data = np.zeros((8, 100))  # 8 features, 100 boxes
    
    # Add one valid detection in column 0
    output_data[:, 0] = [0.5, 0.5, 0.2, 0.3, 0.8, 0.1, 0.1, 0.9]  # High confidence car detection
    
    # Wrap in batch dimension
    output_data = np.expand_dims(output_data, axis=0)
    
    with mock.patch('mower.obstacle_detection.yolov8_detector.get_interpreter_creator') as mock_creator:
        mock_interpreter = create_mock_interpreter_with_output_shape([1, 8, 100], output_data)
        mock_creator.return_value = lambda model_path: mock_interpreter
        
        # Create detector
        detector = YOLOv8TFLiteDetector(
            model_path="fake_model.tflite",
            label_path="fake_labels.txt",
            conf_threshold=0.5,
            use_coral=False
        )
        
        # Mock labels
        detector.labels = ["person", "bicycle", "car"]
        detector.has_detect_output = True
        
        # Test output processing
        detections = detector._process_yolov8_output()
        
        # Verify detection (should work after transposition)
        assert len(detections) == 1
        detection = detections[0]
        assert detection['class_name'] == 'car'
        assert detection['confidence'] > 0.5


def test_yolov8_output_processing_no_objectness():
    """Test output processing without separate objectness confidence."""
    from mower.obstacle_detection.yolov8_detector import YOLOv8TFLiteDetector
    
    # Create test data without objectness [x, y, w, h, class1, class2, class3]
    output_data = np.zeros((100, 7))  # 100 boxes, 7 features (4 bbox + 3 classes)
    
    # Add one valid detection
    output_data[0] = [0.5, 0.5, 0.2, 0.3, 0.1, 0.1, 0.9]  # High confidence car detection
    
    # Wrap in batch dimension
    output_data = np.expand_dims(output_data, axis=0)
    
    with mock.patch('mower.obstacle_detection.yolov8_detector.get_interpreter_creator') as mock_creator:
        mock_interpreter = create_mock_interpreter_with_output_shape([1, 100, 7], output_data)
        mock_creator.return_value = lambda model_path: mock_interpreter
        
        # Create detector
        detector = YOLOv8TFLiteDetector(
            model_path="fake_model.tflite",
            label_path="fake_labels.txt",
            conf_threshold=0.5,
            use_coral=False
        )
        
        # Mock labels
        detector.labels = ["person", "bicycle", "car"]
        detector.has_detect_output = True
        
        # Test output processing
        detections = detector._process_yolov8_output()
        
        # Verify detection
        assert len(detections) == 1
        detection = detections[0]
        assert detection['class_name'] == 'car'
        assert detection['confidence'] > 0.5


def test_yolov8_output_processing_low_confidence_filtered():
    """Test that low confidence detections are filtered out."""
    from mower.obstacle_detection.yolov8_detector import YOLOv8TFLiteDetector
    
    # Create test data with low confidence
    output_data = np.zeros((100, 8))
    
    # Add low confidence detection
    output_data[0] = [0.5, 0.5, 0.2, 0.3, 0.3, 0.1, 0.1, 0.2]  # Low confidence
    
    # Wrap in batch dimension
    output_data = np.expand_dims(output_data, axis=0)
    
    with mock.patch('mower.obstacle_detection.yolov8_detector.get_interpreter_creator') as mock_creator:
        mock_interpreter = create_mock_interpreter_with_output_shape([1, 100, 8], output_data)
        mock_creator.return_value = lambda model_path: mock_interpreter
        
        # Create detector with high threshold
        detector = YOLOv8TFLiteDetector(
            model_path="fake_model.tflite",
            label_path="fake_labels.txt",
            conf_threshold=0.5,  # Higher than the test detection
            use_coral=False
        )
        
        # Mock labels
        detector.labels = ["person", "bicycle", "car"]
        detector.has_detect_output = True
        
        # Test output processing
        detections = detector._process_yolov8_output()
        
        # Verify no detections (filtered out)
        assert len(detections) == 0


if __name__ == "__main__":
    pytest.main([__file__])