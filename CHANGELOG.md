# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased] - 2025-04-23
### Added
- Added `flask-babel` to `setup.py` install_requires for internationalization support.

### Fixed
- Resolved startup failure in `main_controller.py` by ensuring the `flask-babel` dependency is installed.
- Use global `get_config_manager()` in web_ui/app.py to avoid ResourceManager attribute error
- Suppress dotenv parse warnings in main_controller.py

### Changed
- Updated README.md service logs and camera diagnostics sections with expected outputs

## [2025-04-23] - 2025-04-23
- Initial project setup and CI pipeline
