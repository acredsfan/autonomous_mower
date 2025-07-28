# Deployment Checklist

This comprehensive checklist provides a step-by-step guide for deploying the autonomous mower system to a Raspberry Pi. Use this checklist to ensure a successful deployment with all recent improvements and fixes.

## Pre-Deployment Checklist

### System Requirements Validation
- [ ] Verify hardware compatibility
  - [ ] Raspberry Pi 4B+ (4GB RAM recommended) with Raspberry Pi OS Bookworm
  - [ ] Python 3.9+ installed (tested with Python 3.11)
  - [ ] At least 1GB free disk space
  - [ ] Stable power supply (hardware failures can occur with insufficient power)
  - [ ] Internet connection available

### Hardware Validation
- [ ] All required hardware components connected
  - [ ] Camera module connected and enabled: `libcamera-hello -t 5000`
  - [ ] I2C sensors connected: `i2cdetect -y 1`
  - [ ] GPS module connected: `ls -la /dev/ttyACM0`
  - [ ] IMU UART connection: `ls -la /dev/ttyAMA4`
  - [ ] Motor controllers connected
  - [ ] Emergency stop button wired (optional)
  - [ ] GPIO access available: `python3 -c "import RPi.GPIO as GPIO; print('GPIO OK')"`

### Software Prerequisites
- [ ] Repository cloned: `git clone <repository-url>`
- [ ] Environment variables configured (copy `.env.example` to `.env`)
- [ ] Configuration validation: `python scripts/validate_config.py`
- [ ] Log directory permissions: `sudo chown -R pi:pi /var/log/autonomous-mower`

### Pre-Deployment System Validation
- [ ] Run comprehensive system validation:
  ```bash
  python scripts/run_comprehensive_system_tests.py --verbose --output-file pre_deployment_validation.txt
  ```
- [ ] Verify validation results:
  - [ ] Overall Success: PASS (100% success rate)
  - [ ] System initialization: <30 seconds
  - [ ] Memory usage: <600MB typical
  - [ ] Sensor collection: <2 seconds per cycle
- [ ] Hardware-specific testing:
  ```bash
  python tools/test_sensors.py --all
  ```

## Deployment Checklist

- [ ] Clone repository
  ```bash
  git clone https://github.com/yourusername/autonomous_mower.git
  cd autonomous_mower
  ```

- [ ] Choose deployment method
  - [ ] Standard deployment
    ```bash
    ./scripts/enhanced_deploy.sh
    ```
  - [ ] Blue-green deployment
    ```bash
    ./scripts/enhanced_deploy.sh --blue-green
    ```
  - [ ] Remote deployment
    ```bash
    ./scripts/enhanced_deploy.sh -r raspberrypi.local -u pi
    ```

- [ ] Monitor deployment progress
  - [ ] Check for errors during installation
  - [ ] Verify dependencies are installed correctly
  - [ ] Verify service files are created

## Post-Deployment Checklist

### System Validation
- [ ] Run comprehensive post-deployment validation:
  ```bash
  python scripts/run_comprehensive_system_tests.py --verbose --output-file post_deployment_validation.txt
  ```
- [ ] Verify validation results:
  - [ ] Overall Success: PASS (100% success rate)
  - [ ] All test suites passed: Simulation Mode Startup, Hardware Mode Startup, Major Functionality, Error Handling & Recovery, Performance Metrics
  - [ ] System initialization: <30 seconds
  - [ ] Memory usage: <600MB typical
  - [ ] Sensor collection: <2 seconds per cycle

### Service Verification
- [ ] Verify services are running:
  ```bash
  sudo systemctl status mower.service
  sudo systemctl status ntrip-client.service
  ```
- [ ] Check for single instance conflicts:
  ```bash
  ps aux | grep -i mower
  # Should show only one main process
  ```

### Hardware Component Testing
- [ ] Test individual sensors:
  ```bash
  python tools/test_sensors.py --sensor imu
  python tools/test_sensors.py --sensor tof
  python tools/test_sensors.py --sensor bme280
  python tools/test_sensors.py --sensor ina3221
  ```
- [ ] Verify sensor data collection:
  ```bash
  # Should complete within 2 seconds without timeout
  python -c "from mower.main_controller import ResourceManager; rm = ResourceManager(); rm.initialize(); print(rm.get_sensor_data())"
  ```

