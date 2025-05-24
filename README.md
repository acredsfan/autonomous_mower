# Autonomous Lawn Mower

An autonomous lawn mower system built for Raspberry Pi, featuring advanced navigation, obstacle detection, and safety features.

## Features

- Real-time obstacle detection using computer vision
- GPS-based navigation and boundary mapping
- Remote control via web interface
- Weather-aware scheduling
- Safety features and emergency stop
- Support for Google Coral Edge TPU acceleration
- Support for YOLOv8 object detection models
- Remote monitoring and control
- Multiple remote access options (DDNS, Cloudflare, NGROK)
- Automatic startup on boot via systemd service
- Hardware watchdog for system reliability
- Emergency stop button support

## Prerequisites

- Raspberry Pi 4B (4GB RAM or better recommended) or Raspberry Pi 5.
- Python 3.10 or newer.
- Raspberry Pi OS (Bookworm or newer, 64-bit recommended).
- High-quality SD card (Class A2 recommended for performance).
- Camera module (Raspberry Pi Camera Module v2 or v3 recommended).
- RoboHAT MM1 Motor Controller (or compatible PWM driver).
- GPS Module (e.g., U-blox ZED-F9P for RTK, or a standard high-precision GPS).
- IMU Sensor (e.g., BNO085).
- Emergency stop button (physical button is optional but recommended).
- Optional: Google Coral USB Accelerator for enhanced object detection performance.

## Setup Guide

This guide provides comprehensive steps to set up your autonomous mower. You can choose between a detailed manual setup for more control or a more automated script-based installation.

### 1. Initial System Preparation

**A. Flash Raspberry Pi OS:**
   - Download the latest Raspberry Pi OS (Bookworm, 64-bit recommended) from the official website.
   - Use Raspberry Pi Imager to flash the OS onto your SD card.
   - Perform initial boot and complete the setup wizard (user, WiFi, etc.).

**B. System Update:**
   - Open a terminal on your Raspberry Pi.
   - Update your system packages:
     ```bash
     sudo apt update
     sudo apt full-upgrade -y
     sudo reboot
     ```

**C. Clone Repository:**
   ```bash
   git clone https://github.com/acredsfan/autonomous_mower.git
   cd autonomous_mower
   ```

### 2. Detailed Manual Setup

This section walks you through each step of the setup process. If you prefer a more automated approach, see the "Automated Installation Script" section below.

#### A. System-Level Dependencies

These packages are required for hardware communication, building Python packages, and running various components of the mower.

You can install them manually by running the commands listed in the `scripts/rpi_system_dependencies.sh` script, or execute the script directly:

1.  Ensure the script is available at `scripts/rpi_system_dependencies.sh`. (The content of this script is maintained in the repository).
2.  Make it executable:
    ```bash
    chmod +x scripts/rpi_system_dependencies.sh
    ```
3.  Run the script:
    ```bash
    sudo ./scripts/rpi_system_dependencies.sh
    ```
    This script will:
    *   Install libraries for I2C, GPIO, and serial communication.
    *   Set up dependencies for the Picamera2 stack.
    *   Install OpenCV dependencies.
    *   Add the Coral package repository and install `libedgetpu1-std` (if you plan to use a Coral accelerator).
    *   Install common Python build tools (`build-essential`, `python3-dev`, etc.).

#### B. Raspberry Pi Configuration (`raspi-config`)

Configure your Raspberry Pi's hardware interfaces using the `raspi-config` tool:

```bash
sudo raspi-config
```

Navigate using arrow keys and Enter. Enable the following under `3 Interface Options`:

1.  **I1 Camera:** Select `<Yes>` to enable the camera.
2.  **I4 SPI:** Select `<Yes>` to enable SPI.
3.  **I5 I2C:** Select `<Yes>` to enable I2C.
4.  **I6 Serial Port:**
    *   "Would you like a login shell to be accessible over serial?" -> Select `<No>`.
    *   "Would you like the serial port hardware to be enabled?" -> Select `<Yes>`.

After enabling interfaces, select `<Finish>` and reboot if prompted.

