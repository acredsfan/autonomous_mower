# This module deals with generating a path for the robot to follow while mowing the lawn. 
# It will take the robot's current position and the lawn's boundary information as inputs and generate a series of waypoints or a continuous path 
# that the robot should follow to cover the entire area efficiently. 
# This might involve implementing algorithms like A* search, Dijkstra's algorithm, or any other suitable path-planning algorithm that considers the robot's constraints, 
# such as its size and turning radius.

import numpy as np
from pathfinding.core.diagonal_movement import DiagonalMovement
from pathfinding.core.grid import Grid
from pathfinding.finder.a_star import AStarFinder
from shapely.geometry import Polygon, Point
import cv2
import networkx
import rtree
import json

with open("config.json") as f:
    config = json.load(f)

# Constants
GRID_SIZE = (config['GRID_L'],config['GRID_W'])  # Grid size for path planning
OBSTACLE_MARGIN = config['Obstacle_avoidance_margin']  # Margin around obstacles to account for robot size and path safety

# Global variables
user_polygon = None

class PathPlanning:
    def set_user_polygon(polygon_coordinates):
        global user_polygon
        user_polygon = Polygon(polygon_coordinates)

    def generate_grid(obstacles):
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

    def plan_path(start, goal, obstacles):
        if not user_polygon:
            raise Exception("User polygon not set")

        grid_data = generate_grid(obstacles)
        grid = Grid(matrix=grid_data)

        finder = AStarFinder(diagonal_movement=DiagonalMovement.always)
        start_node = grid.node(*start)
        end_node = grid.node(*goal)

        path, _ = finder.find_path(start_node, end_node, grid)

        return path

    # Example usage
    if __name__ == "__main__":
        # Set user polygon
        set_user_polygon([(0, 0), (0, 99), (99, 99), (99, 0)])

        # Test path planning
        start = (10, 10)
        goal = (90, 90)
        obstacles = [Polygon([(30, 30), (30, 60), (60, 60), (60, 30)])]

        path = plan_path(start, goal, obstacles)
        print(path)