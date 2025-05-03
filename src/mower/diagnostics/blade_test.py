"""
Blade test module for testing and calibrating blade motors.

This module provides functions for testing and calibrating the blade motor
of the autonomous mower. It can be run as a standalone script or the functions
can be imported and used in other modules.

Usage:
    python -m mower.diagnostics.blade_test

The module will run the blade motor through a series of speed tests and
allow for calibration of the PWM values if needed.
"""

import time
import argparse
from typing import Tuple
from dotenv import set_key

from mower.utilities.logger_config import LoggerConfigInfo as LoggerConfig
from mower.main_controller import ResourceManager

# Initialize logger
logging = LoggerConfig.get_logger(__name__)


def test_blade_speeds(
    resource_manager: ResourceManager,
    speed_steps: int = 5,
    run_time: float = 2.0,
) -> bool:
    """
    Test the blade motor at different speeds.

    Args:
        resource_manager: An instance of ResourceManager.
        speed_steps: Number of speed steps to test (from 0 to 1).
        run_time: Time to run at each speed step in seconds.

    Returns:
        True if the test completed successfully, False otherwise.
    """
    try:
        blade_controller = resource_manager.get_blade_controller()
        if blade_controller is None:
            logging.error("Failed to get blade controller")
            return False

        print("\n===== BLADE MOTOR SPEED TEST =====")
        print("WARNING: The blade will spin during this test!")
        print("Make sure the mower is in a safe position.\n")
        input("Press Enter to start the test or Ctrl+C to cancel...")

        # Start with blade stopped
        blade_controller.set_speed(0)
        print("Blade motor stopped")
        time.sleep(1)

        # Test increasing speeds
        for i in range(1, speed_steps + 1):
            speed = i / speed_steps
            print(f"Setting blade speed to {speed * 100:.0f}%")
            blade_controller.set_speed(speed)
            time.sleep(run_time)

        # Test decreasing speeds
        for i in range(speed_steps, 0, -1):
            speed = i / speed_steps
            print(f"Setting blade speed to {speed * 100:.0f}%")
            blade_controller.set_speed(speed)
            time.sleep(run_time)

        # Stop the blade
        print("Stopping blade motor")
        blade_controller.set_speed(0)

        print("\nBlade motor test completed successfully.")
        return True

    except Exception as e:
        logging.error(f"Error during blade test: {e}")
        # Ensure blade is stopped
        try:
            blade_controller.set_speed(0)
        except BaseException:
            pass
        return False
    finally:
        # Always ensure blade is stopped when exiting
        try:
            blade_controller.set_speed(0)
        except BaseException:
            pass


def calibrate_blade_pwm(
    resource_manager: ResourceManager,
) -> Tuple[float, float]:
    """
    Calibrate the PWM values for the blade motor.

    This function allows the user to find the minimum PWM value that starts
    the blade spinning and the maximum safe PWM value.

    Args:
        resource_manager: An instance of ResourceManager.

    Returns:
        Tuple of (min_pwm, max_pwm) calibrated values.
    """
    try:
        blade_controller = resource_manager.get_blade_controller()
        if blade_controller is None:
            logging.error("Failed to get blade controller")
            return (0.0, 1.0)

        print("\n===== BLADE MOTOR PWM CALIBRATION =====")
        print("WARNING: The blade will spin during this calibration!")
        print("Make sure the mower is in a safe position.\n")
        print("This process will help determine the minimum PWM value")
        print("that starts the blade moving and the maximum safe value.")
        input("Press Enter to start the calibration or Ctrl+C to cancel...")

        # Start with blade stopped
        blade_controller.set_speed(0)
        print("Blade motor stopped")
        time.sleep(1)

        # Find minimum PWM
        print("\n--- Finding minimum PWM value ---")
        print("The PWM value will slowly increase until the blade starts " "moving.")
        input("Press Enter to begin...")

        min_pwm = 0.0
        step = 0.01

        while min_pwm < 0.5:  # Safety limit
            blade_controller.set_speed(min_pwm)
            print(f"Testing PWM value: {min_pwm:.2f}")
            time.sleep(0.5)

            response = input("Is the blade moving? (y/n/q to quit): ")
            if response.lower() == "y":
                print(f"Minimum PWM value found: {min_pwm:.2f}")
                break
            elif response.lower() == "q":
                break

            min_pwm += step

        # Stop the blade
        blade_controller.set_speed(0)
        time.sleep(1)

        # Find maximum PWM
        print("\n--- Finding maximum safe PWM value ---")
        print("The PWM value will be set to different values for testing.")
        print("Stop when the blade is spinning at maximum safe speed.")
        input("Press Enter to begin...")

        max_pwm = min_pwm + 0.1

        while max_pwm <= 1.0:
            blade_controller.set_speed(max_pwm)
            print(f"Testing PWM value: {max_pwm:.2f}")
            time.sleep(1)

            response = input("Is this the maximum safe speed? (y/n/q to quit): ")
            if response.lower() == "y":
                print(f"Maximum PWM value set: {max_pwm:.2f}")
                break
            elif response.lower() == "q":
                break

            max_pwm += 0.05
            if max_pwm > 1.0:
                max_pwm = 1.0

        # Stop the blade
        blade_controller.set_speed(0)

        print("\nCalibration completed.")
        print(f"Recommended PWM range: {min_pwm:.2f} to {max_pwm:.2f}")

        # Save to .env configuration if desired
        save = input("Save these values to configuration? (y/n): ")
        if save.lower() == "y":
            try:
                env_path = ".env"
                set_key(env_path, "BLADE_MIN_PWM", str(min_pwm))
                set_key(env_path, "BLADE_MAX_PWM", str(max_pwm))
                print(f"Values saved to {env_path}.")
            except Exception as save_error:
                logging.error(f"Failed to save calibration values: {save_error}")
        return (min_pwm, max_pwm)

    except Exception as e:
        logging.error(f"Error during blade calibration: {e}")
        return (0.0, 1.0)
    finally:
        # Always ensure blade is stopped when exiting
        try:
            blade_controller.set_speed(0)
        except BaseException:
            pass


def main():
    """
    Run the blade test module from the command line.

    Command-line options:
        --test: Run the speed test
        --calibrate: Run the PWM calibration
    """
    parser = argparse.ArgumentParser(description="Blade motor testing and calibration")
    parser.add_argument(
        "--test", action="store_true", help="Test blade at different speeds"
    )
    parser.add_argument(
        "--calibrate", action="store_true", help="Calibrate blade PWM values"
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=5,
        help="Number of speed steps for testing",
    )
    parser.add_argument(
        "--time",
        type=float,
        default=2.0,
        help="Time to run at each speed step",
    )

    args = parser.parse_args()

    # If no arguments, default to test
    if not (args.test or args.calibrate):
        args.test = True

    resource_manager = ResourceManager()

    if args.test:
        test_blade_speeds(resource_manager, args.steps, args.time)

    if args.calibrate:
        calibrate_blade_pwm(resource_manager)


if __name__ == "__main__":
    main()
