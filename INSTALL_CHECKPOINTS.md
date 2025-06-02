# Install Requirements Script - Checkpoint/Resume Functionality

## Overview

The `install_requirements.sh` script now supports checkpoint/resume functionality, allowing you to continue where you left off if the installation is interrupted or if you want to skip already completed sections when re-running the script.

## Features

### Checkpoint System

- **Automatic State Tracking**: The script creates a `.install_checkpoints` file to track completed installation steps
- **Resume Support**: When re-running the script, it detects previous installations and offers to skip completed steps
- **Smart Detection**: Automatically detects already completed installations (e.g., existing virtual environment, installed packages)
- **User Control**: Prompts allow you to choose whether to skip or re-run completed steps

### Tracked Installation Steps

The following major installation steps are tracked:

1. **virtual_environment** - Python virtual environment creation
2. **hardware_interfaces** - I2C and UART interface configuration
3. **additional_uart** - Additional UART2 setup
4. **system_packages** - APT package installation
5. **pythonpath_setup** - PYTHONPATH configuration in .bashrc
6. **python_dependencies** - Python package installation via pip
7. **yolov8_setup** - YOLOv8 model installation and configuration
8. **coral_tpu_setup** - Coral TPU support installation
9. **hardware_watchdog** - Hardware watchdog configuration
10. **emergency_stop** - Emergency stop button setup
11. **emergency_stop_skip** - Emergency stop button disable
12. **systemd_service** - Systemd service installation

### How to Use

#### Fresh Installation

```bash
./install_requirements.sh
```

#### Resume Installation

If you run the script again after a previous attempt:

1. The script will detect the existing checkpoint file
2. It will show you which steps were previously completed
3. You can choose to:
   - **Reset and start fresh**: Removes all checkpoints and starts over
   - **Resume**: Skip completed steps and continue from where you left off

#### Example Output

```
INFO: Previous installation found. This script supports checkpoint/resume functionality.

INFO: Previously completed installation steps:
  ✓ virtual_environment (completed: 2025-05-30 10:15:23)
  ✓ hardware_interfaces (completed: 2025-05-30 10:16:45)
  ✓ system_packages (completed: 2025-05-30 10:18:12)

Do you want to reset all checkpoints and start fresh? (y/N)
```

#### Smart Step Detection

The script automatically detects completed installations:

- **Virtual Environment**: Checks for existing `.venv` directory with Python executable
- **Python Dependencies**: Checks for installed packages in virtual environment
- **System Packages**: Checks for key installed packages like `i2c-tools`, `gpsd`
- **PYTHONPATH**: Checks for configuration in `/home/pi/.bashrc`
- **YOLOv8 Models**: Checks for model files in `models/` directory
- **Coral TPU**: Checks for repository and `pycoral` package
- **Watchdog**: Checks for enabled systemd service and configuration
- **Systemd Service**: Checks for enabled `autonomous-mower` service

### Step-by-Step Prompts

For each installation step, if already completed, you'll see:

```
INFO: Virtual environment setup appears to be already completed (completed: 2025-05-30 10:15:23)
Skip this step? (Y/n)
```

- Press **Enter** or **Y** to skip the step
- Press **N** to re-run the step anyway

### Benefits

1. **Time Saving**: Skip lengthy operations that are already complete
2. **Reliability**: Safely resume after interruptions or failures
3. **Development Friendly**: Easily re-run specific parts during development/testing
4. **Error Recovery**: If one step fails, fix the issue and resume without starting over
5. **Selective Re-installation**: Choose to re-run only specific components

### Checkpoint File Management

- **Location**: `.install_checkpoints` in the project root directory
- **Format**: Simple text file with `step_name=timestamp` entries
- **Cleanup**: Automatically archived to `.install_checkpoints.completed.YYYYMMDD_HHMMSS` on successful completion
- **Manual Reset**: Delete `.install_checkpoints` file to start fresh

### Advanced Usage

#### Manual Checkpoint Reset

```bash
rm .install_checkpoints
./install_requirements.sh
```

#### Check Current Status

```bash
cat .install_checkpoints
```

#### View Archived Completions

```bash
ls -la .install_checkpoints.completed.*
```

## Safety and Reliability

- **Non-Destructive**: Skipping steps won't break existing installations
- **User Confirmation**: Always prompts before skipping important steps
- **Graceful Fallback**: If detection fails, defaults to re-running steps
- **Audit Trail**: Maintains timestamps of when each step was completed

This checkpoint system makes the autonomous mower installation process much more robust and user-friendly, especially during development and troubleshooting scenarios.
