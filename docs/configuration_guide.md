# Configuration Guide

This guide provides information on configuring various aspects of the Autonomous Mower system.

## Configuration System

The Autonomous Mower uses a centralized configuration system that allows you to customize various aspects of the mower's operation. Configuration settings are stored in JSON format and can be modified through the setup wizard or directly in the configuration files.

## Core Configuration Options

### Safety Settings

Safety settings control critical safety features of the mower.

```json
{
  "safety": {
    "use_physical_emergency_stop": true, // Whether a physical emergency stop button is installed
    "emergency_stop_pin": 7, // GPIO pin connected to the emergency stop button
    "watchdog_timeout": 15, // Watchdog timeout in seconds
    "tilt_threshold_degrees": 30, // Maximum safe tilt angle in degrees
    "vibration_threshold": 2.5, // Maximum safe vibration level
    "collision_detection_enabled": true, // Enable/disable collision detection
    "perimeter_check_interval": 5 // How often to check perimeter in seconds
  }
}
```

#### Emergency Stop Configuration

The emergency stop button provides a critical safety feature for immediately stopping all mower operations.

**Physical Emergency Stop Button:**

- Set `safety.use_physical_emergency_stop` to `true` if a physical button is installed
- The physical button should be connected to the pin specified in `safety.emergency_stop_pin` (default: GPIO7)
- The button should be normally closed (NC) for fail-safe operation

**Software-Only Emergency Stop:**

- Set `safety.use_physical_emergency_stop` to `false` if no physical button is installed
- The system will operate without checking for a physical button
- Emergency stop functionality is still available through the web interface
- A warning message will be displayed during startup

To modify this setting during installation, answer "n" when prompted to set up the physical emergency stop button. To modify it after installation, edit the configuration file directly or use the web interface configuration panel.

### Motor Settings

```json
{
  "motors": {
    "left_motor_pin": 22,
    "right_motor_pin": 23,
    "max_speed": 100,
    "acceleration": 0.5,
    "blade_speed": 80
  }
}
```

### Sensor Settings

```json
{
  "sensors": {
    "gps_enabled": true,
    "gps_port": "/dev/ttyACM0",
    "imu_enabled": true,
    "imu_port": "/dev/ttyAMA2",
    "tof_enabled": true,
    "lidar_enabled": false
  }
}
```

## Changing Configuration

### During Installation

The installation script (`install_requirements.sh`) will guide you through configuring essential settings, including whether to use a physical emergency stop button.

### Using the Setup Wizard

The setup wizard (`setup_wizard.py`) provides an interactive interface for changing configuration settings:

```bash
python3 setup_wizard.py
```

### Modifying Configuration Files Directly

Configuration settings are stored in JSON files in the `config` directory. You can edit these files directly:

1. Navigate to the `config` directory:

   ```bash
   cd config
   ```

2. Edit the appropriate configuration file using a text editor:

   ```bash
   nano main_config.json
   ```

3. After making changes, restart the mower service:
   ```bash
   sudo systemctl restart mower
   ```

### Through the Web Interface

Some configuration settings can be changed through the web interface:

1. Navigate to the Settings page
2. Modify the desired settings
3. Click Save to apply the changes

## Verifying Configuration

To verify that your configuration has been applied correctly:

1. Check the startup logs:

   ```bash
   sudo journalctl -u mower -n 100
   ```

2. Look for configuration-related messages, including any warnings about the emergency stop button configuration

3. Test the functionality to ensure it behaves as expected
