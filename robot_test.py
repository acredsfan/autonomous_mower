# robot_web_test.py

import sys
import os
import time
import datetime
from threading import Lock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from hardware_interface import SensorInterface, BladeController, RoboHATController, GPIOManager
import logging
from navigation_system import Localization, PathPlanning, GpsLatestPosition
from obstacle_detection.avoidance_algorithm import ObstacleAvoidance
from user_interface.web_interface.app import start_web_interface

import json

# Initialize Logging
logging.basicConfig(filename='web_test.log', level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')

# Global variable for shared resource
shared_resource = []

# Function to initialize all resources
def initialize_resources(cfg):
    from user_interface.web_interface.camera import SingletonCamera
    global sensor_interface, camera, path_planner, avoidance_algo, localization, motor_controller
    sensor_interface = SensorInterface()
    camera = SingletonCamera()
    path_planner = PathPlanning()
    avoidance_algo = ObstacleAvoidance()
    localization = Localization(cfg)
    try:
        motor_controller = RoboHATController(cfg)
    except RuntimeError as e:
        logging.error(f"Failed to initialize RoboHATController: {e}")
        GPIOManager.clean()  # Cleanup all GPIO
        motor_controller = RoboHATController(cfg)  # Retry initialization

# Lock for shared resources
lock = Lock()

# Function to verify the polygon points by traveling to each one
def verify_polygon_points():
    try:
        # Load the mowing area polygon coordinates from the saved JSON file
        with open('user_polygon.json', 'r') as f:
            polygon_points = json.load(f)

        # Check if polygon points are available
        if not polygon_points:
            logging.error("No polygon points found. Please set the mowing area in the web interface.")
            return

        logging.info("Starting polygon verification...")
        for index, point in enumerate(polygon_points):
            logging.info(f"Navigating to point {index + 1}: {point}")
            # Navigate to each point using the robot's motor controller
            motor_controller.navigate_to_location((point['lat'], point['lng']))

            # Optionally wait for confirmation or a set time at each point
            time.sleep(5)  # Adjust the sleep time as needed for verification

            # Log the robot's current position for verification
            current_position = GpsLatestPosition.get_latest_position()
            logging.info(f"Arrived at point {index + 1}, current GPS position: {current_position}")

        logging.info("Polygon verification complete.")
    except FileNotFoundError:
        logging.error("Mowing area not set. Please define the area in the web interface.")
    except Exception as e:
        logging.exception("Error in verify_polygon_points")

# Function to send robot to home location
def go_home():
    try:
        # Load the home location from the saved JSON file
        with open('home_location.json', 'r') as f:
            home_location = json.load(f)
        motor_controller.navigate_to_location((home_location['lat'], home_location['lng']))
    except FileNotFoundError:
        logging.error("Home location not set. Please set it in the web interface.")
    except Exception as e:
        logging.exception("Error in go_home")

# Main loop for testing web interface and sensors
if __name__ == "__main__":
    try:
        # Initialize resources
        cfg = Config()  # Ensure you have a Config class defined with necessary attributes
        initialize_resources(cfg)

        # Start the web interface to test manual controls and sensors
        start_web_interface()

        while True:
            # This loop is only here to keep the program running for web interface testing
            user_input = input("Enter 'verify' to test polygon points, 'home' to go home, or 'exit' to quit: ")
            if user_input.lower() == 'verify':
                verify_polygon_points()
            elif user_input.lower() == 'home':
                go_home()
            elif user_input.lower() == 'exit':
                break
            else:
                logging.info("Web interface test running. Use the web UI to test sensors and controls.")

    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt: Stopping the web test loop.")
    except Exception as e:
        logging.exception("An error occurred during the web interface test.")
    finally:
        # Cleanup
        BladeController.set_speed(0)
        motor_controller.stop()
        logging.info("Exiting the web interface test.")
