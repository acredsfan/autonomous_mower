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
    python3-dev \
    python3-setuptools \
    python3-wheel \
    i2c-tools \
    git
```

### 2. Clone Repository

```bash
git clone https://github.com/yourusername/autonomous_mower.git
cd autonomous_mower
```

### 3. Create Log Directory and Set Permissions

This step is handled automatically by `install_requirements.sh`. No manual action is required.

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
- Set up the systemd service
- Configure hardware interfaces
- Set up the watchdog timer

### 5. Interactive Setup Wizard

The installation script automatically launches the interactive setup wizard at the end. You can also rerun it manually anytime:
```bash
# Run the setup wizard
python3 setup_wizard.py
```

The setup wizard provides a user-friendly interface to:
- Detect and configure hardware components
- Set up mapping and navigation
- Configure safety features
- Set up the web interface and remote access
- Create a mowing schedule
- Configure weather integration
- Set up security features

The wizard adapts to your inputs, only showing relevant options based on your hardware and preferences. It provides clear instructions for obtaining any required tokens or credentials (like Google Maps API keys or weather service tokens).

If you need to interrupt the setup process, your progress will be saved, and you can continue where you left off by running the wizard again.

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

## Remote Access Setup

The mower supports several remote access methods, configurable via the `.env` file. **Choose only one method at a time** by setting `REMOTE_ACCESS_TYPE` in your `.env`.

### ⚠️ Security Warning: Port Forwarding
Port forwarding exposes your mower’s web interface directly to the internet. **This is not recommended unless you fully understand the risks and have secured your device (strong passwords, firewall, etc.).** For most users, DDNS, Cloudflare Tunnel, or NGROK are safer options.

### 1. Port Forwarding
- Set in `.env`:
  ```
  REMOTE_ACCESS_TYPE=port_forward
  ```
- Manually configure your router to forward the web UI port (default: 5000) to your mower’s local IP.
- Access your mower at `http://<your-public-ip>:5000`.

### 2. Dynamic DNS (DDNS)
- Set in `.env`:
  ```
  REMOTE_ACCESS_TYPE=ddns
  DDNS_PROVIDER=duckdns  # or noip
  DDNS_DOMAIN=your-domain.duckdns.org
  DDNS_TOKEN=your-token
  ```
- The setup script will install and configure the DDNS client.
- Combine with port forwarding for external access.

### 3. Cloudflare Tunnel
- Set in `.env`:
  ```
  REMOTE_ACCESS_TYPE=cloudflare
  CLOUDFLARE_TOKEN=your-token
  CLOUDFLARE_ZONE_ID=your-zone-id
  CLOUDFLARE_TUNNEL_NAME=mower-tunnel
  ```
- The setup script will install and configure Cloudflare Tunnel.
- No port forwarding required; Cloudflare provides a secure public URL.

### 4. Custom Domain with SSL
- Set in `.env`:
  ```
  REMOTE_ACCESS_TYPE=custom_domain
  CUSTOM_DOMAIN=mower.yourdomain.com
  SSL_EMAIL=your-email@example.com
  ```
- The setup script will install Certbot and configure SSL for your domain.
- You must own the domain and point its DNS to your mower’s public IP.

### 5. NGROK
- Set in `.env`:
  ```
  REMOTE_ACCESS_TYPE=ngrok
  NGROK_AUTH_TOKEN=your-token
  NGROK_DOMAIN=your-reserved-domain.ngrok.io  # Optional
  ```
- The setup script will install and configure NGROK.
- NGROK provides a secure tunnel and public URL.

### Running the Setup
After editing your `.env`, run:

```bash
python3 src/mower/utilities/setup_remote_access.py
```

Check the logs for success or error messages. For more details, see the comments in `.env.example` and the [Remote Access Setup Utility](src/mower/utilities/setup_remote_access.py).

## Custom Domain & Remote Access Setup

To access your mower remotely using a custom domain or public IP, follow these steps:

### 1. Get Your Raspberry Pi's Public IP Address

On your Raspberry Pi, run:

```
curl ifconfig.me
```

or

```
curl ipinfo.io/ip
```

This will display your public IP address. You will need this to set up remote access or configure your custom domain.

### 2. Port Forwarding

