import unittest
from unittest.mock import patch, MagicMock
import numpy as np
from hardware_interface.camera import CameraProcessor, SingletonCamera

class TestCameraProcessor(unittest.TestCase):

    @patch.object(SingletonCamera, 'get_frame')
    @patch.object(CameraProcessor, 'detect_objects')
    def test_detect_obstacle(self, mock_detect_objects, mock_get_frame):
        """
        Test the detect_obstacle function to ensure it correctly identifies obstacles.
        """

        # Mock frame data
        mock_frame = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
        mock_get_frame.return_value = mock_frame

        # Mock detection results
        mock_detect_objects.return_value = [{'label': 'Class 1', 'box': [0.1, 0.1, 0.2, 0.2]}]

        # Initialize CameraProcessor
        camera_processor = CameraProcessor()

        # Test obstacle detection when objects are detected
        obstacle_detected = camera_processor.detect_obstacle()
        self.assertTrue(obstacle_detected, "Obstacle should be detected when mock objects are present.")

        # Test obstacle detection when no objects are detected
        mock_detect_objects.return_value = []
        obstacle_detected = camera_processor.detect_obstacle()
        self.assertFalse(obstacle_detected, "Obstacle should not be detected when no objects are present.")

    @patch.object(SingletonCamera, 'get_frame')
    def test_no_frame_detect_obstacle(self, mock_get_frame):
        """
        Test the detect_obstacle function to ensure it handles the absence of frames correctly.
        """
        # Simulate no frame available
        mock_get_frame.return_value = None

        # Initialize CameraProcessor
        camera_processor = CameraProcessor()

        # Test obstacle detection when no frame is available
        obstacle_detected = camera_processor.detect_obstacle()
        self.assertFalse(obstacle_detected, "Obstacle should not be detected when no frame is available.")
        
if __name__ == '__main__':
    unittest.main()