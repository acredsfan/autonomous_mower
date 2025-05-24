#!/usr/bin/env python3

import sys
import os
import platform
import subprocess
import glob

# Attempt to import system-specific modules only when needed
if platform.system() == "Linux":
    try:
        import grp
    except ImportError:
        print("WARN: 'grp' module not found. Skipping group membership checks.")
        grp = None # type: ignore
else:
    grp = None # type: ignore

# --- Configuration ---
PYTHON_MAJOR_REQ = 3
PYTHON_MINOR_REQ = 9  # Target is 3.10+ for app, 3.9 is a reasonable pre-check

# Common I2C addresses for probing (use with caution)
BNO085_I2C_ADDR = 0x4A
INA3221_I2C_ADDR = 0x40

# --- Helper Functions ---
def print_check(name, status, success_msg="OK", failure_msg="FAIL", advice=""):
    """Prints a formatted check line."""
    indicator = success_msg if status else failure_msg
    print(f"- {name:<50}: [{indicator}]")
    if not status and advice:
        print(f"  Advice: {advice}")

def print_info(name, value, details=""):
    """Prints informational line."""
    print(f"- {name:<50}: {value} {details}")

def check_library_import(library_name):
    """Checks if a Python library can be imported."""
    try:
        __import__(library_name)
        return True
    except ImportError:
        return False

# --- Main Preflight Checks ---
def check_python_version():
    print("\n--- Python Version ---")
    major = sys.version_info.major
    minor = sys.version_info.minor
    version_str = f"{major}.{minor}.{sys.version_info.micro}"
    print_info("Current Python Version", version_str)
    met_requirement = (major == PYTHON_MAJOR_REQ and minor >= PYTHON_MINOR_REQ) or \
                      (major > PYTHON_MAJOR_REQ)
    print_check("Python Version Requirement (>=3.9)", met_requirement,
                advice=f"Application targets Python 3.10+. Consider upgrading if version is < {PYTHON_MAJOR_REQ}.{PYTHON_MINOR_REQ}.")

def check_env_file():
    print("\n--- Configuration File ---")
    env_exists = os.path.exists(".env")
    print_check(".env File Existence", env_exists, "FOUND", "NOT FOUND",
                "Create a .env file by copying .env.example and customizing it.")

def check_user_groups():
    if platform.system() != "Linux" or not grp:
        print("\n--- User Group Membership (Skipped on non-Linux or if 'grp' module missing) ---")
        return

    print("\n--- User Group Membership (Linux) ---")
    try:
        username = os.getlogin()
        user_groups = [g.gr_name for g in grp.getgrall() if username in g.gr_mem]
        user_groups.append(grp.getgrgid(os.getgid()).gr_name) # Add primary group
    except Exception as e:
        print(f"  Error getting user groups: {e}. Skipping checks.")
        return

    required_groups = ["gpio", "i2c", "dialout", "video"]
    for group_name in required_groups:
        is_member = group_name in user_groups
        print_check(f"User in group '{group_name}'", is_member, "YES", "NO",
                    f"Add user '{username}' to group '{group_name}' (e.g., sudo usermod -a -G {group_name} {username}) and reboot.")

def check_hardware_interfaces():
    print("\n--- Hardware Interfaces (Linux) ---")
    if platform.system() != "Linux":
        print("  Skipping hardware interface checks (not on Linux).")
        return

    # I2C
    i2c1_exists = os.path.exists("/dev/i2c-1")
    print_check("I2C Interface (/dev/i2c-1)", i2c1_exists, "FOUND", "NOT FOUND",
                "Enable I2C via 'sudo raspi-config' (Interface Options -> I2C).")

    # SPI
    spi0_0_exists = os.path.exists("/dev/spidev0.0")
    spi0_1_exists = os.path.exists("/dev/spidev0.1")
    spi_exists = spi0_0_exists or spi0_1_exists
    spi_device_found = "/dev/spidev0.0" if spi0_0_exists else ("/dev/spidev0.1" if spi0_1_exists else "None")
    print_check(f"SPI Interface ({spi_device_found})", spi_exists, "FOUND", "NOT FOUND",
                "Enable SPI via 'sudo raspi-config' (Interface Options -> SPI).")

    # Serial Ports
    print_info("Serial Ports", "Checking common patterns...")
    common_patterns = ["/dev/ttyS*", "/dev/ttyAMA*", "/dev/ttyUSB*", "/dev/ttyACM*"]
    found_serials = []
    for pattern in common_patterns:
        ports = glob.glob(pattern)
        if ports:
            found_serials.extend(ports)

    if found_serials:
        for port in found_serials:
            print(f"  Found: {port}")
    else:
        print("  No common serial ports found. This might be okay if not using serial devices directly or if paths are different.")
    print_check("Serial Port Detection (any found)", bool(found_serials), "PORTS LISTED", "NONE DETECTED",
                "Ensure serial devices are connected or enable serial in raspi-config if using built-in UART.")


    # Camera
    print_info("Camera (vcgencmd)", "Attempting to detect...")
    try:
        result = subprocess.run(["vcgencmd", "get_camera"], capture_output=True, text=True, check=False)
        if result.returncode == 0:
            print(f"  Output: {result.stdout.strip()}")
            cam_detected = "detected=1" in result.stdout
            print_check("Camera Detected via vcgencmd", cam_detected, "DETECTED", "NOT DETECTED (or detected=0)",
                        "Ensure camera is enabled in raspi-config and properly connected. For Picamera2, this check might be less critical if libcamera is working.")
        else:
            print(f"  vcgencmd command failed or not found. Output: {result.stderr.strip()}")
            print_check("Camera Detected via vcgencmd", False, failure_msg="CMD_FAIL/NOT_FOUND",
                        "vcgencmd not found (not a Raspberry Pi or not installed?) or command failed.")
    except FileNotFoundError:
        print("  vcgencmd command not found (likely not a Raspberry Pi or vcgencmd not in PATH).")
        print_check("Camera Detected via vcgencmd", False, failure_msg="CMD_NOT_FOUND",
                    "This check is Raspberry Pi specific.")
    except Exception as e:
        print(f"  Error running vcgencmd: {e}")
        print_check("Camera Detected via vcgencmd", False, failure_msg="ERROR",
                    "An unexpected error occurred.")