**Serial Port Considerations:**
*   The Raspberry Pi has multiple UARTs (e.g., `/dev/ttyAMA0`, `/dev/ttyS0`). Disabling the serial login shell typically makes `/dev/ttyAMA0` (the primary UART) available for peripherals.
*   `/dev/serial0` and `/dev/serial1` are symbolic links that provide stable names.
*   For GPS, `/dev/ttyAMA0` (often aliased to `serial0` or `serial1` depending on Pi model and Bluetooth status) is generally recommended.
*   Check available ports with `ls -l /dev/ttyS0 /dev/ttyAMA* /dev/serial*`.
*   If using a Pi with Bluetooth (Pi 3/4/5), you might need to add `dtoverlay=disable-bt` or `dtoverlay=miniuart-bt` to `/boot/config.txt` (or `/boot/firmware/config.txt` on newer OS versions) to ensure `/dev/ttyAMA0` is free for other uses. Consult Raspberry Pi documentation for details.

#### C. User Group Management

To access hardware interfaces without `sudo`, add your user (e.g., `pi`) to these groups:

```bash
sudo usermod -a -G gpio $USER
sudo usermod -a -G i2c $USER
sudo usermod -a -G dialout $USER  # For serial port access
sudo usermod -a -G video $USER   # For camera access
# sudo usermod -a -G spi $USER   # If spidev is not accessible
```
**Important:** Log out and log back in, or reboot, for group changes to take effect:
```bash
sudo reboot
```

#### D. Python Environment Setup

**Python Version:**
Ensure you have Python 3.10 or newer:
```bash
python3 --version
```

**Virtual Environment (Recommended):**
A virtual environment isolates project dependencies.

1.  Install `python3-venv` if not present:
    ```bash
    sudo apt-get install python3-venv -y
    ```
2.  Navigate to the project root (`autonomous_mower`) and create a virtual environment (e.g., named `.venv`):
    ```bash
    python3 -m venv .venv
    ```
3.  Activate the virtual environment:
    ```bash
    source .venv/bin/activate
    ```
    Your terminal prompt should now show `(.venv)`.

**Install Python Dependencies:**
With the virtual environment activated, install packages from `requirements.txt`:
```bash
pip install -r requirements.txt
```
If you encounter errors during installation, ensure system-level build tools (from step 2A) are installed. Check `pip` error logs for missing `-dev` packages.

#### E. Environment Variable Configuration (`.env` file)

The application uses a `.env` file for configuration.

1.  Create your `.env` file by copying the example:
    ```bash
    cp .env.example .env
    ```
2.  Open `.env` with a text editor and customize the settings. **Critical variables include:**
    *   `MM1_SERIAL_PORT`: Serial port for the RoboHAT MM1 motor controller (e.g., `/dev/ttyS0`, `/dev/ttyAMA0`, `/dev/ttyACM0`). Ensure this port is not used by other services (console, Bluetooth).
    *   `GPS_SERIAL_PORT`: Serial port for your GPS module.
    *   `GPS_BAUD_RATE`: Baud rate for your GPS module (e.g., 9600, 115200). Must match module's configuration.
    *   `IMU_SERIAL_PORT`: Serial port for your IMU if it uses serial (e.g., BNO085).
    *   `USE_CAMERA`: Set to `True` to enable camera.
    *   `CAMERA_INDEX`: Usually `0` for the default Raspberry Pi camera.
    *   `USE_SIMULATION`: **Must be `False`** for hardware operation.
    *   `LOG_LEVEL`: `INFO` or `DEBUG` for troubleshooting.
    *   `ENABLE_WEB_UI`: `True` to enable the web interface.

    Refer to the comments in `.env.example` and the `environment_variable_setup.md` document for detailed explanations of all variables.

### 3. Automated Installation Script (`install_requirements.sh`)

Alternatively, the project provides an `install_requirements.sh` script for a more automated setup.

**Note:**
*   This script attempts to install system dependencies and Python packages **system-wide**.
*   If you prefer using a Python virtual environment (as described in the manual setup), install Python packages manually using `pip install -r requirements.txt` within your activated environment *after* running the system dependency parts of the manual setup.
*   The script may also try to configure some hardware interfaces.

To use the script:
```bash
# Make the script executable
chmod +x install_requirements.sh

# Run the installation script with sudo
sudo ./install_requirements.sh
```
The script will guide you through some installation choices.

