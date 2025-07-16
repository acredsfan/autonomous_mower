# Sensor Testing and Diagnostics

This document provides comprehensive information about testing and diagnosing sensor functionality in the Autonomous Mower project.

## Overview

The project includes several tools for testing sensor reliability, diagnosing hardware issues, and validating sensor performance. These tools range from simple real-time displays to comprehensive reliability assessments.

## Sensor Reliability Test

### Purpose

The `test_sensor_reliability.py` script provides a comprehensive evaluation of sensor consistency and performance over time. This is the primary tool for validating sensor improvements and diagnosing intermittent issues.

### Features

- **Real-time Monitoring**: Live display of sensor data with success rate calculations
- **Statistical Analysis**: Tracks success rates, value ranges, and operational status
- **Automatic Assessment**: Provides reliability ratings based on performance criteria
- **Timeout Protection**: Automatically terminates after 30 seconds
- **Detailed Reporting**: Comprehensive final report with performance metrics

### Usage

```bash
# Run the sensor reliability test
python3 test_sensor_reliability.py
```

### Sample Output

```
=== Sensor Reliability Test ===
Testing improved sensor implementation...
AsyncSensorManager started successfully!

[ 1] ToF: L= 245mm R= 312mm | Success: L= 100.0% R= 100.0% | Op: 5
[ 2] ToF: L= 248mm R= 315mm | Success: L= 100.0% R= 100.0% | Op: 5
[ 3] ToF: L= 251mm R= 318mm | Success: L= 100.0% R= 100.0% | Op: 5
...
[10]     === Status Report ===
       tof_left    : operational  (errors:  0, hw: True)
       tof_right   : operational  (errors:  0, hw: True)
       imu         : operational  (errors:  0, hw: True)
       bme280      : operational  (errors:  0, hw: True)
       ina3221     : operational  (errors:  0, hw: True)
       Left ToF    : avg= 248.0mm, range=245-251mm
       Right ToF   : avg= 315.0mm, range=312-318mm

=== FINAL RELIABILITY REPORT ===
Maximum operational sensors: 5
Left ToF sensor: 25/25 valid readings (100.0% success rate)
  Range: 245-251mm, Average: 248.0mm
Right ToF sensor: 25/25 valid readings (100.0% success rate)
  Range: 312-318mm, Average: 315.0mm

RELIABILITY ASSESSMENT:
✅ EXCELLENT - Both sensors >80% reliability
```

### Reliability Assessment Criteria

| Rating | Criteria | Description |
|--------|----------|-------------|
| **EXCELLENT** | Both sensors >80% success rate | Optimal performance, ready for production |
| **GOOD** | Both sensors >60% success rate | Acceptable performance with minor issues |
| **FAIR** | Both sensors >40% success rate | Marginal performance, may need attention |
| **POOR** | One or both sensors <40% success rate | Significant issues requiring investigation |

### When to Use

- **After Hardware Changes**: Validate sensor performance after hardware modifications
- **Troubleshooting**: Diagnose intermittent sensor issues
- **Performance Validation**: Establish baseline performance metrics
- **Quality Assurance**: Verify sensor reliability before deployment

## Basic Sensor Test Tool

### Purpose

The `tools/test_sensors.py` script provides a simple real-time display of sensor data for quick verification and monitoring.

### Features

- **Real-time Display**: Live sensor data with automatic screen refresh
- **Multi-sensor Support**: IMU, ToF, environmental, and safety sensors
- **Formatted Output**: Clear, organized display of sensor readings
- **Raw Data View**: JSON output for debugging purposes

### Usage

```bash
# Run basic sensor test
python3 tools/test_sensors.py
```

### Sample Output

```
=== Autonomous Mower Sensor Test ===
Platform: Linux
Running on hardware: Yes

--- IMU Data ---
Heading: 45.2°
Roll:    2.1°
Pitch:   -1.3°

--- Distance Sensors ---
Left:  245.0 mm
Right: 312.0 mm

--- Environment ---
Temperature: 22.5°C
Humidity:    55.3%
Pressure:    1013.2 hPa

--- Safety Status ---
Emergency Stop: ✓ OK
Tilt Warning: ✓ OK
Battery Low: ✓ OK
```

### When to Use

- **Quick Verification**: Rapid check of sensor functionality
- **Real-time Monitoring**: Continuous observation of sensor behavior
- **Initial Setup**: Verify sensors are working after installation
- **Development**: Monitor sensor data during development

## Hardware Diagnostic Test

### Purpose

The hardware diagnostic test provides comprehensive validation of all hardware components and their interactions.

### Usage

```bash
# Run comprehensive hardware diagnostics
python3 -m mower.diagnostics.hardware_test --non-interactive --verbose
```

### Features

