import unittest
from unittest.mock import MagicMock
from mower.main_controller import ResourceManager


class TestResourceManager(unittest.TestCase):
    def setUp(self):
        self.resource_manager = ResourceManager()

    def test_get_status(self):
        """Test the get_status method."""
        self.resource_manager.current_state = MagicMock(name="IDLE")
        self.resource_manager.get_battery_status = MagicMock(
            return_value="75%"
        )
        self.resource_manager.get_gps_location = MagicMock(
            return_value=(37.7749, -122.4194)
        )

        status = self.resource_manager.get_status()

        self.assertEqual(status["state"], "IDLE")
        self.assertEqual(status["battery"], "75%")
        self.assertEqual(status["location"], (37.7749, -122.4194))


if __name__ == "__main__":
    unittest.main()
