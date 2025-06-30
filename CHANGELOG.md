# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased] - 2025-05-30

### Added

- **Enhanced YOLOv8 Setup Script with Existing Model Detection:**
  - Added smart model detection in `scripts/setup_yolov8.py` to scan for existing `.tflite` models and label files
  - Implemented user-friendly model selection interface with file size and modification date display
  - Added options to use existing models, download new ones, or exit during setup
  - Created functions: `scan_existing_models()`, `scan_existing_labels()`, `display_existing_models()`, `prompt_use_existing()`, `prompt_select_existing_model()`, `use_existing_model()`
  - Enhanced file size formatting with human-readable units (B, KB, MB, GB)
  - Integrated existing model detection into main workflow to save bandwidth and time
  - Updated environment variable naming to `YOLOV8_MODEL_PATH` and `YOLO_LABEL_PATH` for consistency

### Changed

- Updated README.md documentation to reflect new model detection capabilities and updated environment variable names

## [Unreleased] - 2025-04-25

### Added

- Added `flask-babel` to `setup.py` install_requires for internationalization support.

### Fixed

- Resolved startup failure in `main_controller.py` by ensuring the `flask-babel` dependency is installed.
- Use global `get_config_manager()` in web_ui/app.py to avoid ResourceManager attribute error
- Suppress dotenv parse warnings in main_controller.py
- Added system dependencies (`python3-smbus`, `i2c-tools`, `python3-blinka`, `libgpiod2`) to `Dockerfile` for Raspberry Pi compatibility.
- Installed `adafruit-blinka` in `Dockerfile` to support CircuitPython libraries on Raspberry Pi.
- Updated Dockerfile to improve Raspberry Pi 4B support by adding I2C and GPIO tools.

### Changed

- Updated README.md service logs and camera diagnostics sections with expected outputs

## [2025-04-26] - 2025-04-26

### Fixed

- 2025-04-26: [#safe-polygon-labelmap-tflite-patternconfig] Implemented the following robustness and config fixes:

  - Safe polygon loading in constants.py (always a list, never None)
  - Label map path fallback in obstacle_detector.py (.env LABELMAP_PATH, fallback to models/imagenet_labels.txt)
  - Guarded TFLite Interpreter loading in obstacle_detector.py (logs warning, never crashes on missing model)
  - Injected pattern_config from config_manager into PathPlanner
  - Removed duplicate Web-UI startup in run_robot()
  - Guarded avoidance_algorithm.stop() against None in run_robot()

  All changes follow PEP8, are modular, and documented. See commit for details.

## [2025-04-23] - 2025-04-23

- Initial project setup and CI pipeline
