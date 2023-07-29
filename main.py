from hardware_interface import MotorController, SensorInterface, BladeController
from control_system import trajectory_controller, speed_controller, direction_controller
from navigation_system import localization, path_planning, gps_interface
from obstacle_detection import camera_processing, tof_processing, avoidance_algorithm
from user_interface import web_interface, mobile_app
import time
import datetime
import threading

# Initialize mow_days and mow_hours with default values at the beginning of your script
mow_days = ["Monday", "Wednesday", "Friday"]  # Mow on these days by default
mow_hours = "08:00"  # Mow at this time by default

def main():
  # Initialization code...

  mowing_requested = False
  mower_blades_on = False

  # Main loop
  while True:
    # Check if ideal mowing conditions are met
    if SensorInterface.ideal_mowing_conditions():
      if not mower_blades_on:  # New condition to turn on mower blades
        BladeController.set_speed(90)
        mower_blades_on = True
    else:
      if mower_blades_on:  # New condition to turn off mower blades
        BladeController.set_speed(0)
        mower_blades_on = False
      # Wait for ideal conditions
      time.sleep(60)
      continue

    # Check if today is a mowing day - simplified if statements (issue #3)
    now = datetime.datetime.now()
    weekday = now.strftime("%A")
    current_time = now.strftime("%H:%M")
    if weekday in mow_days and (current_time == mow_hours or mowing_requested):
      if not mower_blades_on:
        BladeController.set_speed(90)
        mower_blades_on = True
    else:
      if mower_blades_on:
        BladeController.set_speed(0)
        mower_blades_on = False

    # Update sensor data
    SensorInterface.update_sensor_data()

    # Update localization
    localization.update_localization()

    # Plan the path
    robot_position = localization.get_current_position()
    goal = localization.get_target_position()
    obstacles = avoidance_algorithm.get_obstacle_data()
    path = path_planning.plan_path(robot_position, goal, obstacles)

    # Move the robot along the path - use threading for concurrent obstacle detection (issue #4)
    if not path_following_thread.is_alive():
      path_following_thread = threading.Thread(target=trajectory_controller.follow_path, args=(path,))
      path_following_thread.start()

    # Check for obstacles and update the path if needed
    obstacles_detected = avoidance_algorithm.detect_obstacles()
    if obstacles_detected and path_following_thread.is_alive():
      # Update the path to avoid obstacles
      path = path_planning.plan_path(robot_position, goal, obstacles_detected)

    # Add a delay to control the loop execution rate
    time.sleep(0.1)

# Wrap the main function call in a try-except block to handle exceptions (issue #5)
try:
  if __name__ == "__main__":
    main()
except Exception as e:
  print(f"An error occurred: {e}")