- **Component Validation**: Tests all hardware components individually
- **Integration Testing**: Verifies component interactions
- **Error Detection**: Identifies hardware configuration issues
- **Detailed Reporting**: Comprehensive test results and recommendations

## Sensor-Specific Diagnostic Tools

### ToF Sensor Diagnostics

For Time-of-Flight sensor specific testing:

```bash
# Diagnose ToF sensor issues
python3 tools/diagnose_tof.py
```

### IMU Calibration and Testing

For IMU sensor calibration and validation:

```bash
# Test IMU functionality
python3 -m mower.hardware.imu
```

## Integration with AsyncSensorManager

### Understanding Sensor States

The AsyncSensorManager tracks sensor states and provides detailed status information:

- **operational**: Sensor is functioning normally
- **degraded**: Sensor has minor issues but is still functional
- **failed**: Sensor is not responding or has critical errors
- **unknown**: Sensor state cannot be determined

### Error Tracking

The system tracks consecutive errors for each sensor:
- **consecutive_errors**: Number of consecutive failed readings
- **is_hardware_available**: Whether the hardware is detected
- **last_successful_read**: Timestamp of last successful reading

## Troubleshooting Common Issues

### ToF Sensor Issues

**Symptoms**: Inconsistent distance readings, high error rates
**Solutions**:
1. Check I2C connections and addresses
2. Verify power supply stability
3. Run ToF-specific diagnostics
4. Check for I2C address conflicts

### IMU Sensor Issues

**Symptoms**: Incorrect orientation data, calibration failures
**Solutions**:
1. Verify UART connection and baud rate
2. Check IMU_SERIAL_PORT environment variable
3. Run IMU calibration procedure
4. Verify mounting orientation

### Environmental Sensor Issues

**Symptoms**: Missing temperature/humidity data
**Solutions**:
1. Check BME280 I2C connection
2. Verify sensor address (0x76 or 0x77)
3. Check power supply voltage
4. Run I2C bus scan

### Power Monitoring Issues

**Symptoms**: Incorrect battery/power readings
**Solutions**:
1. Verify INA3221 connections
2. Check shunt resistor values
3. Calibrate current measurements
4. Verify I2C address

## Performance Monitoring

### Sensor Performance Metrics

Key metrics to monitor:
- **Success Rate**: Percentage of successful readings
- **Response Time**: Time between request and response
- **Data Consistency**: Variation in readings over time
- **Error Frequency**: Rate of sensor errors

### Benchmarking

For performance benchmarking:

```bash
# Run sensor performance benchmarks
pytest tests/benchmarks/ -k sensor
```

## Best Practices

### Regular Testing

- Run reliability tests after hardware changes
- Monitor sensor performance during development
- Establish baseline metrics for comparison
- Document performance characteristics

### Error Handling

- Implement graceful degradation for sensor failures
- Use redundant sensors where possible
- Log sensor errors for analysis
- Provide user feedback for sensor issues

### Maintenance

- Regular sensor cleaning and calibration
- Monitor sensor drift over time
- Replace sensors showing degraded performance
- Keep sensor firmware updated

## Integration with CI/CD

### Automated Testing

Sensor tests can be integrated into continuous integration:

```bash
# Run sensor tests in CI environment
pytest tests/hardware_integration/test_enhanced_tof_reliability.py
```

### Simulation Mode

For testing without hardware:

```bash
# Enable simulation mode
export USE_SIMULATION=True
python3 test_sensor_reliability.py
```

## Logging and Monitoring

### Log Analysis

Sensor performance logs are available in:
- `/var/log/autonomous-mower/mower.log`: General application logs
- `/var/log/autonomous-mower/sensor.log`: Sensor-specific logs (if configured)

### Real-time Monitoring

For continuous monitoring:

```bash
# Monitor sensor logs in real-time
tail -f /var/log/autonomous-mower/mower.log | grep -i sensor
```

## Advanced Diagnostics

### Custom Test Scripts

Create custom test scripts for specific scenarios:

```python
#!/usr/bin/env python3
import asyncio
from mower.hardware.async_sensor_manager import AsyncSensorManager

async def custom_sensor_test():
    async with AsyncSensorManager(simulate=False) as manager:
        for i in range(100):
            data = await manager.get_sensor_data()
            # Custom analysis logic here
            await asyncio.sleep(0.1)

if __name__ == "__main__":
    asyncio.run(custom_sensor_test())
```

### Data Collection

For long-term analysis:

```bash
# Collect sensor data for analysis
python3 test_sensor_reliability.py > sensor_performance_$(date +%Y%m%d_%H%M%S).log
```

## Conclusion

The sensor testing and diagnostic tools provide comprehensive coverage for validating sensor performance, diagnosing issues, and ensuring reliable operation. Regular use of these tools helps maintain optimal system performance and quickly identify potential problems.

For additional support or questions about sensor testing, refer to the troubleshooting guides or create an issue in the project repository.