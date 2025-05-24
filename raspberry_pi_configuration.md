# Raspberry Pi Configuration for Mower Application

This document outlines the necessary steps to configure your Raspberry Pi to ensure all hardware interfaces required by the mower application are enabled and accessible.

## 1. Initial System Update

Before making any configuration changes, it's crucial to update your Raspberry Pi OS to the latest version. Open a terminal and run the following commands:

```bash
sudo apt update
sudo apt full-upgrade -y
```
After the upgrade is complete, it's recommended to reboot your Raspberry Pi:
```bash
sudo reboot
```

## 2. Using `raspi-config`

The `raspi-config` tool provides a simple way to enable various hardware interfaces.

Launch the tool by typing:
```bash
sudo raspi-config
```
Navigate using the arrow keys, and press Enter to select options. Use Esc to go back or exit.

### Enable I2C Interface
1.  Select `3 Interface Options`.
2.  Select `I5 I2C`.
3.  Select `<Yes>` to enable the ARM I2C interface.
4.  Press Enter on `<Ok>`.
5.  You can choose to exit `raspi-config` or continue enabling other interfaces.

### Enable SPI Interface
1.  Select `3 Interface Options`.
2.  Select `I4 SPI`.
3.  Select `<Yes>` to enable the SPI interface.
4.  Press Enter on `<Ok>`.

### Enable Serial Port Hardware
The Raspberry Pi has multiple UARTs. We typically want to use the primary UART (`/dev/ttyAMA0` on older Pis, or PL011 UART on Pi 3/4/5) for peripherals like GPS, and the mini UART (`/dev/ttyS0`) might be used by the Bluetooth module or be less reliable.

1.  Select `3 Interface Options`.
2.  Select `I6 Serial Port`.
3.  **Would you like a login shell to be accessible over serial?**
    *   Select `<No>` if you plan to use the serial port for GPS or other hardware communication. This disables the serial console.
4.  **Would you like the serial port hardware to be enabled?**
    *   Select `<Yes>`.
5.  Press Enter on `<Ok>`.

### Enable Camera Interface
1.  Select `3 Interface Options`.
2.  Select `I1 Camera`.
3.  Select `<Yes>` to enable the legacy camera interface (if using an older camera module and software stack) or ensure the libcamera stack is recognized. For Picamera2, this step might not be strictly necessary if `libcamera` is correctly installed, but it doesn't hurt.
4.  Press Enter on `<Ok>`.

After enabling all necessary interfaces, navigate to `<Finish>` in the main `raspi-config` menu. It might ask if you want to reboot. It's generally a good idea to reboot for all changes to take effect.

## 3. Serial Port Considerations

Raspberry Pi models have at least two UARTs:
*   `/dev/ttyAMA0`: This is typically the primary, more capable PL011 UART. On Raspberry Pis with Bluetooth (Pi 3, 4, 5, Zero W), this UART might be used by default for Bluetooth if not configured otherwise.
*   `/dev/ttyS0`: This is the mini UART, which has some limitations and its clock speed is tied to the VPU core clock, making it less stable if the core frequency changes. On models with Bluetooth, this is often the default for the Linux console if `ttyAMA0` is used by Bluetooth.

By disabling the serial login shell and enabling serial hardware in `raspi-config` (as described above), you typically make `/dev/ttyAMA0` available for general use.

### How to check which serial ports are available:
You can list serial devices:
```bash
ls -l /dev/ttyS0 /dev/ttyAMA* /dev/serial*
```
The `/dev/serial0` and `/dev/serial1` are symbolic links created by udev rules to provide stable names for the primary and secondary UARTs, regardless of whether Bluetooth is active or not.
*   `serial0` usually points to `/dev/ttyS0` (mini UART) if Bluetooth is using `ttyAMA0`.
*   `serial1` usually points to `/dev/ttyAMA0` (primary UART) if it's available.

### Recommendation for GPS:
*   It is generally recommended to use the primary UART (`/dev/ttyAMA0` or its alias `serial1`) for GPS due to its stability.
*   Ensure the Linux serial console is disabled on this port (done via `raspi-config` step above).
*   The mower application's `.env` file might have a `GPS_PORT` setting. Ensure this setting matches the serial port you intend to use for the GPS module (e.g., `GPS_PORT=/dev/ttyAMA0`).

**To ensure `/dev/ttyAMA0` is the primary UART available for applications:**
If you're using a Raspberry Pi with Bluetooth (Pi 3, 4, 5, Zero W), you might need to explicitly disable Bluetooth or configure it to not use the PL011 UART (`ttyAMA0`). This can sometimes be done by adding `dtoverlay=disable-bt` to `/boot/config.txt` or `dtoverlay=miniuart-bt` to make Bluetooth use `/dev/ttyS0`, freeing up `/dev/ttyAMA0`.
A common configuration after running `raspi-config` as described (disabling serial console, enabling serial hardware) on a Pi 4 is that `/dev/ttyAMA0` becomes available as `serial0` for user applications, while `/dev/ttyS0` might be used by the kernel for console output if configured. Always verify with `ls -l /dev/serial*`.

## 4. User Group Management

To access hardware interfaces like GPIO, I2C, SPI, and serial ports without needing `sudo` for every command, your user must be a member of the appropriate groups.

Add the current user (e.g., `pi`) to the necessary groups:
```bash
sudo usermod -a -G gpio $USER
sudo usermod -a -G i2c $USER
sudo usermod -a -G dialout $USER  # For serial port access
sudo usermod -a -G video $USER   # For camera access
# sudo usermod -a -G spi $USER # Often SPI access is managed via gpio group or specific udev rules. If spidev is not accessible, add this group.
```
Note: `$USER` automatically substitutes the current logged-in username.

**Important:** Group changes will only take effect after you log out and log back in, or after a reboot:
```bash
sudo reboot
```

## 5. Checking Configurations

After rebooting, you can verify that the interfaces are enabled:

*   **I2C:** List I2C devices. You should see `i2c-1` (or other numbers).
    ```bash
    ls /dev/i2c*
    ```
*   **SPI:** List SPI devices. You should see `spidev0.0` and `spidev0.1` (or similar).
    ```bash
    ls /dev/spidev*
    ```
*   **Serial Ports:** List available serial ports.
    ```bash
    ls -l /dev/ttyS0 /dev/ttyAMA0 /dev/serial*
    ```
    Check `dmesg | grep tty` for kernel messages about serial ports.
*   **Camera:** Check if the camera is detected by the firmware.
    ```bash
    vcgencmd get_camera
    ```
    This should output something like `supported=1 detected=1` (or `detected=0` if the camera is not connected or faulty). For Picamera2, ensure `libcamera-hello` or a simple Python script using Picamera2 can access the camera.

## Conclusion

Following these steps will prepare your Raspberry Pi with the necessary hardware interfaces and permissions for the mower application. Always refer to the specific documentation for your Raspberry Pi model and peripherals if you encounter issues.
---

This document provides a comprehensive guide for configuring the Raspberry Pi. Is there anything else I should add or modify?
