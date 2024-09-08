# constants.py
import json
import os
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

with open("config.json") as f:
    config = json.load(f)

try:
    with open("user_polygon.json") as f:
        polygon_coordinates = json.load(f)
except FileNotFoundError:
    print("User polygon config file not found.")
    polygon_coordinates = []

# Constants for the project
TIME_INTERVAL = 0.1
EARTH_RADIUS = 6371e3  # Earth's radius in meters

# For navigation_system/path_planning.py
SECTION_SIZE = (10, 10)
GRID_SIZE = (config['GRID_L'], config['GRID_W'])

# For obstacle_detection/avoidance_algorithm.py
OBSTACLE_MARGIN = 10  # Margin to avoid obstacles in CM
CAMERA_OBSTACLE_THRESHOLD = 1000  # Threshold for obstacle detection (in pixels, area w * h)
MOTOR_SPEED = 50  # Speed of the motors in % (0-100)
MIN_DISTANCE_THRESHOLD = 10  # Minimum distance threshold to avoid obstacles in CM
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


if longitudes:
    min_lng = min(longitudes)
    max_lng = max(longitudes)
else:
    min_lng = 10
    max_lng = 11

# Add more constants as needed