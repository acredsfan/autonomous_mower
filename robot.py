# robot.py

from utilities import LoggerConfigInfo as LoggerConfig
from user_interface.web_interface.app import start_web_interface
from hardware_interface import (
    BladeController,
    RoboHATController,
    GPIOManager
)
import threading
import time
import sys
import os

# Initialize logger
logging = LoggerConfig.get_logger(__name__)

# Function to initialize all resources
def initialize_resources():
    global sensor_interface, blade_controller, robohat_controller
    from hardware_interface.sensor_interface import SensorInterface

    # Initialize sensor interface
    sensor_interface = SensorInterface()
    logging.info("Sensor interface initialized.")
    time.sleep(0.2)  # Allow time for sensors to initialize

    # Initialize blade controller
    blade_controller = BladeController()
    logging.info("Blade controller initialized.")
    time.sleep(0.2)

    # Initialize RoboHATController (movement controller)
    try:
        robohat_controller = RoboHATController()
        logging.info("RoboHAT controller initialized.")
    except RuntimeError as e:
        logging.error(f"Failed to initialize RoboHATController: {e}")
        GPIOManager.clean()  # Cleanup all GPIO
        time.sleep(0.5)  # Adding delay before retrying
        try:
            robohat_controller = RoboHATController()
            logging.info("RoboHAT controller initialized after retry.")
        except RuntimeError as e:
            logging.error(f"Retry failed for RoboHATController: {e}")
            robohat_controller = None

if __name__ == "__main__":
    try:
        # Initialize resources
        initialize_resources()

        # Start the web interface in a separate thread
        threading.Thread(target=start_web_interface, daemon=True).start()
        logging.info("Web interface started.")

        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt: Stopping the application.")
    except Exception:
        logging.exception("An error occurred during the application.")
    finally:
        # Cleanup
        BladeController.stop()
        if robohat_controller:
            robohat_controller.stop()
        GPIOManager.clean()
        logging.info("Exiting the application.")
