"""
Scripts for operating the RoboHAT MM1 by Robotics Masters with the Donkeycar
"""

import time
import donkeycar as dk
import os
from dotenv import load_dotenv
from constants import (MM1_MAX_FORWARD, MM1_MAX_REVERSE, MM1_STOPPED_PWM, MM1_STEERING_MID,
                       AUTO_RECORD_ON_THROTTLE, JOYSTICK_DEADZONE, SHOW_STEERING_VALUE)

try:
    import serial
except ImportError:
    print("PySerial not found. Please install: pip install pyserial")

from navigation_system import GpsLatestPosition
import math
from hardware_interface import SensorInterface

load_dotenv()
MM1_SERIAL_PORT = os.getenv("MM1_SERIAL_PORT")

from utils import LoggerConfig

# Initialize logger
logging = LoggerConfig.get_logger(__name__)



class RoboHATController:
    def __init__(self, debug=False):
        self.angle = 0.0
        self.throttle = 0.0
        self.mode = 'user'
        self.recording = False
        self.recording_latch = None
        self.auto_record_on_throttle = AUTO_RECORD_ON_THROTTLE
        self.STEERING_MID = MM1_STEERING_MID
        self.MAX_FORWARD = MM1_MAX_FORWARD
        self.STOPPED_PWM = MM1_STOPPED_PWM
        self.MAX_REVERSE = MM1_MAX_REVERSE
        self.SHOW_STEERING_VALUE = SHOW_STEERING_VALUE
        self.DEAD_ZONE = JOYSTICK_DEADZONE
        self.debug = debug
        # Initialize GPS Latest Position
        self.gps_latest_position = GpsLatestPosition()

        # Initialize the PWM communication
        try:
            self.pwm = serial.Serial(MM1_SERIAL_PORT, 115200, timeout=1)
        except serial.SerialException:
            print("Serial port not found! Please enable: sudo raspi-config")
        except serial.SerialTimeoutException:
            print("Serial connection timed out!")

    def trim_out_of_bound_value(self, value):
        if value > 1.0:
            return 1.0
        elif value < -1.0:
            return -1.0
        else:
            return value
        
    def shutdown(self):
        try:
            self.pwm.close()
        except:
            pass

    def read_serial(self):
        line = str(self.pwm.readline().decode()).strip('\n').strip('\r')
        output = line.split(", ")
        if len(output) == 2:
            if self.SHOW_STEERING_VALUE:
                print("MM1: steering={}".format(output[0]))

            if output[0].isnumeric() and output[1].isnumeric():
                angle_pwm = float(output[0])
                throttle_pwm = float(output[1])

                if self.debug:
                    print("angle_pwm = {}, throttle_pwm= {}".format(
                        angle_pwm, throttle_pwm
                    ))

                if throttle_pwm >= self.STOPPED_PWM:
                    throttle_pwm = dk.utils.map_range_float(
                        throttle_pwm, 1500, 2000, self.STOPPED_PWM, self.MAX_FORWARD
                    )
                    self.throttle = dk.utils.map_range_float(
                        throttle_pwm, self.STOPPED_PWM, self.MAX_FORWARD, 0, 1.0
                    )
                else:
                    throttle_pwm = dk.utils.map_range_float(
                        throttle_pwm, 1000, 1500, self.MAX_REVERSE, self.STOPPED_PWM
                    )
                    self.throttle = dk.utils.map_range_float(
                        throttle_pwm, self.MAX_REVERSE, self.STOPPED_PWM, -1.0, 0
                    )

                if angle_pwm >= self.STEERING_MID:
                    self.angle = dk.utils.map_range_float(
                        angle_pwm, 2000, self.STEERING_MID, -1, 0
                    )
                else:
                    self.angle = dk.utils.map_range_float(
                        angle_pwm, self.STEERING_MID, 1000, 0, 1
                    )

                if self.auto_record_on_throttle:
                    was_recording = self.recording
                    self.recording = self.throttle > self.DEAD_ZONE
                    if was_recording != self.recording:
                        self.recording_latch = self.recording
                        logging.debug(
                            "JoystickController::on_throttle_changes() setting recording = "
                            + str(self.recording)
                        )

                time.sleep(0.01)

    def update(self):
        print("Warming serial port...")
        time.sleep(3)

        while True:
            try:
                self.read_serial()
            except Exception as e:
                logging.error(f"MM1: Error reading serial input: {e}")
                break

    def run(self, img_arr=None, mode=None, recording=None):
        return self.run_threaded(img_arr, mode, recording)

    def run_threaded(self, img_arr=None, mode=None, recording=None):
        self.img_arr = img_arr
        if mode is not None:
            self.mode = mode
        if recording is not None and recording != self.recording:
            logging.debug(
                f"RoboHATController::run_threaded() setting recording from default = {recording}"
            )
            self.recording = recording
        if self.recording_latch is not None:
            logging.debug("RoboHATController::run_threaded() setting recording from latch = " +
                          str(self.recording_latch))
            self.recording = self.recording_latch
            self.recording_latch = None

        return self.angle, self.throttle, self.mode, self.recording

    def navigate_to_location(self, target_location):
        try:
            ts, lat, lon = self.gps_latest_position.run()
            current_position = (lat, lon)
            while not self.has_reached_location(current_position, target_location):
                steering, throttle = self.calculate_navigation_commands(current_position, target_location)
                self.set_pulse(steering, throttle)
                ts, lat, lon = self.gps_latest_position.get_latest_position()
                current_position = (lat, lon)
                time.sleep(0.1)
            self.stop()
            return True
        except Exception as e:
            logging.exception("Error in navigate_to_location")
            self.stop()
            return False

    def calculate_navigation_commands(self, current_position, target_location):
        # Calculate bearing between current_position and target_location
        bearing = self.calculate_bearing(current_position, target_location)
        heading_error = SensorInterface.update_sensors('heading') - bearing

        # Simple proportional controller for steering
        Kp = 0.01  # Proportional gain; adjust as needed
        steering = -Kp * heading_error  # Negative sign to correct the error

        # Set throttle based on distance to target
        distance = self.calculate_distance(current_position, target_location)
        throttle = min(distance * 0.1, 1.0)  # Scale throttle; adjust as needed

        # Clamp steering and throttle values
        steering = max(min(steering, 1.0), -1.0)
        throttle = max(min(throttle, 1.0), 0.0)

        return steering, throttle

    def calculate_bearing(self, current_position, target_location):
        # Calculate the bearing between two GPS coordinates
        lat1, lon1 = map(math.radians, current_position)
        lat2, lon2 = map(math.radians, target_location)
        dLon = lon2 - lon1

        x = math.sin(dLon) * math.cos(lat2)
        y = math.cos(lat1) * math.sin(lat2) - (math.sin(lat1) * math.cos(lat2) * math.cos(dLon))
        initial_bearing = math.atan2(x, y)
        initial_bearing = math.degrees(initial_bearing)
        compass_bearing = (initial_bearing + 360) % 360
        return compass_bearing

    def calculate_distance(self, current_position, target_location):
        # Calculate the distance between two GPS coordinates
        lat1, lon1 = current_position
        lat2, lon2 = target_location
        R = 6371e3  # Earth radius in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        a = math.sin(delta_phi/2) ** 2 + \
            math.cos(phi1) * math.cos(phi2) * \
            math.sin(delta_lambda/2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = R * c
        return distance

    def has_reached_location(self, current_position, target_location, tolerance=0.0001):
        lat1, lon1 = current_position
        lat2, lon2 = target_location
        return abs(lat1 - lat2) < tolerance and abs(lon1 - lon2) < tolerance

    def stop(self):
        self.set_pulse(0, 0)
        logging.info("Robot stopped.")

    def set_pulse(self, steering, throttle):
        try:
            steering = self.trim_out_of_bound_value(steering)
            throttle = self.trim_out_of_bound_value(throttle)

            if throttle > 0:
                output_throttle = dk.utils.map_range(throttle, 0, 1.0, self.STOPPED_PWM, self.MAX_FORWARD)
            else:
                output_throttle = dk.utils.map_range(throttle, -1, 0, self.MAX_REVERSE, self.STOPPED_PWM)

            if steering > 0:
                output_steering = dk.utils.map_range(steering, 0, 1.0, self.STEERING_MID, 1000)
            else:
                output_steering = dk.utils.map_range(steering, -1, 0, 2000, self.STEERING_MID)

            if self.is_valid_pwm_value(output_steering) and self.is_valid_pwm_value(output_throttle):
                if self.debug:
                    print("output_steering=%d, output_throttle=%d" % (output_steering, output_throttle))
                self.write_pwm(output_steering, output_throttle)
            else:
                print(f"Warning: steering = {output_steering}, STEERING_MID = {self.STEERING_MID}")
                print(f"Warning: throttle = {output_throttle}, MAX_FORWARD = {self.MAX_FORWARD}, STOPPED_PWM = {self.STOPPED_PWM}, MAX_REVERSE = {self.MAX_REVERSE}")
                print("Not sending PWM value to MM1")

        except OSError as err:
            print("Unexpected issue setting PWM (check wires to motor board): {0}".format(err))

    def is_valid_pwm_value(self, value):
        return 1000 <= value <= 2000

    def write_pwm(self, steering, throttle):
        self.pwm.write(b"%d, %d\r" % (steering, throttle))

    def shutdown(self):
        try:
            self.serial.close()
        except:
            pass