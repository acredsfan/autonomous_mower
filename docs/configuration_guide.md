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

### Weather API Configuration

The Autonomous Mower utilizes the Google Maps Platform Weather API to fetch weather forecasts. This information is crucial for weather-dependent scheduling features, allowing the mower to adjust its operations based on current and predicted weather conditions (e.g., avoiding mowing during rain).

**Obtaining a Google Weather API Key:**

To use the weather features, you need to obtain an API key from the Google Cloud Console and enable the Weather API.

1.  **Navigate to Google Cloud Console:** Go to [console.cloud.google.com](https://console.cloud.google.com).
2.  **Project Selection:**
    - Create a new project if you don't have one already.
    - Or, select an existing project.
3.  **Enable the Weather API:**
    - In the navigation menu, go to "APIs & Services" > "Library".
    - Search for "Weather API" (it's part of the Google Maps Platform).
    - Select the "Weather API" from the search results and click "Enable".
    - You may also need to ensure a billing account is associated with your project, as Google Cloud services, including the Weather API, require it.
4.  **Create API Credentials:**
    - Go to "APIs & Services" > "Credentials".
    - Click "+ CREATE CREDENTIALS" and select "API key".
    - Your new API key will be displayed. Copy it securely.
5.  **Restrict Your API Key (Highly Recommended for Security):**
    - In the API key list, click on the name of your newly created key (or the pencil icon to edit it).
    - Under "API restrictions":
      - Select "Restrict key".
      - From the dropdown, select "Weather API". If you use this key for other Google services, ensure they are also selected.
    - Under "Application restrictions" (optional but recommended):
      - Consider restricting by IP addresses if your mower has a static public IP or if you access it through a known static IP.
      - Other restriction types might be less applicable for a mower application but review them based on your setup.
    - Click "Save".

**Setting the Environment Variable:**

Once you have your API key, you need to set it in the mower's environment.

- Open or create a `.env` file in the root directory of the project.
- Add the following line, replacing `YOUR_GOOGLE_WEATHER_API_KEY_HERE` with the actual key you obtained:
  ```
  GOOGLE_WEATHER_API_KEY=YOUR_GOOGLE_WEATHER_API_KEY_HERE
  ```
- Refer to the `.env.example` file for the exact variable name and format.

**Important Considerations:**

- **Google Cloud Pricing:** The Weather API is a service provided by Google Cloud. While it may have a free tier, usage beyond that is subject to Google's pricing model. Be sure to review the pricing details for the Weather API on the Google Cloud Platform website. The API might also be in a "Preview" stage, which can have specific terms and conditions.
- **API Key Security:** Protect your API key. Do not commit it directly into your version control system (e.g., Git). The `.env` file is typically included in `.gitignore` to prevent accidental exposure.

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

## ToF Ground‑Plane Cutoff

To prevent false drop‑off alarms with angled front ToF sensors, define per‑sensor ground‑plane cutoff distances (cm) in your `.env`:

```ini
TOF_GROUND_CUTOFF_LEFT=<calibrated left sensor cutoff cm>
TOF_GROUND_CUTOFF_RIGHT=<calibrated right sensor cutoff cm>
```

These values are used by the drop‑off detector to distinguish real cliffs from angled ground readings.

Use the **Calibrate ToF** button on the WebUI Diagnostics page to automatically measure and store these values when the mower is on a flat surface.

## Changing Configuration

### During Installation

The installation script (`install_requirements.sh`) will guide you through configuring essential settings, including whether to use a physical emergency stop button. The script supports both interactive mode (default) and non-interactive mode (`-y` flag) for automated installations.

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
