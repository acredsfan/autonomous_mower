## Configuring the RoboHAT MM1 Motor Controller

The mower application uses the **RoboHAT MM1 by Robotics Masters** to control the motors. This HAT communicates with the Raspberry Pi via a serial (UART) connection. Proper configuration of this connection is crucial for the mower's operation.

### Key Considerations:

1.  **Serial Port Configuration (`MM1_SERIAL_PORT`)**:
    *   The application determines which serial port to use for the RoboHAT MM1 by reading the `MM1_SERIAL_PORT` environment variable from your `.env` file.
    *   If this variable is not set in your `.env` file, it defaults to `/dev/ttyS0`.
    *   **Critical**: The default `/dev/ttyS0` (mini UART) on a Raspberry Pi is often used by the Linux serial console or by the Bluetooth module. If it's in use by another service, the RoboHAT MM1 will not be able to communicate.
    *   **Action Required**:
        *   You **must** ensure that the serial port assigned to `MM1_SERIAL_PORT` in your `.env` file is exclusively available for the RoboHAT MM1.
        *   If you have configured another device (like a GPS module) to use `/dev/ttyS0`, or if the serial console is active on it, you **must** assign a different, available serial port to the RoboHAT MM1 (e.g., `/dev/ttyAMA0` if it's free) and update the `MM1_SERIAL_PORT` variable in your `.env` file accordingly.
        *   Refer to the "Serial Port Considerations" section in the main Raspberry Pi Configuration Guide for details on identifying and configuring serial ports (`/dev/ttyS0`, `/dev/ttyAMA0`, `serial0`, `serial1`).

2.  **Hardware Connection and Power**:
    *   Ensure the RoboHAT MM1 is correctly and securely seated on the Raspberry Pi's GPIO headers.
    *   The RoboHAT MM1 and the motors it drives must be adequately powered according to the HAT's specifications. Insufficient power can lead to erratic behavior or complete failure to operate.
    *   Verify all wiring between the RoboHAT MM1 and the motors.

3.  **Serial Port Permissions**:
    *   The user running the mower application must have permission to access the serial port defined by `MM1_SERIAL_PORT`.
    *   This is typically achieved by adding the user to the `dialout` group.
    *   This step should have been completed during the initial Raspberry Pi setup (as outlined in the "User Group Management" section of the Raspberry Pi Configuration Guide). If you encounter permission errors related to the serial port, double-check that your user is part of the `dialout` group and that you have rebooted or logged out/in since the change was made.

**Troubleshooting Example**:

If the logs show errors like "Serial port for PWM output not found!" or "Failed to write PWM command," consider the following:
*   Is `MM1_SERIAL_PORT` in `.env` set to the correct, available serial port?
*   Is the specified serial port potentially claimed by the serial console or Bluetooth? (Check `sudo raspi-config` settings and `/boot/config.txt` or `/boot/firmware/config.txt`).
*   Is the RoboHAT MM1 properly connected and powered?
*   Does the user have `dialout` group permissions?

By carefully checking these aspects, you can ensure reliable communication between the Raspberry Pi and the RoboHAT MM1.
