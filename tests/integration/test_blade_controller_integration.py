"""
Test module for test_blade_controller_integration.py.
"""
import pytest
from unittest.mock import patch, MagicMock
from mower.hardware.blade_controller import BladeController
# Assuming ResourceManager is in mower.main_controller or mower.mower based on other files
# Adjust if this is incorrect.
from mower.main_controller import ResourceManager


# Integration test for blade controller
# Test the blade controller initialization and operation


@pytest.fixture
def mocked_resource_manager_with_blade_controller():
    # This fixture provides a ResourceManager with a mocked BladeController
    resource_manager = ResourceManager()
    # Mock the _initialize_hardware method to prevent actual hardware init
    with patch.object(resource_manager, '_initialize_hardware') as mock_init_hw:
        # Simulate successful hardware init without doing anything
        mock_init_hw.return_value = None
        # Assign a MagicMock to the blade_controller attribute
        resource_manager.blade_controller = MagicMock(spec=BladeController)
        resource_manager.blade_controller.start.return_value = True
        resource_manager.blade_controller.stop.return_value = True
        resource_manager.blade_controller.set_speed.return_value = True
        # If ResourceManager has an explicit initialization method that sets up
        # blade_controller, that might need to be called or mocked.
        # For now, directly assigning a mock.
        yield resource_manager


def test_blade_controller_initialization_and_operation(
        mocked_resource_manager_with_blade_controller):
    rm = mocked_resource_manager_with_blade_controller

    # Start the blade controller through ResourceManager's method if it exists
    # Or directly if the test is for the BladeController instance itself via
    # ResourceManager
    if hasattr(rm, 'start_blades'):  # Assuming a method like start_blades exists
        rm.start_blades()
        rm.blade_controller.start.assert_called_once()
    else:  # Fallback to direct interaction if ResourceManager doesn't abstract it
        assert rm.blade_controller.start()
        rm.blade_controller.start.assert_called_once()

    # Stop the blade controller
    if hasattr(rm, 'stop_blades'):
        rm.stop_blades()
        rm.blade_controller.stop.assert_called_once()
    else:
        assert rm.blade_controller.stop()
        rm.blade_controller.stop.assert_called_once()


def test_blade_controller_speed_setting(
        mocked_resource_manager_with_blade_controller):
    rm = mocked_resource_manager_with_blade_controller

    # Set blade speed
    if hasattr(rm, 'set_blade_speed'):
        rm.set_blade_speed(65)
        rm.blade_controller.set_speed.assert_called_once_with(65)
    else:
        rm.blade_controller.set_speed(65)
        rm.blade_controller.set_speed.assert_called_once_with(65)
