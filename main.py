import logging
from hardware_interface import MotorController, SensorInterface, BladeController
from control_system import trajectory_controller, speed_controller, direction_controller
from navigation_system import Localization, path_planning
from obstacle_detection import CameraProcessor, ObstacleAvoidance, AvoidanceAlgorithm
from user_interface.web_interface.app import start_web_interface, get_schedule
from user_interface.web_interface.camera import SingletonCamera
from multiprocessing import Process, Lock
import time
import datetime
import threading

# Initialize logging
logging.basicConfig(filename='main.log', level=logging.DEBUG)

# Initialize PathPlanning class
path_planner = path_planning.PathPlanning()

# Initialize AvoidanceAlgorithm, SensorInterface, and Localization
avoidance_algo = AvoidanceAlgorithm(camera)
sensor_interface = SensorInterface()
localization = Localization()

# Initialize MotorController
motor_controller = MotorController()

# Initialize the camera
camera = SingletonCamera()

#start_web_interface(camera_instance=camera)

# Initialize Lock for shared resources
lock = Lock()

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
        logging.error(f"Error in check_mowing_conditions: {e}")
        return False

def main():
    try:
        # Start the Flask app in a separate process
        flask_app_process = Process(target=start_web_interface, args=(camera,))
        flask_app_process.start()

        mowing_requested = False
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
                    lat, lon, _ = localization.get_current_position()
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
                    
                    ret, frame = cap.read()

                    if ret:
                        # Classify obstacle using CNN
                        obstacle_label = CameraProcessor.classify_obstacle(frame)
                        print(f"Detected obstacle type: {obstacle_label}")


                    # Plan the path
                    localization_instance = Localization()
                    robot_position = localization_instance.get_current_position()
                    goal = path_planner.select_next_section(robot_position)
                    avoidance_algorithm = AvoidanceAlgorithm()
                    avoidance_algorithm.run_avoidance()
                    path = path_planner.plan_path(robot_position, goal, obstacles)

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