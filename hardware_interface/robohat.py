#!/usr/bin/env python3
"""
Scripts for operating the RoboHAT MM1 by Robotics Masters.

Updated version based on recommendations.

- Separates controller and driver into two classes.
- Uses cfg for configurations.
- Ensures PWM values are integers.
- Removes navigation logic from controller.
"""

import time
import logging
import serial
from utilities import Utils
from constants import (
    MM1_MAX_FORWARD,
    MM1_MAX_REVERSE,
    MM1_STOPPED_PWM,
    MM1_STEERING_MID
)
import os

logger = logging.getLogger(__name__)




class RoboHATController:
    '''
    Controller to read signals from the RC controller via serial and convert into steering and throttle outputs.
    Input signal range: 1000 to 2000
    Output range: -1.00 to 1.00
    '''

    def __init__(self, cfg, debug=False):
        # Standard variables
        self.angle = 0.0
        self.throttle = 0.0
        self.mode = 'user'
        self.recording = False
        self.recording_latch = None
        self.auto_record_on_throttle = cfg.AUTO_RECORD_ON_THROTTLE
        self.STEERING_MID = cfg.MM1_STEERING_MID
        self.MAX_FORWARD = cfg.MM1_MAX_FORWARD
        self.STOPPED_PWM = cfg.MM1_STOPPED_PWM
        self.MAX_REVERSE = cfg.MM1_MAX_REVERSE
        self.SHOW_STEERING_VALUE = cfg.MM1_SHOW_STEERING_VALUE
        self.DEAD_ZONE = cfg.JOYSTICK_DEADZONE
        self.debug = debug

        # Initialize serial port for reading RC inputs
        try:
            self.serial = serial.Serial(cfg.MM1_SERIAL_PORT, 115200, timeout=1)
            logger.info(f"Serial port {cfg.MM1_SERIAL_PORT} opened for controller input.")
        except serial.SerialException:
            logger.error("Serial port for controller input not found! Please enable: sudo raspi-config")
            self.serial = None
        except serial.SerialTimeoutException:
            logger.error("Serial connection for controller input timed out!")
            self.serial = None

    def shutdown(self):
        if self.serial and self.serial.is_open:
            try:
                self.serial.close()
                logger.info("Controller serial connection closed.")
            except:
                pass

    def read_serial(self):
        '''
        Read the RC controller value from serial port. Map the value into
        steering and throttle.

        Expected format: '####,####\r', where the first number is steering and the second is throttle.
        '''
        if not self.serial or not self.serial.is_open:
            logger.warning("Controller serial port is not open.")
            return

        line = self.serial.readline().decode().strip('\n').strip('\r')

        output = line.split(", ")
        if len(output) == 2:
            if self.SHOW_STEERING_VALUE:
                logger.debug(f"MM1: steering={output[0]}")

            if output[0].isnumeric() and output[1].isnumeric():
                angle_pwm = float(output[0])
                throttle_pwm = float(output[1])

                if self.debug:
                    logger.debug(f"angle_pwm = {angle_pwm}, throttle_pwm= {throttle_pwm}")

                if throttle_pwm >= self.STOPPED_PWM:
                    # Scale down the input PWM (1500 - 2000) to our max forward
                    throttle_pwm_mapped = Utils.map_range_float(throttle_pwm,
                                                                   1500, 2000,
                                                                   self.STOPPED_PWM,
                                                                   self.MAX_FORWARD)
                    # Go forward
                    self.throttle = Utils.map_range_float(throttle_pwm_mapped,
                                                             self.STOPPED_PWM,
                                                             self.MAX_FORWARD,
                                                             0, 1.0)
                else:
                    throttle_pwm_mapped = Utils.map_range_float(throttle_pwm,
                                                                   1000, 1500,
                                                                   self.MAX_REVERSE,
                                                                   self.STOPPED_PWM)
                    # Go backward
                    self.throttle = Utils.map_range_float(throttle_pwm_mapped,
                                                             self.MAX_REVERSE,
                                                             self.STOPPED_PWM,
                                                             -1.0, 0)

                if angle_pwm >= self.STEERING_MID:
                    # Turn left
                    self.angle = Utils.map_range_float(angle_pwm,
                                                          2000, self.STEERING_MID,
                                                          -1, 0)
                else:
                    # Turn right
                    self.angle = Utils.map_range_float(angle_pwm,
                                                          self.STEERING_MID, 1000,
                                                          0, 1)

                if self.debug:
                    logger.debug(f"angle = {self.angle}, throttle = {self.throttle}")

                if self.auto_record_on_throttle:
                    was_recording = self.recording
                    self.recording = abs(self.throttle) > self.DEAD_ZONE
                    if was_recording != self.recording:
                        self.recording_latch = self.recording
                        logger.debug(f"Recording state changed to {self.recording}")

                time.sleep(0.01)

    def update(self):
        # Delay on startup to avoid crashing
        logger.info("Warming up controller serial port...")
        time.sleep(3)

        while True:
            try:
                self.read_serial()
            except Exception as e:
                logger.error(f"MM1: Error reading serial input: {e}")
                break

    def run(self, img_arr=None, mode=None, recording=None):
        """
        :param img_arr: current camera image or None
        :param mode: default user/mode
        :param recording: default recording mode
        """
        return self.run_threaded(img_arr, mode, recording)

    def run_threaded(self, img_arr=None, mode=None, recording=None):
        """
        :param img_arr: current camera image
        :param mode: default user/mode
        :param recording: default recording mode
        """
        self.img_arr = img_arr

        # Enforce defaults if they are not None.
        if mode is not None:
            self.mode = mode
        if recording is not None and recording != self.recording:
            logger.debug(f"Setting recording from default = {recording}")
            self.recording = recording
        if self.recording_latch is not None:
            logger.debug(f"Setting recording from latch = {self.recording_latch}")
            self.recording = self.recording_latch
            self.recording_latch = None

        return self.angle, self.throttle, self.mode, self.recording


