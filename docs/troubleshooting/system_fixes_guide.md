# System Fixes and Troubleshooting Guide

This guide documents the major fixes implemented in the autonomous mower system and provides troubleshooting steps for common issues.

## Table of Contents

1. [Overview of Fixes](#overview-of-fixes)
2. [Hardware Issues and Fixes](#hardware-issues-and-fixes)
3. [Software Issues and Fixes](#software-issues-and-fixes)
4. [Performance Optimizations](#performance-optimizations)
5. [Error Handling Improvements](#error-handling-improvements)
6. [System Validation](#system-validation)
7. [Troubleshooting Workflow](#troubleshooting-workflow)

## Overview of Fixes

The system has undergone comprehensive debugging and optimization to address various hardware and software issues. All fixes maintain backward compatibility and include graceful degradation mechanisms.

### Key Improvements

- **Hardware Abstraction**: Improved hardware initialization and error handling
- **Sensor Management**: Enhanced sensor data collection with timeout protection
- **Error Recovery**: Comprehensive error handling with automatic fallback mechanisms
- **Performance**: Optimized resource usage and reduced memory footprint
- **Validation**: Comprehensive system testing with 100% pass rate
- **Documentation**: Updated guides with troubleshooting information

## Hardware Issues and Fixes

### IMU (Inertial Measurement Unit) Issues

**Problem**: IMU initialization failures with UART communication errors

**Symptoms**:
- `Unhandled UART control SHTP protocol` errors
- `list assignment index out of range` errors
- `Didn't find packet end` errors

**Fix Implemented**:
- Enhanced error handling in IMU initialization
- Graceful degradation when IMU hardware is unavailable
- Automatic fallback to safe default values
- Improved UART communication with better error recovery

**Troubleshooting**:
```bash
# Check UART device
ls -la /dev/ttyAMA4

# Test IMU specifically
python tools/test_sensors.py --sensor imu

# Check system logs
grep -i "imu" /var/log/autonomous-mower/mower.log
```

### ToF (Time of Flight) Sensor Issues

**Problem**: ToF sensor initialization failures and I2C communication errors

**Symptoms**:
- `Failed to find expected ID register values. Check wiring!`
- `Input/output error` on I2C operations
- ToF sensors not detected

**Fix Implemented**:
- Improved I2C error handling and recovery
- Enhanced GPIO pin management for XSHUT control
- Graceful degradation when ToF hardware is unavailable
- Better sensor initialization sequence

**Troubleshooting**:
```bash
# Check I2C devices
i2cdetect -y 1

# Test ToF sensors
python tools/test_sensors.py --sensor tof

# Check GPIO pins
python -c "import RPi.GPIO as GPIO; GPIO.setmode(GPIO.BCM); print('GPIO available')"
```

### BME280 Environmental Sensor Issues

**Problem**: BME280 sensor detection and initialization failures

**Symptoms**:
- `Failed to find BME280! Chip ID 0x34` or similar chip ID errors
- Environmental data not available

**Fix Implemented**:
- Enhanced chip ID detection and validation
- Improved I2C communication error handling
- Automatic fallback to default environmental values
- Better sensor initialization retry logic

**Troubleshooting**:
```bash
# Check BME280 on I2C
i2cdetect -y 1 | grep -E "76|77"

# Test BME280 specifically
python tools/test_sensors.py --sensor bme280

# Manual I2C test
python -c "import board; import busio; i2c = busio.I2C(board.SCL, board.SDA); print('I2C available')"
```

### Power Monitoring (INA3221) Issues

**Problem**: Power monitoring sensor communication failures

**Symptoms**:
- Power data not available
- I2C communication errors with INA3221

**Fix Implemented**:
- Enhanced INA3221 initialization and error handling
- Graceful degradation when power monitoring is unavailable
- Automatic fallback to estimated power values

**Troubleshooting**:
```bash
# Check INA3221 on I2C (address 0x40)
i2cdetect -y 1 | grep 40

# Test power monitoring
python tools/test_sensors.py --sensor ina3221
```

## Software Issues and Fixes

### Sensor Data Collection Timeout

**Problem**: Sensor data collection hanging or timing out

**Symptoms**:
- System appears frozen during sensor collection
- Long delays in web UI updates
- Timeout errors in logs

**Fix Implemented**:
- Thread-safe timeout protection using threading + queue approach
- Automatic fallback to safe default values on timeout
- Enhanced error logging and recovery mechanisms
- Configurable timeout values

**Configuration**:
```json
{
  "sensors": {
    "collection_timeout": 8.0,
    "retry_attempts": 3,
    "fallback_enabled": true
  }
}
```

### JSON Serialization Errors

**Problem**: SensorState enum not JSON serializable for web UI

**Symptoms**:
- `Object of type SensorState is not JSON serializable` errors
- Web UI not receiving sensor data updates

**Fix Implemented**:
- Enhanced JSON serialization handling for enum types
- Automatic conversion of non-serializable objects
- Graceful degradation when serialization fails
- Improved error logging

### Single Instance Management

**Problem**: Multiple mower instances causing hardware conflicts

**Symptoms**:
- `Another mower instance is already running` errors
- Hardware access conflicts
- Service startup failures

**Fix Implemented**:
- Enhanced single instance checking with PID validation
- Force cleanup option for stuck processes
- Better process management and cleanup
- Improved error messages and recovery options

**Usage**:
```bash
# Force cleanup of stuck instances
python -m mower.main_controller --force-cleanup

# Check for running instances
ps aux | grep -i mower
```

### Configuration Management

**Problem**: Missing or invalid configuration files

**Symptoms**:
- Configuration file not found errors
- Invalid configuration values
- System using unexpected defaults

**Fix Implemented**:
- Automatic creation of default configuration files
- Enhanced configuration validation and error handling
- Graceful degradation with safe defaults
- Better error messages for configuration issues

**Default Configuration Creation**:
- `config/main_config.json` - Main system configuration
- `config/user_polygon.json` - Boundary and home location
- `config/components.json` - Dependency injection configuration

## Performance Optimizations

### Memory Usage Optimization

**Problem**: High memory usage (>600MB) during operation

**Improvements**:
- Optimized sensor data collection loops
- Better memory management in async operations
- Reduced object creation in hot paths
- Enhanced garbage collection

**Monitoring**:
```bash
# Monitor memory usage
htop
free -h

# Check specific process
ps aux | grep mower | awk '{print $6}'
```

### Sensor Collection Performance

**Problem**: Slow sensor data collection (>2 seconds)

**Improvements**:
- Optimized I2C communication patterns
- Parallel sensor reading where possible
- Reduced blocking operations
- Better error handling to prevent delays

**Performance Metrics**:
- Target: <2 seconds per collection cycle
- Typical: 0.005-0.009 seconds per collection
- Timeout protection: 8 seconds maximum

## Error Handling Improvements

### Graceful Degradation

The system now includes comprehensive graceful degradation:

1. **Sensor Failures**: System continues with fallback data
2. **Hardware Unavailable**: Automatic simulation mode activation
3. **Communication Errors**: Retry logic with exponential backoff
4. **Resource Exhaustion**: Automatic resource management and throttling

### Circuit Breaker Pattern

Implemented circuit breakers for:
- Hardware component access
- Network operations
- File system operations
- External service calls

### Automatic Recovery

- **Transient Failures**: Automatic retry with backoff
- **Persistent Failures**: Graceful degradation with logging
- **Critical Failures**: Safe shutdown with state preservation
- **Hardware Recovery**: Automatic re-initialization when hardware becomes available

## System Validation

### Comprehensive Testing

The system includes comprehensive validation covering:

1. **System Startup**: Both hardware and simulation modes
2. **Major Functionality**: All core system features
3. **Error Handling**: Failure scenarios and recovery
4. **Performance**: Resource usage and timing metrics

### Running Validation

```bash
# Full system validation
python scripts/run_comprehensive_system_tests.py --verbose --output-file validation_report.txt

# Quick validation
python scripts/run_comprehensive_system_tests.py

# Specific component testing
python tools/test_sensors.py --all
```

### Expected Results

- **Overall Success**: 100% pass rate
- **Initialization Time**: <30 seconds
- **Memory Usage**: <600MB typical
- **Sensor Collection**: <2 seconds per cycle

## Troubleshooting Workflow

### Step 1: Check System Status

```bash
# Check service status
sudo systemctl status mower.service

# Check recent logs
tail -f /var/log/autonomous-mower/mower.log

# Check system resources
htop
df -h
```

### Step 2: Run Diagnostics

```bash
# Hardware diagnostics
python tools/test_sensors.py --all

# System validation
python scripts/run_comprehensive_system_tests.py

# Configuration validation
python scripts/validate_config.py
```

### Step 3: Check Hardware

```bash
# I2C devices
i2cdetect -y 1

# GPIO access
python -c "import RPi.GPIO as GPIO; print('GPIO OK')"

# Serial devices
ls -la /dev/tty*
```

### Step 4: Review Configuration

```bash
# Check configuration files
ls -la config/
cat config/main_config.json

# Validate configuration
python scripts/validate_config.py --verbose
```

### Step 5: Safe Mode Testing

If hardware issues persist:

```bash
# Enable safe mode
export SAFE_MODE_ALLOWED=true

# Start in safe mode
python -m mower.main_controller
```

### Step 6: Force Cleanup

If instance conflicts occur:

```bash
# Force cleanup
python -m mower.main_controller --force-cleanup

# Restart service
sudo systemctl restart mower.service
```

## Getting Additional Help

If issues persist after following this guide:

1. **Check Logs**: Review detailed logs in `/var/log/autonomous-mower/`
2. **Run Validation**: Use comprehensive system validation to identify specific issues
3. **Hardware Check**: Verify all hardware connections and power supply
4. **Configuration**: Ensure all configuration files are valid and complete
5. **Documentation**: Review specific component documentation in `docs/`
6. **Issue Tracker**: Search for similar issues or create a new issue with:
   - System information
   - Error messages
   - Steps to reproduce
   - Log files
   - Validation report