### 4. Create Log Directory and Set Permissions

This step is crucial for the application and its systemd service to log correctly. (The `install_requirements.sh` script might also attempt this).

```bash
# Create log directory
sudo mkdir -p /var/log/autonomous-mower

# Set ownership to the user the service will run as (default 'pi')
sudo chown -R pi:pi /var/log/autonomous-mower

# Set correct permissions
sudo chmod 755 /var/log/autonomous-mower
```

### 5. Pre-flight Check (Recommended)

After setup, run the pre-flight checker script to diagnose common issues:
```bash
python3 scripts/preflight_checker.py
```
This script checks Python version, `.env` file, user groups, hardware interfaces, critical libraries, and optionally probes I2C devices. Review its output for any FAIL or NOT FOUND messages.

## Hardware Setup Details

Ensure all hardware components are correctly connected and configured in your `.env` file.

1.  **Camera Module:**
    *   Connect to the CSI port.
    *   Should be enabled via `raspi-config` (covered in manual setup).
    *   Test with `libcamera-hello -t 2000`.

2.  **RoboHAT MM1 Motor Controller:**
    *   Connect securely to the Raspberry Pi's GPIO headers or via its specified interface.
    *   Ensure `MM1_SERIAL_PORT` in your `.env` file is set to the correct serial port (e.g., `/dev/ttyS0`, `/dev/ttyAMA0`, or `/dev/ttyACM0` if USB).
    *   The port must be exclusively available for the RoboHAT. Check for conflicts with the serial console or Bluetooth.
    *   User must be in the `dialout` group.
    *   Ensure the HAT and motors are adequately powered.

3.  **GPS Module:**
    *   Connect to appropriate UART pins (e.g., GPIO 14/TX, GPIO 15/RX for `/dev/ttyAMA0`).
    *   Ensure `GPS_SERIAL_PORT` and `GPS_BAUD_RATE` in `.env` match your module's connection and configuration.
    *   Serial port should be enabled and configured in `raspi-config` (covered).

4.  **IMU Sensor (e.g., BNO085):**
    *   **I2C Connection (Common for BNO085):** Connect to the I2C pins (SDA, SCL). I2C should be enabled in `raspi-config`.
    *   **Serial Connection:** If your IMU uses serial, connect to appropriate UART pins. Ensure `IMU_SERIAL_PORT` in `.env` is correctly set.
    *   Verify connection with `i2cdetect -y 1` (for I2C) or check serial port.

5.  **Emergency Stop Button (Optional but Recommended):**
    *   Connect between GPIO7 (or configured pin) and GND.
    *   Typically a Normally Closed (NC) button.
    *   Can be enabled/disabled via `safety.use_physical_emergency_stop` in your config (or corresponding `.env` variable if available).

## YOLOv8 Model Download and Conversion

For effective obstacle detection, a TFLite model is required. Due to TensorFlow's export limitations on Raspberry Pi OS Bookworm (Python 3.11+), you **must export YOLOv8 models to TFLite format on a supported PC** (Linux/Windows, Python 3.9 or 3.10), then copy them to your Pi.

### Steps:

1.  **Export on a Supported PC:**
    *   Install `ultralytics` and `tensorflow==2.14.*` (or a compatible version).
    *   Download a YOLOv8 PyTorch model (e.g., `yolov8n.pt`).
    *   Export: `yolo export model=yolov8n.pt format=tflite imgsz=640 nms=False`
    *   This creates a `_float32.tflite` model.

2.  **Copy to Raspberry Pi:**
    *   Place the `.tflite` model in the `models/` directory of your mower project.
    *   Download and place the corresponding label map (e.g., `coco_labels.txt`) in the same `models/` directory.
      *   Example: `wget https://raw.githubusercontent.com/google-coral/test_data/master/coco_labels.txt -O models/coco_labels.txt`

3.  **Update `.env` File:**
    ```
    YOLO_MODEL_PATH=models/yolov8n_float32.tflite # Or your model name
    YOLO_LABEL_PATH=models/coco_labels.txt
    USE_YOLOV8=True
    ```

