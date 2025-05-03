# Task List for Autonomous Mower Deployment

## 1. Complete and Fix Incomplete Logic

- [ ] Implement blade calibration value persistence in `blade_test.py`.
- [ ] Add `set_speed` method in `BladeController`.
- [ ] Implement cliff/drop-off detection in obstacle avoidance module.
- [ ] Add YOLOv8 Non-Max Suppression (NMS) in obstacle detection module.
- [ ] Ensure wheel encoder data sent from RoboHAT RP2040 is properly received and utilized by Raspberry Pi for odometry and navigation.

## 2. Enhance Modularity

- [ ] Consolidate sensor initialization logic to use only `EnhancedSensorInterface`. Remove duplicate sensor initialization from `ResourceManager`.
- [ ] Refactor GPIO pin assignments (blade motor, etc.) to be configurable via `.env` or another centralized config file.

## 3. Update and Improve Documentation

- [ ] Explicitly document enabling Raspberry Pi interfaces (I2C and secondary UART) in `hardware_setup.md`.
- [ ] Add a clear, step-by-step "Using the Mower" section in `README.md`.
- [ ] Clearly document and recommend usage of `setup_wizard.py` for initial configuration.
- [ ] Include wiring diagrams and sensor-pin mappings clearly in main documentation.

## 4. Simplify Setup & Improve User Experience

- [ ] Create a single-command installation script (`curl/bash`) to automate full setup on Raspberry Pi OS Bookworm.
- [ ] Ensure `setup_wizard.py` fully configures `.env` file interactively, prompting for necessary user inputs.
- [ ] Enhance Web UI to include basic configuration capabilities, minimizing SSH necessity.
- [ ] Implement startup self-test logic with clear, user-friendly logging indicating sensor health status.

## 5. Implement Safety and Stability Measures

- [ ] Monitor GPIO for emergency stop signal (GPIO7), integrating immediate motor/blade stop.
- [ ] Ensure system watchdog is actively monitored and "pet" regularly to handle software hangs/crashes.
- [ ] Define and implement clear behavior if critical sensors fail or become unresponsive.
- [ ] Enforce battery and motor current safety thresholds, stopping mower or triggering safe behaviors as needed.
- [ ] Implement failsafe behaviors for connectivity loss (WiFi/WebUI).
- [ ] Enhance logging and UI notifications to clearly communicate critical system/safety states to users in real-time.
