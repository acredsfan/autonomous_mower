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
from hardware_interface.robohat import RoboHATDriver
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
        PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        self.USER_POLYGON_PATH = os.path.join(PROJECT_ROOT, 'user_polygon.json')
        self.MOWING_SCHEDULE_PATH = os.path.join(PROJECT_ROOT, 'mowing_schedule.json')
        
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
            self.gps_latest_position, self.robohat_driver, self.sensor_interface, debug=False
        )

    def load_mowing_area_polygon():
        global mowing_area_polygon_gps
        if not os.path.exists(USER_POLYGON_PATH):
            logger.error(
                "Mowing area polygon file 'user_polygon.json' not found. "
                "Please set the polygon via the user interface."
            )
            exit(1)
        else:
            try:
                with open(USER_POLYGON_PATH, 'r') as f:
                    polygon_data = json.load(f)
                    mowing_area_polygon_gps = [
                        (point['lat'], point['lng']) for point in polygon_data
                    ]
                    if not mowing_area_polygon_gps:
                        logger.error(
                            "'user_polygon.json' does not contain valid data."
                            "Please set the polygon via the user interface."
                        )
                        exit(1)
            except json.JSONDecodeError:
                logger.error(
                    "Error decoding 'user_polygon.json'."
                    "Please ensure it contains valid JSON."
                )
                exit(1)


    def load_mowing_pattern():
        if not os.path.exists(MOWING_SCHEDULE_PATH):
            logger.error(
                "Mowing schedule file 'mowing_schedule.json' not found. "
                "Please set the schedule via the user interface."
            )
            # Default to 'stripes' pattern if schedule file is missing
            return 'stripes'
        else:
            try:
                with open(MOWING_SCHEDULE_PATH, 'r') as f:
                    pattern_data = json.load(f)
                    pattern_type = pattern_data.get('patternType', 'stripes')
                    return pattern_type
            except json.JSONDecodeError:
                logger.error(
                    "Error decoding 'mowing_schedule.json'. "
                    "Please ensure it contains valid JSON."
                )
                exit(1)


    def gps_polygon_to_utm_polygon(polygon_gps):
        global utm_zone_number, utm_zone_letter
        polygon_utm = []
        for idx, (lat, lon) in enumerate(polygon_gps):
            easting, northing, zone_number, zone_letter = utm.from_latlon(lat, lon)
            polygon_utm.append((easting, northing))
            if idx == 0:
                # Store UTM zone information
                utm_zone_number = zone_number
                utm_zone_letter = zone_letter
        return polygon_utm


    def point_in_polygon(x, y, polygon):
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


    def generate_grid_from_polygon(polygon, grid_size=1.0):
        """Generate a grid of points within the mowing area polygon."""
        min_x = min(point[0] for point in polygon)
        max_x = max(point[0] for point in polygon)
        min_y = min(point[1] for point in polygon)
        max_y = max(point[1] for point in polygon)

        grid_x = np.arange(min_x, max_x, grid_size)
        grid_y = np.arange(min_y, max_y, grid_size)
        grid_points = []
        for x in grid_x:
            for y in grid_y:
                if point_in_polygon(x, y, polygon):
                    grid_points.append((x, y))
        return grid_points


    def compute_grid_shape(grid_points, grid_size):
        min_x = min(point[0] for point in grid_points)
        max_x = max(point[0] for point in grid_points)
        min_y = min(point[1] for point in grid_points)
        max_y = max(point[1] for point in grid_points)
        width = int((max_x - min_x) / grid_size) + 1
        height = int((max_y - min_y) / grid_size) + 1
        return width, height, min_x, min_y


    def heuristic(node1, node2):
        """Heuristic for A* (Euclidean distance)."""
        return math.sqrt((node1[0] - node2[0]) ** 2 + (node1[1] - node2[1]) ** 2)


    def a_star_pathfinding(start, end, grid, obstacles):
        """A* algorithm to find the shortest path from start to end."""
        open_list = []
        closed_list = []
        open_list.append(start)

        g = {start: 0}  # Cost from start to node
        f = {start: heuristic(start, end)}  # Estimated cost from start to end

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
            # Filter out neighbors that are obstacles or outside the grid
            return [
                n for n in potential_neighbors
                if n in grid and n not in obstacles
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
                    f[neighbor] = g[neighbor] + heuristic(neighbor, end)

                    if neighbor not in open_list:
                        open_list.append(neighbor)

        return []  # No path found


    def utm_to_gps(easting, northing, zone_number, zone_letter):
        lat, lon = utm.to_latlon(easting, northing, zone_number, zone_letter)
        return (lat, lon)


    def create_pattern(pattern_type, grid_points, grid_size, min_x, min_y):
        """Create waypoints based on selected pattern."""
        waypoints = []
        width, height = compute_grid_dimensions(grid_points,
                                                grid_size,
                                                min_x,
                                                min_y)

        if pattern_type == "stripes":
            # Generate waypoints in stripes
            for x in np.arange(min_x, min_x + width * grid_size, 2 * grid_size):
                column_points = [(x, y) for y in np.arange(
                    min_y, min_y + height * grid_size, grid_size
                    )
                                if (x, y) in grid_points]
                waypoints.extend(column_points)

        elif pattern_type == "criss_cross":
            # Generate stripes in one direction
            for x in np.arange(min_x, min_x + width * grid_size, 2 * grid_size):
                column_points = [(x, y) for y in np.arange(
                    min_y, min_y + height * grid_size, grid_size
                    )
                                if (x, y) in grid_points]
                waypoints.extend(column_points)
            # Generate stripes in the perpendicular direction
            for y in np.arange(min_y, min_y + height * grid_size, 2 * grid_size):
                row_points = [(x, y) for x in np.arange(
                    min_x, min_x + width * grid_size, grid_size
                    )
                            if (x, y) in grid_points]
                waypoints.extend(row_points)

        elif pattern_type == "checkerboard":
            # Generate a checkerboard pattern
            for x in np.arange(min_x, min_x + width * grid_size, 2 * grid_size):
                for y in np.arange(
                    min_y, min_y + height * grid_size, 2 * grid_size
                ):
                    square_points = [
                        (x, y), (x + grid_size, y),
                        (x + grid_size, y + grid_size), (x, y + grid_size)
                    ]
                    waypoints.extend(
                        [pt for pt in square_points if pt in grid_points]
                        )

        elif pattern_type == "diamond":
            # Generate a diamond pattern centered in the area
            center_x = min_x + (width * grid_size) / 2
            center_y = min_y + (height * grid_size) / 2
            max_distance = min(width, height) * grid_size / 2
            for d in np.arange(0, max_distance, grid_size):
                perimeter_points = [
                    (center_x - d, center_y),
                    (center_x, center_y - d),
                    (center_x + d, center_y),
                    (center_x, center_y + d)
                ]
                waypoints.extend(
                    [pt for pt in perimeter_points if pt in grid_points]
                    )

        elif pattern_type == "waves":
            # Generate a wave pattern
            for y in np.arange(min_y, min_y + height * grid_size, grid_size):
                for x in np.arange(min_x, min_x + width * grid_size, grid_size):
                    offset = (np.sin((y - min_y) / 5) * grid_size)
                    x_offset = x + offset
                    if (x_offset, y) in grid_points:
                        waypoints.append((x_offset, y))

        elif pattern_type == "concentric_circles":
            # Generate concentric circles
            center_x = min_x + (width * grid_size) / 2
            center_y = min_y + (height * grid_size) / 2
            max_radius = min(width, height) * grid_size / 2
            for r in np.arange(grid_size, max_radius, grid_size):
                circle_pts = circle_waypoints(center_x, center_y, r, grid_points)
                waypoints.extend(circle_pts)

        elif pattern_type == "stars":
            # Generate a star pattern
            center_x = min_x + (width * grid_size) / 2
            center_y = min_y + (height * grid_size) / 2
            radius = min(width, height) * grid_size / 2
            waypoints.extend(star_waypoints(
                center_x, center_y, radius, grid_points)
                )

        elif pattern_type == "custom_image":
            img_path = os.getenv("USER_IMAGE_PATH", "image.png")
            x_offset = int(os.getenv("IMAGE_X_OFFSET", 0))
            y_offset = int(os.getenv("IMAGE_Y_OFFSET", 0))
            waypoints = image_to_waypoints(
                img_path, x_offset, y_offset, grid_points, grid_size
                )

        else:
            logger.error(f"Unsupported pattern type: {pattern_type}")
            exit(1)

        return waypoints


    def compute_grid_dimensions(grid_points, grid_size, min_x, min_y):
        max_x = max(point[0] for point in grid_points)
        max_y = max(point[1] for point in grid_points)
        width = int((max_x - min_x) / grid_size) + 1
        height = int((max_y - min_y) / grid_size) + 1
        return width, height


    def circle_waypoints(center_x, center_y, radius, grid_points, step=15):
        """Generate waypoints for a circle with a given radius."""
        waypoints = []
        for angle in np.arange(0, 360, step):
            x = center_x + radius * np.cos(np.radians(angle))
            y = center_y + radius * np.sin(np.radians(angle))
            point = (x, y)
            if point_in_polygon(x, y, grid_points):
                waypoints.append(point)
        return waypoints


    def star_waypoints(center_x, center_y, radius, grid_points):
        """Generate waypoints for a star pattern."""
        waypoints = []
        for i in range(5):
            angle = np.radians(i * 144)  # Star points are spaced 144 degrees apart
            x = center_x + radius * np.cos(angle)
            y = center_y + radius * np.sin(angle)
            if point_in_polygon(x, y, grid_points):
                waypoints.append((x, y))
        return waypoints


    def image_to_waypoints(img_path, x_offset, y_offset, grid_points, grid_size):
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


    def navigate_to_waypoints(waypoints, grid_points, obstacles):
        global utm_zone_number, utm_zone_letter
        for waypoint in waypoints:
            # Check for obstacles
            obstacle_detected = detect_obstacle() or detect_drop()
            if obstacle_detected:
                # Handle obstacle avoidance
                logger.info("Obstacle detected, re-planning path.")
                current_position = gps_latest_position.run()
                if not current_position:
                    logger.error("No valid GPS data.")
                    break
                ts, easting, northing, zone_number, zone_letter = current_position
                current_utm = (easting, northing)
                # Add obstacle to obstacle list
                obstacles.append(current_utm)
                # Re-plan path from current position to remaining waypoints
                remaining_waypoints = waypoints[waypoints.index(waypoint):]
                new_path = a_star_pathfinding(current_utm,
                                            waypoint,
                                            grid_points,
                                            obstacles)
                if not new_path:
                    logger.error("Unable to find a new path to the waypoint.")
                    break
                # Continue with new path
                waypoints = new_path + remaining_waypoints
                continue

            # Navigate to the waypoint
            # Convert UTM to GPS
            lat, lon = utm_to_gps(waypoint[0], waypoint[1],
                                utm_zone_number, utm_zone_letter)
            target_location = (lat, lon)
            success = controller.navigate_to_location(target_location)
            if not success:
                logger.error("Failed to navigate to location.")
                break


    def get_path():
        """
        Returns the planned path as a list of GPS coordinates.
        """
        global planned_path
        global mowing_area_polygon_gps
        global utm_zone_number
        global utm_zone_letter

        if planned_path:
            # Path is already generated
            return planned_path

        # Load mowing area polygon
        load_mowing_area_polygon()

        # Convert mowing area polygon to UTM
        mowing_area_polygon_utm = gps_polygon_to_utm_polygon(
            mowing_area_polygon_gps)

        # Generate grid points within the mowing area
        grid_size = 1.0  # Adjust grid size as needed
        grid_points = generate_grid_from_polygon(mowing_area_polygon_utm,
                                                grid_size)

        # Compute grid dimensions
        width, height, min_x, min_y = compute_grid_shape(grid_points, grid_size)

        # Set pattern type
        pattern_type = load_mowing_pattern()

        # Create waypoints based on the pattern
        waypoints = create_pattern(pattern_type, grid_points, grid_size,
                                min_x, min_y)

        # Convert waypoints from UTM to GPS
        gps_waypoints = []
        for waypoint in waypoints:
            easting, northing = waypoint
            lat, lon = utm_to_gps(easting, northing,
                                utm_zone_number, utm_zone_letter)
            # Note order: [lng, lat] for Google Maps
            gps_waypoints.append([lon, lat])

        # Store the planned path
        planned_path = gps_waypoints

        return planned_path


    def main():
        # Load mowing area polygon
        load_mowing_area_polygon()
        # Convert mowing area polygon to UTM
        mowing_area_polygon_utm = gps_polygon_to_utm_polygon(
            mowing_area_polygon_gps)
        # Generate grid points within the mowing area
        grid_size = 1.0  # Adjust grid size as needed
        grid_points = generate_grid_from_polygon(mowing_area_polygon_utm,
                                                grid_size)

        # Compute grid dimensions
        width, height, min_x, min_y = compute_grid_shape(grid_points, grid_size)

        # Set pattern type
        pattern_type = load_mowing_pattern()
        # Create waypoints based on the pattern
        waypoints = create_pattern(pattern_type, grid_points, grid_size,
                                min_x, min_y)

        # Initialize obstacles list
        obstacles = []

        # Navigate to waypoints
        navigate_to_waypoints(waypoints, grid_points, obstacles)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Program terminated by user.")
    finally:
        gps_position_instance.shutdown()
        robohat_driver.shutdown()
