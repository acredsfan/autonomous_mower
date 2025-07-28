# Deployment Guide

This guide provides instructions for deploying the autonomous mower system to a Raspberry Pi. It covers both standard deployment and blue-green deployment with zero-downtime updates.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [System Validation](#system-validation)
3. [Deployment Options](#deployment-options)
4. [Standard Deployment](#standard-deployment)
5. [Blue-Green Deployment](#blue-green-deployment)
6. [Remote Deployment](#remote-deployment)
7. [Rollback Procedures](#rollback-procedures)
8. [Post-Deployment Verification](#post-deployment-verification)
9. [Troubleshooting](#troubleshooting)

## Prerequisites

Before deploying the autonomous mower system, ensure you have the following:

- Raspberry Pi 4 (4GB RAM recommended) with Raspberry Pi OS Bookworm (Debian 12)
- Python 3.9 or higher installed (tested with Python 3.11)
- Git installed
- Internet connection for downloading dependencies
- Required hardware components connected (see [Hardware Setup Guide](hardware_setup.md))
- SSH access to the Raspberry Pi (for remote deployment)
- At least 1GB free disk space for installation
- Stable power supply (hardware failures can occur with insufficient power)

## System Validation

Before deployment, it's recommended to run comprehensive system validation to ensure all components work correctly:

### Pre-Deployment Validation

```bash
# Run comprehensive system tests
python scripts/run_comprehensive_system_tests.py --verbose --output-file validation_report.txt

# Check hardware compatibility
python tools/test_sensors.py --all

# Verify configuration
python scripts/validate_config.py
```

### Validation Coverage

The system validation covers:
- **System startup** in both hardware and simulation modes
- **Major functionality** including sensor data collection, GPS services, navigation, obstacle detection, safety systems, and command execution
- **Error handling and recovery** mechanisms including sensor failures, GPS failures, resource monitoring, emergency stop, and graceful degradation
- **Performance metrics** including initialization time, memory usage, and sensor collection performance

### Expected Results

- All test suites should pass (100% success rate)
- System initialization should complete within 30 seconds
- Memory usage should be reasonable (typically under 600MB)
- Sensor collection should be fast and consistent (under 2 seconds per collection)

## Deployment Options

The autonomous mower system supports several deployment options:

1. **Standard Deployment**: Simple deployment for initial setup or testing
2. **Blue-Green Deployment**: Zero-downtime updates with automatic rollback
3. **Remote Deployment**: Deploy to a remote Raspberry Pi via SSH

## Standard Deployment

Standard deployment is the simplest method and is recommended for initial setup or testing.

### Local Deployment

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/autonomous_mower.git
   cd autonomous_mower
   ```

2. Run the deployment script:
   ```bash
   ./scripts/enhanced_deploy.sh
   ```

3. Follow the prompts to complete the deployment.

### Command-Line Options

The deployment script supports several command-line options:

```bash
./scripts/enhanced_deploy.sh [options]

Options:
  -h, --help                 Show help message
  -b, --branch BRANCH        Specify the branch to deploy (default: main)
  --skip-hardware-check      Skip hardware compatibility check
  --skip-coral               Skip Coral TPU setup
  --skip-remote-access       Skip remote access setup
  --auto-rollback            Automatically roll back on failure
  --log-file FILE            Specify log file
```

## Blue-Green Deployment

Blue-green deployment provides zero-downtime updates by maintaining two separate installations and switching between them.

### How It Works

1. Two complete installations are maintained: "blue" and "green"
2. Only one installation is active at a time
3. Updates are deployed to the inactive installation
4. After successful validation, the system switches to the updated installation
5. If validation fails, the system remains on the current installation

### Performing Blue-Green Deployment

```bash
./scripts/enhanced_deploy.sh --blue-green
```

For automatic rollback on failure:

```bash
./scripts/enhanced_deploy.sh --blue-green --auto-rollback
```

## Remote Deployment

Remote deployment allows you to deploy the system to a remote Raspberry Pi via SSH.

### Prerequisites

- SSH access to the remote Raspberry Pi
- SSH key-based authentication recommended

### Performing Remote Deployment

```bash
./scripts/enhanced_deploy.sh -r raspberrypi.local -u pi
```

Options:
```
  -r, --remote HOST          Deploy to remote Raspberry Pi via SSH
  -u, --user USER            Remote SSH username (default: pi)
  -p, --port PORT            Remote SSH port (default: 22)
```

## Rollback Procedures

### Automatic Rollback

The deployment script can automatically roll back to the previous version if deployment fails:

```bash
./scripts/enhanced_deploy.sh --auto-rollback
```

### Manual Rollback

To manually roll back to a previous version:

1. Stop the current services:
   ```bash
   sudo systemctl stop mower.service
   sudo systemctl stop ntrip-client.service
   ```

2. Restore from backup:
   ```bash
   # List available backups
   ls -la /home/pi/autonomous_mower_backup/
   
   # Restore from a specific backup
   rsync -a /home/pi/autonomous_mower_backup/YYYYMMDD_HHMMSS/ /home/pi/autonomous_mower/
   ```

3. Restart the services:
   ```bash
   sudo systemctl start ntrip-client.service
   sudo systemctl start mower.service
   ```

## Post-Deployment Verification

After deployment, the system automatically performs validation checks. You can also run these checks manually:

### System Validation

```bash
python3 scripts/system_validation.py --verbose
```

### Preflight Checks

```bash
python3 scripts/preflight_check.py --verbose
```

### Service Status

```bash
sudo systemctl status mower.service
sudo systemctl status ntrip-client.service
```

### Log Files

```bash
tail -f /var/log/autonomous-mower/mower.log
```

## Troubleshooting

### Common Issues

#### Service Fails to Start

1. Check the service status:
   ```bash
   sudo systemctl status mower.service
   ```

2. Check the log files:
   ```bash
   tail -f /var/log/autonomous-mower/mower.log
   ```

3. Verify Python dependencies:
   ```bash
   pip3 list | grep -E "numpy|opencv|flask"
   ```

4. Check for single instance conflicts:
   ```bash
   # If another instance is running, use force cleanup
   python -m mower.main_controller --force-cleanup
   ```

#### Hardware Detection Issues

1. Check I2C devices:
   ```bash
   i2cdetect -y 1
   ```

2. Check GPIO access:
   ```bash
   python3 -c "import RPi.GPIO as GPIO; print('GPIO available')"
   ```

3. Run hardware diagnostics:
   ```bash
   python3 tools/test_sensors.py
   ```

4. **IMU Issues**: If IMU fails to initialize:
   - Check UART connection on `/dev/ttyAMA4`
   - Verify baud rate is set to 3000000
   - System will gracefully degrade and use fallback data

5. **ToF Sensor Issues**: If ToF sensors fail:
   - Check I2C wiring and addresses
   - Verify GPIO pins 22 and 23 for XSHUT control
   - System will continue operation without ToF data

6. **BME280 Environmental Sensor**: If BME280 fails:
   - Check I2C connection
   - Verify chip ID detection
   - System provides fallback environmental data

#### Sensor Data Collection Issues

1. **Sensor Interface Timeout**: If sensor collection times out:
   - System automatically uses fallback data
   - Check hardware connections
   - Verify I2C bus stability

2. **GPS Service Issues**: If GPS fails:
   - Check serial port `/dev/ttyACM0`
   - Verify GPS module power and connections
   - System provides fallback GPS data

3. **Shared Sensor Data Errors**: If JSON serialization fails:
   - Check for SensorState enum serialization issues
   - System continues with reduced web UI functionality

#### Memory and Performance Issues

1. **High Memory Usage** (>600MB):
   - Check for memory leaks in sensor threads
   - Restart the service: `sudo systemctl restart mower.service`
   - Monitor with: `htop` or `free -h`

2. **Slow Sensor Collection** (>2 seconds):
   - Check I2C bus speed and stability
   - Verify hardware connections
   - System uses timeout protection to prevent hanging

#### Configuration Issues

1. **Missing Configuration Files**:
   - System creates default configurations automatically
   - Check `/home/pi/autonomous_mower/config/` directory
   - Verify `main_config.json` and `user_polygon.json` exist

2. **Invalid Configuration Values**:
   - Run configuration validation: `python scripts/validate_config.py`
   - Check log files for configuration warnings
   - System uses safe defaults for invalid values

#### Deployment Script Errors

1. Check deployment logs:
   ```bash
   cat /var/log/autonomous-mower/deployment.log
   ```

2. Verify Git repository:
   ```bash
   git status
   git remote -v
   ```

3. **Permission Issues**:
   ```bash
   # Fix ownership
   sudo chown -R pi:pi /home/pi/autonomous_mower
   
   # Fix permissions
   chmod +x scripts/*.sh
   ```

### Error Recovery Mechanisms

The system includes several built-in error recovery mechanisms:

1. **Graceful Degradation**: System continues operation with reduced functionality when components fail
2. **Automatic Fallback Data**: Provides safe default values when sensors fail
3. **Circuit Breakers**: Prevents cascading failures by isolating failing components
4. **Timeout Protection**: Prevents system hanging on slow or failed operations
5. **Emergency Stop**: Always available regardless of other system failures
6. **Resource Monitoring**: Tracks system resources and adjusts operation accordingly

### Safe Mode Operation

If critical components fail, the system can operate in safe mode:

```bash
# Enable safe mode
export SAFE_MODE_ALLOWED=true

# Start system (will run web interface only if hardware fails)
python -m mower.main_controller
```

Safe mode provides:
- Web interface access for monitoring
- Basic system status information
- Manual control capabilities
- Configuration management

### System Validation After Fixes

After resolving issues, run system validation to ensure everything works:

```bash
# Run comprehensive validation
python scripts/run_comprehensive_system_tests.py --verbose

# Check specific components
python tools/test_sensors.py --sensor imu
python tools/test_sensors.py --sensor tof
python tools/test_sensors.py --sensor bme280
```

### Getting Help

If you encounter issues that you cannot resolve, please:

1. Check the [Troubleshooting Guide](troubleshooting/index.md) for more detailed information
2. Search for similar issues in the project's issue tracker
3. Create a new issue with detailed information about the problem, including:
   - Error messages
   - System information
   - Steps to reproduce
   - Log files