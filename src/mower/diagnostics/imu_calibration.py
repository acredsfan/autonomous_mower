"""
IMU calibration module for the BNO085 sensor.

This module provides functionality to calibrate the BNO085 IMU sensor,
which is critical for accurate orientation tracking. It guides the user
through a step-by-step calibration process for the accelerometer,
gyroscope, and magnetometer.

The calibration process is interactive, with the module providing
clear instructions and feedback at each step. The resulting calibration
data is saved to persistent storage and can be loaded automatically
on system startup.

Calibration Importance:
- Accelerometer: Ensures accurate tilt and inclination measurements
- Gyroscope: Ensures accurate rotational velocity measurements
- Magnetometer: Ensures accurate heading (compass) information

Usage:
    python -m mower.diagnostics.imu_calibration

Or use the IMUCalibration class programmatically:
    calibrator = IMUCalibration()
    calibrator.start_calibration()
"""

import os
import time
import json
import threading

from pathlib import Path
from typing import Dict, Optional, Any

from mower.config_management.constants import CONFIG_DIR
from mower.utilities.logger_config import LoggerConfigInfo as LoggerConfig
from mower.main_controller import ResourceManager

# Initialize logger
logging = LoggerConfig.get_logger(__name__)


class IMUCalibration:
    """
    Handles the calibration process for the BNO085 IMU sensor.

    This class provides methods for guiding the user through the calibration
    process and saving the calibration data for future use. It supports both
    interactive terminal-based calibration and programmatic calibration via
    the web interface.

    The calibration process follows these steps:
    1. System calibration - general orientation calibration
    2. Gyroscope calibration - keep device still
    3. Accelerometer calibration - rotate through different orientations
    4. Magnetometer calibration - move in a figure-8 pattern

    Attributes:
        resource_manager: Reference to the system's ResourceManager
        imu: Reference to the IMU sensor
        calibration_data: Dictionary to store calibration values
        calibration_file: Path to the calibration data file
        calibration_in_progress: Flag indicating if calibration is active
    """

    def __init__(self, resource_manager: Optional[ResourceManager] = None):
        """
        Initialize the IMU calibration handler.

        Args:
            resource_manager: An instance of ResourceManager. If None,
            a new one will be created.
        """
        self.resource_manager = resource_manager or ResourceManager()
        self.imu = self.resource_manager.get_imu()
        self.calibration_data = {}

        # Set up calibration file path
        # CONFIG_DIR is imported from mower.config_management.constants
        # and should already point to project_root/config
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.calibration_file = CONFIG_DIR / "imu_calibration.json"

        # Initialize tracking variables
        self.calibration_in_progress = False
        self.calibration_thread = None
        self.current_step = ""
        self.current_status = "Not started"
        self.progress = 0
        self.step_callback = None
        self.completion_callback = None

        # Load existing calibration data if available
        self.load_calibration()

    def get_status(self) -> Dict[str, Any]:
        """
        Get the current calibration status.

        Returns:
            Dict containing calibration status information.
        """
        return {
            "in_progress": self.calibration_in_progress,
            "current_step": self.current_step,
            "status": self.current_status,
            "progress": self.progress,
            "calibrated": (
                self.imu.get_calibration_status() > 2 if self.imu else False
            ),
        }

    def load_calibration(self) -> bool:
        """
        Load calibration data from the saved file.

        This method loads previously saved calibration data and applies it to
        the IMU.

        Returns:
            bool: True if calibration data was successfully loaded and applied,
            False otherwise.
        """
        if not self.imu:
            logging.error("IMU not available, cannot load calibration")
            return False

        try:
            if not self.calibration_file.exists():
                logging.info(
                    "No calibration file found, using factory defaults"
                )
                return False

            # Load calibration data from file
            with open(self.calibration_file, "r") as f:
                self.calibration_data = json.load(f)

            # Apply calibration data to IMU
            if "calibration_matrix" in self.calibration_data:
                logging.info("Applying saved calibration data to IMU")
                calibration_matrix = self.calibration_data[
                    "calibration_matrix"
                ]

                # Apply calibration to the sensor
                success = self.imu.apply_calibration(calibration_matrix)
                if success:
                    logging.info("Calibration data applied successfully")
                    return True
                else:
                    logging.warning("Failed to apply calibration data")
                    return False
            else:
                logging.warning(
                    "Calibration file exists but doesn't contain valid data"
                )
                return False

        except Exception as e:
            logging.error(f"Error loading IMU calibration data: {e}")
            return False

    def save_calibration(self) -> bool:
        """
        Save current calibration data to a file.

        This method retrieves the current calibration from the IMU sensor
        and saves it to a JSON file for future use.

        Returns:
            bool: True if calibration was successfully saved, False otherwise.
        """
        if not self.imu:
            logging.error("IMU not available, cannot save calibration")
            return False

        try:
            # Get current calibration from IMU
            calibration_matrix = self.imu.get_calibration_matrix()
            if not calibration_matrix:
                logging.warning("Failed to get calibration matrix from IMU")
                return False

            # Store calibration data
            self.calibration_data = {
                "timestamp": time.time(),
                "calibration_matrix": calibration_matrix,
                "calibration_status": self.imu.get_calibration_status(),
            }

            # Save to file
            with open(self.calibration_file, "w") as f:
                json.dump(self.calibration_data, f, indent=2)

            logging.info(f"Calibration data saved to {self.calibration_file}")
            return True

        except Exception as e:
            logging.error(f"Error saving IMU calibration data: {e}")
            return False

    def start_calibration(
        self, step_callback=None, completion_callback=None
    ) -> bool:
        """
        Start the IMU calibration process.

        This method begins the calibration sequence in a separate thread,
        allowing it to be used interactively or programmatically.

        Args:
            step_callback: Optional callback function that will be called when
                          a calibration step changes, with status information.
            completion_callback: Optional callback function that will be called
                                when calibration completes, with success status

        Returns:
            bool: True if calibration started successfully, False otherwise.
        """
        if not self.imu:
            logging.error("IMU not available, cannot start calibration")
            if completion_callback:
                completion_callback(False, "IMU not available")
            return False

        if self.calibration_in_progress:
            logging.warning("Calibration already in progress")
            if completion_callback:
                completion_callback(False, "Calibration already in progress")
            return False

        try:
            # Store callbacks
            self.step_callback = step_callback
            self.completion_callback = completion_callback

            # Reset calibration status
            self.calibration_in_progress = True
            self.current_step = "Initializing"
            self.current_status = "Starting calibration"
            self.progress = 0

            # Notify of calibration start
            if self.step_callback:
                self.step_callback(self.get_status())

            # Start calibration thread
            self.calibration_thread = threading.Thread(
                target=self._calibration_process, daemon=True
            )
            self.calibration_thread.start()

            logging.info("IMU calibration started")
            return True

        except Exception as e:
            logging.error(f"Error starting IMU calibration: {e}")
            self.calibration_in_progress = False
            if completion_callback:
                completion_callback(
                    False,
                    f"Error starting calibration: {str(e)}",
                )
            return False

    def cancel_calibration(self) -> bool:
        """
        Cancel an ongoing calibration process.

        Returns:
            bool: True if calibration was successfully cancelled, False
            otherwise.
        """
        if not self.calibration_in_progress:
            return True

        try:
            self.calibration_in_progress = False
            if self.calibration_thread and self.calibration_thread.is_alive():
                # Let the thread terminate naturally by checking the flag
                self.calibration_thread.join(timeout=3.0)

            self.current_step = "Cancelled"
            self.current_status = "Calibration cancelled by user"

            if self.step_callback:
                self.step_callback(self.get_status())

            if self.completion_callback:
                self.completion_callback(False, "Calibration cancelled")

            logging.info("IMU calibration cancelled")
            return True

        except Exception as e:
            logging.error(f"Error cancelling IMU calibration: {e}")
            return False

    def _update_status(self, step: str, status: str, progress: int):
        """
        Update calibration status and notify callback if provided.

        Args:
            step: Current calibration step name
            status: Status message
            progress: Progress percentage (0-100)
        """
        self.current_step = step
        self.current_status = status
        self.progress = progress

        if self.step_callback:
            self.step_callback(self.get_status())

        logging.info(f"IMU Calibration - {step}: {status} ({progress}%)")

    def _calibration_process(self):
        """
        Run the full IMU calibration process.

        This method guides the user through all calibration steps
        and saves the final calibration data when complete.
        """
        success = False
        message = "Unknown error"

        try:
            # Reset IMU to ensure clean calibration
            self._update_status("Reset", "Resetting IMU sensor", 10)
            self.imu.reset()
            time.sleep(2)  # Allow time to reset

            # Step 1: System calibration
            self._update_status(
                "System", "Place the mower on a level surface", 20
            )
            self._wait_for_step_completion(10)

            if not self.calibration_in_progress:
                return  # Cancelled

            # Step 2: Gyroscope calibration
            self._update_status(
                "Gyroscope",
                "Keep the mower still for gyroscope calibration",
                30,
            )
            gyro_success = self._calibrate_gyroscope()

            if not self.calibration_in_progress:
                return  # Cancelled

            if not gyro_success:
                self._update_status(
                    "Failed", "Gyroscope calibration failed", 0
                )
                message = "Gyroscope calibration failed"
                success = False
                return

            # Step 3: Accelerometer calibration
            self._update_status(
                "Accelerometer",
                "Slowly rotate the mower through different orientations",
                50,
            )
            accel_success = self._calibrate_accelerometer()

            if not self.calibration_in_progress:
                return  # Cancelled

            if not accel_success:
                self._update_status(
                    "Failed", "Accelerometer calibration failed", 0
                )
                message = "Accelerometer calibration failed"
                success = False
                return

            # Step 4: Magnetometer calibration
            self._update_status(
                "Magnetometer", "Move the mower in a figure-8 pattern", 70
            )
            mag_success = self._calibrate_magnetometer()

            if not self.calibration_in_progress:
                return  # Cancelled

            if not mag_success:
                self._update_status(
                    "Failed", "Magnetometer calibration failed", 0
                )
                message = "Magnetometer calibration failed"
                success = False
                return

            # Save calibration
            self._update_status("Saving", "Saving calibration data", 90)
            save_success = self.save_calibration()

            if not save_success:
                self._update_status(
                    "Failed", "Failed to save calibration data", 0
                )
                message = "Failed to save calibration data"
                success = False
                return

            # Calibration complete
            self._update_status(
                "Complete", "Calibration completed successfully", 100
            )
            success = True
            message = "Calibration completed successfully"

        except Exception as e:
            logging.error(f"Error during IMU calibration: {e}")
            self._update_status("Error", f"Calibration error: {str(e)}", 0)
            success = False
            message = f"Calibration error: {str(e)}"

        finally:
            self.calibration_in_progress = False
            if self.completion_callback:
                self.completion_callback(success, message)

    def _wait_for_step_completion(self, seconds: int):
        """
        Wait for a specified number of seconds while checking for cancellation.

        Args:
            seconds: Number of seconds to wait
        """
        for i in range(seconds):
            if not self.calibration_in_progress:
                return False
            time.sleep(1)
        return True

    def _calibrate_gyroscope(self) -> bool:
        """
        Calibrate the gyroscope.

        Returns:
            bool: True if calibration was successful, False otherwise.
        """
        start_time = time.time()
        timeout = 30  # seconds

        # Monitor gyroscope calibration
        while time.time() - start_time < timeout:
            if not self.calibration_in_progress:
                return False  # Cancelled

            # Check calibration status
            gyro_status = self.imu.get_gyro_calibration_status()
            progress = min(
                100, int((time.time() - start_time) / timeout * 100)
            )

            self._update_status(
                "Gyroscope",
                f"Gyroscope calibration: Level {gyro_status} of 3",
                30 + int(progress / 5),
            )

            if gyro_status >= 3:
                return True

            time.sleep(1)

        return False

    def _calibrate_accelerometer(self) -> bool:
        """
        Calibrate the accelerometer by guiding the user through different
        orientations.

        Returns:
            bool: True if calibration was successful, False otherwise.
        """
        orientations = [
            "Place mower upright on a level surface",
            "Place mower on its left side",
            "Place mower on its right side",
            "Place mower upside down",
            "Place mower on its front",
            "Place mower on its back",
        ]

        for i, instruction in enumerate(orientations):
            progress = 50 + int((i / len(orientations)) * 20)
            self._update_status("Accelerometer", instruction, progress)

            # Wait for orientation change
            if not self._wait_for_step_completion(8):
                return False  # Cancelled

            # Check calibration status
            accel_status = self.imu.get_accel_calibration_status()
            self._update_status(
                "Accelerometer",
                f"Accelerometer calibration: Level {accel_status} of 3",
                progress,
            )

            if accel_status >= 3:
                return True

        # Final check
        accel_status = self.imu.get_accel_calibration_status()
        return accel_status >= 3

    def _calibrate_magnetometer(self) -> bool:
        """
        Calibrate the magnetometer by guiding the user through a figure-8
        pattern.

        Returns:
            bool: True if calibration was successful, False otherwise.
        """
        start_time = time.time()
        timeout = 60  # seconds

        self._update_status(
            "Magnetometer", "Move the mower in a figure-8 pattern", 70
        )

        # Monitor magnetometer calibration
        while time.time() - start_time < timeout:
            if not self.calibration_in_progress:
                return False  # Cancelled

            # Check calibration status
            mag_status = self.imu.get_mag_calibration_status()
            progress = min(
                100, int((time.time() - start_time) / timeout * 100)
            )

            self._update_status(
                "Magnetometer",
                f"Magnetometer calibration: Level {mag_status} of 3",
                70 + int(progress / 5),
            )

            if mag_status >= 3:
                return True

            time.sleep(1)

        # Final check
        mag_status = self.imu.get_mag_calibration_status()
        return mag_status >= 3


