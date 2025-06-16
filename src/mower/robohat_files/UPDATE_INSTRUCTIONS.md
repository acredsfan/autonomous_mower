# RoboHAT MM1 (RP2040) Firmware Update Instructions

These instructions describe how to update the `code.py` firmware on your RoboHAT MM1 (RP2040) for the Autonomous Mower project. The most reliable method is to reset the RP2040 using `mpremote`, then mount the device as a USB mass storage device and ensure it is mounted read-write.

---

## Method 1: Update via mpremote Reset + USB Mass Storage (Recommended for SSH/CLI)

This method allows you to update the firmware by resetting the RP2040 with `mpremote`, then mounting the device as a USB drive on your Raspberry Pi or Linux PC. **Note:** The device is write-protected by default and must be remounted as read-write.

### Prerequisites
- `mpremote` installed (`pip install mpremote` or `sudo pip install mpremote --break-system-packages` if not using a VENV)
- RoboHAT MM1 connected to your Raspberry Pi via USB
- You have `sudo` access

### Steps
1. **Reset the RP2040 to enter mass storage mode:**
   ```bash
   sudo mpremote /dev/ttyACM1 reset
   ```
   The device should now appear as a new block device (e.g., `/dev/sda1`).

2. **Find the device name:**
   ```bash
   lsblk
   # or
   dmesg | tail
   # Look for a new device like /dev/sda1 or /dev/sdb1
   ```

3. **Remount the device as read-write (IMPORTANT: Write Protection):**
   After reset, the device is typically mounted as **read-only (write-protected)** by default. You must remount it as read-write before copying firmware.
   
   - Unmount if already mounted (ignore errors if not mounted):
     ```bash
     sudo umount /dev/sda1
     ```
   - Create a mount point if needed:
     ```bash
     sudo mkdir -p /mnt/rp2040
     ```
   - Remount as read-write:
     ```bash
     sudo mount -o rw /dev/sda1 /mnt/rp2040
     ```
   > **Note:** If you see a "read-only file system" error when copying, you have not remounted as read-write. See Troubleshooting below.

4. **Copy the new firmware:**
   ```bash
   sudo cp /home/pi/autonomous_mower/src/mower/robohat_files/code.py /mnt/rp2040/code.py
   sync
   ```

5. **Eject/unmount the drive:**
   ```bash
   sudo umount /mnt/rp2040
   ```

6. **The RoboHAT MM1 will automatically reboot and run the new code.**

---

## Method 2: Update via BOOTSEL Button (USB Mass Storage)

This method is useful if you have physical access to the RoboHAT MM1 and want to update from a desktop environment.

### Steps
1. **Disconnect the RoboHAT MM1 from power/USB.**
2. **Press and hold the BOOTSEL (BOOT) button.**
3. **While holding BOOTSEL, connect the USB cable or press the RESET button.**
4. **Release the BOOTSEL button.**
5. **A new USB drive (e.g., `RPI-RP2`) will appear on your computer or Raspberry Pi.**
6. **Copy the new `code.py` file to the root of this drive:**
   - On Linux:
     ```bash
     cp /home/pi/autonomous_mower/src/mower/robohat_files/code.py /media/pi/RPI-RP2/code.py
     sync
     ```
   - On Windows/Mac: Drag and drop `code.py` to the RPI-RP2 drive.
   *(Adjust the path if your mount point is different.)*
7. **Eject/unmount the drive.**
8. **The RoboHAT MM1 will reboot and run the new code.**

---

## Troubleshooting
- If the device does not appear as a block device, check with `lsblk` or `dmesg | tail` after plugging in.
- If the USB drive does not appear, try a different cable or USB port, or repeat the BOOTSEL or mpremote procedure.
- If you see errors about permissions, use `sudo`.
- **If you see 'read-only file system' or 'write-protected' errors:**
  - The device is still mounted as read-only. You must unmount and remount as read-write:
    ```bash
    sudo umount /dev/sda1
    sudo mount -o rw /dev/sda1 /mnt/rp2040
    ```
  - If you still cannot write, try unplugging and replugging the device, then repeat the steps above. Ensure no other process (e.g., file manager) is holding the mount.
- After updating, monitor the serial output (e.g., with `minicom -D /dev/ttyACM1 -b 115200`) to verify successful startup.

---

## Additional Notes
- Always safely eject/unmount the RP2040 drive before unplugging to avoid filesystem corruption.
- Only one `code.py` file should be present on the device root.
- For advanced users: you can automate updates with scripts using `lsblk` and `mount`.

---

For more details, see the project documentation or contact the development team.