4.  **Google Colab for Export (Alternative):**
    If you lack a suitable PC, use Google Colab:
    ```python
    # In a Colab Notebook
    !pip install ultralytics tensorflow==2.14.* flatbuffers==23.*
    from ultralytics import YOLO
    model = YOLO('yolov8n.pt') # Downloads .pt file
    model.export(format='tflite', imgsz=640, nms=False)
    # Download the .tflite file from Colab's file browser
    ```
    Also, download/create and download `coco_labels.txt`.

Refer to the "Object Detection Setup" and "YOLOv8 Model Download" sections further down for more details if needed (some of this is repeated from the original README for now and can be consolidated).

## Running the Mower

### Starting the Service

The application is designed to run as a systemd service. The `install_requirements.sh` script attempts to set this up.

```bash
# Start the service
sudo systemctl start autonomous-mower

# Enable service to start on boot
sudo systemctl enable autonomous-mower

# Check service status
sudo systemctl status autonomous-mower
```

If you did a manual setup, you might need to install and configure the service file (`autonomous-mower.service`) manually.

### Monitoring Logs

Logs are typically stored in `/var/log/autonomous-mower/`:
```bash
# View main application log
tail -f /var/log/autonomous-mower/mower.log

# View systemd service log
sudo journalctl -u autonomous-mower -f
```

## Configuration Overview

The primary configuration is done via the `.env` file. Key areas include:
- Hardware ports and settings (`MM1_SERIAL_PORT`, `GPS_SERIAL_PORT`, `IMU_SERIAL_PORT`, camera settings)
- Operational modes (`USE_SIMULATION`)
- API keys (Google Maps, Weather)
- Object detection model paths (`YOLO_MODEL_PATH`)
- Web UI settings (`ENABLE_WEB_UI`)

Always refer to `.env.example` for a full list and descriptions.

## Safety Features

1.  **Emergency Stop:**
    *   Physical button (optional, GPIO-connected, normally closed).
    *   Web UI button.
    *   Configuration for physical button usage is typically in `.env` or a related JSON config.
2.  **Obstacle Detection:** Utilizes camera and chosen model (e.g., YOLOv8).
3.  **Boundary Enforcement:** GPS and defined mowing areas.
4.  **Sensor Monitoring:** Low battery, sensor failures.
5.  **Hardware Watchdog:** If configured, helps recover from system hangs.

## Troubleshooting

1.  **Service Won't Start:**
    *   Check log directory permissions (`/var/log/autonomous-mower`).
    *   Examine service logs: `sudo journalctl -u autonomous-mower -n 50 --no-pager`.
    *   Run the pre-flight checker: `python3 scripts/preflight_checker.py`.
2.  **Camera Issues:**
    *   Run `vcgencmd get_camera` (should show `supported=1 detected=1`).
    *   Test with `libcamera-hello -t 2000`.
    *   Ensure user is in the `video` group.
3.  **Object Detection Issues:**
    *   Verify model path in `.env` (`YOLO_MODEL_PATH`) and that the model file exists.
    *   Ensure `USE_YOLOV8=True` in `.env`.
4.  **Serial Device Issues (GPS, RoboHAT, IMU):**
    *   Double-check `MM1_SERIAL_PORT`, `GPS_SERIAL_PORT`, `IMU_SERIAL_PORT` in `.env`.
    *   Ensure no port conflicts (e.g., serial console, Bluetooth).
    *   Verify user is in `dialout` group.
    *   Use `ls -l /dev/ttyS* /dev/ttyAMA* /dev/ttyUSB* /dev/ttyACM*` to list available ports.

## Networking Features

(Section on Dual WiFi Configuration can remain as is, if still relevant and up-to-date with project).

## Developer Tooling

- Black (code formatting)
- MyPy (static type checking)
- Flake8 (linting)

## Contributing

1. Fork the repository.
2. Create a feature branch.
3. Make your changes.
4. Run tests and linters.
5. Submit a pull request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Google Coral team for Edge TPU support
- Ultralytics for the YOLOv8 models
- Raspberry Pi Foundation for hardware platform
- OpenCV community for computer vision tools

---
*This README has been updated to provide a more comprehensive setup guide. Please refer to specific documents in the `docs/` folder or scripts in `scripts/` for more granular details where indicated.*
