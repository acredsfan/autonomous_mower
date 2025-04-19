"""
Robot module with dependency injection.

This module provides the main functionality for the autonomous mower,
but with proper dependency injection for better testability and
maintainability.
"""

from typing import Optional

from mower.hardware.adapters.blade_controller_adapter import BladeControllerAdapter
from mower.interfaces.hardware import BladeControllerInterface, MotorDriverInterface
from mower.interfaces.navigation import GpsInterface, LocalizationInterface, PathPlannerInterface
from mower.interfaces.obstacle_detection import AvoidanceAlgorithmInterface
from mower.utilities.logger_config import LoggerConfigInfo


class Robot:
    """
    Main robot class with dependency injection.

    This class coordinates all the components of the autonomous mower
    using dependency injection for better testability and maintainability.
    """

    def __init__(
        self,
        blade_controller: BladeControllerInterface,
        motor_driver: MotorDriverInterface,
        localization: LocalizationInterface,
        avoidance_algorithm: AvoidanceAlgorithmInterface,
        gps: GpsInterface,
        path_planner: PathPlannerInterface
    ):
        """
        Initialize the robot with all required components.

        Args:
            blade_controller: Blade controller component
            motor_driver: Motor driver component
            localization: Localization component
            avoidance_algorithm: Obstacle avoidance component
            gps: GPS component
            path_planner: Path planner component
        """
        self.blade_controller = blade_controller
        self.motor_driver = motor_driver
        self.localization = localization
        self.avoidance_algorithm = avoidance_algorithm
        self.gps = gps
        self.path_planner = path_planner
        self.logger = LoggerConfigInfo.get_logger(__name__)

    def run(self):
        """Main function to run the robot operations."""
        try:
            self.logger.info("Components initialized.")

            # Start the autonomous mower
            self.mow_yard()
        except Exception as e:
            self.logger.exception("An error occurred: %s", e)
        finally:
            # Cleanup
            self.blade_controller.disable()
            if self.motor_driver:
                self.motor_driver.shutdown()
            self.logger.info("Robot operation ended.")

    def mow_yard(self):
        """
        Mow the yard autonomously.
        """
        # Start all components
        self.motor_driver.start() if hasattr(self.motor_driver, 'start') else None
        self.blade_controller.enable()
        self.path_planner.start()
        self.avoidance_algorithm.start()
        self.localization.start()
        self.gps.start()

        self.logger.info("Mowing started.")


# Factory function to create a Robot instance with all dependencies
def create_robot(
    blade_controller: Optional[BladeControllerInterface] = None,
    motor_driver: Optional[MotorDriverInterface] = None,
    localization: Optional[LocalizationInterface] = None,
    avoidance_algorithm: Optional[AvoidanceAlgorithmInterface] = None,
    gps: Optional[GpsInterface] = None,
    path_planner: Optional[PathPlannerInterface] = None
) -> Robot:
    """
    Create a Robot instance with all dependencies.

    If any dependency is not provided, it will be created using the
    default implementation.

    Args:
        blade_controller: Blade controller component
        motor_driver: Motor driver component
        localization: Localization component
        avoidance_algorithm: Obstacle avoidance component
        gps: GPS component
        path_planner: Path planner component

    Returns:
        Robot: A fully initialized Robot instance
    """
    from mower.mower import (
        get_blade_controller,
        get_robohat_driver,
        get_localization,
        get_avoidance_algorithm,
        get_gps_nmea_positions,
        get_path_planner,
    )

    # Use provided dependencies or create default ones
    blade_controller = blade_controller or get_blade_controller()
    motor_driver = motor_driver or get_robohat_driver()
    localization = localization or get_localization()
    avoidance_algorithm = avoidance_algorithm or get_avoidance_algorithm()
    gps = gps or get_gps_nmea_positions()
    path_planner = path_planner or get_path_planner()

    return Robot(
        blade_controller=blade_controller,
        motor_driver=motor_driver,
        localization=localization,
        avoidance_algorithm=avoidance_algorithm,
        gps=gps,
        path_planner=path_planner
    )


def run_robot():
    """Main function to run the robot operations."""
    robot = create_robot()
    robot.run()


if __name__ == "__main__":
    run_robot()
