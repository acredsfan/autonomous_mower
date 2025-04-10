# Autonomous Lawn Mower

An autonomous lawn mower system built for Raspberry Pi, featuring advanced navigation, obstacle detection, and safety features.

## Features

- Real-time obstacle detection using computer vision
- GPS-based navigation and boundary mapping
- Remote control via web interface
- Weather-aware scheduling
- Safety features and emergency stop
- Support for Google Coral Edge TPU acceleration
- Remote monitoring and control
- Multiple remote access options (DDNS, Cloudflare, NGROK)
- Automatic startup on boot via systemd service
- Hardware watchdog for system reliability
- Emergency stop button support

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
    i2c-tools \
    git
```

### 2. Clone Repository

```bash
git clone https://github.com/yourusername/autonomous_mower.git
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
# Run the installation script
./install_requirements.sh
```

The installation script will:
- Install required system packages
- Install required Python packages system-wide
- Set up the systemd service
- Configure hardware interfaces
- Set up the watchdog timer

#### Note on Python Package Installation
This project uses system-wide Python package installation instead of a virtual environment. This is because:
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
   - Connect to I2C pins (GPIO 2/3)
   - Enable I2C in raspi-config
   - Test with: `i2cdetect -y 1`

4. **Emergency Stop Button**
   - Connect between GPIO7 and GND
   - Button should be normally closed (NC)
   - Test with: `gpio read 7`

5. **Motor Controllers**
   - Connect to appropriate GPIO pins
   - Configure in .env file
   - Test with manual control in UI

### Coral TPU Setup (Optional)

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

## Safety Features

1. **Emergency Stop Button**
   - Available in the UI
   - Sensor override controls for testing
   - Battery monitoring and low-battery alerts
   - Hardware watchdog for system reliability

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
- Raspberry Pi Foundation for hardware platform
- OpenCV community for computer vision tools