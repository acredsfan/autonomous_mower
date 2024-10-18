# path_planning.py

import json
import logging
import math
import os

import cv2
import numpy as np
import utm
# Import GPS and navigation modules
from gps import GpsLatestPosition, GpsPosition
from hardware_interfacerobohat import RoboHATDriver
from navigation import NavigationController
from obstacle_detection.local_obstacle_detection import (detect_drop,
                                                         detect_obstacle)

# Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize GPS position instance
gps_position_instance = GpsPosition(serial_port='/dev/ttyACM0', debug=False)
gps_position_instance.start()
gps_latest_position = GpsLatestPosition(
    gps_position_instance=gps_position_instance
    )

# Initialize RoboHAT driver
robohat_driver = RoboHATDriver()

# Initialize NavigationController
sensor_interface = None
controller = NavigationController(
    gps_latest_position, robohat_driver, sensor_interface, debug=False
)

# Define the paths to configuration files
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
USER_POLYGON_PATH = os.path.join(PROJECT_ROOT, 'user_polygon.json')
MOWING_SCHEDULE_PATH = os.path.join(PROJECT_ROOT, 'mowing_schedule.json')

# Global variables to store the mowing area polygon and UTM zone
mowing_area_polygon_gps = []
utm_zone_number = None
utm_zone_letter = None

# Global variable to store the path
planned_path = []


