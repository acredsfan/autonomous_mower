# Autonomous Lawn Mower

A Raspberry Pi-powered autonomous lawn mower with obstacle detection, path planning, and remote control capabilities.

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

## Prerequisites

- Raspberry Pi 4 (recommended) or newer
- Python 3.9 or higher
- Required hardware:
  - Camera module
  - GPS module (UBLOX ZED-F9P recommended)
  - IMU sensor (BNO085 recommended)
  - Motor controllers
  - Optional: Google Coral USB Accelerator

## Installation

### Quick Start (Recommended)

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/autonomous_mower.git
   cd autonomous_mower
   ```

2. Run the installation script:
   ```bash
   chmod +x install_requirements.sh
   ./install_requirements.sh
   ```

3. Configure your environment:
   ```bash
   cp .env.example .env
   # Edit .env with your specific settings
   ```

4. The mower service will start automatically on boot. You can manage it with:
   ```bash
   # Check service status
   sudo systemctl status autonomous-mower
   
   # View logs
   journalctl -u autonomous-mower
   
   # Manually start/stop/restart
   sudo systemctl start autonomous-mower
   sudo systemctl stop autonomous-mower
   sudo systemctl restart autonomous-mower
   ```

### Manual Installation

If you prefer to install manually or encounter issues with the script:

1. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install --upgrade pip wheel setuptools
   pip install "numpy<2.0.0"  # Install numpy first to avoid conflicts
   pip install -e .
   ```

3. Install optional features:
   ```bash
   # For Coral TPU support
   pip install -e ".[coral]"
   
   # For DDNS support
   pip install -e ".[ddns]"
   
   # For Cloudflare support
   pip install -e ".[cloudflare]"
   
   # For SSL support
   pip install -e ".[ssl]"
   ```

4. Set up hardware access:
   ```bash
   sudo usermod -a -G gpio,i2c,dialout,video $USER
   sudo raspi-config nonint do_i2c 0
   sudo raspi-config nonint do_serial 0
   ```

5. Configure your environment:
   ```bash
   cp .env.example .env
   # Edit .env with your specific settings
   ```

6. Set up systemd service:
   ```bash
   # Copy service file
   sudo cp autonomous-mower.service /etc/systemd/system/
   
   # Create log files
   sudo touch /var/log/autonomous-mower.log
   sudo touch /var/log/autonomous-mower.error.log
   sudo chown $USER:$USER /var/log/autonomous-mower.log
   sudo chown $USER:$USER /var/log/autonomous-mower.error.log
   
   # Enable and start service
   sudo systemctl daemon-reload
   sudo systemctl enable autonomous-mower.service
   sudo systemctl start autonomous-mower.service
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

## Usage

### Service Management

The mower runs as a system service and can be managed using systemd:

```bash
# Check service status
sudo systemctl status autonomous-mower

# View logs
journalctl -u autonomous-mower

# Start/stop/restart service
sudo systemctl start autonomous-mower
sudo systemctl stop autonomous-mower
sudo systemctl restart autonomous-mower
```

### Testing Hardware

```bash
mower-test  # Run hardware diagnostics
mower-calibrate  # Calibrate IMU sensor
```

### Remote Access

The mower supports multiple remote access methods:

1. **DDNS** (recommended for home use)
   - Configure your router for port forwarding
   - Set up DDNS in `.env`
   - Access via your DDNS domain

2. **Cloudflare Tunnel** (recommended for production)
   - Set up Cloudflare account
   - Configure tunnel in `.env`
   - Access via Cloudflare domain

3. **NGROK** (good for testing)
   - Set up NGROK account
   - Configure in `.env`
   - Access via NGROK URL

## Accessing the User Interface

1. **Web UI Access**
   - The web interface is available at `http://<raspberry_pi_ip>:5000`
   - Default port is 5000 (configurable in .env file)
   - If running locally, use `http://localhost:5000`

2. **Initial Setup**
   - First-time access requires creating an admin account
   - Default credentials (if not changed):
     - Username: admin
     - Password: admin
   - Change these credentials in the .env file for security

3. **Testing Mower Functionality**
   - **Movement Testing**
     - Use the "Manual Control" section in the UI
     - Test forward, backward, and turning movements
     - Adjust speed using the speed control slider
   
   - **Sensor Testing**
     - View real-time sensor data in the "Sensor Dashboard"
     - Test obstacle detection using the "Obstacle Detection" panel
     - Monitor GPS position in the "Navigation" section
   
   - **Boundary Testing**
     - Use the "Boundary Editor" to create and test mowing boundaries
     - Test virtual fence functionality
     - Verify return-to-home behavior

4. **Safety Features**
   - Emergency stop button available in the UI
   - Sensor override controls for testing
   - Battery monitoring and low-battery alerts

5. **Troubleshooting**
   - Check the "System Logs" section for detailed error messages
   - Use the "Diagnostics" panel to verify hardware connections
   - View sensor calibration data in the "Calibration" section

## Development

### Running Tests

```bash
pip install -e ".[dev]"
pytest
```

### Code Style

```bash
black .
flake8
mypy .
```

## Troubleshooting

### Common Issues

1. **Permission Issues**
   ```bash
   sudo chown -R $USER:$USER .
   sudo chmod -R 755 .
   ```

2. **Hardware Access**
   ```bash
   # Check I2C
   i2cdetect -y 1
   
   # Check Serial
   ls -l /dev/tty*
   ```

3. **Dependency Conflicts**
   ```bash
   pip uninstall numpy tensorflow
   pip install "numpy<2.0.0"
   pip install "tensorflow>=2.5.0,<2.6.0"
   ```

4. **Service Issues**
   ```bash
   # Check service logs
   journalctl -u autonomous-mower -n 100
   
   # Check service status
   sudo systemctl status autonomous-mower
   
   # Restart service
   sudo systemctl restart autonomous-mower
   ```

### Logs

Logs are stored in multiple locations:
- System service logs: `journalctl -u autonomous-mower`
- Application logs: `/var/log/autonomous-mower.log`
- Error logs: `/var/log/autonomous-mower.error.log`
- Rotated logs: `logs/mower.log`, `logs/mower.log.1`, etc.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Google Coral team for Edge TPU support
- Raspberry Pi Foundation for hardware platform
- OpenCV community for computer vision tools