"""
Test module for test_camera_issues.py.

This module contains regression tests for camera-related issues.
"""

# os is used in @patch("os.path.exists") decorators
import os  # noqa: F401
import sys
import pytest
# subprocess is used in @patch("subprocess.run") decorators
import subprocess  # noqa: F401
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import the modules we need to test
# Note: This import may fail during linting if the module doesn't exist,
# but that's expected and handled by the try/except block
try:
    from mower.hardware.camera import Camera  # noqa: F401 # type: ignore
except ImportError:
    # Mock Camera class if it doesn't exist
    # This will cause a "Name already defined" warning if linting includes the import,
    # but that's expected in this testing pattern
    # type: ignore[no-redef]
    class Camera:
        def __init__(self, *args, **kwargs):
            pass

        def initialize(self):
            pass

        def capture_image(self):
            pass

        def cleanup(self):
            pass


class TestCameraIssues:
    """Tests for camera issues."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create a mock subprocess
        self.mock_subprocess = MagicMock()
        self.mock_subprocess.run.return_value.return_code = 0
        self.mock_subprocess.run.return_value.stdout = b"Camera detected"

    @patch("subprocess.run")
    def test_camera_connection(self, mock_run):
        """
        Test that the camera connection is properly checked.

        This tests the fix for the issue mentioned in the README.md
        troubleshooting section: "Camera Issues" - "Check camera connection and enable"
        """
        # Mock subprocess.run to return success for camera check
        mock_run.return_value = MagicMock(
            return_code=0, stdout=b"supported = 1 detected=1"
        )

        # Create a Camera instance
        with patch("mower.hardware.camera.Camera._initialize_picamera"):
            camera = Camera()

            # Call the method that would check the camera connection
            with patch(
                "mower.hardware.camera.Camera._check_camera_enabled"
            ) as mock_check:
                mock_check.return_value = True
                camera.initialize()

        # Verify that subprocess.run was called to check the camera
        mock_run.assert_called_with(
            ["vcgencmd", "get_camera"],
            capture_output=True,
            text=True,
            check=False,
        )

    @patch("subprocess.run")
    def test_camera_not_detected(self, mock_run):
        """
        Test that the system properly handles a camera that is not detected.

        This tests the fix for the issue mentioned in the README.md
        troubleshooting section: "Camera Issues" - "Check camera connection and enable"
        """
        # Mock subprocess.run to return failure for camera check
        mock_run.return_value = MagicMock(
            return_code=0, stdout=b"supported = 1 detected=0"
        )

        # Create a Camera instance
        with patch("mower.hardware.camera.Camera._initialize_picamera"):
            camera = Camera()

            # Call the method that would check the camera connection
            with patch(
                "mower.hardware.camera.Camera._check_camera_enabled"
            ) as mock_check:
                mock_check.return_value = False

                # The initialize method should raise an exception if the camera
                # is not detected
                with pytest.raises(Exception) as excinfo:
                    camera.initialize()

                # Verify that the exception message mentions the camera not
                # being detected
                assert "camera not detected" in str(excinfo.value).lower()

        # Verify that subprocess.run was called to check the camera
        mock_run.assert_called_with(
            ["vcgencmd", "get_camera"],
            capture_output=True,
            text=True,
            check=False,
        )

    @patch("os.path.exists")
    def test_camera_device_detection(self, mock_exists):
        """
        Test that the camera device files are properly checked.

        This tests the fix for the issue mentioned in the README.md
        troubleshooting section: "Camera Issues" - "Verify camera devices"
        """
        # Mock os.path.exists to return True for camera device files
        mock_exists.return_value = True

        # Create a Camera instance
        with patch("mower.hardware.camera.Camera._initialize_picamera"):
            camera = Camera()

            # Call the method that would check the camera device files
            with patch(
                "mower.hardware.camera.Camera._check_camera_devices"
            ) as mock_check:
                mock_check.return_value = True
                camera.initialize()

        # Verify that os.path.exists was called to check the camera device
        # files
        mock_exists.assert_called()

    @patch("os.path.exists")
    def test_camera_device_not_found(self, mock_exists):
        """
        Test that the system properly handles missing camera device files.

        This tests the fix for the issue mentioned in the README.md
        troubleshooting section: "Camera Issues" - "Verify camera devices"
        """
        # Mock os.path.exists to return False for camera device files
        mock_exists.return_value = False

        # Create a Camera instance
        with patch("mower.hardware.camera.Camera._initialize_picamera"):
            camera = Camera()

            # Call the method that would check the camera device files
            with patch(
                "mower.hardware.camera.Camera._check_camera_devices"
            ) as mock_check:
                mock_check.return_value = False

                # The initialize method should raise an exception if the camera
                # device files are not found
                with pytest.raises(Exception) as excinfo:
                    camera.initialize()

                # Verify that the exception message mentions the camera device
                # files not being found
                assert "camera device" in str(excinfo.value).lower()

        # Verify that os.path.exists was called to check the camera device
        # files
        mock_exists.assert_called()

    @patch("subprocess.run")
    def test_camera_permissions(self, mock_run):
        """
        Test that the camera permissions are properly checked.

        This tests the fix for the issue mentioned in the README.md
        troubleshooting section: "Camera Issues" - "Check camera permissions"
        """
        # Mock subprocess.run to return success for camera permissions check
        mock_run.return_value = MagicMock(return_code=0, stdout=b"pi video")

        # Create a Camera instance
        with patch("mower.hardware.camera.Camera._initialize_picamera"):
            camera = Camera()

            # Call the method that would check the camera permissions
            with patch(
                "mower.hardware.camera.Camera._check_camera_permissions"
            ) as mock_check:
                mock_check.return_value = True
                camera.initialize()

        # Verify that subprocess.run was called to check the camera permissions
        mock_run.assert_called()

    @patch("subprocess.run")
    def test_camera_permissions_issue(self, mock_run):
        """
        Test that the system properly handles camera permission issues.

        This tests the fix for the issue mentioned in the README.md
        troubleshooting section: "Camera Issues" - "Check camera permissions"
        """
        # Mock subprocess.run to return failure for camera permissions check
        mock_run.return_value = MagicMock(
            return_code=0, stdout=b"pi"
        )  # 'video' group missing

        # Create a Camera instance
        with patch("mower.hardware.camera.Camera._initialize_picamera"):
            camera = Camera()

            # Call the method that would check the camera permissions
            with patch(
                "mower.hardware.camera.Camera._check_camera_permissions"
            ) as mock_check:
                mock_check.return_value = False

                # The initialize method should raise an exception if the camera
                # permissions are incorrect
                with pytest.raises(Exception) as excinfo:
                    camera.initialize()

                # Verify that the exception message mentions the camera
                # permissions
                assert "permission" in str(excinfo.value).lower()

        # Verify that subprocess.run was called to check the camera permissions
        mock_run.assert_called()

    @patch("picamera.PiCamera")
    def test_camera_initialization(self, mock_picamera):
        """
        Test that the camera is properly initialized.

        This tests the overall camera initialization process,
        which should handle all the issues mentioned in the README.md
        troubleshooting section.
        """
        # Mock PiCamera to return a mock camera
        mock_camera = MagicMock()
        mock_picamera.return_value = mock_camera

        # Create a Camera instance
        with patch(
            "mower.hardware.camera.Camera._check_camera_enabled",
            return_value=True,
        ):
            with patch(
                "mower.hardware.camera.Camera._check_camera_devices",
                return_value=True,
            ):
                with patch(
                    "mower.hardware.camera.Camera._check_camera_permissions",
                    return_value=True,
                ):
                    camera = Camera()
                    camera.initialize()

        # Verify that PiCamera was called to initialize the camera
        mock_picamera.assert_called()

        # Verify that the camera was configured
        assert (
            mock_camera.method_calls
        ), "Camera should be configured after initialization"


if __name__ == "__main__":
    pytest.main(["-v", __file__])
