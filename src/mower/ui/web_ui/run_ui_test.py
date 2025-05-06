#!/usr/bin/env python3
"""
Direct test script for the autonomous mower web UI.
This script runs just the web UI with simulated hardware for testing purposes.
"""

import os
import sys
import time
import json
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.mower.hardware.tof_fixed import VL53L0XSensors
from src.mower.hardware.imu_fixed import BNO085Sensor
from src.mower.ui.web_ui.app import create_app


class MockMower:
    """Mock mower class for testing the UI."""

    def __init__(self):
        """Initialize mock resources."""
        self.tof_sensors = VL53L0XSensors()
        self.imu_sensor = BNO085Sensor()
        self.battery_level = 75.0
        self.resource_manager = self

    def get_status(self):
        """Get mower status."""
        return {
            "mode": "IDLE",
            "battery_level": self.battery_level,
            "connection": True,
            "is_error": False,
            "error_message": "",
            "is_mowing": False,
            "is_charging": False,
        }

    def get_safety_status(self):
        """Get safety status from IMU."""
        return self.imu_sensor.get_safety_status()

    def get_sensor_data(self):
        """Get all sensor data."""
        return {
            "imu": {
                "heading": self.imu_sensor.get_heading(),
                "roll": self.imu_sensor.get_roll(),
                "pitch": self.imu_sensor.get_pitch(),
                "calibration": "Simulated",
                "safety_status": self.imu_sensor.get_safety_status(),
            },
            "environment": {"temperature": 22.5, "humidity": 45.0, "pressure": 1013.25},
            "tof": self.tof_sensors.get_distances(),
            "motors": {"leftSpeed": 0.0, "rightSpeed": 0.0, "bladeSpeed": 0.0},
            "gps": {
                "latitude": 37.7749,
                "longitude": -122.4194,
                "fix": True,
                "satellites": 8,
                "hdop": 1.5,
            },
        }

    def get_battery_level(self):
        """Get battery level."""
        # Simulate battery drain/charge
        self.battery_level = max(10.0, min(100.0, self.battery_level + 0.1))
        return self.battery_level

    def get_mode(self):
        """Get current mode."""
        return "IDLE"

    def get_imu_sensor(self):
        """Get IMU sensor."""
        return self.imu_sensor

    def get_gps(self):
        """Get GPS module."""
        return None

    def get_gps_location(self):
        """Get current GPS location."""
        return (37.7749, -122.4194)

    def get_home_location(self):
        """Get home location."""
        return {"latitude": 37.7749, "longitude": -122.4194}

    def set_home_location(self, location):
        """Set home location."""
        return True

    def get_robohat_driver(self):
        """Get motor driver."""
        return None

    def get_path_planner(self):
        """Get path planner."""
        from collections import namedtuple

        PatternConfig = namedtuple(
            "PatternConfig",
            ["pattern_type", "spacing", "angle", "overlap", "boundary_points"],
        )

        class MockPathPlanner:
            def __init__(self):
                self.pattern_config = PatternConfig(
                    pattern_type=type("obj", (object,), {"name": "PARALLEL"}),
                    spacing=20.0,
                    angle=0.0,
                    overlap=5.0,
                    boundary_points=[],
                )
                self.current_path = []

            def generate_pattern(self, pattern_type, settings):
                return []

            def set_boundary_points(self, points):
                self.pattern_config.boundary_points = points
                return True

        return MockPathPlanner()

    def start(self):
        """Start mowing."""
        return True

    def stop(self):
        """Stop mowing."""
        return True

    def emergency_stop(self):
        """Emergency stop."""
        return True

    def get_boundary(self):
        """Get yard boundary."""
        return []

    def get_no_go_zones(self):
        """Get no-go zones."""
        return []

    def save_boundary(self, boundary):
        """Save yard boundary."""
        return True

    def save_no_go_zones(self, zones):
        """Save no-go zones."""
        return True

    def get_mowing_schedule(self):
        """Get mowing schedule."""
        return {}

    def set_mowing_schedule(self, schedule):
        """Set mowing schedule."""
        return True

    def execute_command(self, command, params):
        """Execute arbitrary command."""
        print(f"Executing command: {command} with params: {params}")
        return {"status": "success", "message": "Command executed"}


if __name__ == "__main__":
    # Create a mock mower
    mower = MockMower()

    # Create the Flask app with the mock mower
    app, socketio = create_app(mower)

    # Run the app
    print("Starting web UI with mock hardware. Access at http://localhost:5000")
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