### Error Handling Verification
- [ ] Test graceful degradation:
  - [ ] System continues operation when sensors fail
  - [ ] Fallback data provided when hardware unavailable
  - [ ] Emergency stop always functional
- [ ] Verify error recovery mechanisms:
  - [ ] Circuit breakers prevent cascading failures
  - [ ] Timeout protection prevents system hanging
  - [ ] Automatic retry with exponential backoff

### Performance Validation
- [ ] Check system resource usage:
  ```bash
  htop  # Monitor CPU and memory usage
  free -h  # Check memory usage (<600MB typical)
  df -h  # Check disk space
  ```
- [ ] Verify sensor collection performance:
  - [ ] Average collection time: <0.01 seconds
  - [ ] Maximum collection time: <2 seconds
  - [ ] No timeout errors in logs

### Web Interface Testing
- [ ] Verify web interface is accessible:
  - [ ] Local access: http://localhost:5000
  - [ ] Remote access: http://<raspberry_pi_ip>:5000
- [ ] Test web interface functionality:
  - [ ] Sensor data displays correctly
  - [ ] Manual control commands work
  - [ ] Emergency stop button functional
  - [ ] System status updates in real-time

### Log File Analysis
- [ ] Check log files for errors:
  ```bash
  tail -f /var/log/autonomous-mower/mower.log
  ```
- [ ] Verify no critical errors:
  - [ ] No sensor timeout errors
  - [ ] No JSON serialization errors
  - [ ] No hardware initialization failures
  - [ ] No memory leak warnings

### Configuration Verification
- [ ] Verify configuration files exist and are valid:
  ```bash
  ls -la config/
  python scripts/validate_config.py --verbose
  ```
- [ ] Check default configurations were created:
  - [ ] `config/main_config.json` exists
  - [ ] `config/user_polygon.json` exists
  - [ ] `config/components.json` exists (if using DI)

### Safe Mode Testing
- [ ] Test safe mode operation:
  ```bash
  export SAFE_MODE_ALLOWED=true
  python -m mower.main_controller
  # Should start web interface even if hardware fails
  ```

## Rollback Checklist (If Needed)

- [ ] Stop services
  ```bash
  sudo systemctl stop mower.service
  sudo systemctl stop ntrip-client.service
  ```

- [ ] Restore from backup
  ```bash
  # List available backups
  ls -la /home/pi/autonomous_mower_backup/
  
  # Restore from a specific backup
  rsync -a /home/pi/autonomous_mower_backup/YYYYMMDD_HHMMSS/ /home/pi/autonomous_mower/
  ```

- [ ] Restart services
  ```bash
  sudo systemctl start ntrip-client.service
  sudo systemctl start mower.service
  ```

- [ ] Verify services are running correctly
  ```bash
  sudo systemctl status mower.service
  sudo systemctl status ntrip-client.service
  ```

## Troubleshooting Checklist

- [ ] Check service status
  ```bash
  sudo systemctl status mower.service
  ```

- [ ] Check log files
  ```bash
  tail -f /var/log/autonomous-mower/mower.log
  ```

- [ ] Check deployment logs
  ```bash
  cat /var/log/autonomous-mower/deployment.log
  ```

- [ ] Check hardware connections
  ```bash
  i2cdetect -y 1
  ```

- [ ] Run hardware diagnostics
  ```bash
  python3 tools/test_sensors.py
  ```

- [ ] Check system resources
  ```bash
  free -h
  df -h
  vcgencmd measure_temp
  ```

## Final Verification Checklist

- [ ] Verify all components are functioning correctly
  ```bash
  ./scripts/final_validation.sh --verbose
  ```

- [ ] Verify the system can be controlled through the web interface
  - [ ] Navigate to http://<raspberry_pi_ip>:5000
  - [ ] Test basic controls
  - [ ] Verify sensor readings are displayed

- [ ] Verify the system can operate autonomously
  - [ ] Set up a test boundary
  - [ ] Start autonomous operation
  - [ ] Verify the system navigates correctly
  - [ ] Verify obstacle detection works
  - [ ] Verify emergency stop works