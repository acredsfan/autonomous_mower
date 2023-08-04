from hardware_interface import MotorController, SensorInterface, BladeController
from control_system import trajectory_controller, speed_controller, direction_controller
from navigation_system import localization, path_planning, gps_interface
from obstacle_detection import CameraProcessor, ObstacleAvoidance, AvoidanceAlgorithm
from user_interface.web_interface.app import start_web_interface, get_schedule
from multiprocessing import Process
import time
import datetime
import threading

def main():
    # Start the Flask app in a separate process
    flask_app_process = Process(target=start_web_interface)
    flask_app_process.start()

    mowing_requested = False
    mower_blades_on = False
    mow_days, mow_hours = get_schedule()

    
    if mow_days is None or mow_hours is None:
        print("Mowing schedule not set. Please set the schedule in the web interface.")
        # You can add logic here to handle this case, such as waiting for the schedule to be set
    else:

      # Main loop
      try:
        while True:
            # Get user schedule
            mow_days, mow_hours = get_schedule()

            # Check if ideal mowing conditions are met (including weather)
            if SensorInterface.ideal_mowing_conditions() and SensorInterface.check_weather():
                if not mower_blades_on:
                    BladeController.set_speed(90)
                    mower_blades_on = True
            else:
                if mower_blades_on:
                    BladeController.set_speed(0)
                    mower_blades_on = False
                time.sleep(60)
                continue

            # Check if today is a mowing day
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
            obstacles = AvoidanceAlgorithm.get_obstacle_data()
            path = path_planning.plan_path(robot_position, goal, obstacles)

            # Move the robot along the path
            if not path_following_thread.is_alive():
                path_following_thread = threading.Thread(target=trajectory_controller.follow_path, args=(path,))
                path_following_thread.start()

            # Check for obstacles and update the path if needed
            obstacles_detected = AvoidanceAlgorithm.detect_obstacles()
            if obstacles_detected and path_following_thread.is_alive():
                path = path_planning.plan_path(robot_position, goal, obstacles_detected)

            # Add a delay to control the loop execution rate
            time.sleep(0.1)

      except KeyboardInterrupt:
          print("Exiting...")
 
          # Terminate the Flask app process
          flask_app_process.terminate()

          # Shut down the GStreamer pipeline (if applicable)
          gstreamer_pipeline.stop()

          # Shut down other components (if applicable)
          MotorController.stop()
          BladeController.stop()

          print("Shutdown complete.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"An error occurred: {e}")
        flask_app_process.terminate()
        
        # Shut down the GStreamer pipeline (if applicable)
        #gstreamer_pipeline.stop()

        # Shut down other components (if applicable)
        MotorController.stop()
        BladeController.stop()