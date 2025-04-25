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

## [2025-04-23] - 2025-04-23
- Initial project setup and CI pipeline
