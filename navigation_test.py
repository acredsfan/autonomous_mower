import json
import time
from hardware_interface import RoboHATController
from navigation_system import GpsLatestPosition
from obstacle_detection import ObstacleAvoidance
from utils import LoggerConfig

# Initialize logger
logging = LoggerConfig.get_logger(__name__)

# Initialize GPS Latest Position and RoboHAT Controller
gps_latest_position = GpsLatestPosition()
robohat_controller = RoboHATController()
obstacle_detection = ObstacleAvoidance()


def navigate_and_confirm_polygon_points():
    try:
        # Load the mowing area polygon coordinates from the saved JSON file
        with open('user_polygon.json', 'r') as f:
            polygon_points = json.load(f)

        if not polygon_points:
            logging.error("No polygon points found. Please set the mowing area in the web interface.")
            return

        logging.info("Starting perimeter navigation and confirmation...")

        # Loop through each point in the polygon
        for index, point in enumerate(polygon_points):
            logging.info(f"Navigating to point {index + 1}: {point}")

            # Navigate to the point while avoiding obstacles
            robohat_controller.navigate_to_location((point['lat'], point['lng']))
            obstacle_detection.avoid_obstacles()

            # Wait for a moment to stabilize and get current GPS position
            time.sleep(5)
            current_position = gps_latest_position.run()

            # Display current point and prompt user for confirmation or update
            print(f"Arrived at point {index + 1}, current GPS position: {current_position}")
            user_input = input("Confirm point (y) or modify (m)? ")

            if user_input.lower() == 'm':
                # Allow user to input new coordinates
                new_lat = float(input("Enter new latitude: "))
                new_lng = float(input("Enter new longitude: "))
                polygon_points[index] = {'lat': new_lat, 'lng': new_lng}
                logging.info(f"Updated point {index + 1} to: {polygon_points[index]}")

            # Save the updated polygon points back to the file
            with open('user_polygon.json', 'w') as f:
                json.dump(polygon_points, f, indent=4)

        logging.info("Perimeter navigation and confirmation complete.")

    except FileNotFoundError:
        logging.error("Mowing area not set. Please define the area in the web interface.")
    except Exception as e:
        logging.exception(f"Error during perimeter navigation: {e}")


# Main loop for testing the feature
if __name__ == "__main__":
    try:
        # Start the feature when script is run
        navigate_and_confirm_polygon_points()
    except KeyboardInterrupt:
        logging.info("Process interrupted.")
    except Exception as e:
        logging.exception(f"An error occurred: {e}")
