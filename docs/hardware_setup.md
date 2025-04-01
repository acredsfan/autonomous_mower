# Hardware Setup Guide

This guide provides comprehensive instructions for setting up the hardware components of the Autonomous Mower system. Follow these steps carefully to ensure proper connections and configuration.

## Table of Contents

1. [System Overview](#system-overview)
2. [Required Components](#required-components)
3. [Wiring Diagram](#wiring-diagram)
4. [Component Setup](#component-setup)
   - [Raspberry Pi](#raspberry-pi)
   - [Motor Control](#motor-control)
   - [GPS and Navigation](#gps-and-navigation)
   - [Sensors](#sensors)
   - [Power System](#power-system)
   - [Camera](#camera)
5. [Hardware Testing](#hardware-testing)
6. [Troubleshooting](#troubleshooting)

## System Overview

The autonomous mower hardware system consists of several interconnected components:

- **Computing Core**: Raspberry Pi that runs the main control software
- **Motor Control System**: Drives wheel motors and blade motors
- **Navigation System**: GPS and IMU for position tracking and heading
- **Sensor System**: Various sensors for obstacle detection and environmental monitoring
- **Power System**: Battery, charging system, and power management
- **Communications**: WiFi connectivity for remote monitoring and control

All these components work together to create a robust autonomous mowing platform capable of navigating your yard safely and efficiently.

## Required Components

### Essential Components

| Component | Recommended Model | Quantity | Purpose |
|-----------|-------------------|----------|---------|
| Single-board Computer | Raspberry Pi 4 (4GB+) | 1 | Main controller |
| Motor Driver | RoboHAT Motor Controller | 1 | Controls wheel motors |
| Wheel Motors | 12V Worm Gear Motors | 2 | Propulsion system |
| Blade Motor | 12V DC Motor (997 type) | 1 | Cutting system |
| Blade Motor Controller | IBT-4 Motor Driver | 1 | Controls blade motors |
| GPS Module | GPS-RTK-SMA or NEO-M8N | 1 | Position tracking |
| IMU | BNO085 Sensor | 1 | Orientation tracking |
| Distance Sensors | VL53L0X ToF Sensors | 2+ | Obstacle detection |
| Camera | Raspberry Pi Camera Module | 1 | Visual navigation |
| Environmental Sensor | BME280 | 1 | Weather monitoring |
| Power Monitor | INA3221 | 1 | Battery management |
| Battery | 12V 20AH LiFePO4 | 1 | Power supply |
| Solar Panel | 20W 12V Panel | 1 | Battery charging |
| Solar Charge Controller | 10A 12V Controller | 1 | Charge management |
| WiFi Adapter | AC1300 WiFi Adapter | 1 | Connectivity |
| DC-DC Converter | 12V to 5V Buck Converter | 1 | Power regulation |
| I2C Splitter | I2C Hub | 1 | Sensor connections |
| Hall Effect Sensors | KY-003 | 2 | Wheel encoders |

### Tools Required

- Soldering iron and solder
- Wire strippers
- Heat shrink tubing
- Multimeter
- Screwdriver set
- Wire cutters
- Crimping tool and connectors
- Cable ties

## Wiring Diagram

![Wiring Diagram](images/wiring_diagram.png)

*Note: The above image shows the complete wiring diagram for all components. Follow this diagram for proper connections.*

## Component Setup

### Raspberry Pi

1. **Initial Setup**:
   - Flash Raspberry Pi OS (64-bit) to the microSD card
   - Configure WiFi and enable SSH, I2C, SPI, and Serial interfaces
   - Update the system: `sudo apt update && sudo apt upgrade -y`

2. **Connections**:
   - Connect 5V power from the buck converter
   - Connect the I2C bus to the I2C splitter
   - Connect the SPI bus to the appropriate sensors
   - Connect the camera to the CSI port
   - Connect the USB WiFi adapter

3. **Configuration**:
   ```bash
   # Enable I2C
   sudo raspi-config nonint do_i2c 0
   
   # Enable SPI
   sudo raspi-config nonint do_spi 0
   
   # Enable camera
   sudo raspi-config nonint do_camera 0
   
   # Enable serial (disable login shell, enable hardware)
   sudo raspi-config nonint do_serial 2
   ```

### Motor Control

#### RoboHAT Motor Controller

1. **Installation**:
   - Connect the RoboHAT to the Raspberry Pi's GPIO pins
   - Secure it with standoffs to prevent movement

2. **Motor Connections**:
   - Connect left wheel motor to outputs M1A and M1B
   - Connect right wheel motor to outputs M2A and M2B
   - Connect the motor power input to the battery (12V)
   - Ensure proper polarity on all connections

3. **Configuration**:
   - Upload the `rp2040_code.py` from the `robohat_files` directory to the RoboHAT's RP2040 microcontroller
   - Rename it to `code.py` on the controller
   - Connect to the Raspberry Pi via I2C (default address: 0x40)

#### Blade Motor Controller (IBT-4)

1. **Connections**:
   - Connect R_EN and L_EN to 5V (enable pins)
   - Connect RPWM to GPIO23 on the Raspberry Pi
   - Connect LPWM to GPIO24 on the Raspberry Pi
   - Connect VCC to 5V
   - Connect GND to ground
   - Connect motor outputs to the blade motor
   - Connect power input to the battery (12V)

2. **Testing**:
   ```bash
   # Install GPIO library if not already installed
   sudo pip3 install RPi.GPIO
   
   # Test blade motor (forward)
   python3 -m mower.diagnostics.blade_test
   ```

### GPS and Navigation

#### GPS Module

1. **Mounting**:
   - Mount the GPS antenna on the highest point of the mower with a clear view of the sky
   - Keep the antenna away from other electronics to minimize interference
   - Use a ground plane under the antenna if possible for better reception

2. **Connections**:
   - Connect the GPS module to the Raspberry Pi via UART
   - Connect VCC to 3.3V
   - Connect GND to ground
   - Connect TX to RXD (GPIO15) on the Raspberry Pi
   - Connect RX to TXD (GPIO14) on the Raspberry Pi

3. **Configuration**:
   - Set the baud rate to 9600 (default) or 115200 if using a high-speed module
   - Update the `.env` file with the correct serial port: `GPS_SERIAL_PORT=/dev/ttyAMA0`

#### BNO085 IMU

1. **Mounting**:
   - Mount the IMU on a flat, level surface
   - Align the forward axis with the forward direction of the mower
   - Secure it firmly to prevent vibration

2. **Connections**:
   - Connect the IMU to the I2C splitter
   - Connect VIN to 3.3V
   - Connect GND to ground
   - Connect SCL to the I2C clock line
   - Connect SDA to the I2C data line

3. **Calibration**:
   - Run the calibration procedure: `python3 -m mower.diagnostics.imu_calibration`
   - Follow the on-screen instructions to perform the calibration movements
   - Verify proper operation with: `python3 -m mower.diagnostics.imu_test`

### Sensors

#### VL53L0X Distance Sensors

1. **Mounting**:
   - Mount sensors at the front of the mower, facing forward
   - Position multiple sensors to cover different angles (e.g., front-left, front-center, front-right)
   - Protect sensors from direct sunlight and water

2. **Connections**:
   - Connect each sensor to the I2C splitter
   - Connect VIN to 3.3V
   - Connect GND to ground
   - Connect SCL to the I2C clock line
   - Connect SDA to the I2C data line
   - Connect XSHUT pins to GPIO pins for address configuration:
     - Sensor 1: GPIO4
     - Sensor 2: GPIO17
     - Sensor 3: GPIO27 (if using a third sensor)

3. **Address Configuration**:
   - The software will automatically assign different I2C addresses to multiple VL53L0X sensors
   - Default addresses start at 0x29 and increment for each additional sensor

#### BME280 Environmental Sensor

1. **Mounting**:
   - Mount the sensor in a location with good airflow
   - Protect it from direct sunlight and rain

2. **Connections**:
   - Connect the sensor to the I2C splitter
   - Connect VIN to 3.3V
   - Connect GND to ground
   - Connect SCL to the I2C clock line
   - Connect SDA to the I2C data line

3. **Testing**:
   - Verify proper operation with: `python3 -m mower.diagnostics.bme280_test`

#### Hall Effect Sensors (Wheel Encoders)

1. **Mounting**:
   - Attach magnets to the wheel hubs
   - Mount the Hall effect sensors close to the path of the magnets
   - Adjust the position to ensure reliable triggering

2. **Connections**:
   - Connect VCC to 3.3V
   - Connect GND to ground
   - Connect signal pin to GPIO inputs:
     - Left wheel: GPIO5
     - Right wheel: GPIO6

3. **Testing**:
   - Verify proper operation with: `python3 -m mower.diagnostics.encoder_test`

### Power System

#### Battery and Power Management

1. **Battery Setup**:
   - Mount the LiFePO4 battery securely in the mower chassis
   - Connect the battery to the power distribution system
   - Install a main power switch for emergency shutdown
   - Add appropriate fusing for all major circuits

2. **Solar Charging System**:
   - Mount the solar panel on top of the mower, angled for optimal sun exposure
   - Connect the solar panel to the charge controller
   - Connect the charge controller to the battery
   - Configure the charge controller for LiFePO4 batteries

3. **Power Distribution**:
   - Connect the DC-DC buck converter to the battery
   - Set the output of the buck converter to 5V
   - Connect the 5V output to the Raspberry Pi
   - Connect the 12V battery directly to the motor controllers

4. **INA3221 Power Monitor**:

   - **Connections**:
     - Connect the sensor to the I2C splitter
     - Connect V+ to 3.3V
     - Connect GND to ground
     - Connect SCL to the I2C clock line
     - Connect SDA to the I2C data line
     - Connect Channel 1 to monitor battery voltage and current
     - Connect Channel 2 to monitor motor current (optional)
     - Connect Channel 3 to monitor solar panel output (optional)

   - **Configuration**:
     - Configure the shunt resistor values in the software to match your setup
     - Set appropriate voltage and current thresholds in the `.env` file

### Camera

1. **Mounting**:
   - Mount the camera at the front of the mower for obstacle detection
   - Position it to have a clear view of the ground ahead
   - Protect it from direct sunlight and water

2. **Connections**:
   - Connect the camera to the Raspberry Pi's CSI port using the ribbon cable
   - Ensure the cable is properly seated on both ends

3. **Testing**:
   - Verify proper operation with: `python3 -m mower.diagnostics.camera_test`

## Hardware Testing

After completing all connections, run the comprehensive hardware test to verify all components are working correctly:

```bash
python3 -m mower.diagnostics.hardware_test
```

This will test each component and report any issues found. Address any failures before proceeding to operation.

## Troubleshooting

### General Troubleshooting

1. **Check Power First**: Always verify that components are receiving the correct voltage.
2. **Inspect Connections**: Look for loose wires, poor solder joints, or disconnected cables.
3. **Verify Ground Connections**: Many issues stem from improper grounding.
4. **Check for Shorts**: Use a multimeter to check for short circuits.
5. **Review Logs**: Check system logs for error messages: `tail -f /var/log/syslog`

### Component-Specific Issues

#### Raspberry Pi Issues

- **Won't Boot**: Check power supply, SD card, and connections.
- **Overheating**: Ensure proper ventilation and consider adding a heat sink or fan.
- **Crashes Randomly**: Check for power supply issues or SD card corruption.

#### Motor Control Issues

- **Motors Don't Run**: Check connections, power, and motor driver configuration.
- **Motors Run in Wrong Direction**: Swap the motor leads or reverse direction in software.
- **Erratic Movement**: Check for loose connections or interference with the motor driver.

#### GPS Issues

- **No Fix**: Ensure the antenna has a clear view of the sky and check connections.
- **Poor Accuracy**: Verify antenna placement and consider using RTK corrections.
- **Serial Communication Errors**: Check baud rate settings and UART configuration.

#### Sensor Issues

- **I2C Device Not Found**: Check connections, verify I2C is enabled, and check addresses.
- **Incorrect Readings**: Calibrate sensors and check for interference.
- **Intermittent Operation**: Check for loose connections or power issues.

#### Power System Issues

- **Low Battery Voltage**: Check charging system and battery health.
- **Overheating Components**: Check for current draw issues or inadequate cooling.
- **Solar Panel Not Charging**: Verify connections and ensure panel has sunlight exposure.

#### Camera Issues

- **No Image**: Check ribbon cable connections and camera module integrity.
- **Poor Image Quality**: Clean lens and adjust camera settings.
- **High CPU Usage**: Adjust resolution and frame rate in settings.

### Advanced Troubleshooting

For persistent issues, use these diagnostic commands:

- **I2C Bus Scan**: `i2cdetect -y 1`
- **USB Device List**: `lsusb`
- **Serial Port List**: `ls -la /dev/tty*`
- **GPIO Status**: `gpio readall`
- **System Resource Usage**: `htop`
- **Network Connectivity**: `iwconfig` or `ifconfig`

### Getting Help

If you encounter issues you cannot resolve, please:

1. Check the project documentation for known issues
2. Search the GitHub issues for similar problems
3. Create a new issue with detailed information about the problem
4. Include logs, photos of connections, and steps to reproduce the issue

## Maintenance

Perform regular maintenance to keep your autonomous mower functioning properly:

1. **Weekly Checks**:
   - Inspect all electrical connections
   - Check blade sharpness and balance
   - Clean camera lens and sensors
   - Verify wheel operation and check for debris

2. **Monthly Checks**:
   - Calibrate the IMU
   - Check battery health and charging system
   - Update software to the latest version
   - Inspect chassis and mechanical components
   - Clean or replace air filters (if installed)

3. **Seasonal Maintenance**:
   - Replace blades if needed
   - Check motor bearings and lubricate if necessary
   - Clean solar panel surface
   - Verify waterproofing integrity
   - Recalibrate sensors

By following these maintenance procedures, you can ensure reliable operation of your autonomous mower throughout its service life. 