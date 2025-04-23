# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased] - 2025-04-23
### Added
- Added `flask-babel` to `setup.py` install_requires for internationalization support.

### Fixed
- Resolved startup failure in `main_controller.py` by ensuring the `flask-babel` dependency is installed.
