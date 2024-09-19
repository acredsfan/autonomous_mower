from utilities import LoggerConfigDebug as LoggerConfig
import requests
from constants import (
    SECTION_SIZE,
    GRID_SIZE,
    polygon_coordinates,
    min_lat,
    max_lat,
    min_lng,
    max_lng
)
from shapely.geometry import Polygon
from pathfinding.finder.a_star import AStarFinder
from pathfinding.core.grid import Grid
from pathfinding.core.diagonal_movement import DiagonalMovement
import random
import numpy as np
import os

# Initialize logger
logging = LoggerConfig.get_logger(__name__)

# Global variables
user_polygon = None  # Will be set by set_user_polygon method
OPEN_WEATHER_MAP_API_KEY = os.getenv("OPEN_WEATHER_MAP_API")


class PathPlanning:
    def __init__(self, localization):
        self.min_lng = min_lng
        self.max_lng = max_lng
        self.min_lat = min_lat
        self.max_lat = max_lat
        self.localization = localization  # Accept localization instance
        self.obstacle_map = np.zeros(GRID_SIZE, dtype=np.uint8)
        self.obstacles = set()
        self.sections = self.divide_yard_into_sections()
        self.set_min_max_coordinates()
        # 4 actions: up, down, left, right
        self.q_table = np.zeros((GRID_SIZE[0], GRID_SIZE[1], 4))
        self.last_action = None
        self.goal = None  # Define goal attribute
        self.latest_position = None  # Define latest_position attribute

    def set_min_max_coordinates(self):
        self.lat_grid_size = (self.max_lat - self.min_lat) / GRID_SIZE[0]
        self.lng_grid_size = (self.max_lng - self.min_lng) / GRID_SIZE[1]

    def set_user_polygon(self, polygon_points):
        """
        Sets the user-defined polygon (mowing area).
        """
        global user_polygon
        user_polygon = Polygon([(p['lng'], p['lat']) for p in polygon_points])

    def divide_yard_into_sections(self):
        """
        Divides the yard into sections.
        """
        sections = []
        for i in range(0, GRID_SIZE[0], SECTION_SIZE[0]):
            for j in range(0, GRID_SIZE[1], SECTION_SIZE[1]):
                section = (i, j, i + SECTION_SIZE[0], j + SECTION_SIZE[1])
                sections.append(section)
        return sections

    def select_next_section(self, current_position):
        """
        Selects the next section to go to.
        """
        # Implement logic to select the next section
        # For simplicity, we'll select a random section not yet visited
        next_section = random.choice(self.sections)
        return next_section

    def update_obstacle_map(self, obstacle_positions):
        """
        Updates the obstacle map with new obstacles.
        """
        for obstacle_position in obstacle_positions:
            grid_cell = self.coord_to_grid(obstacle_position[0],
                                           obstacle_position[1])
            self.obstacle_map[grid_cell[0], grid_cell[1]] = 1

    def generate_grid(self):
        """
        Generates a grid with marked obstacles.
        """
        return self.obstacle_map.copy()

    def plan_path(self, start, goal):
        if user_polygon is None:
            raise Exception("User polygon not set")

        grid_data = self.generate_grid()
        grid = Grid(matrix=grid_data)

        finder = AStarFinder(diagonal_movement=DiagonalMovement.always)
        start_node = grid.node(*start)
        end_node = grid.node(*goal)

        path, _ = finder.find_path(start_node, end_node, grid)

        return path

    def get_path(self, start, goal):
        path = self.plan_path(start, goal)
        path_coords = []
        for cell in path:
            coord = self.grid_to_coord(cell)
            path_coords.append(coord)
        return path_coords

    def calculate_goal_position(self, next_section):
        # Determine the center of the selected section
        section_size = (
            next_section[2] - next_section[0],
            next_section[3] - next_section[1])

        # Calculate the goal position within the selected section
        goal_position = (
            next_section[0] + section_size[0] // 2,
            next_section[1] + section_size[1] // 2)

        return goal_position

    def get_start_and_goal(self):
        current_position = self.estimate_position()
        next_section = self.select_next_section(current_position)

        start = current_position
        goal = self.calculate_goal_position(next_section)
        self.goal = goal  # Update the goal attribute

        return start, goal

    def coord_to_grid(self, lat, lng):
        # Calculate the grid indices based on lat/lng
        grid_x = int((lat - self.min_lat) / self.lat_grid_size)
        grid_y = int((lng - self.min_lng) / self.lng_grid_size)
        # Ensure the indices are within grid bounds
        grid_x = max(0, min(grid_x, GRID_SIZE[0] - 1))
        grid_y = max(0, min(grid_y, GRID_SIZE[1] - 1))
        return (grid_x, grid_y)

    def grid_to_coord(self, cell):
        # Convert grid cell back to lat/lng
        lat = self.min_lat + cell[0] * self.lat_grid_size
        lng = self.min_lng + cell[1] * self.lng_grid_size
        return {"lat": lat, "lng": lng}

    def estimate_position(self):
        # Estimmate where on grid the robot is using localization
        lat, lng = self.localization.estimmate_position()
        return self.coord_to_grid(lat, lng)

    def get_weather_data(self, lat, lon):
        """
        Fetch current weather data from OpenWeatherMap API.
        :param lat: Latitude of the location
        :param lon: Longitude of the location
        :return: Dictionary containing weather data
        """
        url = (
            f"http://api.openweathermap.org/data/2.5/weather?lat={lat}"
            f"&lon={lon}&appid={OPEN_WEATHER_MAP_API_KEY}&units=metric"
        )
        try:
            response = requests.get(url)
            weather_data = response.json()
            logging.info(f"Weather data: {weather_data}")
            return weather_data
        except Exception as e:
            logging.error(f"Error fetching weather data: {e}")
            return {}

    def is_sunny(self, weather_data):
        """
        Determine if the current weather conditions are sunny.
        :param weather_data: Weather data dictionary from OpenWeatherMap
        :return: True if sunny, False otherwise
        """
        try:
            cloud_coverage = weather_data.get(
                "clouds", {}).get(
                "all", 100)  # Cloud coverage percentage
            logging.info(f"Cloud coverage: {cloud_coverage}%")
            # Consider it sunny if cloud coverage is less than 20%
            return cloud_coverage < 20
        except Exception as e:
            logging.error(f"Error determining sun conditions: {e}")
            return False

    def find_sunny_location(self, current_location, search_radius=10):
        """
        Finds a sunny location within a given radius
        using weather data and GPS coordinates.
        :param current_location: Current GPS coordinates of the robot
        :param search_radius: Radius around the current location to search
        :return: Best location with the highest likelihood of sunlight
        """
        best_location = current_location
        lat, lng = current_location

        # Fetch weather data for the current location
        weather_data = self.get_weather_data(lat, lng)

        # Check if current weather conditions are ideal for sun exposure
        if self.is_sunny(weather_data):
            logging.info(
                "Current location is sunny, "
                "using current location for charging.")
            return best_location

        # Generate search grid to find the best nearby sunny location
        search_grid = self.generate_search_grid(lat, lng, search_radius)

        for location in search_grid:
            weather_data = self.get_weather_data(location[0], location[1])
            if self.is_sunny(weather_data):
                logging.info(f"Found sunny location: {location}")
                return location

        logging.info(
            "No ideal sunny location found within the search radius. "
            "Defaulting to current location.")
        return best_location

    def generate_search_grid(self, lat, lng, radius):
        """
        Generate a grid of points around the current
        location within the given radius.
        :param lat: Current latitude
        :param lng: Current longitude
        :param radius: Search radius in meters
        :return: List of (lat, lng) points to search
        """
        step_size = radius / (
            self.grid_size[0]
        )  # Define step size based on the grid size and radius
        search_points = []

        for i in range(-self.grid_size[0] // 2, self.grid_size[0] // 2):
            for j in range(-self.grid_size[1] // 2, self.grid_size[1] // 2):
                # Adjust these multipliers based on scale and lat/lng
                new_lat = lat + (i * step_size) * 0.00001
                new_lng = lng + (j * step_size) * 0.00001
                search_points.append((new_lat, new_lng))

        return search_points


class FollowOutline:
    # Path to follow outline of user generated polygon/yard

    def __init__(self):
        self.path_planning = PathPlanning()
        self.path = []
        self.current_position = None
        self.goal_position = None

    def follow_outline(self):
        # Follow the outline of the user generated polygon/yard
        self.path_planning.set_user_polygon(polygon_coordinates)
        self.current_position = self.path_planning.estimate_position()
        self.goal_position = self.path_planning.get_goal_position()
        self.path = self.path_planning.plan_path(
            self.current_position, self.goal_position)
        for point in self.path:
            self.move_to_point(point)

    def move_to_point(self, point):
        # Move the robot to the specified point while
        #  avoiding obstacles and drop-offs.
        from hardware_interface import RoboHATController
        robohat_controller = RoboHATController()
        from obstacle_detection import ObstacleAvoidance
        obstacle_detection = ObstacleAvoidance()
        robohat_controller.navigate_to_location(point)
        obstacle_detection.avoid_obstacles()

    def get_current_position(self):
        return self.current_position

    def get_goal_position(self):
        return self.goal_position

    def get_path(self):
        return self.path

    def set_current_position(self, current_position):
        self.current_position = current_position
