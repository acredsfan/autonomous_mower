# Code to test motors via robohat and blade controller
import time
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
print(sys.path)
from hardware_interface.robohat import RoboHATDriver



def test_motors():
    """
    Test the motors by running them in forward and reverse directions.
    """
    try:
        robot = RoboHATDriver()
        print("Testing motors...")
        robot.write_pwm(0, 0)
        time.sleep(2)
        robot.write_pwm(1, 0)
        time.sleep(1)
        robot.write_pwm(0, 1)
        time.sleep(2)
        robot.write_pwm(1, 1)
        time.sleep(2)
        robot.write_pwm(0, 0)
        print("Motor test complete.")
    except Exception as e:
        print(f"Error in test_motors: {e}")


if __name__ == '__main__':
    test_motors()
