"""Direction controller module.

Controls the direction of the robot based on sensor input to avoid obstacles. 

Class DirectionController:

    Attributes:
        DISTANCE_THRESHOLD: Minimum distance to obstacle to trigger avoidance
        CHECK_INTERVAL: Time between direction checks going forward
        TURN_INTERVAL: Time to turn when avoiding obstacle
        sensor_interface: SensorInterface instance  
        motor_controller: MotorController instance

    Methods:

        __init__(): Initializes controller attributes.

        obstacle_detected(): Checks sensor readings for obstacles.

        choose_turn_direction(): Decides turn direction based on obstacles.

        control_direction(): Main control loop to handle direction.

"""
import time
import logging
from hardware_interface import MotorController
from hardware_interface.sensor_interface import SensorInterface
import logging

# Initialize logging
logging.basicConfig(filename='main.log', level=logging.DEBUG)

class DirectionController:
    def __init__(self):
        self.DISTANCE_THRESHOLD = 300
        self.CHECK_INTERVAL = 0.5
        self.TURN_INTERVAL = 1
        self.sensor_interface = SensorInterface()
        self.motor_controller = MotorController()
        
        logging.basicConfig(filename='main.log', level=logging.DEBUG)

    def obstacle_detected(self):
        left_distance = self.sensor_interface.read_vl53l0x_left()
        right_distance = self.sensor_interface.read_vl53l0x_right()
        return left_distance < self.DISTANCE_THRESHOLD, right_distance < self.DISTANCE_THRESHOLD

    def choose_turn_direction(self, left_obstacle, right_obstacle):
        if left_obstacle and right_obstacle:
            return "backward"
        elif left_obstacle:
            return "right"
        elif right_obstacle:
            return "left"
        else:
            return "forward"

    def control_direction(self):
        self.sensor_interface.init_sensors()
        self.motor_controller.init_motor_controller()

        while True:
            left_obstacle, right_obstacle = self.obstacle_detected()
            if left_obstacle or right_obstacle:
                direction = self.choose_turn_direction(left_obstacle, right_obstacle)
                self.motor_controller.set_motor_direction(direction)
                self.motor_controller.set_motor_speed(50, 50)
                time.sleep(self.TURN_INTERVAL)
            else:
                self.motor_controller.set_motor_direction("forward")
                self.motor_controller.set_motor_speed(50, 50)
                time.sleep(self.CHECK_INTERVAL)

def main():
    direction_controller = DirectionController()
    try:
        direction_controller.control_direction()
    except KeyboardInterrupt:
        direction_controller.motor_controller.stop_motors()
        direction_controller.motor_controller.cleanup()
        direction_controller.sensor_interface.cleanup()

if __name__ == "__main__":
    main()