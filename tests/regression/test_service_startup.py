"""
Test module for test_service_startup.py.
"""

from mower.main_controller import RobotController, ResourceManager
import os
import sys
import pytest
import tempfile
import shutil
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import the modules we need to test


class TestServiceStartupIssues:
    """Tests for service startup issues."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create a temporary directory for logs
        self.temp_dir = tempfile.mkdtemp()
        self.log_dir = Path(self.temp_dir) / "logs"
        self.log_dir.mkdir(exist_ok=True)

        # Create a mock resource manager
        self.mock_resource_manager = MagicMock(spec=ResourceManager)

        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def teardown_method(self):
        """Tear down test fixtures after each test method."""
        # Remove the temporary directory
        shutil.rmtree(self.temp_dir)

    @patch("os.path.exists")
    @patch("os.makedirs")
    @patch("os.chmod")
    def test_log_directory_creation(
        self, mock_chmod, mock_makedirs, mock_exists
    ):
        """Test that the log directory is created if it does not exist.

        This tests the fix for the issue mentioned in the README.md troubleshooting section:
        "Service Won't Start" - "Check log directory permissions"
        """
        # Mock os.path.exists to return False for the log directory
        mock_exists.return_value = False

        # Create a RobotController instance
        with patch(
            "mower.main_controller.ResourceManager",
            return_value=self.mock_resource_manager,
        ):
            with patch("mower.main_controller.RobotController._load_config"):
                controller = RobotController()

                # Call the method that would create the log directory
                with patch("mower.main_controller.LOG_DIR", self.log_dir):
                    controller._initialize_logging()

        # Verify that os.makedirs was called to create the log directory
        mock_makedirs.assert _called_with(self.log_dir, exist_ok=True)

        # Verify that os.chmod was called to set the permissions
        mock_chmod.assert_called()

    @patch("os.path.exists")
    @patch("os.access")
    def test_log_directory_permissions(self, mock_access, mock_exists):
        """
        Test that the log directory permissions are checked and
        fixed if needed.

        This tests the fix for the issue mentioned in the README.md troubleshooting section:
        "Service Won't Start" - "Check log directory permissions"
        """
        # Mock os.path.exists to return True for the log directory
        mock_exists.return_value = True

        # Mock os.access to return False(no write permission)
        mock_access.return_value = False

        # Create a RobotController instance
        with patch(
            "mower.main_controller.ResourceManager",
            return_value=self.mock_resource_manager,
        ):
            with patch("mower.main_controller.RobotController._load_config"):
                controller = RobotController()

                # Call the method that would check and fix the log directory
                # permissions
                with patch("mower.main_controller.LOG_DIR", self.log_dir):
                    with patch("os.chmod") as mock_chmod:
                        controller._initialize_logging()

        # Verify that os.access was called to check the permissions
        mock_access.assert_called_with(self.log_dir, os.W_OK)

    @patch("logging.FileHandler")
    def test_log_file_creation(self, mock_file_handler):
        """
        Test that log files are created successfully.

        This tests the fix for the issue mentioned in the README.md troubleshooting section:
        "Service Won't Start" - "Check service logs"
        """
        # Create a RobotController instance
        with patch(
            "mower.main_controller.ResourceManager",
            return_value=self.mock_resource_manager,
        ):
            with patch("mower.main_controller.RobotController._load_config"):
                controller = RobotController()

                # Call the method that would create the log files
                with patch("mower.main_controller.LOG_DIR", self.log_dir):
                    controller._initialize_logging()

        # Verify that FileHandler was called to create the log files
        assert (
            mock_file_handler.call_count > 0
        ), "FileHandler should be called to create log files"

    @patch("importlib.import_module")
    def test_python_environment(self, mock_import_module):
        """
        Test that the Python environment is correctly set up.

        This tests the fix for the issue mentioned in the README.md troubleshooting section:
        "Service Won't Start" - "Verify Python environment"
        """
        # Mock importlib.import_module to return a mock module
        mock_module = MagicMock()
        mock_import_module.return_value = mock_module

        # Create a ResourceManager instance
        with patch(
            "mower.main_controller.ResourceManager._initialize_hardware"
        ):
            with patch(
                "mower.main_controller.ResourceManager._initialize_software"
            ):
                resource_manager = ResourceManager()

                # Call the method that would import modules
                resource_manager.initialize()

        # Verify that importlib.import_module was called
        mock_import_module.assert_called()


if __name__ == "__main__":
    pytest.main(["-v", __file__])