- Log in to your home router's admin page.
- Set up port forwarding to forward external traffic (e.g., port 80 or 443) to your Raspberry Pi's local IP address and the port your mower web UI is running on (default: 5000).
- Make sure your Raspberry Pi has a static local IP or DHCP reservation.

### 3. (Optional) Use a Dynamic DNS Service

If your public IP changes periodically, use a Dynamic DNS (DDNS) service (e.g., DuckDNS, No-IP) to get a hostname that always points to your current IP. Follow the DDNS provider's instructions to set up a client on your Pi.

### 4. Setting Up a Custom Domain

- Register a domain name with your preferred registrar.
- Set an A record for your domain to point to your public IP (from step 1).
- If using DDNS, set a CNAME record to your DDNS hostname instead.

### 5. Secure Remote Access (Recommended)

- Enable SSL in your .env file (`ENABLE_SSL=True`) and provide valid certificate and key paths.
- Consider using a reverse proxy (e.g., Nginx) for added security and flexibility.
- Optionally, restrict access by IP or enable authentication in your .env file.

### 6. Test Remote Access

- From a device outside your home network, visit `http://<your-public-ip>:<port>` or your custom domain.
- Ensure you can access the mower web UI securely.

### Troubleshooting

- If you can't connect, check your router's port forwarding, firewall settings, and that your Pi's web UI is running.
- Use `ping <your-public-ip>` and `telnet <your-public-ip> <port>` to test connectivity.

For more details, see the `docs/setup_remote_access.md` or the [Remote Access](docs/hardware_setup.md#remote-access) section.

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

The correct output should look similar to this (with 'pi' as the owner and group, and 'drwxr-xr-x' as the permissions):
```
drwxr-xr-x 2 pi pi 4096 May 15 10:30 /var/log/autonomous-mower
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

You should see log entries showing the service startup process. A successful startup would show entries similar to:
```
May 15 10:35:20 raspberrypi autonomous-mower[1234]: Starting Autonomous Mower service...
May 15 10:35:22 raspberrypi autonomous-mower[1234]: Initializing hardware components...
May 15 10:35:25 raspberrypi autonomous-mower[1234]: Starting web interface on port 5000...
May 15 10:35:26 raspberrypi autonomous-mower[1234]: Autonomous Mower service started successfully
```

Look for any error messages that might indicate what's preventing the service from starting.

3. Verify Python environment:
```bash
python3 -m mower.diagnostics.hardware_test --non-interactive --verbose
```

A successful test should show output similar to:
```
[INFO] Starting hardware diagnostics in non-interactive mode
[INFO] Checking Python version... OK (3.9.2)
[INFO] Checking required packages... OK
[INFO] Checking GPIO access... OK
[INFO] Checking I2C access... OK
[INFO] Checking camera access... OK
[INFO] Checking GPS module... OK
[INFO] All tests passed successfully!
```

If any tests fail, the output will indicate which component is having issues.

### Camera Issues

1. Check camera connection and enable:
```bash
vcgencmd get_camera
```

The correct output should show that the camera is detected and enabled:
```
supported=1 detected=1
```
If you see `detected=0`, the camera is not properly connected.

Then test the camera with:
```bash
libcamera-hello -t 5000
```

This should open a preview window showing the camera feed for 5 seconds. If successful, you'll see output similar to:
```
libcamera-hello: Using camera 0, sensor model(s) imx219, color filter pattern RGGB
libcamera-hello: Preview window resolution 1536x864
libcamera-hello: Viewfinder size 1536x864, display size 1536x864
libcamera-hello: Press Ctrl-C to quit
```

2. Verify camera devices:
```bash
ls /dev/video*
```

You should see multiple video devices listed. A typical output on a Raspberry Pi with a camera connected would be:
```
/dev/video0  /dev/video1  /dev/video10  /dev/video11  /dev/video12
```
The exact number of devices may vary, but you should see at least `/dev/video0`.

3. Check camera permissions:
```bash
groups | grep video
```

The output should show that your user (typically 'pi') is a member of the 'video' group:
```
pi adm dialout cdrom sudo audio video plugdev games users input netdev gpio i2c spi
```

If you don't see 'video' in the output, add your user to the video group:
```bash
sudo usermod -aG video pi  # Replace 'pi' with your username if different
```
Then log out and log back in for the changes to take effect.

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
