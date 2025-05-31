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

## Environment Variables

See [`.env.example`](.env.example:1) for required environment variables, including:

- `USE_SIMULATION`
- `LOG_LEVEL`
- `CONFIG_DIR`
- `IMU_SERIAL_PORT`

## Module Overview

Overview of key modules:

- `MainController`: Coordinates all subsystems and state transitions
- `NavigationController`: Handles path planning and movement control
- `ObstacleDetector`: Processes sensor data and obstacle avoidance
- `HardwareManager`: Provides hardware abstraction for sensors and actuators

Architecture diagram placeholder: see [docs/system_architecture.md](docs/system_architecture.md)

## Developer Tooling

- Black (code formatting)
- MyPy (static type checking)
- Flake8 (linting)

Refer to coverage targets in [docs/test_coverage.md](docs/test_coverage.md)

## Prerequisites

- Raspberry Pi 4B (4GB RAM or better recommended)
- Python 3.9 or newer
- Raspberry Pi OS (Bookworm or newer)
- Camera module (v2 or v3 recommended)
- Various sensors (see Hardware Setup)
- Emergency stop button (normally closed)
- Optional: Google Coral USB Accelerator

## Initial Setup

### 1. System Dependencies

```bash
# Update system packages
sudo apt-get update
sudo apt-get upgrade

# Install required system packages
sudo apt-get install -y \
    python3-pip \
    python3-dev \
    python3-setuptools \
    python3-wheel \
    i2c-tools \
    git \
    libsystemd-dev
```

### 2. Clone Repository

```bash
git clone https://github.com/acredsfan/autonomous_mower.git
cd autonomous_mower
```

### 3. Create Log Directory and Set Permissions

Before running the installation script or service, you must create the log directory and set the correct permissions:

```bash
# Create log directory
sudo mkdir -p /var/log/autonomous-mower

# Set ownership to pi user
sudo chown -R pi:pi /var/log/autonomous-mower

# Set correct permissions
sudo chmod 755 /var/log/autonomous-mower
```

These steps are required only once during initial setup. The service will use this directory for all logging operations.

### 4. Installation

```bash
# Make the script executable
chmod +x install_requirements.sh

# Run the installation script with sudo
sudo ./install_requirements.sh
```

The installation script will:

- Install required system packages
- Install required Python packages system-wide
- Set up PYTHONPATH environment variable permanently
- Set up the systemd service
- Configure hardware interfaces
- Set up the watchdog timer
- Optionally install YOLOv8 models for improved object detection
- Optionally set up Google Coral TPU if available

#### Checkpoint/Resume Functionality

The installation script supports checkpoint/resume functionality, allowing you to continue where you left off if interrupted or skip already completed sections when re-running:

**First Installation:**

```bash
sudo ./install_requirements.sh
```

**Resume Installation After Interruption:**
If the installation was interrupted or you want to re-run it:

```bash
sudo ./install_requirements.sh
```

The script will automatically:

- Detect previous installation progress
- Show you which steps were completed and when
- Offer to skip completed steps or start fresh
- Allow you to selectively re-run specific components

**Example Resume Prompt:**

```
INFO: Previous installation found. This script supports checkpoint/resume functionality.

INFO: Previously completed installation steps:
  ✓ virtual_environment (completed: 2025-05-30 10:15:23)
  ✓ system_packages (completed: 2025-05-30 10:18:12)
  ✓ python_dependencies (completed: 2025-05-30 10:22:45)

Do you want to reset all checkpoints and start fresh? (y/N)
```

**Manual Reset (Start Fresh):**

```bash
# Remove checkpoint file to start completely fresh
rm .install_checkpoints
sudo ./install_requirements.sh
```

**Benefits:**

- ⏱️ **Time Saving**: Skip lengthy operations already completed
- 🔄 **Resume After Interruption**: Continue where you left off if installation fails
- 🛠️ **Development Friendly**: Re-run specific sections during testing/development
- 🎯 **Selective Installation**: Choose which components to reinstall
- 🔒 **Safe & Non-Destructive**: Won't break existing installations

For detailed information about the checkpoint system, see [`INSTALL_CHECKPOINTS.md`](INSTALL_CHECKPOINTS.md).

#### Note on Python Package Installation

This project uses system-wide Python package installation with the `--break-system-packages` flag to bypass PEP 668 restrictions. This is because:

1. The mower requires direct access to hardware interfaces (GPIO, I2C, etc.)
2. It's a dedicated device running only the mower software
3. System-wide installation ensures proper permissions and access to hardware resources
4. It simplifies service integration and maintenance

The installation uses the `--break-system-packages` flag to bypass PEP 668 restrictions, which is appropriate for this dedicated device. This approach has been tested and documented in our issues tracking system.

