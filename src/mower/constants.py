# constants.py
"""Constants and configuration loading for the autonomous mower system.

This module defines project-wide constants and handles loading of configuration
data from files, with proper error handling and type validation.

The module loads polygon coordinates from user_polygon.json and defines various
constants used throughout the autonomous mower system including timing intervals,
physical constants, and hardware configuration parameters.

Example:
    Basic usage of constants:
        
        from mower.constants import TIME_INTERVAL, OBSTACLE_MARGIN
        
        # Use timing constant
        time.sleep(TIME_INTERVAL)
        
        # Use obstacle detection margin
        if distance < OBSTACLE_MARGIN:
            avoid_obstacle()

Attributes:
    TIME_INTERVAL (float): Main loop timing interval in seconds.
    EARTH_RADIUS (float): Earth's radius in meters for GPS calculations.
    OBSTACLE_MARGIN (int): Safety margin for obstacle avoidance in centimeters.
    polygon_coordinates (List[Dict[str, Union[float, int]]]): Loaded polygon boundary coordinates.
"""

import json
from json import JSONDecodeError
from pathlib import Path
from typing import Any, Dict, List, Union

from dotenv import load_dotenv

from mower.utilities.logger_config import LoggerConfigInfo

# Initialize logger
logging = LoggerConfigInfo.get_logger(__name__)

# Load .env variables
load_dotenv()

# Set up base directory for consistent file referencing
BASE_DIR: Path = Path(__file__).resolve().parents[2]  # Go up to project root
CONFIG_DIR: Path = BASE_DIR / "config"  # Use config directory
polygon_path: Path = CONFIG_DIR / "user_polygon.json"

# Type definitions for polygon coordinates
CoordinateDict = Dict[str, Union[float, int]]
PolygonCoordinates = List[CoordinateDict]

# Open user polygon config file
polygon_coordinates: PolygonCoordinates = []
try:
    with open(polygon_path, encoding='utf-8') as f:
        data: Any = json.load(f)
    
    # Validate and process the data
    if isinstance(data, list):
        filtered: PolygonCoordinates = []
        for idx, coord in enumerate(data):
            if isinstance(coord, dict) and "lat" in coord and "lng" in coord:
                filtered.append(coord)
            else:
                logging.warning("Skipping invalid coordinate at index %d: %s", idx, coord)
        polygon_coordinates = filtered
    else:
        logging.warning(
            "Invalid polygon_coordinates: expected list, got %s. Using empty list.",
            type(data),
        )
        polygon_coordinates = []
        
except (FileNotFoundError, JSONDecodeError) as e:
    logging.warning("User polygon config file not found. Initializing with an empty list.")
    logging.debug("polygon load error: %s", e)
    polygon_coordinates = []

# Constants for the project
TIME_INTERVAL: float = 0.1
EARTH_RADIUS: float = 6371e3  # Earth's radius in meters

# For navigation_system/path_planning.py
SECTION_SIZE: tuple[int, int] = (10, 10)
GRID_L: int = 100  # Grid length
GRID_W: int = 100  # Grid width
GRID_SIZE: tuple[int, int] = (GRID_L, GRID_W)

# For obstacle_detection/avoidance_algorithm.py
OBSTACLE_MARGIN: int = 10  # Margin to avoid obstacles in CM
# Threshold for obstacle detection (in pixels, area w * h)
CAMERA_OBSTACLE_THRESHOLD: int = 1000
MOTOR_SPEED: int = 50  # Speed of the motors in % (0-100)
MIN_DISTANCE_THRESHOLD: int = 30
""" Minimum distance threshold to avoid obstacles in MM"""

AVOIDANCE_DELAY: float = 0.1  # Delay for obstacle avoidance in seconds

# For RoboHATController
MM1_MAX_FORWARD: int = 2000
MM1_MAX_REVERSE: int = 1000
MM1_STOPPED_PWM: int = 1500
MM1_STEERING_MID: int = 1500
AUTO_RECORD_ON_THROTTLE: bool = True
JOYSTICK_DEADZONE: float = 0.1
SHOW_STEERING_VALUE: bool = True  # Update this based on your use case

# Derived constants for UI limits
latitudes: List[Union[float, int]] = [
    coord["lat"] for coord in polygon_coordinates 
    if isinstance(coord, dict) and "lat" in coord
]
longitudes: List[Union[float, int]] = [
    coord["lng"] for coord in polygon_coordinates 
    if isinstance(coord, dict) and "lng" in coord
]

min_lat: Union[float, int] = min(latitudes) if latitudes else 10
max_lat: Union[float, int] = max(latitudes) if latitudes else 11
min_lng: Union[float, int] = min(longitudes) if longitudes else 10
max_lng: Union[float, int] = max(longitudes) if longitudes else 11
