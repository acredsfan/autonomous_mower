import logging
from hardware_interface import MotorController, SensorInterface, BladeController
from control_system import trajectory_controller, speed_controller, direction_controller
from navigation_system import Localization, path_planning
from obstacle_detection import CameraProcessor, ObstacleAvoidance, AvoidanceAlgorithm
from user_interface.web_interface.app import start_web_interface, get_schedule
from multiprocessing import Process, Lock
import time
import datetime
import threading

# Initialize logging
logging.basicConfig(filename='main.log', level=logging.INFO)

# Initialize PathPlanning class
path_planner = path_planning.PathPlanning()
sensor_interface = SensorInterface()

# Initialize Lock for shared resources
lock = Lock()

def check_mowing_conditions():
    try:
        if sensor_interface.ideal_mowing_conditions():
            if not mower_blades_on:
                BladeController.set_speed(90)
                return True
        else:
            if mower_blades_on:
                BladeController.set_speed(0)
        return False
    except Exception as e:
        logging.error(f"Error in check_mowing_conditions: {e}")
        return False

def main():
    try:
        # Start the Flask app in a separate process
        flask_app_process = Process(target=start_web_interface)
        flask_app_process.start()

        mowing_requested = False
        mower_blades_on = False
        mow_days, mow_hours = get_schedule()
        localization_instance = Localization()
        robot_position = localization_instance.get_current_position()
        path_following_thread = threading.Thread()

        if mow_days is None or mow_hours is None:
            logging.warning("Mowing schedule not set. Please set the schedule in the web interface.")
        else:
            # Main loop
            while True:
                with lock:
                # Get user schedule
                    mow_days, mow_hours = get_schedule()

                    # Check if ideal mowing conditions are met (including weather)
                    mower_blades_on = check_mowing_conditions()
                    if not mower_blades_on:
                        time.sleep(60)
                        continue

                    # Check if today is a mowing day
                    now = datetime.datetime.now()
                    weekday = now.strftime("%A")
                    current_time = now.strftime("%H")
                    if weekday in mow_days and (current_time == mow_hours):
                        mowing_requested = True

                    # Update sensor data
                    SensorInterface.update_sensor_data()

                    # Update localization
                    Localization.update_localization()

                    # Plan the path
                    robot_position = Localization.get_current_position()
                    goal = path_planner.select_next_section(robot_position)
                    obstacles = AvoidanceAlgorithm.get_obstacle_data()
                    path = path_planner.plan_path(robot_position, goal, obstacles)

                    # Move the robot along the path
                    if not path_following_thread.is_alive():
                        path_following_thread = threading.Thread(target=trajectory_controller.follow_path, args=(path,))
                        path_following_thread.start()

                    # Check for obstacles and update the path if needed
                    obstacles_detected = AvoidanceAlgorithm.detect_obstacles()
                    if obstacles_detected and path_following_thread.is_alive():
                        path = path_planner.plan_path(robot_position, goal, obstacles_detected)

                    # Add a delay to control the loop execution rate
                    time.sleep(0.1)

    except KeyboardInterrupt:
        logging.info("Exiting...")
        flask_app_process.terminate()
        MotorController.stop_motors()
        BladeController.stop()
        logging.info("Shutdown complete.")
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        flask_app_process.terminate()
        MotorController.stop_motors()
        BladeController.stop()

if __name__ == "__main__":
    main()