def check_critical_libraries():
    print("\n--- Critical Python Libraries ---")
    libraries = {
        "RPi.GPIO": "For GPIO control (Raspberry Pi specific). Install with 'pip install RPi.GPIO'.",
        "smbus2": "For I2C communication. Install with 'pip install smbus2'.",
        "picamera2": "For Camera (Picamera2 stack). Install with 'pip install picamera2'.",
        "serial": "For serial communication (PySerial). Install with 'pip install pyserial'.",
        "pynmea2": "For parsing NMEA GPS sentences. Install with 'pip install pynmea2'."
    }
    all_imported = True
    for lib, advice in libraries.items():
        imported = check_library_import(lib)
        print_check(f"Library Import: {lib}", imported, "IMPORTED", "NOT IMPORTED", advice)
        if not imported:
            all_imported = False
    return all_imported, check_library_import("smbus2") # Return smbus2 status for I2C probe

def probe_i2c_devices(smbus2_available):
    print("\n--- I2C Device Probing (Optional) ---")
    if platform.system() != "Linux":
        print("  Skipping I2C probe (not on Linux).")
        return
    if not os.path.exists("/dev/i2c-1"):
        print("  Skipping I2C probe (/dev/i2c-1 not found).")
        return
    if not smbus2_available:
        print("  Skipping I2C probe (smbus2 library not available).")
        return

    print("  Attempting to probe for common I2C devices on bus 1...")
    bus = None
    try:
        from smbus2 import SMBus
        bus = SMBus(1) # 1 indicates /dev/i2c-1

        # Probe for BNO085
        try:
            bus.read_byte_data(BNO085_I2C_ADDR, 0) # Try to read a byte (register 0)
            print_check(f"BNO085-like device at 0x{BNO085_I2C_ADDR:X}", True, "RESPONDED", "NO_RESPONSE")
        except Exception: # pylint: disable=broad-except
            # Catching general exception as various I/O errors can occur
            print_check(f"BNO085-like device at 0x{BNO085_I2C_ADDR:X}", False, "RESPONDED", "NO_RESPONSE/ERROR")

        # Probe for INA3221
        try:
            bus.read_byte_data(INA3221_I2C_ADDR, 0) # Try to read a byte (register 0)
            print_check(f"INA3221-like device at 0x{INA3221_I2C_ADDR:X}", True, "RESPONDED", "NO_RESPONSE")
        except Exception: # pylint: disable=broad-except
            print_check(f"INA3221-like device at 0x{INA3221_I2C_ADDR:X}", False, "RESPONDED", "NO_RESPONSE/ERROR")

        print("  Note: 'RESPONDED' means a device acknowledged the address. It does not guarantee it's the correct device or fully functional.")

    except ImportError:
        print("  Error: smbus2 import failed unexpectedly during probe (should have been checked before).")
    except FileNotFoundError:
        print("  Error: I2C bus 1 not found during probe (e.g., /dev/i2c-1 disappeared).")
    except Exception as e: # pylint: disable=broad-except
        print(f"  An unexpected error occurred during I2C probing: {e}")
    finally:
        if bus:
            try:
                bus.close()
            except Exception: # pylint: disable=broad-except
                pass # Ignore errors on close

def main():
    print("Starting Raspberry Pi Pre-flight Checks...")
    print("==========================================")

    check_python_version()
    check_env_file()
    check_user_groups()
    check_hardware_interfaces()
    _, smbus2_imported = check_critical_libraries() # Get smbus2 status
    probe_i2c_devices(smbus2_imported)

    print("\n==========================================")
    print("Pre-flight checks complete.")
    print("Review any FAIL or NOT FOUND messages and consult advice.")

if __name__ == "__main__":
    # Assuming the script is in 'scripts/' and project root is parent directory
    # Change CWD to project root if necessary for .env check,
    # but for now, assume it's run from where .env is expected (project root).
    # If run as 'python3 scripts/preflight_checker.py' from project root, CWD is fine.
    main()
```

I've created the script with all the requested features.
- It checks Python version, `.env` file, user groups, hardware interfaces (I2C, SPI, Serial, Camera via `vcgencmd`), and critical Python libraries.
- It includes an optional I2C device probing section for BNO085 and INA3221 if I2C and `smbus2` are available.
- Output is formatted with PASS/FAIL or FOUND/NOT FOUND indicators and provides advice for failures.
- It attempts to handle non-Linux environments or missing tools/libraries gracefully by skipping relevant checks or reporting errors.
- The script is intended to be placed in `scripts/` and run from the project root directory.

Final check of the code before submitting.
- Python version check is against 3.9 as a minimum, with a note about 3.10+ for the app.
- `.env` check is for the current working directory.
- Group checks use `grp` module.
- Hardware checks are Linux-specific. `vcgencmd` has error handling.
- Library imports are wrapped in try-except.
- I2C probing uses `smbus2`, checks for device response by trying to read a byte, and handles exceptions.
- Output formatting seems clear.

The script looks good.
