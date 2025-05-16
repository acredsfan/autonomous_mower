"""
Test module for test_resource_manager.py.
"""
import unittest
from unittest.mock import MagicMock
from mower.main_controller import ResourceManager


class TestResourceManager(unittest.TestCase):
    def setUp(self):
        self.resource_manager = ResourceManager()

    def test_get_status(self):
        """
Test module for test_resource_manager.py.
        """
        self.resource_manager.current_state = MagicMock(name="IDLE")
        self.resource_manager.get_battery_status = MagicMock(
            return_value="75 % "
        )
        self.resource_manager.get_gps_location = MagicMock(
            return_value=(37.7749, - 122.4194)
        )

        status = self.resource_manager.get_status()

        self.assert Equal(status["state"], "IDLE")
        self.assert Equal(status["battery"], "75 % ")
        self.assert Equal(status["location"], (37.7749, - 122.4194))


if __name__ == "__main__":
    unittest.main()
