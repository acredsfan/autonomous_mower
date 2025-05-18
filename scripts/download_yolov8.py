#!/usr/bin/env python3
"""
YOLOv8 TFLite Model Setup Script for Autonomous Mower

This script now uses the local export process to generate a YOLOv8 TFLite model.
Direct download of YOLOv8 .tflite files is NOT supported by Ultralytics.
Instead, this script invokes the official export logic in
src/mower/obstacle_detection/yolov8_downloads.py, which:
  1. Downloads the YOLOv8 .pt model from Ultralytics.
  2. Converts it to TFLite using the Ultralytics export API.
  3. Saves the COCO label map.
  4. Updates the .env file.

Usage:
  python3 download_yolov8.py [--model yolov8n|yolov8s|yolov8m] [--output <output_dir>] [--imgsz 640] [--fp16|--int8] [--data <calibration_yaml>]

All arguments are passed through to the export script.

This change fixes the 404 error and ensures the model is always available in the correct format.
"""

import sys
import subprocess
import os


def main():
    # Build the command to invoke the export script
    script_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "src", "mower", "obstacle_detection", "yolov8_downloads.py"
    )
    script_path = os.path.normpath(script_path)

    # Pass through all CLI arguments
    cmd = [sys.executable, script_path] + sys.argv[1:]

    print("INFO: Invoking YOLOv8 export script:", " ".join(cmd))
    try:
        result = subprocess.run(cmd, check=True)
        sys.exit(result.returncode)
    except subprocess.CalledProcessError as e:
        print("ERROR: YOLOv8 export process failed with exit code", e.returncode)
        sys.exit(e.returncode)
    except Exception as e:
        print("ERROR: Unexpected error during YOLOv8 export:", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