def main():
    """
    Run the IMU calibration process from the command line.
    """
    print("\n===== BNO085 IMU CALIBRATION TOOL =====\n")
    print("This tool will guide you through the process of calibrating")
    print("the IMU sensor for accurate orientation tracking.\n")

    # Create resource manager
    resource_manager = ResourceManager()

    # Initialize IMU
    if not resource_manager.init_imu():
        print("Error: Failed to initialize IMU. Please check connections.")
        return

    # Create calibration handler
    calibrator = IMUCalibration(resource_manager)

    # Check if already calibrated
    imu = resource_manager.get_imu()
    if imu and imu.get_calibration_status() >= 3:
        print("IMU appears to already be well calibrated.")
        choice = input("Do you want to recalibrate anyway? (y/n): ")
        if choice.lower() != "y":
            print("Exiting without recalibration.")
            return

    print("\nStarting IMU calibration process...")
    print("Follow the instructions for each step.\n")

    # Define simple terminal callback
    def status_callback(status):
        print(
            f"\n{status['current_step']}: {status['status']} ({status['progress']}%)"
        )

    def completion_callback(success, message):
        if success:
            print("\n✓ IMU calibration completed successfully!")
        else:
            print(f"\n✗ IMU calibration failed: {message}")

    # Start calibration
    calibrator.start_calibration(status_callback, completion_callback)

    # Wait for completion
    try:
        while calibrator.calibration_in_progress:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nCalibration cancelled by user.")
        calibrator.cancel_calibration()

    print("\nIMU calibration process complete.")

    # Check final calibration status
    if imu and imu.get_calibration_status() >= 3:
        print("IMU is now well calibrated.")
    else:
        print("IMU may need additional calibration.")

    print("\nExiting calibration tool.")


if __name__ == "__main__":
    main()
