# This module deals with generating a path for the robot to follow while mowing the lawn. 

import numpy as np
from pathfinding.core.diagonal_movement import DiagonalMovement
from pathfinding.core.grid import Grid
from pathfinding.finder.a_star import AStarFinder
from shapely.geometry import Polygon, Point
import cv2
import networkx
import rtree
import json
import random

with open("config.json") as f:
    config = json.load(f)

with open("user_polygon.json") as f:
    polygon_coordinates = json.load(f)

# Set user polygon
set_user_polygon(polygon_coordinates)

# Constants
GRID_SIZE = (config['GRID_L'],config['GRID_W'])  # Grid size for path planning
OBSTACLE_MARGIN = config['Obstacle_avoidance_margin']  # Margin around obstacles to account for robot size and path safety

# Global variables
user_polygon = None
obstacle_map = np.zeros(GRID_SIZE, dtype=np.uint8)  # Map of known obstacles

class PathPlanning:
    def __init__(self):
        self.obstacle_map = np.zeros(GRID_SIZE, dtype=np.uint8)  # Map of known obstacles
        self.last_action = None

    def set_user_polygon(self, polygon_coordinates):
        global user_polygon
        user_polygon = Polygon(polygon_coordinates)

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

    def reward_function(self, old_state, new_state, action):
        if new_state == 'goal':
            return 100
        elif self.obstacle_map[action] == 1:
            return -100
        elif action != self.last_action:
            return -10
        else:
            return -1

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

        return new_state

    def q_learning(self, start, goal, obstacles, episodes=1000, learning_rate=0.1, discount_factor=0.9, exploration_rate=0.1):
        q_table = np.zeros((GRID_SIZE[0], GRID_SIZE[1], 4))  # 4 actions: up, down, left, right

        for episode in range(episodes):
            state = start

            for step in range(100):  # Limit each episode to a maximum of 100 steps
                if random.uniform(0, 1) < exploration_rate:
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

        return q_table

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