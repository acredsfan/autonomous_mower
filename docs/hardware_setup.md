# Hardware Setup

This document provides detailed instructions for setting up the hardware components of the Autonomous Mower.

## Overview

The Autonomous Mower requires several hardware components to function properly. This guide will walk you through the process of assembling and connecting these components.

## Required Components

### Core Components

- Raspberry Pi 4B (4GB RAM or better recommended)
- Raspberry Pi Camera Module v2 or v3
- RoboHAT motor controller board
- 2 x 12V DC motors with encoders (for drive wheels)
- 1 x 12V DC motor (for cutting blade)
- 12V LiPo battery (minimum 5000mAh recommended)
- Emergency stop button (normally closed)
- GPS module (e.g., NEO-6M)
- IMU sensor (e.g., BNO085)
- 3 x Ultrasonic distance sensors (HC-SR04)
- Optional: Google Coral USB Accelerator for improved obstacle detection

### Chassis and Mechanical Components

- Mower chassis (custom or modified from existing mower)
- 2 x Drive wheels (minimum 20cm diameter recommended)
- 1 x Castor wheel (front)
- Cutting blade assembly
- Blade guard
- Weatherproof enclosure for electronics
- Charging station

### Tools and Supplies

- Soldering iron and solder
- Wire cutters and strippers
- Heat shrink tubing
- Screwdrivers (Phillips and flathead)
- M3 and M4 screws and nuts
- Zip ties
- Electrical tape
- Multimeter

## Assembly Diagram

```
                                   +-------------+
                                   |  Raspberry  |
                                   |     Pi      |
                                   +------+------+
                                          |
                                          v
+-------------+    +-------------+    +---+---+    +-------------+
|    Camera   |<-->|    GPIO     |<-->| Robo  |<-->|  Motors &   |
|   Module    |    | Connections |    |  HAT  |    |   Blade     |
+-------------+    +------+------+    +---+---+    +-------------+
                          ^               |
                          |               v
                   +------+------+    +---+---+
                   |   Sensors   |    | Power |
                   | (GPS, IMU,  |    | Mgmt  |
                   | Ultrasonic) |    +---+---+
                   +-------------+        |
                                          v
                                   +------+------+
                                   |   Battery   |
                                   |   (12V)     |
                                   +-------------+
```

## Step-by-Step Assembly

### 1. Chassis Preparation

1. If using a modified existing mower, remove all original electronics and the gas/electric motor
2. Clean the chassis and ensure it's free from debris and sharp edges
3. Drill mounting holes for the Raspberry Pi, RoboHAT, and other components
4. Install the castor wheel at the front of the chassis
5. Mount the drive wheels and motors

![Chassis Preparation](images/chassis_preparation.jpg)

### 2. Electronics Mounting

1. Create a weatherproof enclosure for the electronics
2. Mount the Raspberry Pi in the enclosure
3. Mount the RoboHAT on top of or adjacent to the Raspberry Pi
4. Secure all connections with screws
5. Ensure adequate ventilation for cooling

![Electronics Mounting](images/electronics_mounting.jpg)

### 3. Motor Connections

1. Connect the drive motors to the RoboHAT:
   - Left motor: M1 terminals
   - Right motor: M2 terminals
2. Connect the blade motor to the RoboHAT:
   - Blade motor: M3 terminals
3. Connect the motor encoders to the encoder inputs on the RoboHAT

![Motor Connections](images/motor_connections.jpg)

### 4. Sensor Installation

#### Camera Module

1. Connect the camera module to the Raspberry Pi's camera port using the ribbon cable
2. Mount the camera at the front of the mower, facing forward
3. Ensure the camera has a clear view of the area in front of the mower
4. Secure the ribbon cable to prevent damage

![Camera Installation](images/camera_installation.jpg)

#### GPS Module

1. Connect the GPS module to the Raspberry Pi:
   - VCC to 3.3V
   - GND to GND
   - TX to GPIO15 (RXD)
   - RX to GPIO14 (TXD)
2. Mount the GPS module on top of the mower with a clear view of the sky
3. Use a GPS antenna if necessary for better reception

![GPS Installation](images/gps_installation.jpg)

#### IMU Sensor

1. Connect the IMU sensor to the Raspberry Pi's I2C pins:
   - VCC to 3.3V
   - GND to GND
   - SDA to GPIO2
   - SCL to GPIO3
2. Mount the IMU sensor securely to the chassis to minimize vibration
3. Ensure the sensor is oriented correctly (arrow pointing forward)

![IMU Installation](images/imu_installation.jpg)

#### Ultrasonic Sensors

1. Connect the ultrasonic sensors to the Raspberry Pi:
   - VCC to 5V
   - GND to GND
   - TRIG to GPIO pins (e.g., GPIO23, GPIO24, GPIO25)
   - ECHO to GPIO pins (e.g., GPIO17, GPIO27, GPIO22)
