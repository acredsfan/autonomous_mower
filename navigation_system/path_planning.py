from utilities import LoggerConfig
import requests
from constants import (
    SECTION_SIZE,
    GRID_SIZE,
    OBSTACLE_MARGIN,
    polygon_coordinates,
    min_lat,
    max_lat,
    min_lng,
    max_lng
)
import time
from navigation_system import Localization
from shapely import wkt
from shapely.geometry import Polygon, Point
from pathfinding.finder.a_star import AStarFinder
from pathfinding.core.grid import Grid
from pathfinding.core.diagonal_movement import DiagonalMovement
import random
import numpy as np
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# Initialize logger
logging = LoggerConfig.get_logger(__name__)

# Global variables
user_polygon = polygon_coordinates
obstacle_map = np.zeros(GRID_SIZE, dtype=np.uint8)
OPEN_WEATHER_MAP_API_KEY = os.getenv("OPEN_WEATHER_MAP_API")


class PathPlanning:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PathPlanning, cls).__new__(cls)
            cls.__init__(cls._instance)
        return cls._instance

    def __init__(self):
        self.min_lng = min_lng
        self.max_lng = max_lng
        self.min_lat = min_lat
        self.max_lat = max_lat
        self.localization = Localization()
        self.obstacle_map = np.zeros(GRID_SIZE, dtype=np.uint8)
        self.obstacles = set()
        self.sections = self.divide_yard_into_sections()
        self.set_min_max_coordinates()
        # 4 actions: up, down, left, right
        self.q_table = np.zeros((GRID_SIZE[0], GRID_SIZE[1], 4))
        self.last_action = None

    def set_min_max_coordinates(self):
        self.lat_grid_size = (self.max_lat - self.min_lat) / GRID_SIZE[0]
        self.lng_grid_size = (self.max_lng - self.min_lng) / GRID_SIZE[1]

    def set_user_polygon(self, polygon_coordinates):
        """
        Sets the user polygon.
        :param polygon_coordinates:
        :return:
        """
        global user_polygon
        user_polygon = Polygon(polygon_coordinates)

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
        pass

    def select_next_section(self, current_position):
        """
        Selects the next section to go to.
        :param current_position:
        :return: next_section
        """
        next_section = (current_position[0] + 1, current_position[1])

        return next_section

    def update_obstacle_map(self, new_obstacles):
        """
        Updates the obstacle map.
        :param new_obstacles:
        :return:
        """
        new_obstacle_set = set([obstacle.wkt for obstacle in new_obstacles])

        # Find obstacles that were removed
        removed_obstacles = self.obstacles - new_obstacle_set

        # Remove the removed obstacles from the map
        for obstacle_wkt in removed_obstacles:
            obstacle = wkt.loads(obstacle_wkt)
            obstacle_expanded = obstacle.buffer(OBSTACLE_MARGIN)
            minx, miny, maxx, maxy = obstacle_expanded.bounds
            for x in range(int(minx), int(maxx) + 1):
                for y in range(int(miny), int(maxy) + 1):
                    point = Point(x, y)
                    if obstacle_expanded.contains(point):
                        self.obstacle_map[x, y] = 0

        # Add the new obstacles to the map
        for obstacle in new_obstacles:
            obstacle_expanded = obstacle.buffer(OBSTACLE_MARGIN)
            minx, miny, maxx, maxy = obstacle_expanded.bounds
            for x in range(int(minx), int(maxx) + 1):
                for y in range(int(miny), int(maxy) + 1):
                    point = Point(x, y)
                    if obstacle_expanded.contains(point):
                        self.obstacle_map[x, y] = 1

        # Update the set of known obstacles
        self.obstacles = new_obstacle_set

        # Trigger a new path planning if the obstacle map has changed
        if np.any(obstacle_map != self.obstacle_map):
            self.plan_path(
                self.start, self.goal, [
                    wkt.loads(wkt) for wkt in self.obstacles])
        self.obstacle_map = obstacle_map

    # This function generates a grid with marked obstacles
    def generate_grid(self, obstacles):
        """
        Generates a grid with marked obstacles.
        :param obstacles:
        :return:
        """
        grid = np.zeros(GRID_SIZE, dtype=np.uint8)

        # Mark the obstacles on the grid
        for obstacle in obstacles:
            # Add margins around the obstacles
            obstacle_expanded = obstacle.buffer(OBSTACLE_MARGIN)
            minx, miny, maxx, maxy = obstacle_expanded.bounds
            for x in range(int(minx), int(maxx) + 1):
                for y in range(int(miny), int(maxy) + 1):
                    point = Point(x, y)
                    if obstacle_expanded.contains(point):
                        grid[x, y] = 1

        return grid

    # This function plans the path using A* algorithm
    def plan_path(self, start, goal, obstacles):
        if not user_polygon:
            raise Exception("User polygon not set")

        grid_data = self.generate_grid(obstacles)
        grid = Grid(matrix=grid_data)

        finder = AStarFinder(diagonal_movement=DiagonalMovement.always)
        start_node = grid.node(*start)
        end_node = grid.node(*goal)

        path, _ = finder.find_path(start_node, end_node, grid)

        return path

    def reward_function(self, old_state, new_state, action):
        """
        This function calculates the reward for the given state transition.
        :param old_state:
        :param new_state:
        :param action:
        :return:
        """
        if new_state == 'goal':
            return 100
        elif self.obstacle_map[new_state[0], new_state[1]] == 1:
            return -100
        elif action != self.last_action:
            return -10  # Penalty for not moving in a straight line
        else:
            return 1  # Reward for moving in a straight line

    # This function determines the new state based on the action taken
    def take_action(self, state, action):
        if action == 'up':
            new_state = (state[0] - 1, state[1])
        elif action == 'down':
            new_state = (state[0] + 1, state[1])
        elif action == 'left':
            new_state = (state[0], state[1] - 1)
        elif action == 'right':
            new_state = (state[0], state[1] + 1)
        else:
            raise ValueError(f"Invalid action: {action}")

        # Make sure the new state is within the grid
        new_state = (max(min(new_state[0], GRID_SIZE[0] - 1), 0),
                     max(min(new_state[1], GRID_SIZE[1] - 1), 0))

        # Check if the new state is an obstacle
        if self.obstacle_map[new_state] == 1:
            return state

        return new_state

    # This function implements the Q-Learning algorithm
    def q_learning(
            self,
            start,
            goal,
            episodes=1000,
            learning_rate=0.1,
            discount_factor=0.9,
            epsilon=1.0,
            epsilon_decay=0.995,
            epsilon_min=0.1):
        """"""
        for episode in range(episodes):
            state = start
            for step in range(100):
                if random.uniform(0, 1) < epsilon:
                    action = random.choice(['up', 'down', 'left', 'right'])
                else:
                    action = np.argmax(self.q_table[state])

                new_state = self.take_action(state, action)
                reward = self.reward_function(state, new_state, action)

                old_value = self.q_table[state][action]
                next_max = np.max(self.q_table[new_state])
                new_value = (1 - learning_rate) * old_value + \
                    learning_rate * (reward + discount_factor * next_max)
                self.q_table[state][action] = new_value

                state = new_state
                self.last_action = action

                if state == goal:
                    break

            if epsilon > epsilon_min:
                epsilon *= epsilon_decay

    # This function returns the path to the goal
    def get_path(self, start, goal):
        path = self.q_learning(start, goal)
        path_coords = []
        for cell in path:
            coord = self.grid_to_coord(cell)
            path_coords.append(coord)
        return path_coords

    def calculate_goal_position(self, next_section):
        # Determine the boundaries of thr selected section
        if next_section is None:
            logging.error("Next section is None.  Waiting for result...")
            time.sleep(1)
        section_size = (
            next_section[2] -
            next_section[0],
            next_section[3] -
            next_section[1])

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
        # Get location of mower from Locatlization class
        lat, lng, alt = self.localization.estimate_position()
        # Convert lat, lng, alt to Grid Cell location
        grid_cell = self.coord_to_grid(lat, lng)
        return grid_cell

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
