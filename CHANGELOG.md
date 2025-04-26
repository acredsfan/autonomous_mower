# Changelog

All notable changes to this project will be documented in this file.

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
