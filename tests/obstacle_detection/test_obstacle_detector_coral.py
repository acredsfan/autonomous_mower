"""Test ObstacleDetector YOLOv8 integration with Coral detection."""

import unittest.mock as mock
import pytest
import os


@pytest.fixture
def mock_env_vars():
    """Mock environment variables."""
    env_vars = {
        'YOLOV8_MODEL_PATH': '/fake/path/coral_model_quantized_int8_edgetpu.tflite',
        'LABEL_MAP_PATH': '/fake/path/labels.txt',
        'USE_YOLOV8': 'True',
        'MIN_CONF_THRESHOLD': '0.5'
    }
    with mock.patch.dict(os.environ, env_vars):
        yield env_vars


def test_obstacle_detector_detects_coral_model():
    """Test that ObstacleDetector correctly detects when to use Coral based on filename."""
    with mock.patch('mower.obstacle_detection.obstacle_detector.os.path.exists') as mock_exists:
        with mock.patch('mower.obstacle_detection.obstacle_detector.get_hardware_registry') as mock_registry:
            with mock.patch('mower.obstacle_detection.obstacle_detector.YOLOv8TFLiteDetector') as mock_detector_class:
                
                # Mock file existence
                mock_exists.return_value = True
                
                # Mock hardware registry
                mock_camera = mock.Mock()
                mock_registry.return_value.get_camera.return_value = mock_camera
                
                # Set environment variables
                with mock.patch.dict(os.environ, {
                    'YOLOV8_MODEL_PATH': '/models/coral_model_quantized_int8_edgetpu.tflite',
                    'LABEL_MAP_PATH': '/models/labels.txt',
                    'USE_YOLOV8': 'True',
                    'MIN_CONF_THRESHOLD': '0.5'
                }):
                    
                    from mower.obstacle_detection.obstacle_detector import ObstacleDetector
                    
                    # Create obstacle detector
                    detector = ObstacleDetector()
                    
                    # Verify YOLOv8TFLiteDetector was created with use_coral=True
                    mock_detector_class.assert_called_once_with(
                        model_path='/models/coral_model_quantized_int8_edgetpu.tflite',
                        label_path='/models/labels.txt',
                        conf_threshold=0.5,
                        use_coral=True
                    )


def test_obstacle_detector_detects_cpu_model():
    """Test that ObstacleDetector correctly detects when to use CPU based on filename."""
    with mock.patch('mower.obstacle_detection.obstacle_detector.os.path.exists') as mock_exists:
        with mock.patch('mower.obstacle_detection.obstacle_detector.get_hardware_registry') as mock_registry:
            with mock.patch('mower.obstacle_detection.obstacle_detector.YOLOv8TFLiteDetector') as mock_detector_class:
                
                # Mock file existence
                mock_exists.return_value = True
                
                # Mock hardware registry
                mock_camera = mock.Mock()
                mock_registry.return_value.get_camera.return_value = mock_camera
                
                # Set environment variables with CPU model
                with mock.patch.dict(os.environ, {
                    'YOLOV8_MODEL_PATH': '/models/pi_model_float32.tflite',
                    'LABEL_MAP_PATH': '/models/labels.txt',
                    'USE_YOLOV8': 'True',
                    'MIN_CONF_THRESHOLD': '0.5'
                }):
                    
                    from mower.obstacle_detection.obstacle_detector import ObstacleDetector
                    
                    # Create obstacle detector
                    detector = ObstacleDetector()
                    
                    # Verify YOLOv8TFLiteDetector was created with use_coral=False
                    mock_detector_class.assert_called_once_with(
                        model_path='/models/pi_model_float32.tflite',
                        label_path='/models/labels.txt',
                        conf_threshold=0.5,
                        use_coral=False
                    )


