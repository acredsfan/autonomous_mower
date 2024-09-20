# robot.py

import sys
import signal
import threading
import time
from utilities import LoggerConfigInfo as LoggerConfig
from user_interface.web_interface.app import start_web_interface, position_reader  # Ensure position_reader is accessible
from hardware_interface import (
    BladeController,
    RoboHATController,
    GPIOManager
)
import logging

# Initialize logger
logging = LoggerConfig.get_logger(__name__)

# Function to initialize all resources
def initialize_resources():
    global sensor_interface, blade_controller, robohat_controller
    from hardware_interface.sensor_interface import get_sensor_interface

    try:
        # Initialize sensor interface
        sensor_interface = get_sensor_interface()
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
    except Exception as e:
        logging.exception(f"Exception during resource initialization: {e}")
        sys.exit(1)

def monitor_gps_status(position_reader):
    """
    Periodically checks the GPS status and prints it to the console.
    """
    while True:
        try:
            status = position_reader.get_status()
            print(f"[GPS Status] {status}")
            time.sleep(2)  # Adjust the interval as needed
        except Exception as e:
            logging.error(f"Error in monitor_gps_status: {e}")
            time.sleep(2)

def shutdown_handler(signum, frame):
    """
    Handles graceful shutdown on receiving termination signals.
    """
    logging.info("Shutdown signal received. Cleaning up resources...")
    
    # Stop GPS Position
    try:
        if position_reader and position_reader.gps_position:
            position_reader.gps_position.shutdown()
            logging.info("GPS Position shut down successfully.")
    except Exception as e:
        logging.error(f"Error shutting down GPS Position: {e}")
    
    # Stop BladeController
    try:
        BladeController.stop()
        logging.info("BladeController stopped successfully.")
    except Exception as e:
        logging.error(f"Error stopping BladeController: {e}")
    
    # Stop RoboHATController
    try:
        if robohat_controller:
            robohat_controller.stop()
            logging.info("RoboHATController stopped successfully.")
    except Exception as e:
        logging.error(f"Error stopping RoboHATController: {e}")
    
    # Clean GPIO
    try:
        GPIOManager.clean()
        logging.info("GPIOs cleaned successfully.")
    except Exception as e:
        logging.error(f"Error cleaning GPIOs: {e}")
    
    logging.info("All resources cleaned up. Exiting application.")
    sys.exit(0)

if __name__ == "__main__":
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)
    
    try:
        # Initialize resources
        initialize_resources()
        
        # Verify that position_reader is initialized
        if not position_reader:
            logging.error("Position reader is not initialized. Exiting application.")
            sys.exit(1)
        
        # Start GPS status monitoring in a separate thread
        gps_thread = threading.Thread(target=monitor_gps_status, args=(position_reader,), daemon=True)
        gps_thread.start()
        logging.info("GPS status monitoring thread started.")
        
        # Start the web interface in a separate thread
        web_thread = threading.Thread(target=start_web_interface, daemon=True)
        web_thread.start()
        logging.info("Web interface thread started.")
        
        # Keep the main thread alive to listen for signals
        logging.info("Robot application is running. Press Ctrl+C to exit.")
        while True:
            time.sleep(1)
    
    except Exception as e:
        logging.exception(f"An unexpected error occurred: {e}")
        shutdown_handler(None, None)