class PathPlanner:
    def __init__(self):
        # Define the path to user_polygon.json and mowing_schedule.json
        PROJECT_ROOT = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..')
            )
        self.USER_POLYGON_PATH = os.path.join(PROJECT_ROOT,
                                              'user_polygon.json'
                                              )
        self.MOWING_SCHEDULE_PATH = os.path.join(PROJECT_ROOT,
                                                 'mowing_schedule.json'
                                                 )

        # Initialize variables
        self.mowing_area_polygon_gps = []
        self.mowing_area_polygon_utm = []
        self.utm_zone_number = None
        self.utm_zone_letter = None
        self.pattern_type = "stripes"  # Default pattern
        self.grid_points = []
        self.planned_path = []
        self.obstacles = []

        # Initialize GPS position instance
        self.gps_position_instance = GpsPosition(serial_port='/dev/ttyACM0',
                                                 debug=False
                                                 )
        self.gps_position_instance.start()
        self.gps_latest_position = GpsLatestPosition(
            gps_position_instance=self.gps_position_instance
            )

        # Initialize RoboHAT driver
        self.robohat_driver = RoboHATDriver()

        # Initialize NavigationController
        self.sensor_interface = sensor_interface
        self.controller = NavigationController(
            self.gps_latest_position, self.robohat_driver,
            self.sensor_interface, debug=False
        )

    def load_mowing_area_polygon(self):
        if not os.path.exists(self.USER_POLYGON_PATH):
            logger.error(
                "Mowing area polygon file 'user_polygon.json' not found. "
                "Please set the polygon via the user interface."
            )
            exit(1)
        else:
            try:
                with open(self.USER_POLYGON_PATH, 'r') as f:
                    polygon_data = json.load(f)
                    self.mowing_area_polygon_gps = [
                        (point['lat'], point['lng']) for point in polygon_data
                    ]
                    if not self.mowing_area_polygon_gps:
                        logger.error(
                            "'user_polygon.json' does not contain valid "
                            "polygon data. "
                            "Please set the polygon via the user interface."
                        )
                        exit(1)
            except json.JSONDecodeError:
                logger.error(
                    "Error decoding 'user_polygon.json'. "
                    "Please ensure it contains valid JSON."
                )
                exit(1)

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

    def gps_polygon_to_utm_polygon(self):
        self.mowing_area_polygon_utm = []
        for idx, (lat, lon) in enumerate(self.mowing_area_polygon_gps):
            easting, northing, zone_number, zone_letter = utm.from_latlon(
                lat, lon
                )
            self.mowing_area_polygon_utm.append((easting, northing))
            if idx == 0:
                # Store UTM zone information
                self.utm_zone_number = zone_number
                self.utm_zone_letter = zone_letter

    # Generate grid from polygon
    def point_in_polygon(self, x, y, polygon):
        """Check if a point (x, y) is inside the polygon."""
        num_points = len(polygon)
        j = num_points - 1
        inside = False
        for i in range(num_points):
            xi, yi = polygon[i]
            xj, yj = polygon[j]
            intersect = ((yi > y) != (yj > y)) and \
                        (x < ((xj - xi) * (y - yi) / (yj - yi) + xi))
            if intersect:
                inside = not inside
            j = i
        return inside

    def generate_grid_from_polygon(self, grid_size=1.0):
        """Generate a grid of points within the mowing area polygon."""
        min_x = min(point[0] for point in self.mowing_area_polygon_utm)
        max_x = max(point[0] for point in self.mowing_area_polygon_utm)
        min_y = min(point[1] for point in self.mowing_area_polygon_utm)
        max_y = max(point[1] for point in self.mowing_area_polygon_utm)

        grid_x = np.arange(min_x, max_x + grid_size, grid_size)
        grid_y = np.arange(min_y, max_y + grid_size, grid_size)
        grid_points = []
        for x in grid_x:
            for y in grid_y:
                if self.point_in_polygon(x, y, self.mowing_area_polygon_utm):
                    grid_points.append((x, y))
        self.grid_points = grid_points

    def a_star_pathfinding(self, start, end):
        """A* algorithm to find the shortest path from start to end."""
        open_list = []
        closed_list = []
        open_list.append(start)

        g = {start: 0}  # Cost from start to node
        f = {start: self.heuristic(start, end)}

        parent = {start: None}

        def neighbors(node):
            x, y = node
            # Neighboring cells (4-way movement)
            potential_neighbors = [
                (x + 1, y),
                (x - 1, y),
                (x, y + 1),
                (x, y - 1)
            ]
            # Filter out neighbors that are in grid_points and not in obstacles
            return [
                n for n in potential_neighbors
                if n in self.grid_points and n not in self.obstacles
            ]

        while open_list:
            # Get the node with the lowest f-score
            current = min(open_list, key=lambda n: f[n])

            if current == end:
                # Path has been found; reconstruct it
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

                tentative_g = g[current] + 1  # Distance between nodes is 1
                if neighbor not in open_list or tentative_g < g[neighbor]:
                    parent[neighbor] = current
                    g[neighbor] = tentative_g
                    f[neighbor] = g[neighbor] + self.heuristic(neighbor, end)

                    if neighbor not in open_list:
                        open_list.append(neighbor)

        return []  # No path found

    def heuristic(self, node1, node2):
        """Heuristic for A* (Euclidean distance)."""
        return math.sqrt(
            (node1[0] - node2[0]) ** 2 + (node1[1] - node2[1]) ** 2
            )

    # Convert UTM to GPS
    def utm_to_gps(self, easting, northing):
        lat, lon = utm.to_latlon(
            easting, northing, self.utm_zone_number, self.utm_zone_letter
            )
        return (lat, lon)

    # Create mowing pattern
    def create_pattern(self):
        """Create waypoints based on selected pattern."""
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
                    if (x_offset, y) in grid_points:
                        waypoints.append((x_offset, y))

        elif self.pattern_type == "concentric_circles":
            # Generate concentric circles
            center_x = min_x + (width * grid_size) / 2
            center_y = min_y + (height * grid_size) / 2
            max_radius = min(width, height) * grid_size / 2
            for r in np.arange(grid_size, max_radius, grid_size):
                circle_pts = self.circle_waypoints(
                    center_x, center_y, r, grid_points
                    )
                waypoints.extend(circle_pts)

        elif self.pattern_type == "stars":
            # Generate a star pattern
            center_x = min_x + (width * grid_size) / 2
            center_y = min_y + (height * grid_size) / 2
            radius = min(width, height) * grid_size / 2
            waypoints.extend(self.star_waypoints(
                center_x, center_y, radius, grid_points)
                )

        elif self.pattern_type == "custom_image":
            img_path = os.getenv("USER_IMAGE_PATH", "image.png")
            x_offset = int(os.getenv("IMAGE_X_OFFSET", 0))
            y_offset = int(os.getenv("IMAGE_Y_OFFSET", 0))
            waypoints = self.image_to_waypoints(
                img_path, x_offset, y_offset, grid_points, grid_size
                )

        else:
            logger.error(f"Unsupported pattern type: {self.pattern_type}")
            exit(1)

        return waypoints

    def compute_grid_dimensions(self, grid_points, grid_size, min_x, min_y):
        max_x = max(point[0] for point in grid_points)
        max_y = max(point[1] for point in grid_points)
        width = int((max_x - min_x) / grid_size) + 1
        height = int((max_y - min_y) / grid_size) + 1
        return width, height

    def circle_waypoints(self, center_x, center_y,
                         radius, grid_points, step=15):
        """Generate waypoints for a circle with a given radius."""
        waypoints = []
        for angle in np.arange(0, 360, step):
            x = center_x + radius * np.cos(np.radians(angle))
            y = center_y + radius * np.sin(np.radians(angle))
            point = (x, y)
            if self.point_in_polygon(x, y, grid_points):
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

    def navigate_to_waypoints(self, waypoints):
        """Navigate mower through a list of waypoints."""
        for waypoint in waypoints:
            # Check for obstacles
            obstacle_detected = detect_obstacle() or detect_drop()
            if obstacle_detected:
                # Handle obstacle avoidance
                logger.info("Obstacle detected, re-planning path.")
                current_position = self.gps_latest_position.run()
                if not current_position:
                    logger.error("No valid GPS data.")
                    break
                ts, easting, northing, zone_number, \
                    zone_letter = current_position
                current_utm = (easting, northing)
                # Add obstacle to obstacle list
                self.obstacles.append(current_utm)
                # Re-plan path from current position to remaining waypoints
                remaining_waypoints = waypoints[waypoints.index(waypoint):]
                new_path = self.a_star_pathfinding(current_utm, waypoint)
                if not new_path:
                    logger.error("Unable to find a new path to the waypoint.")
                    break
                # Continue with new path
                waypoints = new_path + remaining_waypoints
                continue

            # Navigate to the waypoint
            # Convert UTM to GPS
            lat, lon = self.utm_to_gps(waypoint[0], waypoint[1])
            target_location = (lat, lon)
            success = self.controller.navigate_to_location(target_location)
            if not success:
                logger.error("Failed to navigate to location.")
                break

    def get_path(self):
        """
        Returns the planned path as a list of GPS coordinates.
        """
        if self.planned_path:
            # Path is already generated
            return self.planned_path

        # Load mowing area polygon
        self.load_mowing_area_polygon()
        # Load pattern type
        self.load_mowing_pattern()
        # Convert mowing area polygon to UTM
        self.gps_polygon_to_utm_polygon()
        # Generate grid points within the mowing area
        self.generate_grid_from_polygon(grid_size=1.0)
        # Create waypoints based on the pattern
        waypoints = self.create_pattern()

        # Convert waypoints from UTM to GPS
        gps_waypoints = []
        for waypoint in waypoints:
            lat, lon = self.utm_to_gps(waypoint[0], waypoint[1])
            # Note order: [lng, lat] for Google Maps
            gps_waypoints.append([lon, lat])

        # Store the planned path
        self.planned_path = gps_waypoints

        return self.planned_path

    def main(self):
        # Load mowing area polygon
        self.load_mowing_area_polygon()
        # Load pattern type
        self.load_mowing_pattern()
        # Convert mowing area polygon to UTM
        self.gps_polygon_to_utm_polygon()
        # Generate grid points within the mowing area
        self.generate_grid_from_polygon(grid_size=1.0)
        # Create waypoints based on the pattern
        waypoints = self.create_pattern()
        # Navigate to waypoints
        self.navigate_to_waypoints(waypoints)

    def shutdown(self):
        # Shutdown GPS position instance and robohat driver
        self.gps_position_instance.shutdown()
        self.robohat_driver.shutdown()


if __name__ == "__main__":
    planner = PathPlanner()
    try:
        path = planner.get_path()
        print("Planned Path:")
        for coord in path:
            print(f"Longitude: {coord[0]}, Latitude: {coord[1]}")
    except Exception as e:
        logger.error(f"Error generating path: {e}")
    finally:
        planner.shutdown()
