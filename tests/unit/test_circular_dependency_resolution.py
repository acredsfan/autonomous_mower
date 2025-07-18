"""
Test for circular dependency resolution in Task 3.2.

This test verifies that the refactored module structure eliminates
circular dependencies and provides clean module boundaries.
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the src directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


class TestCircularDependencyResolution(unittest.TestCase):
    """Test circular dependency resolution between modules."""
    
    def setUp(self):
        """Set up test environment."""
        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {
            'USE_SIMULATION': 'true',
            'MM1_SERIAL_PORT': '/dev/ttyACM1'
        })
        self.env_patcher.start()
    
    def tearDown(self):
        """Clean up after tests."""
        self.env_patcher.stop()
    
    @patch('mower.hardware.camera_instance.get_camera_instance')
    @patch('mower.hardware.robohat.RoboHAT')
    @patch('mower.hardware.blade_controller.BladeController')
    @patch('mower.hardware.serial_port.SerialPort')
    def test_hardware_registry_initialization(self, mock_serial, mock_blade, mock_robohat, mock_camera):
        """Test that HardwareRegistry can initialize without circular dependencies."""
        # Setup mocks
        mock_camera.return_value = MagicMock()
        mock_robohat.return_value = MagicMock()
        mock_blade.return_value = MagicMock()
        mock_serial.return_value = MagicMock()
        
        # Import and test
        from mower.hardware.hardware_registry import get_hardware_registry
        
        registry = get_hardware_registry()
        success = registry.initialize()
        
        self.assertTrue(success)
        self.assertIsNotNone(registry.get_camera())
        self.assertIsNotNone(registry.get_blade_controller())
    
    @patch('mower.hardware.hardware_registry.get_hardware_registry')
    @patch('mower.hardware.async_sensor_manager.AsyncSensorInterface')
    def test_resource_manager_delegates_to_hardware_registry(self, mock_sensor, mock_get_registry):
        """Test that ResourceManager delegates to HardwareRegistry instead of duplicating."""
        # Setup mocks
        mock_registry = MagicMock()
        mock_registry.initialize.return_value = True
        mock_registry.get_camera.return_value = MagicMock()
        mock_registry.get_robohat.return_value = MagicMock()
        mock_get_registry.return_value = mock_registry
        
        mock_sensor_interface = MagicMock()
        mock_sensor.return_value = mock_sensor_interface
        
        # Import and test
        from mower.main_controller import ResourceManager
        
        resource_manager = ResourceManager()
        
        # Test hardware initialization delegates to registry
        success = resource_manager._initialize_hardware()
        self.assertTrue(success)
        mock_registry.initialize.assert_called_once()
        
        # Test that ResourceManager delegates hardware access
        camera = resource_manager.get_camera()
        mock_registry.get_camera.assert_called_once()
        
        robohat = resource_manager.get_robohat()
        mock_registry.get_robohat.assert_called_once()
    
    def test_module_import_isolation(self):
        """Test that modules can be imported independently without circular imports."""
        # These imports should not raise ImportError due to circular dependencies
        
        try:
            from mower.hardware.hardware_registry import HardwareRegistry
            from mower.main_controller import ResourceManager
            from mower.hardware.async_sensor_manager import AsyncSensorManager
            from mower.utilities.async_resource_manager import AsyncResourceManager
        except ImportError as e:
            self.fail(f"Circular import detected: {e}")
    
    @patch('mower.hardware.hardware_registry.get_hardware_registry')
    def test_no_duplicate_hardware_management(self, mock_get_registry):
        """Test that ResourceManager doesn't duplicate hardware management."""
        mock_registry = MagicMock()
        mock_registry.initialize.return_value = True
        mock_get_registry.return_value = mock_registry
        
        from mower.main_controller import ResourceManager
        
        resource_manager = ResourceManager()
        resource_manager._initialize_hardware()
        
        # Verify ResourceManager stores registry reference, not individual components
        hardware_registry = resource_manager._resources.get("hardware_registry")
        self.assertIsNotNone(hardware_registry)
        
        # Verify no duplicate component storage
        self.assertNotIn("camera", resource_manager._resources)
        self.assertNotIn("robohat", resource_manager._resources) 
        self.assertNotIn("blade_controller", resource_manager._resources)


class TestModuleBoundaries(unittest.TestCase):
    """Test clear module boundaries and interfaces."""
    
    def test_hardware_registry_interface(self):
        """Test HardwareRegistry provides expected interface."""
        from mower.hardware.hardware_registry import HardwareRegistry
        
        registry = HardwareRegistry.get_instance()
        
        # Verify expected methods exist
        self.assertTrue(hasattr(registry, 'get_camera'))
        self.assertTrue(hasattr(registry, 'get_robohat'))
        self.assertTrue(hasattr(registry, 'get_blade_controller'))
        self.assertTrue(hasattr(registry, 'get_serial_port'))
        self.assertTrue(hasattr(registry, 'get_ina3221'))
        self.assertTrue(hasattr(registry, 'initialize'))
        self.assertTrue(hasattr(registry, 'cleanup'))
    
    def test_resource_manager_interface(self):
        """Test ResourceManager provides expected interface."""
        from mower.main_controller import ResourceManager
        
        manager = ResourceManager()
        
        # Verify expected delegation methods exist
        self.assertTrue(hasattr(manager, 'get_camera'))
        self.assertTrue(hasattr(manager, 'get_robohat'))
        self.assertTrue(hasattr(manager, 'get_sensor_interface'))
        self.assertTrue(hasattr(manager, 'get_resource'))
    
    def test_async_modules_independence(self):
        """Test that async modules don't interfere with hardware registry."""
        # These should be independent modules
        from mower.hardware.async_sensor_manager import AsyncSensorManager
        from mower.utilities.async_resource_manager import AsyncResourceManager
        
        # Should be able to create instances without affecting hardware registry
        sensor_manager = AsyncSensorManager(simulate=True)
        self.assertIsNotNone(sensor_manager)


if __name__ == '__main__':
    unittest.main()
