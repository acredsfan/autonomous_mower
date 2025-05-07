"""
Simulation helper for the web UI to provide simulated
sensor data when running on Windows
or in simulation mode.
"""

import os
# import math
import time
import random
import platform
import logging
from typing import Dict, Any

# Initialize logger
logger = logging.getLogger(__name__)

# Check if running on Windows - likely a development environment without
# real hardware
IS_WINDOWS = platform.system() == "Windows"

# Cache for simulated data to provide consistent but changing values over time
_sim_data_cache = {
    "last_update": time.time(),
    "heading": 0.0,
    "pitch": 0.0,
    "roll": 0.0,
    "temperature": 21.5,
    "humidity": 45.0,
    "pressure": 1013.25,
    "left_distance": 120.0,
    "right_distance": 85.0,
    "front_distance": 150.0,
    "left_motor_speed": 0.0,
    "right_motor_speed": 0.0,
    "blade_speed": 0.0,
}


def should_use_simulation() -> bool:
    """
    Determine if simulation mode should be used based on platform and env variables.

    Returns:
        bool: True if simulation should be used
    """
    # Check environment variable
    sim_env = os.environ.get(
        "USE_SIMULATION", "").lower() in (
        "true", "1", "yes")

    # Check if we're running on Windows
    return IS_WINDOWS or sim_env


def get_simulated_sensor_data() -> Dict[str, Any]:
    """
    Generate simulated sensor data for testing and development
    on systems without hardware.

    Returns:
        Dict[str, Any]: Simulated sensor data
    """
    global _sim_data_cache

    current_time = time.time()
    elapsed_time = current_time - _sim_data_cache["last_update"]

    # Only update values every 0.5 seconds for more natural changes
    if elapsed_time > 0.5:
        # Update simulated values with small random changes
        _sim_data_cache.update(
            {
                "last_update": current_time,
                "heading": (_sim_data_cache["heading"] + random.uniform(-5, 5)) % 360,
                "pitch": max(
                    -30, min(30, _sim_data_cache["pitch"] + random.uniform(-1, 1))
                ),
                "roll": max(
                    -30, min(30, _sim_data_cache["roll"] + random.uniform(-1, 1))
                ),
                "temperature": max(
                    10,
                    min(40, _sim_data_cache["temperature"] + random.uniform(-0.2, 0.2)),
                ),
                "humidity": max(
                    20, min(90, _sim_data_cache["humidity"] + random.uniform(-1, 1))
                ),
                "pressure": max(
                    980,
                    min(1030, _sim_data_cache["pressure"] + random.uniform(-0.5, 0.5)),
                ),
                "left_distance": max(
                    5,
                    min(300, _sim_data_cache["left_distance"] + random.uniform(-5, 5)),
                ),
                "right_distance": max(
                    5,
                    min(300, _sim_data_cache["right_distance"] + random.uniform(-5, 5)),
                ),
                "front_distance": max(
                    5,
                    min(300, _sim_data_cache["front_distance"] + random.uniform(-5, 5)),
                ),
            }
        )

    # Create a complete sensor data structure
    return {
        "imu": {
            "heading": _sim_data_cache["heading"],
            "roll": _sim_data_cache["roll"],
            "pitch": _sim_data_cache["pitch"],
            "calibration": "Simulated",
            "safety_status": {
                "tilt_warning": abs(_sim_data_cache["roll"]) > 20
                or abs(_sim_data_cache["pitch"]) > 20,
                "tilt_error": abs(_sim_data_cache["roll"]) > 30
                or abs(_sim_data_cache["pitch"]) > 30,
                "vibration_warning": False,
                "vibration_error": False,
                "impact_detected": False,
            },
        },
        "environment": {
            "temperature": _sim_data_cache["temperature"],
            "humidity": _sim_data_cache["humidity"],
            "pressure": _sim_data_cache["pressure"],
        },
        "tof": {
            "left": _sim_data_cache["left_distance"],
            "right": _sim_data_cache["right_distance"],
            "front": _sim_data_cache["front_distance"],
        },
        "motors": {
            "leftSpeed": _sim_data_cache["left_motor_speed"],
            "rightSpeed": _sim_data_cache["right_motor_speed"],
            "bladeSpeed": _sim_data_cache["blade_speed"],
        },
        "gps": {
            "latitude": 37.7749 + random.uniform(-0.0001, 0.0001),
            "longitude": -122.4194 + random.uniform(-0.0001, 0.0001),
            "fix": True,
            "fix_quality": "3d",
            "satellites": random.randint(6, 12),
            "hdop": random.uniform(1.0, 2.0),
        },
    }


def update_simulated_motor_data(
        left_speed: float = None,
        right_speed: float = None,
        blade_speed: float = None) -> None:
    """
    Update the simulated motor values to reflect commands sent by the user.

    Args:
        left_speed: Left motor speed (-1.0 to 1.0)
        right_speed: Right motor speed (-1.0 to 1.0)
        blade_speed: Blade motor speed (0.0 to 1.0)
    """
    global _sim_data_cache

    if left_speed is not None:
        _sim_data_cache["left_motor_speed"] = max(-1.0, min(1.0, left_speed))

    if right_speed is not None:
        _sim_data_cache["right_motor_speed"] = max(-1.0, min(1.0, right_speed))

    if blade_speed is not None:
        _sim_data_cache["blade_speed"] = max(0.0, min(1.0, blade_speed))
