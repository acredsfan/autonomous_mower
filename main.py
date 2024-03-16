from hardware_interface.sensor_interface import SensorInterface
import logging
from hardware_interface import MotorController, BladeController
from control_system import trajectory_controller
from navigation_system import Localization, path_planning
from obstacle_detection import CameraProcessor, ObstacleAvoidance
from user_interface.web_interface.app import start_web_interface, get_schedule
from user_interface.web_interface.camera import SingletonCamera
from multiprocessing import Process
import time
import datetime
from threading import Thread, Lock
import subprocess
import RPi.GPIO as GPIO

# Initialize logging
logging.basicConfig(filename='main.log', level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')

# Global variable for shared resource
shared_resource = []

# Function to initialize all resources
def initialize_resources():
    global sensor_interface, camera, path_planner, avoidance_algo, localization, motor_controller
    sensor_interface = SensorInterface()
    camera = SingletonCamera()
    path_planner = path_planning.PathPlanning()
    avoidance_algo = ObstacleAvoidance(camera)
    localization = Localization()
    try:
        motor_controller = MotorController()
    except RuntimeError as e:
        logging.error(f"Failed to initialize MotorController: {e}")
        GPIO.cleanup()  # Cleanup all GPIO
        motor_controller = MotorController()  # Retry initialization

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

# Function to update shared resource
def update_shared_resource():
    with lock:
        shared_resource.append("new_data")
        logging.debug("Shared resource updated.")

# Function to read from shared resource
def read_shared_resource():
    with lock:
        if shared_resource:
            logging.debug(f"Reading from shared resource: {shared_resource[-1]}")
        else:
            logging.debug("Shared resource is empty.")

# Main function
def main():
    gunicorn_process = None
    update_thread = None
    read_thread = None
    try:
        initialize_resources()
        logging.info("All resources initialized successfully.")

        update_thread = Thread(target=update_shared_resource)
        read_thread = Thread(target=read_shared_resource)
        update_thread.start()
        read_thread.start()

        gunicorn_process = subprocess.Popen(["gunicorn", "-k", "eventlet", "-w", "1", "--bind", "0.0.0.0:5000", "user_interface.web_interface.app:app"])
        logging.info("Gunicorn server started.")

        while True:
            mowing_conditions_met = check_mowing_conditions()
            if mowing_conditions_met:
                logging.info("Mowing conditions met. Mowing initiated.")
                
            else:
                logging.info("Mowing conditions not met. Waiting.")
                # Additional logic for waiting
            time.sleep(1)

    except KeyboardInterrupt:
        logging.info("Manual interruption received (Ctrl+C). Shutting down...")

    finally:
        if gunicorn_process:
            gunicorn_process.terminate()
            logging.info("Gunicorn server terminated.")

        if update_thread and update_thread.is_alive():
            update_thread.join()

        if read_thread and read_thread.is_alive():
            read_thread.join()

        if 'motor_controller' in globals():
            motor_controller.cleanup()
        BladeController.stop()
        camera.cleanup()
        GPIO.cleanup()
        logging.info("All resources cleaned up and application has been successfully shut down.")

if __name__ == "__main__":
    main()