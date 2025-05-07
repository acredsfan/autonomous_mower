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
