# path_planning.py

import json
import math
import os
from dotenv import load_dotenv
import numpy as np
import random
import utm
import cv2

from mower.mower import (
    get_gps_position,
    get_gps_latest_position,
    get_robohat_driver,
    get_detect_drop,
    get_detect_obstacle,
    get_logger_config, get_navigation_controller
)


# Initialize logger
logger = get_logger_config()

# Load environment variables
load_dotenv()

class PathPlanner:
    def __init__(self):
        self.pattern_type = None
        PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        self.USER_POLYGON_PATH = os.path.join(PROJECT_ROOT, 'user_polygon.json')
        self.MOWING_SCHEDULE_PATH = os.path.join(PROJECT_ROOT, 'mowing_schedule.json')

        self.mowing_area_polygon_gps = []
        self.mowing_area_polygon_utm = []
        self.utm_zone_number = None
        self.utm_zone_letter = None
        self.grid_points = []
        self.planned_path = []
        self.obstacles = []

        self.gps_position_instance = get_gps_position()
        self.gps_latest_position = get_gps_latest_position()

        self.robohat_driver = get_robohat_driver()
        self.controller = get_navigation_controller()

    def utm_to_gps(self, easting, northing):
        """Convert UTM coordinates to GPS coordinates."""
        zone_number = self.utm_zone_number
        zone_letter = self.utm_zone_letter
        lat, lon = utm.to_latlon(easting, northing, zone_number, zone_letter)
        return lat, lon

    def compute_grid_dimensions(self, grid_points, grid_size, min_x, min_y):
        max_x = max(point[0] for point in grid_points)
        max_y = max(point[1] for point in grid_points)
        width = int((max_x - min_x) / grid_size) + 1
        height = int((max_y - min_y) / grid_size) + 1
        return width, height

    def load_mowing_area_polygon(self):
        if not os.path.exists(self.USER_POLYGON_PATH):
            logger.error("Mowing area polygon file 'user_polygon.json' not found.")
            exit(1)
        with open(self.USER_POLYGON_PATH, 'r') as f:
            polygon_data = json.load(f)
            self.mowing_area_polygon_gps = [(point['lat'], point['lng']) for point in polygon_data]
        if not self.mowing_area_polygon_gps:
            logger.error("'user_polygon.json' does not contain valid polygon data.")
            exit(1)

    def gps_polygon_to_utm_polygon(self):
        self.mowing_area_polygon_utm = []
        for idx, (lat, lon) in enumerate(self.mowing_area_polygon_gps):
            easting, northing, zone_number, zone_letter = utm.from_latlon(lat, lon)
            self.mowing_area_polygon_utm.append((easting, northing))
            if idx == 0:
                self.utm_zone_number = zone_number
                self.utm_zone_letter = zone_letter

    def generate_grid_from_polygon(self, grid_size=1.0):
        min_x = min(point[0] for point in self.mowing_area_polygon_utm)
        max_x = max(point[0] for point in self.mowing_area_polygon_utm)
        min_y = min(point[1] for point in self.mowing_area_polygon_utm)
        max_y = max(point[1] for point in self.mowing_area_polygon_utm)

        grid_x = np.arange(min_x, max_x + grid_size, grid_size)
        grid_y = np.arange(min_y, max_y + grid_size, grid_size)
        self.grid_points = [
            (x, y) for x in grid_x for y in grid_y
            if self.point_in_polygon(x, y, self.mowing_area_polygon_utm)
        ]

    def point_in_polygon(self, x, y, polygon):
        num_points = len(polygon)
        j = num_points - 1
        inside = False
        for i in range(num_points):
            xi, yi = polygon[i]
            xj, yj = polygon[j]
            intersect = ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi)
            if intersect:
                inside = not inside
            j = i
        return inside

    def a_star_pathfinding(self, start, end):
        open_list = [start]
        closed_list = []
        g = {start: 0}
        f = {start: self.heuristic(start, end)}
        parent = {start: None}

        def neighbors(node):
            x, y = node
            potential_neighbors = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
            return [n for n in potential_neighbors if n in self.grid_points and n not in self.obstacles]

        while open_list:
            current = min(open_list, key=lambda n: f[n])
            if current == end:
                path = []
                while current:
                    path.append(current)
                    current = parent[current]
                return path[::-1]

            open_list.remove(current)
            closed_list.append(current)

            for neighbor in neighbors(current):
                if neighbor in closed_list:
                    continue
                tentative_g = g[current] + 1
                if neighbor not in open_list or tentative_g < g[neighbor]:
                    parent[neighbor] = current
                    g[neighbor] = tentative_g
                    f[neighbor] = g[neighbor] + self.heuristic(neighbor, end)
                    if neighbor not in open_list:
                        open_list.append(neighbor)
        return []

    def heuristic(self, node1, node2):
        return math.sqrt((node1[0] - node2[0]) ** 2 + (node1[1] - node2[1]) ** 2)

    def rrt_planner(self, start, goal, obstacles, step_size=1.0, max_iter=1000):
        min_x = min(point[0] for point in self.mowing_area_polygon_utm)
        max_x = max(point[0] for point in self.mowing_area_polygon_utm)
        min_y = min(point[1] for point in self.mowing_area_polygon_utm)
        max_y = max(point[1] for point in self.mowing_area_polygon_utm)
        def distance(p1, p2):
            return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)

        def is_collision_free(point, obstacles, buffer=1.0):
            return all(distance(point, obs) >= buffer for obs in obstacles)

        tree = {start: None}
        for _ in range(max_iter):
            rand_point = (random.uniform(min_x, max_x), random.uniform(min_y, max_y))
            nearest = min(tree.keys(), key=lambda p: distance(p, rand_point))
            direction = ((rand_point[0] - nearest[0]), (rand_point[1] - nearest[1]))
            length = distance(nearest, rand_point)
            step = (nearest[0] + step_size * direction[0] / length, nearest[1] + step_size * direction[1] / length)
            if is_collision_free(step, obstacles):
                tree[step] = nearest
                if distance(step, goal) < step_size:
                    path = [goal]
                    while path[-1] is not None:
                        path.append(tree[path[-1]])
                    return path[::-1]
        logger.error("RRT failed to find a path.")
        return []

    def handle_obstacle(self, current_position, remaining_waypoints):
        next_waypoint = remaining_waypoints[0]
        rrt_path = self.rrt_planner(current_position, next_waypoint, self.obstacles)
        if not rrt_path:
            logger.error("Unable to find a path around the obstacle.")
            return remaining_waypoints
        return rrt_path + remaining_waypoints[1:]

    def navigate_to_waypoints(self, waypoints):
        for waypoint in waypoints:
            if get_detect_obstacle() or get_detect_drop():
                logger.warning("Obstacle detected. Re-planning path.")
                current_position = self.gps_latest_position.run()
                if not current_position:
                    logger.error("No valid GPS data.")
                    break
                ts, easting, northing, _, _ = current_position
                current_utm = (easting, northing)
                remaining_waypoints = waypoints[waypoints.index(waypoint):]
                waypoints = self.handle_obstacle(current_utm, remaining_waypoints)
                continue
            lat, lon = self.utm_to_gps(waypoint[0], waypoint[1])
            target_location = (lat, lon)
            if not self.controller.navigate_to_location(target_location):
                logger.error("Failed to navigate to location.")
                break

    def load_mowing_pattern(self):
        if not os.path.exists(self.MOWING_SCHEDULE_PATH):
            logger.error(
                "Mowing schedule file 'mowing_schedule.json' not found. "
                "Please set the schedule via the user interface."
            )
            # Default to "stripes" pattern if schedule file not found
            self.pattern_type = "stripes"
        else:
            try:
                with open(self.MOWING_SCHEDULE_PATH, 'r') as f:
                    pattern_data = json.load(f)
                    self.pattern_type = pattern_data.get(
                        'patternType', 'stripes'
                    )
            except json.JSONDecodeError:
                logger.error(
                    "Error decoding 'mowing_schedule.json'. "
                    "Please ensure it contains valid JSON."
                )
                # Default to "stripes" pattern if error occurs
                self.pattern_type = "stripes"

    # Create mowing pattern

    def create_pattern(self):
        """Create waypoints based on selected pattern."""
        """Start by calculating minimum grid dimensions and grid size"""
        min_x = min(x for x, y in self.grid_points)
        min_y = min(y for x, y in self.grid_points)
        grid_size = 1.0
        width, height = self.compute_grid_dimensions(self.grid_points, grid_size, min_x, min_y)


        waypoints = []
        if not self.grid_points:
            logger.error("Grid points have not been generated.")
            return waypoints

        # Sort grid points for consistent processing
        sorted_grid = sorted(self.grid_points, key=lambda p: (p[1], p[0]))

        if self.pattern_type == "stripes":
            # Group points by y-coordinate (rows)
            rows = {}
            for x, y in sorted_grid:
                rows.setdefault(y, []).append((x, y))
            # Create waypoints by alternating the direction in each row
            for idx, row in enumerate(sorted(rows.keys())):
                points = rows[row]
                if idx % 2 == 0:
                    waypoints.extend(points)
                else:
                    waypoints.extend(points[::-1])

        elif self.pattern_type == "criss_cross":
            # Generate stripes in one direction
            self.pattern_type = "stripes"
            waypoints = self.create_pattern()
            # Generate stripes in the other direction
            self.pattern_type = "stripes_vertical"
            waypoints += self.create_pattern()
            self.pattern_type = "criss_cross"  # Reset pattern type

        elif self.pattern_type == "stripes_vertical":
            # Group points by x-coordinate (columns)
            columns = {}
            for x, y in sorted_grid:
                columns.setdefault(x, []).append((x, y))
            # Create waypoints by alternating the direction in each column
            for idx, col in enumerate(sorted(columns.keys())):
                points = columns[col]
                if idx % 2 == 0:
                    waypoints.extend(points)
                else:
                    waypoints.extend(points[::-1])

        elif self.pattern_type == "checkerboard":
            # Generate a checkerboard pattern
            for y in sorted(set(y for x, y in sorted_grid)):
                row_points = [pt for pt in sorted_grid if pt[1] == y]
                if y % 2 == 0:
                    waypoints.extend(row_points[::2])
                else:
                    waypoints.extend(row_points[1::2])

        elif self.pattern_type == "diamond":
            # Generate a diamond pattern centered in the area
            grid_points = set(self.grid_points)
            grid_size = 1.0
            min_x = min(point[0] for point in grid_points)
            min_y = min(point[1] for point in grid_points)
            width, height = self.compute_grid_dimensions(
                grid_points, grid_size, min_x, min_y
            )
            center_x = min_x + (width * grid_size) / 2
            center_y = min_y + (height * grid_size) / 2
            for y in np.arange(min_y, min_y + height * grid_size, grid_size):
                for x in np.arange(
                        min_x, min_x + width * grid_size, grid_size
                ):
                    if (x, y) in grid_points:
                        waypoints.append((x, y))

        elif self.pattern_type == "waves":
            # Generate a wave pattern
            for y in np.arange(min_y, min_y + height * grid_size, grid_size):
                for x in np.arange(
                        min_x, min_x + width * grid_size, grid_size
                ):
                    offset = (np.sin((y - min_y) / 5) * grid_size)
                    x_offset = x + offset
                    if (x_offset, y) in self.grid_points:
                        waypoints.append((x_offset, y))

        elif self.pattern_type == "concentric_circles":
            # Generate concentric circles
            center_x = min_x + (width * grid_size) / 2
            center_y = min_y + (height * grid_size) / 2
            max_radius = min(width, height) * grid_size / 2
            for r in np.arange(grid_size, max_radius, grid_size):
                circle_pts = self.circle_waypoints(
                    center_x, center_y, r, self.grid_points
                )
                waypoints.extend(circle_pts)

        elif self.pattern_type == "stars":
            # Generate a star pattern
            center_x = min_x + (width * grid_size) / 2
            center_y = min_y + (height * grid_size) / 2
            radius = min(width, height) * grid_size / 2
            waypoints.extend(self.star_waypoints(
                center_x, center_y, radius, self.grid_points)
            )

        elif self.pattern_type == "custom_image":
            img_path = os.getenv("USER_IMAGE_PATH", "image.png")
            x_offset = int(os.getenv("IMAGE_X_OFFSET", 0))
            y_offset = int(os.getenv("IMAGE_Y_OFFSET", 0))
            waypoints = self.image_to_waypoints(
                img_path, x_offset, y_offset, self.grid_points, grid_size
            )

        else:
            logger.error(f"Unsupported pattern type: {self.pattern_type}")
            exit(1)

        return waypoints

  
    def circle_waypoints(self, center_x, center_y,
    
        all_points = []  # List to store all generated points
                     radius, grid_points, step=15):
        """Generate waypoints for a circle with a given radius."""
        waypoinid_points):
        
                for i in range(0, 360, step):
            angle = np.radians(i)
            x = center_x + radius * np.cos(angle)
            y = center_y + radius * np.sin(angle)
            all_points.append((x, y))

        # Filter points based on the polygon check
        waypoints = [point for point in all_points if self.point_in_polygon(point[0], point[1], grid_points)]
        waypoints.append(point)
        return waypoints

    def star_waypoints(self, center_x, center_y, radius, grid_points):
        """Generate waypoints for a star pattern."""
        waypoints = []
        for i in range(5):
            angle = np.radians(i * 144)
            x = center_x + radius * np.cos(angle)
            y = center_y + radius * np.sin(angle)
            if self.point_in_polygon(x, y, grid_points):
                waypoints.append((x, y))
        return waypoints

    def image_to_waypoints(self, img_path, x_offset,
                           y_offset, grid_points, grid_size):
        """Convert an image to a set of waypoints."""
        if not os.path.exists(img_path):
            logger.error(
                f"Image file '{img_path}' not found for custom image pattern."
            )
            exit(1)

        # Load and process the image
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        img_height, img_width = img.shape

        # Create a binary image
        _, binary = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY_INV)

        # Find contours in the binary image
        contours, _ = cv2.findContours(binary,
                                       cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)

        waypoints = []
        for contour in contours:
            for point in contour:
                x_img = point[0][0]
                y_img = point[0][1]

                # Map image coordinates to UTM coordinates
                x = x_offset + x_img * grid_size
                y = y_offset + y_img * grid_size
                if (x, y) in grid_points:
                    waypoints.append((x, y))

        return waypoints

    def create_waypoint_map(self):
        waypoints = self.create_pattern()
        waypoint_map = []
        for waypoint in waypoints:
            lat, lon = self.utm_to_gps(waypoint[0], waypoint[1])
            waypoint_map.append({"lat": lat, "lon": lon})
        return waypoint_map

    def waypoint_map_to_json(self, waypoint_map):
        """Convert a list of waypoints to a JSON string."""
        return json.dumps(waypoint_map)


    def main(self):
        self.load_mowing_area_polygon()
        self.gps_polygon_to_utm_polygon()
        self.generate_grid_from_polygon(grid_size=1.0)
        waypoints = self.create_pattern()
        self.navigate_to_waypoints(waypoints)

    def shutdown(self):
        self.gps_position_instance.shutdown()
        self.robohat_driver.shutdown()


if __name__ == "__main__":
    planner = PathPlanner()
    try:
        planner.main()
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        planner.shutdown()
