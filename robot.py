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
from user_interface.web_interface.app import start_web_interface, get_schedule
from user_interface.web_interface.camera import SingletonCamera
import json


# Initialize Logging
logging.basicConfig(filename='main.log', level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')

# Global variable for shared resource
shared_resource = []

# Function to initialize all resources
def initialize_resources(cfg):
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

# Function to check mowing conditions
def check_mowing_conditions():
    try:
        if sensor_interface.ideal_mowing_conditions():
            if not BladeController.blades_on:
                BladeController.set_speed(90)
                return True
        else:
            if BladeController.blades_on:
                BladeController.set_speed(0)
        return False
    except Exception as e:
        logging.exception("Error in check_mowing_conditions")
        return False

# Function to check if it is a scheduled mowing time
def check_scheduled_mowing_time():
    try:
        current_time = datetime.datetime.now()
        schedule = get_schedule()
        if schedule:
            next_scheduled_mow = datetime.datetime.strptime(schedule, "%Y-%m-%d %H:%M:%S")
            if current_time >= next_scheduled_mow:
                return True
        return False
    except Exception as e:
        logging.exception("Error in check_scheduled_mowing_time")

# Function to ensure the robot is in the correct starting position
def check_starting_position():
    try:
        current_position = GpsLatestPosition.get_latest_position()
        if current_position == path_planner.starting_position:
            return True
        else:
            return False
    except Exception as e:
        logging.exception("Error in check_starting_position")

# Function to turn on mower and send to the next waypoints until the final waypoint is reached, checking location along the way
def start_mowing():
    try:
        if not check_starting_position():
            logging.error("Starting position is incorrect. Reposition the robot.")
            return
        
        BladeController.set_speed(90)
        
        while not check_final_waypoint():
            # Continuously check if mowing conditions are still ideal
            if not check_mowing_conditions():
                logging.info("Mowing conditions are no longer ideal. Stopping mowing.")
                stop_mowing()
                return
            
            # Detect obstacles and update the obstacle map
            detected_obstacles = avoidance_algo.detect_and_update_obstacles()
            if detected_obstacles:
                # Pass the detected obstacles to the path planner
                path_planner.update_obstacle_map(detected_obstacles)
            
            current_position = GpsLatestPosition.get_latest_position()
            next_waypoint = path_planner.get_next_waypoint()
            
            if next_waypoint is None:
                logging.error("No more waypoints available.")
                break

            # Attempt to navigate to the next waypoint
            if not motor_controller.navigate_to_waypoint(current_position, next_waypoint):
                logging.warning("Navigation to waypoint failed. Re-planning path.")
                path_planner.plan_path(current_position, next_waypoint, [wkt.loads(wkt) for wkt in path_planner.obstacles])
                continue
            
        stop_mowing()

    except Exception as e:
        logging.exception("Error in start_mowing")

# Function to check if the robot is at the final waypoint
def check_final_waypoint():
    try:
        current_position = GpsLatestPosition.get_latest_position()
        if current_position == path_planner.final_waypoint:
            return True
        else:
            return False
    except Exception as e:
        logging.exception("Error in check_final_waypoint")

# Function to stop the robot and turn off the mower
def stop_mowing():
    try:
        BladeController.set_speed(0)
        motor_controller.stop()
    except Exception as e:
        logging.exception("Error in stop_mowing")

# Function to find a sunny location for the robot to charge
def find_sunny_location():
    try:
        sensor_interface.ideal_charging_conditions()
        sunny_location = PathPlanning.find_sunny_location()
        motor_controller.navigate_to_location(sunny_location)
    except Exception as e:
        logging.exception("Error in find_sunny_location")

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

# Main loop
if __name__ == "__main__":
    try:
        # Initialize resources
        cfg = Config()
        initialize_resources(cfg)

        # Start the web interface
        start_web_interface()

        while True:
            # Continuously check mowing conditions
            if not check_mowing_conditions():
                logging.info("Mowing conditions are no longer ideal. Stopping operation.")
                stop_mowing()
                continue  # Skip further checks and re-check conditions in the next loop
            
            # Detect obstacles and update the obstacle map
            detected_obstacles = avoidance_algo.detect_and_update_obstacles()
            if detected_obstacles:
                path_planner.update_obstacle_map(detected_obstacles)
            
            # Check scheduled mowing time and start mowing if appropriate
            if check_scheduled_mowing_time():
                start_mowing()
            else:
                find_sunny_location()
                go_home()
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt: Stopping the main loop.")
    except Exception as e:
        logging.exception("An error occurred in the main loop.")
    finally:
        # Cleanup
        BladeController.set_speed(0)
        motor_controller.stop()
        logging.info("Exiting the main loop.")
