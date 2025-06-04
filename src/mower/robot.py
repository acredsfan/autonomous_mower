# Updated 11.1.24
from mower.mower import (
    get_avoidance_algorithm,
    get_blade_controller,
    get_gps_nmea_positions,
    get_localization,
    get_path_planner,
    get_robohat_driver,
)
from mower.utilities.logger_config import LoggerConfigInfo

# Initialize logger
logging = LoggerConfigInfo.get_logger(__name__)


def run_robot():
    """Main function to run the robot operations."""
    try:
        # Get components from interfaces
        blade_controller = get_blade_controller()
        robohat_driver = get_robohat_driver()
        logging.info("Components initialized.")

        # Start the autonomous mower
        mow_yard()
    except Exception as e:
        logging.exception("An error occurred: %s", e)
    finally:
        # Cleanup
        blade_controller.stop_blade()
        if robohat_driver:
            robohat_driver.shutdown()
        logging.info("Robot operation ended.")


def mow_yard():
    """
    Mow the yard autonomously.
    """
    position_reader = get_gps_nmea_positions()
    path_planner = get_path_planner()
    robohat_driver = get_robohat_driver()
    blade_controller = get_blade_controller()
    localization = get_localization()
    obstacle_algorithm = get_avoidance_algorithm()

    # Start the mower
    blade_controller.enable()
    path_planner.start()
    obstacle_algorithm.start()
    localization.start()
    position_reader.start()

    logging.info("Mowing started.")
