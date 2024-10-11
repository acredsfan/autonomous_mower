from utilities import LoggerConfigInfo as LoggerConfig
from user_interface.web_interface.app import start_web_interface, position_reader, start_mqtt_client
from hardware_interface.blade_controller import BladeController
from hardware_interface.robohat import RoboHATDriver  # Updated import
from hardware_interface.gpio_manager import GPIOManager
import threading
import time
import sys
import os

# Add the path to the sys path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))


# Initialize logger
logging = LoggerConfig.get_logger(__name__)

# Function to initialize all resources
def initialize_resources():
    global sensor_interface, blade_controller, robohat_driver  # Updated variable
    from hardware_interface.sensor_interface import get_sensor_interface

    # Initialize sensor interface
    sensor_interface = get_sensor_interface()
    logging.info("Sensor interface initialized.")
    time.sleep(0.2)  # Allow time for sensors to initialize

    # Initialize blade controller
    blade_controller = BladeController()
    logging.info("Blade controller initialized.")
    time.sleep(0.2)

    # Initialize RoboHATDriver (movement controller)
    try:
        robohat_driver = RoboHATDriver()  # Pass cfg
        logging.info("RoboHAT driver initialized.")
    except RuntimeError as e:
        logging.error(f"Failed to initialize RoboHATDriver: {e}")
        GPIOManager.clean()  # Cleanup all GPIO
        time.sleep(0.5)  # Adding delay before retrying
        try:
            robohat_driver = RoboHATDriver()  # Retry initialization
            logging.info("RoboHAT driver initialized after retry.")
        except RuntimeError as e:
            logging.error(f"Retry failed for RoboHATDriver: {e}")
            robohat_driver = None


def monitor_gps_status(position_reader):
    """
    Periodically checks the GPS status and prints it to the console.
    """
    while True:
        try:
            status = position_reader.get_status()
            print(f"[GPS Status] {status}")
            time.sleep(2)
        except Exception as e:
            print(f"[GPS Status] Error: {e}")
            time.sleep(2)


if __name__ == "__main__":
    try:
        # Initialize resources
        initialize_resources()
        if not position_reader:
            logging.error("Failed to initialize GPS position reader.")
            sys.exit(1)

        # Start the MQTT client in a separate thread
        mqtt_thread = threading.Thread(target=start_mqtt_client, daemon=True)
        mqtt_thread.start()
        logging.info("MQTT client started.")

        # Start the web interface in a separate thread
        web_thread = threading.Thread(target=start_web_interface, daemon=True)
        web_thread.start()
        logging.info("Web interface started.")

        gps_thread = threading.Thread(target=monitor_gps_status,
                                      args=(position_reader,), daemon=True)
        gps_thread.start()
        logging.info("GPS status monitoring started.")

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
        if robohat_driver:
            robohat_driver.shutdown()  # Use shutdown method
        GPIOManager.clean()
        logging.info("Exiting the application.")
