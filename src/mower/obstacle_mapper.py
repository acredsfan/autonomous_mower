import json
import logging
import time

from shapely.geometry import Point, Polygon

# from mower.navigation.navigation import NavigationController  # Removed:
# not used directly
from mower.constants import MIN_DISTANCE_THRESHOLD, polygon_coordinates
from mower.hardware.hardware_registry import get_hardware_registry
from mower.hardware.sensor_interface import EnhancedSensorInterface
from mower.navigation.localization import Localization

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ObstacleMapper:
    def __init__(
        self,
        localization: Localization,
        sensors: EnhancedSensorInterface,
    ):
        self.localization = localization  # Store the instance properly
        self.sensors = sensors
        self.driver = get_hardware_registry().get_robohat_driver()
        self.obstacle_map = []  # Store obstacle locations
        # Pass required interfaces to NavigationController
        # NOTE: NavigationController expects GpsLatestPosition,
        # RoboHATDriver, and EnhancedSensorInterface.
        # Replace the following line with correct types as needed for your
        # project.
        # self.navigation_controller = NavigationController(
        #     gps_latest_position,
        #     robohat_driver,
        #     sensor_interface
        # )
        # Placeholder, user must implement navigation logic.
        self.navigation_controller = None

        # Convert polygon_coordinates to a Shapely Polygon
        self.yard_boundary = self.load_yard_boundary()

    def load_yard_boundary(self):
        """Convert polygon_coordinates to a Shapely Polygon."""
        points = []

        # Handle empty or invalid polygon_coordinates
        if not polygon_coordinates or not isinstance(polygon_coordinates, list):
            logger.warning("Invalid polygon_coordinates. Using default boundary.")
            # Return a default small polygon around (0,0)
            return Polygon(
                [
                    (0.001, 0.001),
                    (0.001, -0.001),
                    (-0.001, -0.001),
                    (-0.001, 0.001),
                ]
            )

        # Process each coordinate, handling both 'lng'/'lat' and 'lon'/'lat'
        # formats
        for coord in polygon_coordinates:
            if not isinstance(coord, dict):
                logger.warning(f"Invalid coordinate format: {coord}. Skipping.")
                continue

            # Try to get longitude (either 'lng' or 'lon')
            lon = None
            if "lng" in coord:
                lon = coord["lng"]
            elif "lon" in coord:
                lon = coord["lon"]

            # Try to get latitude
            lat = coord.get("lat")

            # Only add point if both coordinates are valid
            if lon is not None and lat is not None:
                points.append((lon, lat))

        # If no valid points were found, use default
        if not points:
            logger.warning("No valid points found in polygon_coordinates. Using default boundary.")
            return Polygon(
                [
                    (0.001, 0.001),
                    (0.001, -0.001),
                    (-0.001, -0.001),
                    (-0.001, 0.001),
                ]
            )

        return Polygon(points)

    def detect_obstacle(self):
        """Check if an obstacle is detected using the sensors."""
        left_distance = float("inf")
        right_distance = float("inf")
        if hasattr(self.sensors, "sensor_data") and isinstance(self.sensors.sensor_data, dict):
            left_distance = self.sensors.sensor_data.get("left_distance", float("inf"))
            right_distance = self.sensors.sensor_data.get("right_distance", float("inf"))

        return left_distance < MIN_DISTANCE_THRESHOLD or right_distance < MIN_DISTANCE_THRESHOLD

    def record_obstacle(self):
        """Record the current GPS position as an obstacle if inside the boundary."""
        position = self.localization.estimate_position()  # Call properly
        if position:
            lat, lon = position
            obstacle_point = Point(lon, lat)

            if self.yard_boundary.contains(obstacle_point):
                logger.info(f"Obstacle detected inside boundary at {lat}, {lon}")
                self.obstacle_map.append({"latitude": lat, "longitude": lon})
            else:
                logger.warning(f"Obstacle at {lat}, {lon} is outside boundary. Ignored.")

    def save_obstacle_map(self, filename="obstacle_map.json"):
        """Save the obstacle map to a JSON file."""
        with open(filename, "w") as f:
            json.dump(self.obstacle_map, f, indent=4)
        logger.info(f"Obstacle map saved to {filename}")

    def is_within_yard(self, position):
        """Check if the current position is within the yard boundary."""
        if position:
            lat, lon = position
            return self.yard_boundary.contains(Point(lon, lat))
        return False

    def explore_yard(self, duration=300):
        """Explore the yard to map obstacles for a given duration (in seconds)."""
        start_time = time.time()

        while time.time() - start_time < duration:
            # Get the current position and ensure it's inside the yard
            # Find the top right corner of the yard
            corner = self.yard_boundary.bounds
            top_right_lat = corner[3]
            top_right_lon = corner[2]
            logger.info(f"Center of the yard is at {top_right_lat}, {top_right_lon}")

            # Move Robot to the center of the yard and grid pattern
            # User should implement navigation logic to move robot to
            # (top_right_lat, top_right_lon)
            pass
            # Create a grid pattern to cover the yard
            # Define the grid parameters
            grid_spacing = 1.0  # Distance between grid points in meters

            # Get the bounds of the yard
            minx, miny, maxx, maxy = self.yard_boundary.bounds

            # Generate grid points within the yard boundary
            grid_points = []
            x = minx
            while x <= maxx:
                y = miny
                while y <= maxy:
                    point = Point(x, y)
                    if self.yard_boundary.contains(point):
                        grid_points.append((y, x))
                    y += grid_spacing
                x += grid_spacing

            # Navigate to each grid point
            for lat, lon in grid_points:
                # User should implement navigation logic to move robot to (lat,
                # lon)
                pass
                """
                    Check for obstacles and record them if found,
                    then move around them to get to the target location.
                """
                if self.detect_obstacle():
                    self.record_obstacle()
                    # Move around the obstacle
                    # Only call if method exists
                    # User should implement obstacle avoidance logic here if
                    # needed.
                    pass
                # Check if Robot reached the point them move to the next point
                # User should implement location check logic here if needed.
                pass
                # If the Robot is not in the yard, allow it to return to the
                # yard
                if not self.is_within_yard(self.localization.estimate_position()):
                    # User should implement navigation logic to return robot to
                    # (top_right_lat, top_right_lon)
                    pass

            # Drive the mower forward at low speed
            self.driver.run(steering=0.0, throttle=0.2)

            # Check for obstacles and record them if found
            if self.detect_obstacle():
                self.record_obstacle()

            time.sleep(0.1)  # Adjust the loop frequency

        # Stop the mower after exploration
        self.driver.run(0.0, 0.0)
        self.save_obstacle_map()


# Usage example
if __name__ == "__main__":
    localization = Localization()  # Ensure proper instantiation
    sensors = EnhancedSensorInterface()
    driver = get_hardware_registry().get_robohat_driver()

    mapper = ObstacleMapper(localization, sensors)
    logger.info("Starting yard exploration to build the obstacle map...")
    mapper.explore_yard(duration=600)  # Explore for 10 minutes
