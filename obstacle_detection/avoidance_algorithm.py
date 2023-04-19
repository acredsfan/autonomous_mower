# Code for the obstacle avoidance algorithm
# Uses the data from the ToF sensors and the camera to calculate the best direction to move in

#IMPORTS
# IMPORTS
import threading
from tof_processing import ObstacleAvoidance as ToFAvoidance
from camera_processing import CameraProcessor
from motor_controller import init_motor_controller, set_motor_speed, set_motor_direction, stop_motors, cleanup

# Constants
CAMERA_OBSTACLE_THRESHOLD = 1000  # Minimum area to consider an obstacle from the camera
MOTOR_SPEED = 70

class AvoidanceAlgorithm:
    def __init__(self):
        self.tof_avoidance = ToFAvoidance()
        self.camera_processor = CameraProcessor()
        self.obstacle_detected = False

        init_motor_controller()

    def _tof_avoidance_thread(self):
        """Run the Time of Flight obstacle avoidance in a separate thread."""
        self.tof_avoidance.avoid_obstacles()

    def check_camera_obstacles(self):
        """Check for obstacles using the camera and update the obstacle_detected attribute."""
        obstacles = self.camera_processor.process_frame()

        for _, _, w, h in obstacles:
            if w * h > CAMERA_OBSTACLE_THRESHOLD:
                self.obstacle_detected = True
                return

        self.obstacle_detected = False

    def run_avoidance(self):
        """Continuously run the avoidance algorithm using data from ToF sensors and the camera."""
        # Start the ToF avoidance thread
        tof_thread = threading.Thread(target=self._tof_avoidance_thread)
        tof_thread.start()

        try:
            set_motor_speed(MOTOR_SPEED, MOTOR_SPEED)
            set_motor_direction("forward")

            while True:
                self.check_camera_obstacles()

                if self.tof_avoidance.obstacle_left or self.tof_avoidance.obstacle_right or self.obstacle_detected:
                    # Handle obstacle avoidance here
                    stop_motors()
                    set_motor_direction("backward")
                    set_motor_speed(MOTOR_SPEED, MOTOR_SPEED)
                    time.sleep(1)

                    set_motor_direction("left" if self.tof_avoidance.obstacle_left else "right")
                    time.sleep(0.5)

                    set_motor_direction("forward")
                    set_motor_speed(MOTOR_SPEED, MOTOR_SPEED)

                else:
                    # No obstacles detected
                    # Continue the normal operation of the robot
                    print("No obstacles detected.")

        except KeyboardInterrupt:
            print("Stopping the avoidance algorithm...")

        finally:
            stop_motors()
            self.camera_processor.close()
            tof_thread.join()
            cleanup()

if __name__ == "__main__":
    avoidance_algorithm = AvoidanceAlgorithm()
    avoidance_algorithm.run_avoidance()
