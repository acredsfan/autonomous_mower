# constants.py
import json
from json import JSONDecodeError
from pathlib import Path

from dotenv import load_dotenv

from mower.utilities.logger_config import LoggerConfigInfo

# Initialize logger
logging = LoggerConfigInfo.get_logger(__name__)

# Load .env variables
load_dotenv()

# Set up base directory for consistent file referencing
BASE_DIR = Path(__file__).resolve().parents[2]  # Go up to project root
CONFIG_DIR = BASE_DIR / "config"  # Use config directory
polygon_path = CONFIG_DIR / "user_polygon.json"

# Open user polygon config file
try:
    with open(polygon_path) as f:
        data = json.load(f)
    # Ensure data is always a list (possibly empty)
    coords = data if isinstance(data, list) else []
    if not isinstance(coords, list):
        logging.warning(
            ("Invalid polygon_coordinates: expected list, got %s. " "Using empty list."),
            type(coords),
        )
        polygon_coordinates = []
    else:
        filtered = []
        for idx, coord in enumerate(coords):
            if isinstance(coord, dict) and "lat" in coord and "lng" in coord:
                filtered.append(coord)
            else:
                logging.warning("Skipping invalid coordinate at index %d: %s", idx, coord)
        polygon_coordinates = filtered
except (FileNotFoundError, JSONDecodeError) as e:
    logging.warning("User polygon config file not found. " "Initializing with an empty list.")
    logging.debug("polygon load error: %s", e)
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

# Derived constants for UI limits
latitudes = [coord["lat"] for coord in polygon_coordinates if isinstance(coord, dict) and "lat" in coord]
longitudes = [coord["lng"] for coord in polygon_coordinates if isinstance(coord, dict) and "lng" in coord]

min_lat = min(latitudes) if latitudes else 10
max_lat = max(latitudes) if latitudes else 11
min_lng = min(longitudes) if longitudes else 10
max_lng = max(longitudes) if longitudes else 11