class RoboHATDriver:
    """
    PWM motor controller using Robo HAT MM1 boards.
    """

    def __init__(self, debug=False):
        # Initialize the Robo HAT using the serial port
        self.debug = debug
        self.MAX_FORWARD = MM1_MAX_FORWARD
        self.MAX_REVERSE = MM1_MAX_REVERSE
        self.STOPPED_PWM = MM1_STOPPED_PWM
        self.STEERING_MID = MM1_STEERING_MID

        # Read the serial port from environment variables or use default
        MM1_SERIAL_PORT = os.getenv("MM1_SERIAL_PORT", "/dev/ttyS0")

        # Initialize serial port for sending PWM signals
        try:
            self.pwm = serial.Serial(MM1_SERIAL_PORT, 115200, timeout=1)
            logger.info(f"Serial port {MM1_SERIAL_PORT} opened for PWM output.")
        except serial.SerialException:
            logger.error("Serial port for PWM output not found! Please enable: sudo raspi-config")
            self.pwm = None
        except serial.SerialTimeoutException:
            logger.error("Serial connection for PWM output timed out!")
            self.pwm = None

    def trim_out_of_bound_value(self, value):
        """Trim steering and throttle values to be within -1.0 and 1.0"""
        if value > 1:
            logger.warning(f"MM1: Warning, value out of bound. Value = {value}")
            return 1.0
        elif value < -1:
            logger.warning(f"MM1: Warning, value out of bound. Value = {value}")
            return -1.0
        else:
            return value

    def set_pulse(self, steering, throttle):
        try:
            steering = self.trim_out_of_bound_value(steering)
            throttle = self.trim_out_of_bound_value(throttle)

            if throttle > 0:
                output_throttle = Utils.map_range(throttle,
                                                  0, 1.0,
                                                  self.STOPPED_PWM, self.MAX_FORWARD)
            else:
                output_throttle = Utils.map_range(throttle,
                                                  -1, 0,
                                                  self.MAX_REVERSE, self.STOPPED_PWM)

            if steering > 0:
                output_steering = Utils.map_range(steering,
                                                  0, 1.0,
                                                  self.STEERING_MID, 1000)
            else:
                output_steering = Utils.map_range(steering,
                                                  -1, 0,
                                                  2000, self.STEERING_MID)

            # Ensure PWM values are integers
            output_steering = int(output_steering)
            output_throttle = int(output_throttle)

            if self.is_valid_pwm_value(output_steering) and self.is_valid_pwm_value(output_throttle):
                if self.debug:
                    logger.debug(f"output_steering={output_steering}, output_throttle={output_throttle}")
                self.write_pwm(output_steering, output_throttle)
            else:
                logger.warning(f"Invalid PWM values: steering = {output_steering}, throttle = {output_throttle}")
                logger.warning("Not sending PWM value to MM1")

        except OSError as err:
            logger.error(f"Unexpected issue setting PWM (check wires to motor board): {err}")

    def is_valid_pwm_value(self, value):
        """Check if the PWM value is within valid range (1000 to 2000)"""
        return 1000 <= value <= 2000

    def write_pwm(self, steering, throttle):
        if self.pwm and self.pwm.is_open:
            try:
                pwm_command = b"%d, %d\r" % (steering, throttle)
                self.pwm.write(pwm_command)
                logger.debug(f"Sent PWM command: {pwm_command}")
            except Exception as e:
                logger.error(f"Failed to write PWM command: {e}")
        else:
            logger.error("Cannot write PWM command. PWM serial port is not open.")

    def run(self, steering, throttle):
        self.set_pulse(steering, throttle)

    def shutdown(self):
        if self.pwm and self.pwm.is_open:
            try:
                self.pwm.close()
                logger.info("PWM serial connection closed.")
            except:
                pass