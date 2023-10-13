from hardware_interface.sensor_interface import SensorInterface
import logging
from hardware_interface import MotorController, BladeController
from control_system import trajectory_controller, speed_controller, direction_controller
from navigation_system import Localization, path_planning
from obstacle_detection import CameraProcessor, ObstacleAvoidance, AvoidanceAlgorithm
from user_interface.web_interface.app import start_web_interface, get_schedule
from user_interface.web_interface.camera import SingletonCamera
from multiprocessing import Process, Lock
import time
import datetime
from threading import Thread, Lock
import threading
import subprocess
from hardware_interface.sensor_interface import sensor_interface# Explicitly initialize common attributes and debug
sensor_interface.init_common_attributes()
print("Debugging SensorInterface:")
print(f"  Type: {type(sensor_interface)}")
print(f"  Has 'bus': {hasattr(sensor_interface, 'bus')}")
print(f"  Has 'ina3221': {hasattr(sensor_interface, 'ina3221')}")

# Initialize logging
logging.basicConfig(filename='main.log', level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')

#Function to initialize all resources
def initialize_resources():
    global sensor_interface, camera, path_planner, avoidance_algo, localization, motor_controller
    sensor_interface = SensorInterface()
    camera = SingletonCamera()
    path_planner = path_planning.PathPlanning()
    avoidance_algo = AvoidanceAlgorithm(camera)
    localization = Localization()
    motor_controller = MotorController()

# Initialize Lock for shared resources
lock = Lock()

# Shared Resource
shared_resource = []

def check_mowing_conditions():
    sensor_interface_instance = sensor_interface
    try:
        if sensor_interface_instance.ideal_mowing_conditions():
            if not BladeController.blades_on:
                BladeController.set_speed(90)
                return True
        else:
            if BladeController.blades_on:
                BladeController.set_speed(0)
        return False
    except Exception as e:
        logging.exception('An error occurred')
        logging.error(f"Error in check_mowing_conditions: {e}")
        return False

# Function to update shared resource
def update_shared_resource():
    global shared_resource
    with lock:
        # Update the shared resource here
        shared_resource.append("new_data")

# Function to read from shared resource
def read_shared_resource():
    global shared_resource
    with lock:
        # Read the shared resource here
        print(shared_resource)

def main():
    try:
        # Initialize all resources
        initialize_resources()

        update_thread = Thread(target=update_shared_resource)
        read_thread = Thread(target=read_shared_resource)
        update_thread.start()
        read_thread.start()

        # Start the Gunicorn server in a separate process
        gunicorn_process = subprocess.Popen(["gunicorn", "-k", "eventlet", "-w", "1", "--bind", "0.0.0.0:90", "user_interface.web_interface.wsgi:app"])

        mowing_requested = False
        mow_days, mow_hours = get_schedule()
        localization_instance = Localization()
        robot_position = localization_instance.estimate_position()
        path_following_thread = threading.Thread()

        if mow_days is None or mow_hours is None:
            logging.warning("Mowing schedule not set. Please set the schedule in the web interface.")
        else:
            # Main loop
            while True:
                try:
                    with lock:
                    # Get user schedule
                        mow_days, mow_hours = get_schedule()

                        # Update Localization
                        localization.update()

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
                        sensor_interface.update_obstacle_data()

                        # Get current state for RL
                        lat, lon, _ = localization.estimate_position()
                        current_state = (lat, lon)

                        # Update Q-table and get next action
                        avoidance_algo.q_learning(current_state, sensor_interface.get_obstacle_data())
                        next_action = avoidance_algo.get_next_action(current_state)

                        # Execute Next action
                        if next_action == 0:
                            motor_controller.set_motor_speed_and_direction(0)
                        elif next_action == 1:
                            motor_controller.set_motor_speed_and_direction(1)
                        elif next_action == 2:
                            continue
                        
                        ret, frame = camera.get_frame()

                        if ret:
                            # Classify obstacle using CNN
                            obstacle_label = CameraProcessor.classify_obstacle(frame)
                            print(f"Detected obstacle type: {obstacle_label}")


                        # Plan the path
                        localization_instance = Localization()
                        robot_position = localization_instance.estimate_position()
                        goal = path_planner.select_next_section(robot_position)
                        avoidance_algorithm = AvoidanceAlgorithm()
                        avoidance_algorithm.run_avoidance()
                        path = path_planner.plan_path(robot_position, goal, path_planning.obstacle_map)

                        # Move the robot along the path
                        if not path_following_thread.is_alive():
                            path_following_thread = threading.Thread(target=trajectory_controller.follow_path, args=(path,))
                            path_following_thread.start()

                        # Here, add Q-Learning logic for motor control
                        deviation_from_path = 0  # Calculate the deviation from the path
                        current_state = 0  # Define the current state based on your criteria

                        motor_controller.q_learning(current_state, deviation_from_path)
                        motor_controller.set_motor_speed_and_direction(current_state)

                        # Check for obstacles and update the path if needed
                        obstacles_detected = AvoidanceAlgorithm.detect_obstacles()
                        if obstacles_detected and path_following_thread.is_alive():
                            path = path_planner.plan_path(robot_position, goal, obstacles_detected)

                        # Add a delay to control the loop execution rate
                        time.sleep(0.1)
                
                except Exception as inner_e:
                    logging.exception(f"Error inside main loop: {inner_e}")


    except KeyboardInterrupt:
        logging.info("Exiting...")
        gunicorn_process.terminate()
        MotorController.stop_motors()
        BladeController.stop()
        update_thread.join()
        read_thread.join()
        logging.info("Shutdown complete.")

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        gunicorn_process.terminate()
        MotorController.stop_motors()
        BladeController.stop()
        #stop sensor thread
        
if __name__ == "__main__":
    main()