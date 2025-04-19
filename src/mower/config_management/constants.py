"""
Configuration constants for the autonomous mower.

This module defines constants for the configuration management system,
including standard configuration paths and default values.
"""

import os
from pathlib import Path

# Base directory for consistent file referencing
BASE_DIR = Path(__file__).parent.parent.parent.parent

# Configuration directory
CONFIG_DIR = BASE_DIR / "config"

# Standard configuration files
USER_POLYGON_PATH = CONFIG_DIR / "user_polygon.json"
HOME_LOCATION_PATH = CONFIG_DIR / "home_location.json"
MOWING_SCHEDULE_PATH = CONFIG_DIR / "mowing_schedule.json"
PATTERN_PLANNER_PATH = CONFIG_DIR / "models" / "pattern_planner.json"

# Default configuration values
DEFAULT_CONFIG = {
    # General settings
    "mower": {
        "name": "AutonoMow",
        "log_level": "INFO",
        "debug_mode": False,
    },
    
    # Hardware settings
    "hardware": {
        "use_simulation": False,
        "imu_address": "0x68",
        "gps_serial_port": "/dev/ttyAMA0",
        "gps_baud_rate": 115200,
        "gps_timeout": 1,
    },
    
    # Camera settings
    "camera": {
        "use_camera": True,
        "width": 640,
        "height": 480,
        "fps": 30,
        "index": 0,
    },
    
    # Path planning settings
    "path_planning": {
        "default_speed": 0.5,
        "max_speed": 1.0,
        "turn_speed": 0.3,
        "avoidance_distance": 40,
        "stop_distance": 20,
        "pattern_type": "PARALLEL",
        "spacing": 0.3,
        "angle": 0.0,
        "overlap": 0.1,
    },
    
    # Safety settings
    "safety": {
        "emergency_stop_pin": 7,
        "watchdog_timeout": 15,
        "battery_low_threshold": 20,
        "battery_critical_threshold": 10,
        "max_slope_angle": 15,
        "rain_sensor_enabled": True,
        "tilt_sensor_enabled": True,
    },
    
    # Web UI settings
    "web_ui": {
        "enable": True,
        "port": 5000,
        "enable_ssl": False,
        "ssl_cert_path": "",
        "ssl_key_path": "",
        "auth_required": True,
        "auth_username": "admin",
        "auth_password": "",
    },
    
    # Google Maps settings
    "google_maps": {
        "api_key": "",
        "map_id": "",
        "default_lat": 39.095657,
        "default_lng": -84.515959,
    },
}

# Environment variable prefix
ENV_PREFIX = "MOWER_"

# Default configuration file
DEFAULT_CONFIG_FILE = CONFIG_DIR / "config.json"

# Default environment file
DEFAULT_ENV_FILE = BASE_DIR / ".env"

# Create configuration directory if it doesn't exist
CONFIG_DIR.mkdir(parents=True, exist_ok=True)