def test_obstacle_detector_yolov8_disabled():
    """Test that YOLOv8 detector is not created when disabled."""
    with mock.patch('mower.obstacle_detection.obstacle_detector.os.path.exists') as mock_exists:
        with mock.patch('mower.obstacle_detection.obstacle_detector.get_hardware_registry') as mock_registry:
            with mock.patch('mower.obstacle_detection.obstacle_detector.YOLOv8TFLiteDetector') as mock_detector_class:
                
                # Mock file existence
                mock_exists.return_value = True
                
                # Mock hardware registry
                mock_camera = mock.Mock()
                mock_registry.return_value.get_camera.return_value = mock_camera
                
                # Set environment variables with YOLOv8 disabled
                with mock.patch.dict(os.environ, {
                    'YOLOV8_MODEL_PATH': '/models/pi_model_float32.tflite',
                    'LABEL_MAP_PATH': '/models/labels.txt',
                    'USE_YOLOV8': 'False',
                    'MIN_CONF_THRESHOLD': '0.5'
                }):
                    
                    from mower.obstacle_detection.obstacle_detector import ObstacleDetector
                    
                    # Create obstacle detector
                    detector = ObstacleDetector()
                    
                    # Verify YOLOv8TFLiteDetector was not created
                    mock_detector_class.assert_not_called()
                    assert detector.yolov8_detector is None


def test_obstacle_detector_coral_filename_variations():
    """Test various Coral filename patterns are detected correctly."""
    coral_filenames = [
        'model_edgetpu.tflite',
        'yolov8_model_EdgeTPU.tflite',
        'coral_model_quantized_int8_edgetpu.tflite',
        'MODEL_EDGETPU.TFLITE'
    ]
    
    cpu_filenames = [
        'model.tflite',
        'yolov8_model_float32.tflite',
        'pi_model.tflite',
        'regular_model.tflite'
    ]
    
    for filename in coral_filenames:
        with mock.patch('mower.obstacle_detection.obstacle_detector.os.path.exists') as mock_exists:
            with mock.patch('mower.obstacle_detection.obstacle_detector.get_hardware_registry') as mock_registry:
                with mock.patch('mower.obstacle_detection.obstacle_detector.YOLOv8TFLiteDetector') as mock_detector_class:
                    
                    # Mock file existence
                    mock_exists.return_value = True
                    
                    # Mock hardware registry
                    mock_camera = mock.Mock()
                    mock_registry.return_value.get_camera.return_value = mock_camera
                    
                    # Set environment variables
                    with mock.patch.dict(os.environ, {
                        'YOLOV8_MODEL_PATH': f'/models/{filename}',
                        'LABEL_MAP_PATH': '/models/labels.txt',
                        'USE_YOLOV8': 'True',
                        'MIN_CONF_THRESHOLD': '0.5'
                    }):
                        
                        from mower.obstacle_detection.obstacle_detector import ObstacleDetector
                        
                        # Create obstacle detector
                        detector = ObstacleDetector()
                        
                        # Verify use_coral=True was passed
                        args, kwargs = mock_detector_class.call_args
                        assert kwargs['use_coral'] is True, f"Failed for filename: {filename}"
    
    for filename in cpu_filenames:
        with mock.patch('mower.obstacle_detection.obstacle_detector.os.path.exists') as mock_exists:
            with mock.patch('mower.obstacle_detection.obstacle_detector.get_hardware_registry') as mock_registry:
                with mock.patch('mower.obstacle_detection.obstacle_detector.YOLOv8TFLiteDetector') as mock_detector_class:
                    
                    # Mock file existence
                    mock_exists.return_value = True
                    
                    # Mock hardware registry
                    mock_camera = mock.Mock()
                    mock_registry.return_value.get_camera.return_value = mock_camera
                    
                    # Set environment variables
                    with mock.patch.dict(os.environ, {
                        'YOLOV8_MODEL_PATH': f'/models/{filename}',
                        'LABEL_MAP_PATH': '/models/labels.txt',
                        'USE_YOLOV8': 'True',
                        'MIN_CONF_THRESHOLD': '0.5'
                    }):
                        
                        from mower.obstacle_detection.obstacle_detector import ObstacleDetector
                        
                        # Create obstacle detector
                        detector = ObstacleDetector()
                        
                        # Verify use_coral=False was passed
                        args, kwargs = mock_detector_class.call_args
                        assert kwargs['use_coral'] is False, f"Failed for filename: {filename}"


if __name__ == "__main__":
    pytest.main([__file__])