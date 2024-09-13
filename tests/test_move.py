# Code to test motors via robohat and blade controller
import time
from hardware_interface import RoboHATController, BladeController
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_motors():
    robohat = RoboHATController()
    blade_controller = BladeController()
    robohat.set_motors(0.5, 0.5)
    blade_controller.set_blades(0.5, 0.5)
    time.sleep(5)
    robohat.set_motors(0, 0)
    blade_controller.set_blades(0, 0)
    print("Motors are working correctly")


if __name__ == '__main__':
    test_motors()
