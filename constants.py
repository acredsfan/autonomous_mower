# constants.py
import json

with open("config.json") as f:
    config = json.load(f)

try:
    with open("user_polygon.json") as f:
        polygon_coordinates = json.load(f)
except FileNotFoundError:
    print("config file not found")
    polygon_coordinates = []

# For control_system/speed_controller.py
MIN_SPEED = 0
MAX_SPEED = 10
ACCELERATION_RATE = 2  # Increase in motor speed per loop iteration
DECELERATION_RATE = 3  # Decrease in motor speed per loop iteration
TIME_INTERVAL = 0.1 # Time interval between loop iterations

# For control_system/trajectory_controller.py
MIN_DISTANCE_TO_OBSTACLE = 30  # in centimeters
TURN_ANGLE = 45  # in degrees
SPEED = 50  # as a percentage of the maximum motor speed
WAYPOINT_REACHED_THRESHOLD = 30  # in centimeters

# For navigation_system/localization.py
EARTH_RADIUS = 6371e3  # Earth's radius in meters

# For navigation_system/path_planning.py
SECTION_SIZE = (10, 10)
GRID_SIZE = (config['GRID_L'], config['GRID_W'])
OBSTACLE_MARGIN = config['Obstacle_avoidance_margin']

# For obstacle_detection/avoidance_algorithm.py
CAMERA_OBSTACLE_THRESHOLD = config['CAMERA_OBSTACLE_THRESHOLD'] # Minimum area to consider an obstacle from the camera
MOTOR_SPEED = 70

# For obstacle_detection/tof_processing.py
MIN_DISTANCE_THRESHOLD = 150  # Minimum distance to consider an obstacle in millimeters
AVOIDANCE_DELAY = 0.5  # Time to wait between avoidance checks in seconds

# For user_interface (if you add more modules here)
UI_REFRESH_RATE = 1  # UI refresh rate in Hz

# Add more constants as needed
