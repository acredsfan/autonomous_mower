"""
Scripts for operating the RoboHAT MM1 by Robotics Masters with the Donkeycar
"""

import logging
import os
import time
import math

from dotenv import load_dotenv
from navigation_system import GpsLatestPosition
from .sensor_interface import SensorInterface
from utils import LoggerConfig, Utils
from constants import (
    MM1_MAX_FORWARD,
    MM1_MAX_REVERSE,
    MM1_STOPPED_PWM,
    MM1_STEERING_MID,
    AUTO_RECORD_ON_THROTTLE,
    JOYSTICK_DEADZONE,
    SHOW_STEERING_VALUE
)

try:
    import serial
except ImportError:
    print("PySerial not found. Please install: pip install pyserial")


load_dotenv()
MM1_SERIAL_PORT = os.getenv("MM1_SERIAL_PORT")

# Initialize logger
LoggerConfig.configure_logging()
logging = logging.getLogger(__name__)


class RoboHATController:
    """Controller for the RoboHAT MM1 hardware interface."""

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
            logging.info(
                f"Serial port {MM1_SERIAL_PORT} opened successfully."
            )
        except serial.SerialException:
            logging.error(
                "Serial port not found! Please enable: sudo raspi-config"
            )
            self.pwm = None
        except serial.SerialTimeoutException:
            logging.error("Serial connection timed out!")
            self.pwm = None

    @staticmethod
    def trim_out_of_bound_value(value):
        """Clamps the value between -1.0 and 1.0."""
        return max(min(value, 1.0), -1.0)

    def shutdown(self):
        """Closes the PWM serial connection."""
        if self.pwm and self.pwm.is_open:
            try:
                self.pwm.close()
                logging.info("PWM serial connection closed.")
            except Exception as e:
                logging.error(
                    f"Error closing PWM serial connection: {e}"
                )

    def read_serial(self):
        """Reads and processes data from the serial port."""
        if not self.pwm or not self.pwm.is_open:
            logging.warning("PWM serial port is not open.")
            return

        line = self.pwm.readline().decode().strip()
        output = line.split(", ")
        if len(output) == 2:
            if self.SHOW_STEERING_VALUE:
                print(f"MM1: steering={output[0]}")

            if output[0].isnumeric() and output[1].isnumeric():
                angle_pwm = float(output[0])
                throttle_pwm = float(output[1])

                if self.debug:
                    print(
                        f"angle_pwm = {angle_pwm}, throttle_pwm= "
                        f"{throttle_pwm}"
                    )

                if throttle_pwm >= self.STOPPED_PWM:
                    throttle_pwm = Utils.map_range_float(
                        throttle_pwm, 1500, 2000,
                        self.STOPPED_PWM, self.MAX_FORWARD
                    )
                    self.throttle = Utils.map_range_float(
                        throttle_pwm, self.STOPPED_PWM, self.MAX_FORWARD,
                        0, 1.0
                    )
                else:
                    throttle_pwm = Utils.map_range_float(
                        throttle_pwm, 1000, 1500,
                        self.MAX_REVERSE, self.STOPPED_PWM
                    )
                    self.throttle = Utils.map_range_float(
                        throttle_pwm, self.MAX_REVERSE, self.STOPPED_PWM,
                        -1.0, 0
                    )

                if angle_pwm >= self.STEERING_MID:
                    self.angle = Utils.map_range_float(
                        angle_pwm, 2000, self.STEERING_MID, -1, 0
                    )
                else:
                    self.angle = Utils.map_range_float(
                        angle_pwm, self.STEERING_MID, 1000, 0, 1
                    )

                if self.auto_record_on_throttle:
                    was_recording = self.recording
                    self.recording = self.throttle > self.DEAD_ZONE
                    if was_recording != self.recording:
                        self.recording_latch = self.recording
                        logging.debug(
                            "JoystickController::on_throttle_changes() "
                            f"setting recording = {self.recording}"
                        )

        time.sleep(0.01)

    def update(self):
        """Continuously reads serial data."""
        logging.info("Warming serial port...")
        time.sleep(3)

        while True:
            try:
                self.read_serial()
            except Exception as e:
                logging.error(
                    f"MM1: Error reading serial input: {e}"
                )
                break

    def run(self, img_arr=None, mode=None, recording=None):
        """Runs the controller in a non-threaded mode."""
        return self.run_threaded(img_arr, mode, recording)

    def run_threaded(self, img_arr=None, mode=None, recording=None):
        """Runs the controller in a threaded mode."""
        self.img_arr = img_arr
        if mode is not None:
            self.mode = mode
        if recording is not None and recording != self.recording:
            logging.debug(
                f"RoboHATController::run_threaded() {recording} "
                f"setting recording from default = {recording}"
            )
            self.recording = recording
        if self.recording_latch is not None:
            logging.debug(
                f"RoboHATController::run_threaded() setting recording "
                f"from latch = {self.recording_latch}"
            )
            self.recording = self.recording_latch
            self.recording_latch = None

        return self.angle, self.throttle, self.mode, self.recording

    def navigate_to_location(self, target_location):
        """Navigates the robot to the specified target location."""
        try:
            ts, lat, lon = self.gps_latest_position.run()
            current_position = (lat, lon)
            while not self.has_reached_location(
                    current_position, target_location):
                steering, throttle = self.calculate_navigation_commands(
                    current_position, target_location
                )
                self.set_pulse(steering, throttle)
                ts, lat, lon = (
                    self.gps_latest_position
                    .get_latest_position()
                )
                current_position = (lat, lon)
                time.sleep(0.1)
            self.stop()
            return True
        except Exception:
            logging.exception("Error in navigate_to_location")
            self.stop()
            return False

    def calculate_navigation_commands(self, current_position, target_location):
        """
        Calculates steering and throttle commands based on current and
        target positions.
        """
        # Calculate bearing between current_position and target_location
        bearing = self.calculate_bearing(
            current_position, target_location
        )
        heading_error = (
            SensorInterface.update_sensors('heading') - bearing
        )

        # Simple proportional controller for steering
        Kp = 0.01  # Proportional gain; adjust as needed
        steering = -Kp * heading_error  # Negative sign to correct the error

        # Set throttle based on distance to target
        distance = self.calculate_distance(
            current_position, target_location
        )
        throttle = min(distance * 0.1, 1.0)  # Scale throttle; adjust as needed

        # Clamp steering and throttle values
        steering = max(min(steering, 1.0), -1.0)
        throttle = max(min(throttle, 1.0), 0.0)

        return steering, throttle

    @staticmethod
    def calculate_bearing(current_position, target_location):
        """Calculates the bearing from current_position to target_location."""
        lat1, lon1 = current_position
        lat2, lon2 = target_location
        angle_rad = math.atan2(lon2 - lon1, lat2 - lat1)
        # Normalize to 0-360 degrees
        bearing = (math.degrees(angle_rad) + 360) % 360
        return bearing

    @staticmethod
    def calculate_distance(current_position, target_location):
        """Calculates the Euclidean distance
        between current and target positions."""
        lat1, lon1 = current_position
        lat2, lon2 = target_location
        distance = math.hypot(lat2 - lat1, lon2 - lon1)
        return distance

    @staticmethod
    def has_reached_location(current_position, target_location,
                             tolerance=0.0001):
        """
        Determines if the current_position is within the tolerance of the
        target_location.
        """
        lat1, lon1 = current_position
        lat2, lon2 = target_location
        return (abs(lat1 - lat2) < tolerance and
                abs(lon1 - lon2) < tolerance)

    def stop(self):
        """Stops the robot by setting throttle and steering to zero."""
        self.set_pulse(0, 0)
        logging.info("Robot stopped.")

    def set_pulse(self, steering, throttle):
        """Sets the PWM signals for steering and throttle."""
        try:
            steering = self.trim_out_of_bound_value(steering)
            throttle = self.trim_out_of_bound_value(throttle)

            if throttle > 0:
                output_throttle = Utils.map_range(
                    throttle, 0, 1.0,
                    self.STOPPED_PWM, self.MAX_FORWARD
                )
            else:
                output_throttle = Utils.map_range(
                    throttle, -1, 0,
                    self.MAX_REVERSE, self.STOPPED_PWM
                )

            if steering > 0:
                output_steering = Utils.map_range(
                    steering, 0, 1.0,
                    self.STEERING_MID, 1000
                )
            else:
                output_steering = Utils.map_range(
                    steering, -1, 0,
                    2000, self.STEERING_MID
                )

            if (self.is_valid_pwm_value(output_steering) and
                    self.is_valid_pwm_value(output_throttle)):
                if self.debug:
                    print(
                        f"output_steering={output_steering}, "
                        f"output_throttle={output_throttle}"
                    )
                self.write_pwm(output_steering, throttle)
            else:
                logging.warning(
                    f"Warning: steering = {output_steering}, "
                    f"STEERING_MID = {self.STEERING_MID}"
                )
                logging.warning(
                    f"Warning: throttle = {output_throttle}, "
                    f"MAX_FORWARD = {self.MAX_FORWARD}, "
                    f"STOPPED_PWM = {self.STOPPED_PWM}, "
                    f"MAX_REVERSE = {self.MAX_REVERSE}"
                )
                logging.warning("Not sending PWM value to MM1")

        except OSError as err:
            logging.error(
                f"Unexpected issue setting PWM (check wires to motor "
                f"board): {err}"
            )

    @staticmethod
    def is_valid_pwm_value(value):
        """Checks if the PWM value is within the valid range."""
        return 1000 <= value <= 2000

    def write_pwm(self, steering, throttle):
        """Writes the PWM signals to the serial port."""
        if self.pwm and self.pwm.is_open:
            try:
                pwm_command = f"{steering}, {throttle}\r".encode()
                self.pwm.write(pwm_command)
                logging.debug(f"Sent PWM command: {pwm_command}")
            except Exception as e:
                logging.error(f"Failed to write PWM command: {e}")
        else:
            logging.error("Cannot write PWM command. Serial port is not open.")
