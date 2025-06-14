# RoboHAT MM1 (RP2040) Firmware Update Instructions

These instructions describe how to update the `code.py` firmware on your RoboHAT MM1 (RP2040) for the Autonomous Mower project. Two reliable methods are provided: using `mpremote` (recommended for SSH/CLI users) and the BOOTSEL button (drag-and-drop via USB mass storage).

---

## Method 1: Update via `mpremote` (Recommended for SSH/CLI)

This method allows you to update the firmware without physically pressing buttons, ideal for remote or headless setups.

### Prerequisites
- `mpremote` installed (`pip install mpremote` or `sudo pip install mpremote --break-system-packages` if not using a VENV)
- RoboHAT MM1 connected to your Raspberry Pi via USB
- The device appears as `/dev/ttyACM1` (adjust if needed)

### Steps
1. **Reset the RP2040 and mount the filesystem:**
   ```bash
   sudo mpremote /dev/ttyACM1 reset
   sudo mpremote mount /mnt/qtpy
   ```
   (If `/mnt/qtpy` does not exist, create it: `sudo mkdir -p /mnt/qtpy`)

2. **Copy the new firmware:**
   ```bash
   sudo cp /home/pi/autonomous_mower/src/mower/robohat_files/code.py /mnt/qtpy/code.py
   sync
   ```

3. **(Optional) Unmount and reset:**
   ```bash
   sudo umount /mnt/qtpy
   sudo mpremote /dev/ttyACM1 reset
   ```

4. **The RoboHAT MM1 will automatically reboot and run the new code.**

---

## Method 2: Update via BOOTSEL Button (USB Mass Storage)

This method is useful if you have physical access to the RoboHAT MM1.

### Steps
1. **Disconnect the RoboHAT MM1 from power/USB.**
2. **Press and hold the BOOTSEL (BOOT) button.**
3. **While holding BOOTSEL, connect the USB cable or press the RESET button.**
4. **Release the BOOTSEL button.**
5. **A new USB drive (e.g., `RPI-RP2`) will appear on your computer or Raspberry Pi.**
6. **Copy the new `code.py` file to the root of this drive:**
   ```bash
   cp /home/pi/autonomous_mower/src/mower/robohat_files/code.py /media/pi/RPI-RP2/code.py
   sync
   ```
   *(Adjust the path if your mount point is different.)*
7. **Eject/unmount the drive.**
8. **The RoboHAT MM1 will reboot and run the new code.**

---

## Troubleshooting
- If the device does not appear as `/dev/ttyACM1`, check with `ls /dev/ttyACM*` or `dmesg | tail` after plugging in.
- If the USB drive does not appear, try a different cable or USB port, or repeat the BOOTSEL procedure.
- If you see errors about permissions, use `sudo`.
- After updating, monitor the serial output (e.g., with `minicom -D /dev/ttyACM1 -b 115200`) to verify successful startup.

---

## Additional Notes
- Always safely eject/unmount the RP2040 drive before unplugging to avoid filesystem corruption.
- Only one `code.py` file should be present on the device root.
- For advanced users: you can automate updates with scripts using `mpremote`.

---

For more details, see the project documentation or contact the development team.