You may see the message "Defaulting to user installation because normal site-packages is not writeable" during installation. This is normal and expected on modern Linux systems due to PEP 668. Our installation script handles this by:

1. Using `--break-system-packages` to ensure system-wide installation
2. Installing packages in the correct location for hardware access
3. Setting proper permissions for the installed packages

## Running the Mower

### Starting the Service

```bash
# Start the service
sudo systemctl start autonomous-mower

# Enable service to start on boot
sudo systemctl enable autonomous-mower

# Check service status
sudo systemctl status autonomous-mower
```

### Monitoring Logs

The mower logs are stored in `/var/log/autonomous-mower/`:

```bash
# View service log
tail -f /var/log/autonomous-mower/service.log

# View error log
tail -f /var/log/autonomous-mower/error.log

# View application log
tail -f /var/log/autonomous-mower/mower.log
```

Logs are automatically rotated when they reach 1MB, with 5 backup files kept.

## Hardware Setup

### Required Hardware Connections

1. **Camera Module**

   - Connect to CSI port
   - Enable camera in raspi-config
   - Test with: `raspistill -v -o test.jpg`

2. **GPS Module**

   - Connect to UART pins (GPIO 14/15)
   - Enable serial in raspi-config
   - Test with: `gpsmon /dev/ttyAMA0`

3. **IMU Sensor**

   - Connect to UART pins (GPIO 8/10, i.e., TXD0/RXD0 or as configured)
   - Enable serial/UART in raspi-config
   - Test with: `python3 -m mower.hardware.imu` (shows live IMU data if connected)
   - Ensure your `.env` or environment variables specify the correct UART port (eg., `IMU_SERIAL_PORT=/dev/ttyAMA2`)

4. **Emergency Stop Button** (Optional)

   - Connect between GPIO7 and GND
   - Button should be normally closed (NC)
   - Test with: `gpio read 7`
   - Can be disabled in configuration if not physically installed

5. **Motor Controllers**
   - Connect to appropriate GPIO pins
   - Configure in .env file
   - Test with manual control in UI

### Object Detection Setup

#### YOLOv8 Setup (Recommended)

1. During installation, choose to install YOLOv8 models when prompted
2. Alternatively, run the setup script manually:

   ```bash
   python3 scripts/setup_yolov8.py --model yolov8n
   ```

   **Smart Model Detection:** The setup script will automatically scan for existing models in the `models/` directory and give you the option to use them instead of downloading new ones. This saves time and bandwidth when models are already available.

3. Configure detection in .env file:
   ```
   USE_YOLOV8=True
   YOLO_MODEL_PATH=/path/to/yolov8n.tflite
   YOLO_LABEL_PATH=/path/to/coco_labels.txt
   ```
4. Test with:
   ```bash
   python3 -m mower.obstacle_detection.yolov8_detector
   ```

#### Coral TPU Setup (Optional)

1. Connect Coral USB Accelerator
2. Install Coral runtime during installation
3. Verify detection:
   ```bash
   lsusb | grep "1a6e:089a"
   ```
4. Test with:
   ```bash
   python3 -c "import tflite_runtime.interpreter as tflite; print('Coral TPU detected')"
   ```

## YOLOv8 Model Download and Conversion (Required for Obstacle Detection)

**Note:** Due to TensorFlow's lack of support for export on Raspberry Pi OS Bookworm (Python 3.11+), you must export YOLOv8 models to TFLite format on a supported PC (Linux/Windows, Python 3.9 or 3.10), then copy them to your Pi.

### Steps:

1. **Export the YOLOv8 model to TFLite format on a supported PC:**

   - Use a Linux or Windows PC (x86_64) with Python 3.9 or 3.10.
   - Install the required packages:
     ```sh
     pip install ultralytics tensorflow==2.14.* flatbuffers==23.*
     ```
   - Download the YOLOv8 PyTorch model (e.g., yolov8n.pt) from Ultralytics.
   - Export to TFLite:
     ```sh
     yolo export model=yolov8n.pt format=tflite imgsz=640 nms=False
     ```
   - The exported file will be named `yolov8n_float32.tflite` (or similar).

2. **Copy the exported `.tflite` model and label map to your Raspberry Pi:**

   - Place the `.tflite` file in the `models/` directory of your mower project.
   - Place the label map (e.g., `imagenet_labels.txt` or `coco_labels.txt`) in the same directory.

3. **Update your `.env` file:**

   - Add or update these lines:
     ```
     # YOLOv8 configuration
     YOLO_MODEL_PATH=models/yolov8n_float32.tflite
     YOLO_LABEL_PATH=models/coco_labels.txt
     USE_YOLOV8=True
     ```

