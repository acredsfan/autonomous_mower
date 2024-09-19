# robot_test.py

from utilities import LoggerConfig
import json
from user_interface.web_interface.app import start_web_interface
from obstacle_detection.avoidance_algorithm import AvoidanceAlgorithm
from navigation_system.localization import Localization
from navigation_system.gps import GpsLatestPosition
from path_planning import PathPlanning  # Import directly
from hardware_interface import (
    SensorInterface,
    BladeController,
    RoboHATController,
    GPIOManager
)
import sys
import os
import time
import threading

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# Initialize logger
logging = LoggerConfig.get_logger(__name__)

# Initialize GPS Latest Position
gps_latest_position = GpsLatestPosition()

# Global variable for shared resource
shared_resource = []
robohat_controller = None


# Function to initialize all resources
def initialize_resources():
    from hardware_interface.camera import SingletonCamera
    global sensor_interface, camera, path_planner
    global avoidance_algorithm, localization, robohat_controller

    sensor_interface = SensorInterface()
    time.sleep(0.2)  # Adding delay to allow I2C bus stabilization
    camera = SingletonCamera()
    time.sleep(0.2)
    localization = Localization()
    time.sleep(0.2)
    path_planner = PathPlanning(localization)
    time.sleep(0.2)
    try:
        # Pass gps_latest_position to RoboHATController
        robohat_controller = RoboHATController(gps_latest_position)
    except RuntimeError as e:
        logging.error(f"Failed to initialize RoboHATController: {e}")
        GPIOManager.clean()  # Cleanup all GPIO
        time.sleep(0.5)  # Adding delay before retrying
        try:
            robohat_controller = RoboHATController(gps_latest_position)
        except RuntimeError as e:
            logging.error(f"Retry failed for RoboHATController: {e}")
            robohat_controller = None

    # Initialize AvoidanceAlgorithm with dependencies
    avoidance_algorithm = AvoidanceAlgorithm(
        path_planner, robohat_controller, sensor_interface
    )


def start_mowing():
    # Start the mowing process
    logging.info("Starting the mowing process...")
    try:
        # Load the mowing area polygon coordinates from the saved JSON file
        with open('user_polygon.json', 'r') as f:
            polygon_points = json.load(f)

        # Check if polygon points are available
        if not polygon_points:
            logging.error(
                "No polygon points found."
                "Please set the mowing area in the web interface.")
            return

        # Set the user-defined polygon in PathPlanning
        path_planner.set_user_polygon(polygon_points)

        # Start the AvoidanceAlgorithm in a separate thread
        avoidance_thread = threading.Thread(
            target=avoidance_algorithm.run_avoidance, daemon=True)
        avoidance_thread.start()

        # Generate the path using PathPlanning
        start_point, goal_point = path_planner.get_start_and_goal()

        path = path_planner.get_path(start_point, goal_point)

        # Start mowing along the planned path
        BladeController.set_speed(100)  # Start the blades

        for coord in path:
            logging.info(f"Mowing at coordinate: {coord}")
            # Navigate to each coordinate while checking for obstacles
            robohat_controller.navigate_to_location((coord['lat'], coord['lng']))
            time.sleep(0.1)  # Adjust as needed

        logging.info("Mowing process complete.")

    except FileNotFoundError:
        logging.error(
            "Mowing area not set. Please define the area "
            "in the web interface.")
    except Exception:
        logging.exception("Error in start_mowing")
    finally:
        # Stop the blades and avoidance algorithm
        BladeController.set_speed(0)
        avoidance_algorithm.obstacle_avoidance.stop()


def stop_mowing():
    # Stop the mowing process
    logging.info("Stopping the mowing process...")
    BladeController.set_speed(0)
    robohat_controller.stop()
    avoidance_algorithm.obstacle_avoidance.stop()


# Main loop for testing web interface and sensors
if __name__ == "__main__":
    try:
        # Start the web interface in a separate thread
        threading.Thread(target=start_web_interface, daemon=True).start()

        # Initialize resources
        initialize_resources()

        while True:
            # This loop is only here to keep the program running for web
            # interface testing
            user_input = input(
                "Enter 'start' to begin mowing, 'stop' to stop mowing, 'exit' to quit: ")
            if user_input.lower() == 'start':
                start_mowing()
            elif user_input.lower() == 'stop':
                stop_mowing()
            elif user_input.lower() == 'exit':
                break
            else:
                logging.info(
                    "Test running. Use the webUI to test features.")

    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt: Stopping the web test loop.")

    except Exception:
        logging.exception("An error occurred during the web interface test.")

    finally:
        # Cleanup
        BladeController.stop()
        if robohat_controller:
            robohat_controller.stop()
        GPIOManager.clean()
        logging.info("Exiting the web interface test.")
