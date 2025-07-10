"""Test YOLOv8 Coral integration functionality."""

import unittest.mock as mock
import pytest
import numpy as np
from PIL import Image


@pytest.fixture
def mock_coral_utils():
    """Mock coral_utils module."""
    with mock.patch('mower.obstacle_detection.yolov8_detector.get_interpreter_creator') as mock_creator:
        yield mock_creator


@pytest.fixture
def mock_interpreter():
    """Mock TFLite interpreter."""
    interpreter = mock.Mock()
    
    # Mock input details
    interpreter.get_input_details.return_value = [
        {
            'index': 0,
            'shape': [1, 640, 640, 3],
            'dtype': np.float32
        }
    ]
    
    # Mock output details
    interpreter.get_output_details.return_value = [
        {
            'index': 0,
            'shape': [1, 8400, 85]  # YOLOv8 format: [batch, boxes, features]
        }
    ]
    
    # Mock inference output
    # Format: [x, y, w, h, confidence, class_prob1, class_prob2, ...]
    mock_output = np.zeros((8400, 85))
    # Add one valid detection
    mock_output[0] = [0.5, 0.5, 0.2, 0.3, 0.8] + [0.1] * 79 + [0.9]  # High confidence person detection
    interpreter.get_tensor.return_value = np.expand_dims(mock_output, axis=0)
    
    return interpreter


@pytest.fixture
def mock_labels_file(tmp_path):
    """Create a temporary labels file."""
    labels_file = tmp_path / "labels.txt"
    labels = ["person", "bicycle", "car", "motorcycle", "airplane", "bus", "train"]
    labels_file.write_text("\n".join(labels))
    return str(labels_file)


@pytest.fixture
def mock_model_file(tmp_path):
    """Create a temporary model file."""
    model_file = tmp_path / "test_model.tflite"
    model_file.write_bytes(b"TFL3fake_model_content")  # Fake TFLite content
    return str(model_file)


def test_yolov8_detector_uses_coral_when_enabled(mock_coral_utils, mock_interpreter, mock_labels_file, mock_model_file):
    """Test that YOLOv8 detector uses coral when use_coral=True."""
    from mower.obstacle_detection.yolov8_detector import YOLOv8TFLiteDetector
    
    # Mock the coral utils to return our mock interpreter
    mock_coral_utils.return_value = lambda model_path: mock_interpreter
    
    # Create detector with Coral enabled
    detector = YOLOv8TFLiteDetector(
        model_path=mock_model_file,
        label_path=mock_labels_file,
        conf_threshold=0.5,
        use_coral=True
    )
    
    # Verify coral utils was called with use_coral=True
    mock_coral_utils.assert_called_once_with(use_coral=True)
    
    # Verify interpreter was created
    assert detector.interpreter is not None


def test_yolov8_detector_uses_cpu_when_coral_disabled(mock_coral_utils, mock_interpreter, mock_labels_file, mock_model_file):
    """Test that YOLOv8 detector uses CPU when use_coral=False."""
    from mower.obstacle_detection.yolov8_detector import YOLOv8TFLiteDetector
    
    # Mock the coral utils to return our mock interpreter
    mock_coral_utils.return_value = lambda model_path: mock_interpreter
    
    # Create detector with Coral disabled
    detector = YOLOv8TFLiteDetector(
        model_path=mock_model_file,
        label_path=mock_labels_file,
        conf_threshold=0.5,
        use_coral=False
    )
    
    # Verify coral utils was called with use_coral=False
    mock_coral_utils.assert_called_once_with(use_coral=False)
    
    # Verify interpreter was created
    assert detector.interpreter is not None


def test_yolov8_detector_detection_with_coral(mock_coral_utils, mock_interpreter, mock_labels_file, mock_model_file):
    """Test detection works correctly with Coral integration."""
    from mower.obstacle_detection.yolov8_detector import YOLOv8TFLiteDetector
    
    # Mock the coral utils to return our mock interpreter
    mock_coral_utils.return_value = lambda model_path: mock_interpreter
    
    # Create detector
    detector = YOLOv8TFLiteDetector(
        model_path=mock_model_file,
        label_path=mock_labels_file,
        conf_threshold=0.5,
        use_coral=True
    )
    
    # Create test image
    test_image = Image.new('RGB', (640, 640), color='red')
    
    # Run detection
    detections = detector.detect(test_image)
    
    # Verify detection was performed
    mock_interpreter.set_tensor.assert_called_once()
    mock_interpreter.invoke.assert_called_once()
    mock_interpreter.get_tensor.assert_called_once()
    
    # Verify detection results
    assert len(detections) > 0
    detection = detections[0]
    assert detection['class_name'] == 'person'
    assert detection['confidence'] > 0.5
    assert detection['type'] == 'yolov8_tflite'
    assert len(detection['box']) == 4


if __name__ == "__main__":
    pytest.main([__file__])