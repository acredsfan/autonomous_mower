# Hardware Setup

This document provides detailed instructions for setting up the hardware components of the Autonomous Mower.

## Overview

## Software Dependencies

- Python 3.9 or newer is required (Raspberry Pi OS Bookworm).
- Install system dependencies:

```bash
sudo apt-get update
sudo apt-get install -y libatlas-base-dev
```

- Ensure compatible GPIO libraries:
  - gpiozero (>=1.7)
  - RPi.GPIO (>=0.7)

The Autonomous Mower requires several hardware components to function properly. This guide will walk you through the process of assembling and connecting these components.

## Required Components

### Core Components

- Raspberry Pi 4B (4GB RAM or better recommended)
- Raspberry Pi Camera Module v2 or v3
- RoboHAT motor controller board
- 2 x 12V Worm Gear DC motors (Hall Sensors added Separately) (for drive wheels)
- 1 x 12V DC motor (for cutting blade such as a 997 DC motor)
- Cytron MDDRC10 board for Wheel Motor controller
- IBT-4 Driver for Blade Motor
- 12V 20AH LiFePO4 Battery
- Optional but recommended: Emergency stop button (normally closed)
- GPS module with RTK compatibility (e.g., SparkFun GPS-RTK-SMA Kit)
- IMU sensor (e.g., BNO085)
- 2 x VL53L0X Time of Flight Sensors
- INA3221 Power Monitor
- Optional: Google Coral USB Accelerator for improved obstacle detection

### Chassis and Mechanical Components