4. **Restart the mower software.**
   - The obstacle detector will automatically use the YOLOv8 TFLite model if configured.

### About the COCO Label Map (`coco_labels.txt`)

The YOLOv8 TFLite model requires a label map file that lists the names of all object classes the model can detect. For standard COCO-trained models, this file is usually called `coco_labels.txt` or `coco_labels.txt`.

- **What is it?**
  - A plain text file, one label per line, matching the order of classes in the model.
  - Example first lines:
    ```
    person
    bicycle
    car
    motorcycle
    ...
    toothbrush
    ```
- **Where do I get it?**
  - You can download it from the official Ultralytics or Google Coral repositories:
    - [COCO labels from Google Coral](https://raw.githubusercontent.com/google-coral/test_data/master/coco_labels.txt)
  - Or create it manually in a text editor using the full COCO class list (see above).
- **How do I use it?**
  - Place `coco_labels.txt` in your `models/` directory next to your `.tflite` model.
  - Update your `.env` file:
    ```
    LABEL_MAP_PATH=models/coco_labels.txt
    ```
- **Why is it needed?**
  - The label map allows the mower software to display human-readable class names for detected objects (e.g., "person", "car") instead of just class numbers.

### Exporting YOLOv8 Models Using Google Colab (Recommended for Most Users)

If you do not have access to a local PC with Python 3.9/3.10, you can use Google Colab to export YOLOv8 models to TFLite format:

1. **Open a new notebook at [Google Colab](https://colab.research.google.com/)**
2. **Paste and run the following code cells:**

```python
# Install dependencies
!pip install ultralytics tensorflow==2.14.* flatbuffers==23.*

# Download YOLOv8n PyTorch model
from ultralytics import YOLO
model = YOLO('yolov8n.pt')

# Export to TFLite (FP32)
model.export(format='tflite', imgsz=640, nms=False)
```

3. **Download the exported `.tflite` file:**

   - After running the export, the file (e.g., `yolov8n_float32.tflite`) will appear in the Colab file browser (left sidebar).
   - Right-click and select "Download" to save it to your computer.

4. **Download the label map:**

   - You can create a `coco_labels.txt` file in Colab with:
     `python
     COCO_LABELS = """person
bicycle
car
motorcycle
... (full list as in docs) ...
toothbrush""".splitlines()
with open('coco_labels.txt', 'w') as f:
    for label in COCO_LABELS:
        f.write(label + '\n')
     `
   - Download `coco_labels.txt` from the file browser.

5. **Copy both files to your Raspberry Pi and follow the setup steps above.**

#### Troubleshooting

- If you see errors about TensorFlow or FlatBuffers versions, ensure you did the export on a supported PC, not on the Pi.
- If the model or label map is missing, download or export them as described above.
- For more details, see the project documentation or ask for help in the project forums.

## Configuration

The `.env` file contains all configuration settings. Key sections include:

- Google Maps integration
- GPS and IMU settings
- Camera and obstacle detection
- Remote access configuration
- Hardware settings
- Path planning parameters
- Maintenance settings

See `.env.example` for detailed descriptions of each setting.

Note: For weather-dependent scheduling, you will also need to configure a `GOOGLE_WEATHER_API_KEY`. Instructions for obtaining this key are in the `docs/configuration_guide.md` and prompted during the `setup_wizard.py`.

## Safety Features

1. **Emergency Stop**

   - Available as both:
     - Physical button (optional hardware component)
     - Web UI button (always available)
   - System can operate with or without a physical button
   - Configure in settings: `safety.use_physical_emergency_stop`
   - Sensor override controls for testing
   - Battery monitoring and low-battery alerts
   - Hardware watchdog for system reliability

### Emergency Stop Configuration

The autonomous mower supports two modes of emergency stop functionality:

1. **With Physical Button (Default)**:

   - Connect a normally closed (NC) button between GPIO7 and GND
   - Set `safety.use_physical_emergency_stop` to `true` in config
   - When pressed or if wire is disconnected, the mower stops immediately
   - Provides a hardware failsafe independent of software

2. **Software-Only Mode**:
   - Set `safety.use_physical_emergency_stop` to `false` in config
   - Emergency stop functionality available only through web interface
   - No physical button required
   - Suitable when hardware button is not available or desired

During installation, you'll be asked whether to configure a physical emergency stop button.
You can change this setting later by editing the configuration file.

2. **Safety Guidelines**
   - Pre-Operation Checks
     - Verify emergency stop functionality
     - Check battery level
     - Ensure all sensors are working
     - Verify boundary settings
   - During Operation
     - Monitor system status
     - Keep emergency stop accessible
     - Watch for obstacle detection
     - Monitor battery levels
   - Maintenance
     - Regular blade inspection
     - Battery maintenance
     - Sensor cleaning
     - Software updates

## Troubleshooting

Common issues and their solutions:

### Service Won't Start

1. Check log directory permissions:

```bash
ls -l /var/log/autonomous-mower
```

If permissions are wrong, run:

```bash
sudo chown -R pi:pi /var/log/autonomous-mower
sudo chmod 755 /var/log/autonomous-mower
```

2. Check service logs:

```bash
sudo journalctl -u autonomous-mower -n 50 --no-pager
```

3. Verify Python environment:

```bash
python3 -m mower.diagnostics.hardware_test --non-interactive --verbose
```

### Camera Issues

1. Check camera connection and enable:

```bash
vcgencmd get_camera
libcamera-hello -t 5000
```

2. Verify camera devices:

```bash
ls /dev/video*
```

3. Check camera permissions:

```bash
groups | grep video
sudo usermod -aG video pi  # If 'video' group missing
```

### Object Detection Issues

1. Check YOLOv8 model exists:

```bash
ls -l src/mower/obstacle_detection/models/yolov8n.tflite
```

2. Reinstall YOLOv8 model if missing:

```bash
python3 scripts/setup_yolov8.py --model yolov8n
```

3. Check environment variables:

```bash
grep YOLOV8 .env
```

## Networking Features

### Dual WiFi Configuration with Automatic Failover

The autonomous mower supports a dual WiFi configuration that enables more reliable wireless connectivity by utilizing both the Raspberry Pi's onboard WiFi and an external USB WiFi adapter with an antenna. This setup provides:

- **Improved Range**: External USB WiFi adapters with antennas typically offer better range
- **Automatic Failover**: If one connection fails, the system automatically switches to the other
- **Prioritized Connectivity**: Primary (USB WiFi) is used when available, falling back to secondary (onboard)
- **Seamless Operation**: Switching happens automatically without interrupting mower operation

#### When to Use Dual WiFi

Consider using the dual WiFi setup if:

- Your mowing area has poor WiFi coverage or dead zones
- You need extended range beyond what the onboard WiFi provides
- You want redundant connectivity for increased reliability
- Your mower operates in areas with potential WiFi interference

#### Required Hardware

- Raspberry Pi with onboard WiFi (e.g., Pi 4B or Pi 5)
- USB WiFi adapter with external antenna (recommended for best range)
- Two available WiFi networks (can be the same network on different bands)

#### Setup Instructions

1. **Install the USB WiFi adapter**:

   - Connect the USB WiFi adapter to an available USB port on the Raspberry Pi
   - Ensure the antenna is properly attached and positioned for best reception

2. **Run the setup script**:

   ```bash
   chmod +x setup_dual_wifi.sh
   ./setup_dual_wifi.sh
   ```

3. **Configure your WiFi credentials**:

   - Edit the script before running or follow the prompts to enter:
     - Primary WiFi SSID and password (USB adapter - wlan1)
     - Secondary WiFi SSID and password (onboard WiFi - wlan0)
     - Country code for regulatory compliance

4. **Verify the setup**:

   ```bash
   # Check network interfaces
   ip addr show

   # Verify the watchdog service is running
   sudo systemctl status wifi-watchdog
   ```

#### How the Watchdog Works

The WiFi watchdog service monitors connectivity using these components:

1. **Python Monitoring Script**: Checks connectivity to the configured gateway
2. **Routing Priority**: Dynamically adjusts routing metrics to prefer the working connection
3. **Automatic Recovery**: Switches back to primary when it becomes available again
4. **Systemd Service**: Ensures the watchdog continues running across reboots

The watchdog runs these basic operations:

- Pings the primary gateway every 5 seconds
- If 3 consecutive pings fail, switches to the secondary connection
- When primary connection is restored, automatically switches back

#### Troubleshooting

If you experience connectivity issues:

1. **Check service status**:

   ```bash
   sudo systemctl status wifi-watchdog
   ```

2. **View watchdog logs**:

   ```bash
   sudo journalctl -u wifi-watchdog -n 50
   ```

3. **Verify both WiFi interfaces are recognized**:

   ```bash
   iwconfig
   ```

4. **Restart the service if needed**:

   ```bash
   sudo systemctl restart wifi-watchdog
   ```

5. **Check routing table**:
   ```bash
   ip route show
   ```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and style checks
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Google Coral team for Edge TPU support
- Ultralytics for the YOLOv8 models
- Raspberry Pi Foundation for hardware platform
- OpenCV community for computer vision tools