2. Mount the sensors:
   - Front sensor: Facing forward
   - Left sensor: Facing left
   - Right sensor: Facing right
3. Ensure the sensors have a clear view without obstructions

![Ultrasonic Installation](images/ultrasonic_installation.jpg)

### 5. Power System

1. Mount the battery securely in the chassis
2. Connect the battery to the RoboHAT power input:
   - Positive (red) to VIN
   - Negative (black) to GND
3. Install a power switch between the battery and RoboHAT
4. Add a fuse for protection (10A recommended)

![Power System](images/power_system.jpg)

### 6. Emergency Stop Button

1. Mount the emergency stop button in an easily accessible location
2. Connect the emergency stop button:
   - Wire the button between GPIO7 and GND
   - Ensure the button is normally closed (NC)
3. Test the emergency stop functionality

![Emergency Stop](images/emergency_stop.jpg)

### 7. Blade Assembly

1. Mount the cutting blade motor securely to the chassis
2. Attach the cutting blade to the motor shaft
3. Install the blade guard around the blade
4. Ensure the blade can spin freely without contacting any part of the chassis

![Blade Assembly](images/blade_assembly.jpg)

### 8. Charging Station

1. Assemble the charging station according to its instructions
2. Position it in a suitable location in your yard
3. Connect it to a power outlet
4. Test the connection between the mower and the charging station

![Charging Station](images/charging_station.jpg)

## Wiring Diagram

### Raspberry Pi GPIO Connections

| Component | GPIO Pin | Function |
|-----------|----------|----------|
| RoboHAT | Various | Motor control, I2C, etc. |
| GPS Module | GPIO14/15 | UART |
| IMU Sensor | GPIO2/3 | I2C |
| Ultrasonic (Front) | GPIO23/17 | TRIG/ECHO |
| Ultrasonic (Left) | GPIO24/27 | TRIG/ECHO |
| Ultrasonic (Right) | GPIO25/22 | TRIG/ECHO |
| Emergency Stop | GPIO7 | Input (NC) |

### RoboHAT Connections

| Terminal | Connection |
|----------|------------|
| M1 | Left Drive Motor |
| M2 | Right Drive Motor |
| M3 | Cutting Blade Motor |
| VIN | Battery Positive |
| GND | Battery Negative |
| ENC1 | Left Motor Encoder |
| ENC2 | Right Motor Encoder |

## Testing the Hardware

After completing the assembly, perform the following tests to ensure everything is working correctly:

### 1. Power Test

1. Turn on the power switch
2. Check that the Raspberry Pi powers up (green LED should light up)
3. Check that the RoboHAT powers up (status LEDs should light up)

### 2. Motor Test

1. Run the motor test script:
   ```bash
   python3 src/mower/diagnostics/motor_test.py
   ```
2. Verify that both drive motors and the blade motor function correctly

### 3. Sensor Test

1. Run the sensor test script:
   ```bash
   python3 src/mower/diagnostics/sensor_test.py
   ```
2. Verify that all sensors are providing valid readings

### 4. Emergency Stop Test

1. Start the mower in test mode
2. Press the emergency stop button
3. Verify that all motors stop immediately

## Troubleshooting

### Motors Not Running

1. Check power connections
2. Verify motor wiring
3. Check for blown fuses
4. Test motors directly with a battery

### Sensors Not Working

1. Check wiring connections
2. Verify GPIO pin assignments in software
3. Test sensors with simple test scripts
4. Check for hardware damage

### Raspberry Pi Not Booting

1. Check power supply
2. Verify SD card is properly inserted
3. Try a fresh OS installation
4. Check for physical damage

## Maintenance

Regular maintenance is essential for reliable operation:

1. **Weekly**:
   - Clean the blade and blade guard
   - Check all sensors for debris
   - Inspect wiring for damage

2. **Monthly**:
   - Check battery connections
   - Tighten any loose screws
   - Lubricate wheel bearings if necessary

3. **Quarterly**:
   - Check motor brushes (if applicable)
   - Inspect the chassis for damage
   - Clean the electronics enclosure

## Safety Considerations

- Always disconnect the battery before performing maintenance
- Keep hands away from the cutting blade
- Test the emergency stop button regularly
- Store the mower in a dry, secure location when not in use
- Follow all local regulations regarding autonomous devices

## Conclusion

With the hardware properly assembled and tested, your Autonomous Mower is ready for software installation and configuration. Refer to the [Software Setup](software_setup.md) guide for the next steps.

## References

- [Raspberry Pi GPIO Documentation](https://www.raspberrypi.org/documentation/usage/gpio/)
- [RoboHAT Documentation](https://robohat.org/docs)
- [Motor Specifications](https://www.example.com/motor_specs)
- [Sensor Datasheets](https://www.example.com/sensor_datasheets)