- Mower chassis (e.g. https://cults3d.com/en/3d-model/home/pimowrobot-case or modified from existing mower)
- 30W 12V Solar Panel (e.g., Offgridtec 30W)
- 10A 12V Solar Charge Controller (e.g., Renogy)
- DC 12V/24V to 5V Step Down Converter With USB C output
- Charging station (alternative to solar charging)

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

1. Connect the drive motors to the MDDRC10 motor driver:
   - Left motor: M1 terminals
   - Right motor: M2 terminals
   - The MDDRC10 takes input from the RoboHAT (RC inputs and encoder inputs)
2. Connect the 997 DC motor for blades to the IBT-4 motor driver:
   - Connect the IBT-4 driver to the appropriate GPIO pins (see Raspberry Pi GPIO.xlsx)
3. Connect the motor encoders (Hall Sensors) to the encoder inputs on the RoboHAT

![Motor Connections](images/motor_connections.jpg)

### 4. Sensor Installation

#### Camera Module

1. Connect the camera module to the Raspberry Pi's camera port using the ribbon cable
2. Mount the camera at the front of the mower, facing forward
3. Ensure the camera has a clear view of the area in front of the mower
4. Secure the ribbon cable to prevent damage

![Camera Installation](images/camera_installation.jpg)

#### GPS Module with RTK Compatibility

1. Connect the GPS module (e.g., SparkFun GPS-RTK-SMA Kit) to the Raspberry Pi's USB port:
   - Connect the GPS module to any available USB port on the Raspberry Pi
2. Mount the GPS module on top of the mower with a clear view of the sky
3. Use the included GPS antenna for better reception
4. For RTK functionality (millimeter accuracy):
   - Set up a base station OR
   - Subscribe to an NTRIP correction service
   - If centimeter accuracy (1.5-2.5 meters) is sufficient, a NEO-M9N or NEO-M8N can be used without RTK

![GPS Installation](images/gps_installation.jpg)

#### IMU Sensor

1. Connect the IMU sensor to the Raspberry Pi's second UART:
   - VCC to 3.3V
   - GND to GND
   - Refer to Raspberry Pi GPIO.xlsx for proper UART pins
2. Enable the second UART in Raspberry Pi configuration:
   - Edit /boot/config.txt to add the necessary overlay for the second UART
   - Reboot the Raspberry Pi after making changes
3. Mount the IMU sensor securely to the chassis to minimize vibration
4. Ensure the sensor is oriented correctly (arrow pointing forward)

![IMU Installation](images/imu_installation.jpg)

#### VL53L0X Time of Flight Sensors

1. Connect the VL53L0X sensors to the Raspberry Pi's I2C pins:
   - VCC to 3.3V
   - GND to GND
   - SDA to GPIO2/RoboHAT SDA (I2C1 SDA)
   - SCL to GPIO3/RoboHAT SCL (I2C1 SCL)
   - Connect XSHUT pins to GPIO pins for address configuration
   - Left sensor uses I2C address 0x29
   - Right sensor uses I2C address 0x30
2. Mount the sensors:
   - Left sensor: Facing left for obstacle detection
   - Right sensor: Facing right for obstacle detection
3. Ensure the sensors have a clear view without obstructions

![ToF Sensors Installation](images/tof_installation.jpg)

### 5. Power System

1. Mount the 12V 20AH LiFePO4 battery securely in the chassis
   - LiFePO4 batteries are preferred for their safety, longer lifespan, and stable discharge
   - Ensure proper ventilation around the battery
2. Connect the battery to the Step Down Converter:
3. Connect the battery to all 12V components:
   - IBT-4 motor driver
   - MDDRC10 motor driver
4. Connect the Step Down Converter's USB C output to the Raspberry Pi's power input

![Power System](images/power_system.jpg)

### 6. Emergency Stop Button (Optional)

1. Mount the emergency stop button in an easily accessible location
2. Connect the emergency stop button:
   - Wire the button between GPIO7 and GND
   - Ensure the button is normally closed (NC) for fail-safe operation
3. Test the emergency stop functionality
4. The emergency stop button is optional - the system can operate without it by setting the `safety.use_physical_emergency_stop` option to `False` in the configuration
5. When no physical button is present, the software will provide an emergency stop feature through the user interface

![Emergency Stop](images/emergency_stop.jpg)

### 7. Blade Assembly

1. Mount the cutting blade motor securely to the chassis
2. Attach the cutting blade to the motor shaft
3. Install the blade guard around the blade
4. Ensure the blade can spin freely without contacting any part of the chassis

![Blade Assembly](images/blade_assembly.jpg)

### 8. Power System Options

#### Solar Charging (Primary Option)

1. Mount the solar panel securely on top of the mower
2. Connect the solar panel to the charge controller:
   - Positive (red) to the solar input positive terminal
   - Negative (black) to the solar input negative terminal
3. Connect the charge controller to the battery:
   - Positive (red) to the battery output positive terminal
   - Negative (black) to the battery output negative terminal
4. Position the solar panel for maximum sun exposure

![Solar Charging](images/solar_charging.jpg)

#### Charging Station (Alternative Option)

1. Assemble the charging station according to its instructions
2. Position it in a suitable location in your yard
3. Connect it to a power outlet
4. Test the connection between the mower and the charging station

![Charging Station](images/charging_station.jpg)

## Wiring Diagram

### Raspberry Pi GPIO Connections

| Component                 | Connection                 | Function                                  |
| ------------------------- | -------------------------- | ----------------------------------------- |
| RoboHAT                   | Various GPIO pins          | Motor control, RC inputs, encoder inputs  |
| GPS Module (RTK)          | USB Port                   | Serial communication                      |
| IMU Sensor                | Second UART (/dev/ttyAMA2) | Orientation data                          |
| VL53L0X Sensors           | GPIO2/3                    | I2C (shared bus, addresses 0x29 and 0x30) |
| IBT-4 Motor Driver        | Various GPIO pins          | Blade motor control                       |
| INA3221 Power Monitor     | GPIO pins                  | Battery/Power Monitoring                  |
| Emergency Stop (Optional) | GPIO7                      | Input (NC)                                |

### RoboHAT Connections

| Terminal | Connection              |
| -------- | ----------------------- |
| VIN      | Battery Positive        |
| GND      | Battery Negative        |
| ENC1     | Left Motor Hall Sensor  |
| ENC2     | Right Motor Hall Sensor |

### MDDRC10 Motor Driver Connections

| Terminal | Connection          |
| -------- | ------------------- |
| IN1      | RoboHAT RC Throttle |
| IN2      | RoboHAT RC Steering |
| M1       | Left Drive Motor    |
| M2       | Right Drive Motor   |
| VIN      | Battery Positive    |
| GND      | Battery Negative    |

### IBT-4 Motor Driver Connections

| Terminal     | Connection         |
| ------------ | ------------------ |
| PWM Input    | RoboHAT RC3 output |
| Motor Output | 997 DC Blade Motor |
| VIN          | Battery Positive   |
| GND          | Battery Negative   |

### Solar Charging Connections

| Component                   | Connection                      |
| --------------------------- | ------------------------------- |
| Solar Panel +               | Charge Controller Solar Input + |
| Solar Panel -               | Charge Controller Solar Input - |
| Charge Controller Battery + | Battery Positive                |
| Charge Controller Battery - | Battery Negative                |
| Charge Controller Load +    | RoboHAT VIN (optional)          |
| Charge Controller Load -    | RoboHAT GND (optional)          |

## GPIO Pin Configuration

The following table lists the GPIO pin assignments for the Autonomous Mower:

| Component           | GPIO Pin | Direction | Description                          |
| ------------------- | -------- | --------- | ------------------------------------ |
| Blade Enable        | 17       | Output    | Controls the blade motor             |
| Blade Direction     | 27       | Output    | Sets the blade motor direction       |
| Emergency Stop      | 7        | Input     | Emergency stop button (NC, optional) |
| Left Motor Control  | 22       | Output    | Controls the left drive motor        |
| Right Motor Control | 23       | Output    | Controls the right drive motor       |

Ensure these pins are connected as per the wiring diagram and configured in the software.

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

### 4. Emergency Stop Test (if installed)

1. Start the mower in test mode
2. Press the emergency stop button
3. Verify that all motors stop immediately

### 5. Solar Charging Test (if using solar panel)

1. Place the solar panel in direct sunlight
2. Check the charge controller indicators
3. Verify that the battery is receiving charge
4. Measure the voltage at the battery terminals to confirm charging

## Troubleshooting

### Motors Not Running

1. Check power connections
2. Verify motor wiring
3. Check for blown fuses
4. Test motors directly with a battery

### Sensors Not Working

1. Check wiring connections
2. Verify I2C addresses for VL53L0X sensors
3. Check I2C bus with `i2cdetect -y 1` command
4. Test sensors with simple test scripts
5. Check for hardware damage

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
- [VL53L0X Time of Flight Sensor Datasheet](https://www.st.com/resource/en/datasheet/vl53l0x.pdf)
- [SparkFun GPS-RTK-SMA Kit Documentation](https://learn.sparkfun.com/tutorials/gps-rtk-hookup-guide)
- [LiFePO4 Battery Information](https://www.batteryspace.com/lifepo4-batteries.aspx)
- [Renogy Solar Charge Controller Manual](https://www.renogy.com/template/files/Manuals/10A%20Charge%20Controller%20Manual.pdf)
- [RTK GPS Guide](https://learn.sparkfun.com/tutorials/what-is-gps-rtk/all)

## Emergency Stop Configuration

### Physical Emergency Stop Button

The physical emergency stop button is an optional safety feature that provides a hardware-based emergency shutdown capability. When installed:

1. The button should be wired between GPIO7 and GND
2. It should be a normally closed (NC) button, which opens the circuit when pressed
3. This fail-safe design ensures that if the button is pressed or the wire is disconnected, the mower will stop

### Software Configuration

To configure the emergency stop button in software:

1. During installation, you will be prompted whether to set up a physical emergency stop button
2. You can modify this setting later in the configuration:

```json
{
  "safety": {
    "use_physical_emergency_stop": true, // Set to false if no physical button is installed
    "emergency_stop_pin": 7
    // Other safety settings...
  }
}
```

3. When `use_physical_emergency_stop` is set to `false`:
   - The system will operate without checking for a physical button
   - Emergency stop functionality is still available through the web interface
   - A warning message will be displayed during startup

### Testing

After installation:

1. Press the emergency stop button (if installed)
2. Verify that the mower immediately stops all operations
3. Check the web interface to confirm the EMERGENCY_STOP state is active
4. Reset the button and verify normal operation can resume
