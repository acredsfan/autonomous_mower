# This module deals with generating a path for the robot to follow while mowing the lawn. 
import numpy as np
from pathfinding.core.diagonal_movement import DiagonalMovement
from pathfinding.core.grid import Grid
from pathfinding.finder.a_star import AStarFinder
from shapely.geometry import Polygon, Point
import json

with open("config.json") as f:
    config = json.load(f)

try:
    with open("user_polygon.json") as f:
        polygon_coordinates = json.load(f)
except FileNotFoundError:
    polygon_coordinates = []  # or some default value

# Constants
GRID_SIZE = (config['GRID_L'], config['GRID_W'])
OBSTACLE_MARGIN = config['Obstacle_avoidance_margin']
SECTION_SIZE = (10, 10)  # Example section size, you can adjust this

# Global variables
user_polygon = None
obstacle_map = np.zeros(GRID_SIZE, dtype=np.uint8)

class PathPlanning:
    def __init__(self):
        self.obstacle_map = np.zeros(GRID_SIZE, dtype=np.uint8)
        self.obstacles = set()
        self.sections = self.divide_yard_into_sections()

    def set_user_polygon(self, polygon_coordinates):
        global user_polygon
        user_polygon = Polygon(polygon_coordinates)

    def divide_yard_into_sections(self):
        sections = []
        for i in range(0, GRID_SIZE[0], SECTION_SIZE[0]):
            for j in range(0, GRID_SIZE[1], SECTION_SIZE[1]):
                section = (i, j, i + SECTION_SIZE[0], j + SECTION_SIZE[1])
                sections.append(section)
        return sections

    def select_next_section(self, current_position):
        closest_section = min(self.sections, key=lambda section: abs(current_position[0] - section[0]) + abs(current_position[1] - section[1]))
        return closest_section

    def update_obstacle_map(self, new_obstacles):
        new_obstacle_set = set([obstacle.wkt for obstacle in new_obstacles])

        # Find obstacles that were removed
        removed_obstacles = self.obstacles - new_obstacle_set

        # Remove the removed obstacles from the map
        for obstacle_wkt in removed_obstacles:
            obstacle = shapely.wkt.loads(obstacle_wkt)
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
            self.plan_path(self.start, self.goal, [shapely.wkt.loads(wkt) for wkt in self.obstacles])
        self.obstacle_map = obstacle_map          

    # This function generates a grid with marked obstacles
    def generate_grid(self, obstacles):
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

    # This function updates the obstacle map
    def update_obstacle_map(self, new_obstacles):
        for obstacle in new_obstacles:
            # Add the obstacle to the map
            obstacle_expanded = obstacle.buffer(OBSTACLE_MARGIN)
            minx, miny, maxx, maxy = obstacle_expanded.bounds
            for x in range(int(minx), int(maxx) + 1):
                for y in range(int(miny), int(maxy) + 1):
                    point = Point(x, y)
                    if obstacle_expanded.contains(point):
                        self.obstacle_map[x, y] = 1
        # Trigger a new path planning if the obstacle map has changed
        if np.any(obstacle_map != self.obstacle_map):
            self.plan_path(self.start, self.goal, new_obstacles)
        self.obstacle_map = obstacle_map

    # This function calculates the reward based on the action taken
    def reward_function(self, old_state, new_state, action):
        if new_state == 'goal':
            return 100
        elif self.obstacle_map[new_state[0], new_state[1]] == 1:
            return -100
        elif action != self.last_action:
            return -10
        else:
            return -1

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
    def q_learning(self, start, goal, obstacles, episodes=1000, learning_rate=0.1, discount_factor=0.9, epsilon=1.0, epsilon_decay=0.995, epsilon_min=0.1):
        q_table = np.zeros((GRID_SIZE[0], GRID_SIZE[1], 4))  # 4 actions: up, down, left, right

        for episode in range(episodes):
            state = start

            for step in range(100):  # Limit each episode to a maximum of 100 steps
                if random.uniform(0, 1) < epsilon:
                    action = random.choice(['up', 'down', 'left', 'right'])  # Explore a random action
                else:
                    action = np.argmax(q_table[state])  # Exploit the best known action

                # Take the action and get the new state and reward
                new_state = self.take_action(state, action)
                reward = self.reward_function(state, new_state, action)

                # Update the Q-table
                old_value = q_table[state][action]
                next_max = np.max(q_table[new_state])
                new_value = (1 - learning_rate) * old_value + learning_rate * (reward + discount_factor * next_max)
                q_table[state][action] = new_value

                # Update the state
                state = new_state

                # Update the last action
                self.last_action = action

                # End the episode if we reached the goal
                if state == goal:
                    break

            # Decay epsilon after each episode
            if epsilon > epsilon_min:
                epsilon *= epsilon_decay

        state = start
        path = [state]
        while state != goal:
            action = np.argmax(q_table[state])
            state = self.take_action(state, action)
            path.append(state)
        return path
        
    # This function gets the path using Q-Learning algorithm
    def get_path(self, start, goal):  # added start and goal as parameters
        # Run Q-Learning algorithm
        path = self.q_learning(start, goal, self.obstacles)

        # Convert the result into a list of (lat, lng) coordinates
        path_coords = []
        for cell in path:
            coord = self.grid_to_coord(cell)
            path_coords.append(coord)
            
        return path_coords
    
    # This function converts a grid cell to a (lat, lng) coordinate
    def grid_to_coord(self, cell):
        lat = cell[0] * self.lat_grid_size + self.min_lat
        lng = cell[1] * self.lng_grid_size + self.min_lng
        return {"lat": lat, "lng": lng}
    
    
    def get_start_and_goal(self):
        current_position = self.get_current_position()
        sections = self.divide_yard_into_sections()
        next_section = self.select_next_section(current_position, sections)
        
        start = current_position
        goal = self.calculate_goal_position(next_section)
        
        return start, goal


# Example usage
if __name__ == "__main__":
    path_planner = PathPlanning((10, 10), (90, 90))  # Pass start and goal to the constructor

    # Set user polygon
    path_planner.set_user_polygon([(0, 0), (0, 99), (99, 99), (99, 0)])

    # Test path planning
    start = (10, 10)
    goal = (90, 90)
    obstacles = [Polygon([(30, 30), (30, 60), (60, 60), (60, 30)])]

    path = path_planner.plan_path(start, goal, obstacles)
    print(path)

    def divide_yard_into_sections(self):
        sections = []
        for i in range(0, grid_size[0], section_size[0]):
            for j in range(0, grid_size[1], section_size[1]):
                section = (i, j, i + section_size[0], j + section_size[1])
                sections.append(section)
        return sections

    def select_next_section(self, current_position, sections):
        # Example logic to select the next section based on proximity to current position
        # You can replace this with your specific logic
        closest_section = min(sections, key=lambda section: abs(current_position[0] - section[0]) + abs(current_position[1] - section[1]))
        return closest_section


    def get_current_position(self):
        # TODO: Implement logic to get the current position of the mower
        # This could be based on sensors, GPS, or other localization methods
        return (10, 10)  # Example current position

    def calculate_goal_position(self, next_section):
        # TODO: Implement logic to calculate the goal position within the selected section
        # This could be the center of the section or another specific point
        return (next_section[0] + section_size[0] // 2, next_section[1] + section_size[1] // 2)

    def get_start_and_goal(self):
        current_position = self.get_current_position()
        sections = self.divide_yard_into_sections()
        next_section = self.select_next_section(current_position, sections)
        
        start = current_position
        goal = self.calculate_goal_position(next_section)
        
        return start, goal