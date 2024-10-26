# constants.py
import json
from pathlib import Path

from dotenv import load_dotenv
from autonomous_mower.utilities.logger_config import (
    LoggerConfigInfo as LoggerConfig
)

# Initialize logger
logging = LoggerConfig.get_logger(__name__)

# Load .env variables
load_dotenv()

# Set up base directory for consistent file referencing
BASE_DIR = Path(__file__).resolve().parents[1]
config_path = BASE_DIR / "config.json"
polygon_path = BASE_DIR / "user_polygon.json"

# Open config file
try:
    with open(config_path) as f:
        config = json.load(f)
except FileNotFoundError:
    logging.error("Config file not found.")
    config = {}

# Open user polygon config file
try:
    with open(polygon_path) as f:
        polygon_coordinates = json.load(f)
except FileNotFoundError:
    logging.error("User polygon config file not found.")
    polygon_coordinates = []

# Constants for the project
TIME_INTERVAL = 0.1
EARTH_RADIUS = 6371e3  # Earth's radius in meters

# For navigation_system/path_planning.py
SECTION_SIZE = (10, 10)
GRID_SIZE = (config['GRID_L'], config['GRID_W'])

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
latitudes = [coord['lat'] for coord in polygon_coordinates]
longitudes = [coord['lng'] for coord in polygon_coordinates]

min_lat = min(latitudes) if latitudes else 10
max_lat = max(latitudes) if latitudes else 11
min_lng = min(longitudes) if longitudes else 10
max_lng = max(longitudes) if longitudes else 11
