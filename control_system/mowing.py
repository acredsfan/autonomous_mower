# mowing.py
import logging
from hardware_interface import MotorController, BladeController
from navigation_system import Localization
from obstacle_detection import ObstacleAvoidance
from control_system import trajectory_controller
from user_interface.web_interface.app import update_status  # Adjust according to your actual update status method

class MowingSystem:
    def __init__(self):
        # Initialize components; these are assumed to be singleton or effectively singleton in use
        self.blade_controller = BladeController()
        self.motor_controller = MotorController()
        self.localization = Localization()
        self.obstacle_avoidance = ObstacleAvoidance()
        self.trajectory_controller = trajectory_controller
        self.is_mowing = False

    def start_mowing(self):
        try:
            # Start the blades
            self.blade_controller.start()
            self.is_mowing = True
            logging.info("Blades started for mowing.")

            # Begin mowing along the planned path, integrating obstacle avoidance
            self.begin_path_following_and_obstacle_avoidance()
            logging.info("Mowing started successfully.")
            update_status("Mowing started.")
        except Exception as e:
            logging.error(f"Failed to start mowing: {e}")
            update_status(f"Mowing error: {e}")

    def stop_mowing(self):
        try:
            # Stop the blades
            self.blade_controller.stop()
            self.is_mowing = False
            logging.info("Mowing stopped successfully.")
            update_status("Mowing stopped.")
        except Exception as e:
            logging.error(f"Failed to stop mowing: {e}")
            update_status(f"Mowing stop error: {e}")

    def begin_path_following_and_obstacle_avoidance(self):
        """
        Start following the path while checking for obstacles.
        This method will integrate the trajectory controller and obstacle avoidance system.
        """
        # Placeholder for starting trajectory following and obstacle avoidance logic
        # Example: self.trajectory_controller.follow_path_with_obstacle_avoidance()
        # Note: You'll need to implement or adjust this method based on your system design
        pass

    def update_mowing_status(self):
        """
        Update the mowing status on the web UI.
        """
        status_message = "Mowing in progress" if self.is_mowing else "Mowing paused or stopped"
        update_status(status_message)

# Example usage within other parts of your system could be as simple as:
# mowing_system = MowingSystem()
# mowing_system.start_mowing()
# ... later ...
# mowing_system.stop_mowing()
