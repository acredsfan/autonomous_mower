# Troubleshooting: Sensor Issues

This guide covers common I²C sensor issues and how to resolve them.

## Symptoms

- I²C devices disappear from the bus (`i2cdetect` shows no address)
- Address conflicts when multiple sensors use the same default address
- Bus busy or locking errors (e.g., `Input/output error`)

## Possible Causes

- Incorrect wiring or loose connections
- Missing or incorrect pull-up resistors on SDA/SCL lines
- Two devices sharing the same I²C address without address configuration
- Sensors not properly initialized in software
- Insufficient bus power or voltage level mismatch

## Solutions

1. Check wiring

   - Ensure SDA to SDA (GPIO2) and SCL to SCL (GPIO3)
   - Verify ground connections between Pi and sensor board

2. Verify I²C bus with:

   ```bash
   i2cdetect -y 1
   ```

   - Confirm sensor addresses appear
   - If missing, power-cycle the sensor

3. Configure unique I²C addresses

   - Use XSHUT or address selection pins (e.g., VL53L0X sensors)
   - Refer to sensor datasheet for address configuration

4. Add pull-up resistors (4.7kΩ–10kΩ) if missing

   - Check that boards include pull-ups by default

5. Re-initialize sensors in software

   - Use the `SensorInterface` API to reopen I²C bus
   - Catch and handle `IOError` or `OSError` exceptions

6. Increase I²C bus timeout or retries

   - Configure retry logic in `hardware/sensor_interface.py`

7. Check for voltage compatibility

   - Ensure sensor VCC matches Pi 3.3V logic levels

8. Review test logs
   - Refer to `tests/integration/test_i2c_sensor_stability.py` for stability patterns

## Diagnostic Tools

### Sensor Reliability Test

Use the comprehensive sensor reliability test to diagnose intermittent sensor issues:

```bash
# Run 30-second sensor reliability assessment
python3 test_sensor_reliability.py
```

This test provides:
- Real-time success rate monitoring for each sensor
- Detailed statistics on sensor performance
- Reliability assessment (EXCELLENT/GOOD/FAIR/POOR)
- Operational status tracking with error counts

**Example output for problematic sensors:**
```
[15] ToF: L= -1mm R= 312mm | Success: L= 60.0% R= 100.0% | Op: 4
     === Status Report ===
       tof_left    : degraded     (errors:  6, hw: True)
       tof_right   : operational  (errors:  0, hw: True)

RELIABILITY ASSESSMENT:
⚠️  FAIR - Both sensors >40% reliability
```

### Basic Sensor Test

For quick sensor verification:

```bash
# Real-time sensor data display
python3 tools/test_sensors.py
```

### Hardware Diagnostics

For comprehensive hardware validation:

```bash
# Full hardware diagnostic test
python3 -m mower.diagnostics.hardware_test --non-interactive --verbose
```

## Sensor-Specific Issues

### ToF Sensor (VL53L0X) Issues

**Symptoms**: Inconsistent distance readings, -1 values, high error rates

**Solutions**:
1. Check I2C address conflicts (default 0x29)
2. Verify XSHUT pin connections for address programming
3. Ensure adequate power supply (3.3V, sufficient current)
4. Run ToF-specific diagnostics:
   ```bash
   python3 tools/diagnose_tof.py
   ```

### IMU Sensor Issues

**Symptoms**: Incorrect orientation data, calibration failures

**Solutions**:
1. Verify UART connection and baud rate settings
2. Check `IMU_SERIAL_PORT` environment variable
3. Run IMU test:
   ```bash
   python3 -m mower.hardware.imu
   ```
4. Perform IMU calibration procedure

### Environmental Sensor (BME280) Issues

**Symptoms**: Missing temperature/humidity/pressure data

**Solutions**:
1. Verify I2C address (0x76 or 0x77)
2. Check sensor power supply voltage
3. Ensure proper I2C pull-up resistors
4. Test with basic I2C scan

For detailed sensor testing procedures, see the [Sensor Testing Guide](../sensor_testing.md).
