# constants.py
import json
from pathlib import Path
import os

from dotenv import load_dotenv  # type:ignore
from mower.utilities.logger_config import (
    LoggerConfigInfo as LoggerConfig,
)

# Initialize logger
logger = LoggerConfig.get_logger(__name__)

# Load .env variables
load_dotenv()

# Set up base directory for consistent file referencing
BASE_DIR = Path(__file__).resolve().parents[2]  # Go up to project root
CONFIG_DIR = BASE_DIR / "config"  # Use config directory
polygon_path = CONFIG_DIR / "user_polygon.json"

# Open user polygon config file
try:
    with open(polygon_path) as f:
        polygon_data = json.load(f)
        # Extract the polygon coordinates from the correct structure
        if isinstance(polygon_data, dict) and 'polygon' in polygon_data:
            polygon_coordinates = polygon_data['polygon']
        else:
            # Handle legacy format or unexpected structure
            polygon_coordinates = polygon_data if isinstance(
                polygon_data, list) else []
            logger.warning(
                "User polygon data has unexpected structure. "
                "Expected a dictionary with 'polygon' key."
            )
except FileNotFoundError:
    logger.warning(
        "User polygon config file not found. "
        "Initializing with an empty list."
    )
    polygon_coordinates = []
except json.JSONDecodeError:
    logger.error(
        "Error decoding user polygon JSON file. "
        "Initializing with an empty list."
    )
    polygon_coordinates = []
except Exception as e:
    logger.error(f"Unexpected error loading user polygon: {e}")
    polygon_coordinates = []

# Constants for the project
TIME_INTERVAL = 0.1
EARTH_RADIUS = 6371e3  # Earth's radius in meters

# For navigation_system/path_planning.py
SECTION_SIZE = (10, 10)
GRID_L = 100  # Grid length
GRID_W = 100  # Grid width
GRID_SIZE = (GRID_L, GRID_W)

# For obstacle_detection/avoidance_algorithm.py
OBSTACLE_MARGIN = 10  # Margin to avoid obstacles in CM
# Threshold for obstacle detection (in pixels, area w * h)
CAMERA_OBSTACLE_THRESHOLD = 1000
MOTOR_SPEED = 50  # Speed of the motors in % (0-100)
MIN_DISTANCE_THRESHOLD = 30
""" Minimum distance threshold
to avoid obstacles in MM"""

AVOIDANCE_DELAY = 0.1  # Delay for obstacle avoidance in seconds

# For RoboHATController
MM1_MAX_FORWARD = 2000
MM1_MAX_REVERSE = 1000
MM1_STOPPED_PWM = 1500
MM1_STEERING_MID = 1500
AUTO_RECORD_ON_THROTTLE = True
JOYSTICK_DEADZONE = 0.1
SHOW_STEERING_VALUE = True  # Update this based on your use case
MM1_SERIAL_PORT = os.getenv("MM1_SERIAL_PORT", "/dev/ttyACM1")
MM1_BAUD_RATE = os.getenv("MM1_BAUD_RATE", 115200)

# Derived constants for UI limits
# Safely extract coordinates with proper error handling
latitudes = []
longitudes = []

# Only process if we have valid polygon coordinates
if polygon_coordinates and isinstance(polygon_coordinates, list):
    for coord in polygon_coordinates:
        if isinstance(coord, dict):
            # Try both 'lat'/'lng' and 'lat'/'lon' formats
            if 'lat' in coord:
                latitudes.append(coord['lat'])
            if 'lng' in coord:
                longitudes.append(coord['lng'])
            elif 'lon' in coord:
                longitudes.append(coord['lon'])

min_lat = min(latitudes) if latitudes else 10
max_lat = max(latitudes) if latitudes else 11
min_lng = min(longitudes) if longitudes else 10
max_lng = max(longitudes) if longitudes else 11
