from hardware_interface import motor_controller, sensor_interface, relay_controller
from control_system import trajectory_controller, speed_controller, direction_controller
from navigation_system import localization, path_planning, gps_interface
from obstacle_detection import camera_processing, tof_processing, avoidance_algorithm
from user_interface import web_interface, mobile_app
import time

def main():
    # Initialize hardware components
    motor_controller.init_motor_controller()
    sensor_interface.init_sensors()
    relay_controller.init_relay_controller()

    # Initialize control systems
    speed_controller.init_speed_controller()
    direction_controller.init_direction_controller()

    # Initialize navigation system
    localization.init_localization_system()
    path_planning.init_path_planning()
    gps_interface.init_gps_interface()

    # Initialize obstacle detection system
    camera_processing.init_camera_processing()
    tof_processing.init_tof_processing()
    avoidance_algorithm.init_avoidance_algorithm()

    # Initialize user interfaces
    web_interface.init_web_interface()
    mobile_app.init_mobile_app()

    # Main loop
    while True:
        # Update sensor data
        sensor_interface.update_sensor_data()

        # Update localization
        localization.update_localization()

        # Plan the path
        robot_position = localization.get_current_position()
        goal = localization.get_target_position()
        obstacles = avoidance_algorithm.get_obstacle_data()
        path = path_planning.plan_path(robot_position, goal, obstacles)

        # Move the robot along the path
        trajectory_controller.follow_path(path)

        # Check for obstacles and update the path if needed
        obstacles_detected = avoidance_algorithm.detect_obstacles()
        if obstacles_detected:
            # Update the path to avoid obstacles
            path = path_planning.plan_path(robot_position, goal, obstacles_detected)

        # Add a delay to control the loop execution rate
        time.sleep(0.1)

if __name__ == "__main__":
    main()