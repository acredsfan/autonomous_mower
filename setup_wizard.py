"""
Autonomous Mower Setup Wizard

This script provides an interactive setup process for the autonomous mower system.
It guides users through configuring all necessary settings, collecting tokens and
credentials, and setting up the environment based on their specific needs.
"""

import getpass
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional
import textwrap
import traceback

# Try to import dotenv, install if not available
try:
    from dotenv import set_key
except ImportError:
    print("Installing python-dotenv...")
    os.system(f"{sys.executable} -m pip install python-dotenv --break-system-packages")
    from dotenv import set_key

# Constants
CONFIG_DIR = Path("config")
ENV_FILE = Path(".env")
ENV_EXAMPLE = Path(".env.example")
SETUP_STATE_FILE = Path("setup_state.json")

# ANSI color codes for terminal output
COLORS = {
    "RESET": "\033[0m",
    "BOLD": "\033[1m",
    "RED": "\033[91m",
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "BLUE": "\033[94m",
    "MAGENTA": "\033[95m",
    "CYAN": "\033[96m",
}

# Setup state to track progress
setup_state = {
    "completed_sections": [],
    "user_choices": {},
    "hardware_config": {},
    "feature_flags": {},
}


def create_webui_data_symlink() -> None:
    """
    Ensures the Web UI static data symlink exists and points to the collected images directory.
    @hardware_interface: symbolic link
    @gpio_pin_usage: N/A
    """
    import os
    src = os.path.abspath("data/collected_images")
    dst = os.path.abspath("src/mower/ui/web_ui/static/data")
    try:
        # Remove existing symlink if it exists and is incorrect
        if os.path.islink(dst) and os.readlink(dst) != src:
            os.unlink(dst)
        # Create symlink if missing
        if not os.path.exists(dst):
            os.symlink(src, dst)
            print(f"Created symlink: {dst} -> {src}")
        else:
            print(f"Symlink already exists: {dst}")
    except Exception as e:
        print(f"Error creating symlink: {e}")



def color_text(text: str, color: str) -> str:
    """Add color to terminal text."""
    return f"{COLORS.get(color, '')}{text}{COLORS['RESET']}"


def install_dependencies() -> bool:
    """Install required Python dependencies before running permission checks."""
    print_header("Installing Dependencies")
    print_info("Installing required Python packages...")

    packages = ["pydantic>=2.0.0", "python-dotenv"]

    for package in packages:
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", package, "--break-system-packages"],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                print_success(f"Successfully installed {package}")
            else:
                print_error(f"Failed to install {package}: {result.stderr}")
                return False
        except Exception as e:
            print_error(f"Error installing {package}: {e}")
            return False

    return True


def run_enhanced_permission_checks() -> bool:
    """
    Run permission checks with automatic fixing after dependencies are installed.
    Returns True if all checks pass or are fixed, False otherwise.
    """
    print_header("Permission Checks")
    print_info("Checking and fixing permissions...")

    try:
        # Import after dependencies are installed
        from src.mower.utilities.permission_check import check_directory_permissions, check_group_membership

        # Check directory permissions
        dir_errors = check_directory_permissions()

        # Try to fix directory permission issues
        fixed_dirs = []

        for error in dir_errors:
            if "does not exist" in error:
                # Extract directory path from error message
                match = re.search(r"Directory '([^']+)' does not exist", error)
                if match:
                    dir_path = match.group(1)
                    try:
                        os.makedirs(dir_path, exist_ok=True)
                        print_success(f"Created directory: {dir_path}")
                        fixed_dirs.append(dir_path)
                    except Exception as e:
                        print_error(f"Failed to create directory {dir_path}: {e}")

            elif "access denied" in error:
                # Extract directory path and fix permissions
                match = re.search(r"for '([^']+)'", error)
                if match:
                    dir_path = match.group(1)
                    try:
                        if "Read access denied" in error:
                            cmd = f"sudo chmod a+r '{dir_path}'"
                            result = os.system(cmd)
                            if result == 0:
                                print_success(f"Fixed read permissions for: {dir_path}")
                                fixed_dirs.append(dir_path)
                            else:
                                print_error(f"Failed to fix read permissions for: {dir_path}")

                        if "Write access denied" in error:
                            cmd = f"sudo chmod a+rw '{dir_path}'"
                            result = os.system(cmd)
                            if result == 0:
                                print_success(f"Fixed write permissions for: {dir_path}")
                                fixed_dirs.append(dir_path)
                            else:
                                print_error(f"Failed to fix write permissions for: {dir_path}")
                    except Exception as e:
                        print_error(f"Error fixing permissions for {dir_path}: {e}")

        # Re-check directory permissions after fixes
        remaining_dir_errors = check_directory_permissions()

        # Check group membership
        group_errors = check_group_membership()

        # Provide guidance for group membership issues
        if group_errors:
            print_warning("Group membership issues found:")
            for error in group_errors:
                print_warning(f"  {error}")
            print_info("Group membership changes require a logout/login to take effect.")
            print_info("You can continue setup, but hardware access may be limited.")

        all_remaining_errors = remaining_dir_errors + group_errors

        if all_remaining_errors:
            print_warning("Some permission issues remain:")
            for error in all_remaining_errors:
                print_warning(f"  {error}")

            # Ask if user wants to continue
            continue_anyway = prompt_bool(
                "Continue setup despite permission issues?",
                default=True,
                help_text=(
                    "You can continue setup and fix these issues later. "
                    "Some features may not work until permissions are resolved."
                ),
            )
            return continue_anyway
        else:
            print_success("All permission checks passed!")
            return True

    except ImportError as e:
        print_error(f"Could not import permission check module: {e}")
        print_warning("Permission checks will be skipped.")
        return True  # Continue setup anyway
    except Exception as e:
        print_error(f"Error during permission checks: {e}")
        return False


# Pre-flight permission check will be done after dependency installation


def print_header(title: str) -> None:
    """Print a formatted section header."""
    width = 80
    print("\n" + "=" * width)
    print(color_text(f"{title.center(width)}", "BOLD"))
    print("=" * width)


def print_subheader(title: str) -> None:
    """Print a formatted subsection header."""
    print(f"\n{color_text('▶ ' + title, 'CYAN')}")


def print_info(message: str) -> None:
    """Print an info message."""
    print(f"{color_text('ℹ', 'BLUE')} {message}")


def print_success(message: str) -> None:
    """Print a success message."""
    print(f"{color_text('✓', 'GREEN')} {message}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    print(f"{color_text('⚠', 'YELLOW')} {message}")


def print_error(message: str) -> None:
    """Print an error message."""
    print(f"{color_text('✗', 'RED')} {message}")


def print_help(message: str) -> None:
    """Print a help message with proper wrapping."""
    for line in textwrap.wrap(message, width=76):
        print(f"{color_text('💡', 'MAGENTA')} {line}")


def ensure_directory(path: Path) -> None:
    """Ensure a directory exists."""
    if not path.exists():
        path.mkdir(parents=True)
        print_info(f"Created directory: {path}")


def ensure_env_file() -> None:
    """Ensure .env file exists, create from example if needed."""
    if not ENV_FILE.exists():
        print_info(f"Creating {ENV_FILE} from {ENV_EXAMPLE}...")
        try:
            if ENV_EXAMPLE.exists():
                shutil.copy(ENV_EXAMPLE, ENV_FILE)
                print_success(f"{ENV_FILE} created successfully.")
            else:
                ENV_FILE.touch() # Create an empty .env file
                print_warning(f"{ENV_EXAMPLE} not found. Created an empty {ENV_FILE}.")
            # Ensure the new .env file is writable
            os.chmod(ENV_FILE, 0o600) # Set permissions (rw-------) for security
        except Exception as e:
            print_error(f"Could not create {ENV_FILE}: {e}")
            print_warning("Please ensure you have write permissions in the current directory.")
            # Exit if .env cannot be created, as it's crucial
            sys.exit(1)
    elif not os.access(ENV_FILE, os.W_OK):
        # File exists but not writable
        print_warning(f"{ENV_FILE} is not writable")
        if sys.platform.startswith("linux"):
            try:
                result = subprocess.run(
                    ["sudo", "chmod", "664", str(ENV_FILE)],
                    capture_output=True,
                    text=True,
                )

                if result.returncode == 0:
                    print_success(f"Fixed permissions for {ENV_FILE}")
                else:
                    print_error(f"Could not fix permissions: {result.stderr}")
            except Exception as e:
                print_error(f"Permission fix failed: {e}")


def save_setup_state() -> None:
    """Save the current setup state to a file."""
    with open(SETUP_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(setup_state, f, indent=2)
    print_info(f"Setup progress saved to {SETUP_STATE_FILE}")


def load_setup_state() -> bool:
    """Load setup state from file if it exists."""
    global setup_state  # pylint: disable=global-statement
    if SETUP_STATE_FILE.exists():
        try:
            with open(SETUP_STATE_FILE, "r", encoding="utf-8") as f:
                loaded_state = json.load(f)
                # Basic validation of loaded state structure
                if isinstance(loaded_state, dict) and "completed_sections" in loaded_state:
                    setup_state = loaded_state
                    print_info(f"Setup progress loaded from {SETUP_STATE_FILE}")
                    return True
                else:
                    print_warning(f"Invalid format in {SETUP_STATE_FILE}. Starting fresh.")
                    # Optionally, backup the corrupted file
                    # SETUP_STATE_FILE.rename(SETUP_STATE_FILE.with_suffix(".json.corrupted"))
                    return False
        except json.JSONDecodeError:
            print_warning(f"Could not parse {SETUP_STATE_FILE}. Starting fresh.")
            return False
        except Exception as e:
            print_error(f"Error loading setup state: {e}")
            return False
    return False


def update_env_var(key: str, value: str) -> None:
    """Update an environment variable in the .env file."""
    # Proactively ensure the .env file exists and has proper permissions
    # before calling set_key to avoid internal permission errors in
    # python-dotenv
    if not ENV_FILE.exists():
        print_info(f"{ENV_FILE} does not exist, creating from example")
        if ENV_EXAMPLE.exists():
            shutil.copy(ENV_EXAMPLE, ENV_FILE)
            print_success(f"Created {ENV_FILE} from {ENV_EXAMPLE}")
        else:
            ENV_FILE.touch()
            print_info(f"Created empty {ENV_FILE}")
        # Ensure proper permissions on Raspberry Pi
        if sys.platform.startswith("linux"):
            try:
                result = subprocess.run(
                    ["sudo", "chmod", "664", str(ENV_FILE)],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    print_success(f"Set proper permissions for {ENV_FILE}")
                else:
                    print_warning(f"Could not set permissions: {result.stderr}")
            except Exception as e:
                print_warning(f"Permission setting failed: {e}")
    elif not os.access(ENV_FILE, os.W_OK):
        warning_msg = f"{ENV_FILE} is not writable, fixing permissions..."
        print_warning(warning_msg)
        try:
            if sys.platform.startswith("linux"):
                subprocess.run(
                    ["sudo", "chmod", "664", str(ENV_FILE)],
                    check=True,
                    capture_output=True,
                    text=True,
                )

                # Ensure current user owns the file
                current_user = os.getenv("USER", "pi")
                subprocess.run(
                    ["sudo", "chown", f"{current_user}:{current_user}", str(ENV_FILE)],
                    check=True,
                    capture_output=True,
                    text=True,
                )

                success_msg = f"Fixed permissions for {ENV_FILE}"
                print_success(success_msg)
            else:
                print_warning("Cannot fix permissions on Windows")
        except Exception as e:
            print_error(f"Failed to fix permissions: {e}")
            print_info("Please manually fix permissions:")
            print_info("sudo chmod 664 .env && sudo chown $USER:$USER .env")
            sys.exit(1)

    # Now attempt to write to the file
    try:
        # Ensure the .env file is writable before calling set_key
        if not os.access(ENV_FILE, os.W_OK):
            try:
                os.chmod(ENV_FILE, 0o600) # Attempt to make it writable
            except OSError as e_chmod:
                print_error(f"Cannot change permissions for {ENV_FILE}: {e_chmod}")
                print_warning(f"Skipping update for {key} in {ENV_FILE}.")
                return

        set_key(str(ENV_FILE), key, value, quote_mode="always")
        print_success(f"Updated {key} in {ENV_FILE}")
    except PermissionError as e:
        print_error(f"Still cannot write to {ENV_FILE}: {e}")
        print_info("Please manually fix permissions and ownership:")
        print_info("sudo chmod 664 .env && sudo chown $USER:$USER .env")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error writing to {ENV_FILE}: {e}")
        sys.exit(1)


def get_env_var(key: str, default: str = "") -> str:
    """Get an environment variable value, with fallback to default."""
    return os.environ.get(key, default)


def prompt_choice(prompt: str, choices: List[str], default: Optional[int] = None) -> str:
    """Prompt user to select from a list of choices."""
    print(f"\n{prompt}")
    for idx, choice in enumerate(choices, 1):
        default_marker = " (default)" if default is not None and idx == default else ""
        print(f"  {idx}. {choice}{default_marker}")

    while True:
        try:
            sel = input(f"Enter choice [1-{len(choices)}]" + (f" (default: {default}): " if default else ": "))
            if not sel and default is not None:
                return choices[default - 1]
            if sel.isdigit() and 1 <= int(sel) <= len(choices):
                return choices[int(sel) - 1]
            print_error("Invalid selection. Please try again.")
        except (KeyboardInterrupt, EOFError):
            print("\nSetup canceled.")
            sys.exit(1)


def prompt_value(
    prompt: str,
    default: Optional[str] = None,
    required: bool = False,
    validator: Optional[Callable[[str, str], bool]] = None,
    field_name: Optional[str] = None,
    help_text: Optional[str] = None,
    secret: bool = False,
    extra_info: Optional[str] = None,
) -> str:
    """
    Prompt user for input with validation.

    Args:
        prompt: The prompt to display
        default: Default value if user presses Enter
        required: Whether the field is required
        validator: Function to validate input
        field_name: Name of the field for validation messages
        help_text: Help text to display
        secret: Whether to hide input (for passwords)
        extra_info: Additional information to display

    Returns:
        User input or default value
    """
    if extra_info:
        print_info(extra_info)
    if help_text:
        print_help(help_text)

    while True:
        try:
            if secret:
                val = getpass.getpass(f"{prompt} " + (" (default: [hidden]): " if default else ": "))
            else:
                val = input(f"{prompt} " + (f" (default: {default}): " if default else ": "))

            if not val and default is not None:
                val = default

            if required and not val:
                print_error(f"{field_name or prompt} is required.")
                continue

            if validator and val and not validator(val, field_name or prompt):
                continue

            return val
        except (KeyboardInterrupt, EOFError):
            print("\nSetup canceled.")
            sys.exit(1)


def prompt_bool(
    prompt: str,
    default: Optional[bool] = None,
    help_text: Optional[str] = None,
) -> bool:
    """Prompt for a yes/no response."""
    if help_text:
        print_help(help_text)

    default_str = None
    if default is not None:
        default_str = "y" if default else "n"

    while True:
        try:
            val = input(f"{prompt} (y/n)" + (f" (default: {default_str}): " if default_str else ": "))

            if not val and default is not None:
                return default

            if val.lower() in ["y", "yes", "true"]:
                return True
            if val.lower() in ["n", "no", "false"]:
                return False

            print_error("Please enter 'y' or 'n'.")
        except (KeyboardInterrupt, EOFError):
            print("\nSetup canceled.")
            sys.exit(1)


def validate_float(
    value: str,
    field_name: str,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
) -> bool:
    """Validate a float value."""
    try:
        val = float(value)
        if min_value is not None and val < min_value:
            print_error(f"{field_name} must be >= {min_value}.")
            return False
        if max_value is not None and val > max_value:
            print_error(f"{field_name} must be <= {max_value}.")
            return False
        return True
    except ValueError:
        print_error(f"{field_name} must be a number.")
        return False


def validate_int(
    value: str,
    field_name: str,
    min_value: Optional[int] = None,
    max_value: Optional[int] = None,
) -> bool:
    """Validate an integer value."""
    try:
        val = int(value)
        if min_value is not None and val < min_value:
            print_error(f"{field_name} must be >= {min_value}.")
            return False
        if max_value is not None and val > max_value:
            print_error(f"{field_name} must be <= {max_value}.")
            return False
        return True
    except ValueError:
        print_error(f"{field_name} must be an integer.")
        return False


def validate_lat_lng(value: str, field_name: str) -> bool:
    """Validate latitude,longitude format."""
    try:
        lat, lng = map(float, value.split(","))
        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            print_error(f"{field_name} must be valid latitude,longitude.")
            return False
        return True
    except ValueError:
        print_error(f"{field_name} must be in format: lat,lng (e.g. 39.1,-84.5)")
        return False


def welcome_screen() -> None:
    """Display welcome screen and introduction."""
    print_header("Autonomous Mower Setup Wizard")
    print(
        """
Welcome to the Autonomous Mower Setup Wizard! This interactive tool will guide
you through the process of setting up your autonomous mower system.

The wizard will help you configure:
- Hardware components and connections
- Software features and integrations
- Safety settings and boundaries
- Remote access and monitoring
- User interface preferences

You can exit at any time by pressing Ctrl+C, and your progress will be saved.
Let's get started!
    """
    )
    input("Press Enter to continue...")


# Helper functions for JSON configuration handling
def load_main_config(path: Path) -> Dict:
    """Load the main JSON configuration file."""
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print_warning(f"Could not parse {path}, treating as empty config for this section.")
            return {}
        except IOError:
            print_warning(f"Could not read {path}, treating as empty config for this section.")
            return {}
    return {}


def save_main_config(path: Path, config_data: Dict) -> None:
    """Save data to the main JSON configuration file."""
    try:
        ensure_directory(path.parent) # Ensure config directory exists
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4)
        print_success(f"Configuration saved to {path}")
    except IOError:
        print_error(f"Could not write to {path}")
    except Exception as e:
        print_error(f"Failed to save {path}: {e}")


def setup_hardware_detection() -> Dict[str, bool]:
    """Detect available hardware components."""
    print_header("Hardware Detection")
    print_info("Checking for connected hardware components...")

    hardware = {
        "raspberry_pi": True,  # We're running on a Raspberry Pi
        "camera": False,
        "gps": False,
        "imu": False,
        "tof_sensors": False,
        "coral_tpu": False,
        "robohat": False,
    }

    # Check for camera
    try:
        if os.path.exists("/dev/video0"):
            hardware["camera"] = True
            print_success("Camera detected at /dev/video0")
        else:
            print_warning("No camera detected")
    except Exception:
        # Check for GPS (serial device)
        print_warning("Failed to check for camera")
    try:
        if os.path.exists("/dev/ttyAMA0") or os.path.exists("/dev/serial0"):
            hardware["gps"] = True
            print_success("GPS serial port detected")
        else:
            print_warning("No GPS serial port detected")
    except Exception:
        print_warning("Failed to check for GPS")

    # Check for I2C devices (IMU, ToF sensors)
    try:
        i2c_devices = os.popen("i2cdetect -y 1").read()
        if "68" in i2c_devices:  # Common IMU address
            hardware["imu"] = True
            print_success("IMU detected on I2C bus")
        if "29" in i2c_devices:  # Common ToF sensor address
            hardware["tof_sensors"] = True
            print_success("ToF sensors detected on I2C bus")
        if not hardware["imu"] and not hardware["tof_sensors"]:
            print_warning("No I2C sensors detected")
    except Exception:
        print_warning("Failed to check for I2C devices")

    # Check for Coral TPU
    try:
        usb_devices = os.popen("lsusb").read()
        if "1a6e:089a" in usb_devices:  # Coral TPU USB ID
            hardware["coral_tpu"] = True
            print_success("Google Coral TPU detected")
        else:
            print_warning("No Google Coral TPU detected")
    except Exception:
        print_warning("Failed to check for Coral TPU")

    # Check for RoboHAT MM1
    try:
        if os.path.exists("/dev/ttyACM1"):
            hardware["robohat"] = True
            print_success("Potential RoboHAT MM1 detected at /dev/ttyACM1")
        else:
            print_warning("No RoboHAT MM1 detected")
    except Exception:
        print_warning("Failed to check for RoboHAT MM1")

    print("\nHardware detection complete. You can manually override these settings later.")
    input("Press Enter to continue...")

    return hardware


def setup_basic_configuration() -> None:
    """Configure basic mower settings."""
    print_header("Basic Configuration")

    print_subheader("Mower Identity")
    mower_name = prompt_value(
        "Mower name",
        default=get_env_var("MOWER_NAME", "AutonoMow"),
        required=True,
        help_text=("A unique name for your mower. " "This will be used in logs and the web interface."),
    )
    update_env_var("MOWER_NAME", mower_name)

    print_subheader("Logging")
    log_level = prompt_choice(
        "Select log level",
        ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=2,  # INFO
    )
    update_env_var("LOG_LEVEL", log_level)

    debug_mode = prompt_bool(
        "Enable debug mode?",
        default=False,
        help_text="Debug mode provides additional logging and diagnostic information.",
    )
    update_env_var("DEBUG_MODE", str(debug_mode))

    print_subheader("Simulation Mode")
    use_simulation = prompt_bool(
        "Use simulation mode?",
        default=False,
        help_text=(
            "Simulation mode allows testing without physical hardware. " "Recommended for initial setup and testing."
        ),
    )
    update_env_var("USE_SIMULATION", str(use_simulation))

    # Save to setup state
    setup_state["user_choices"]["mower_name"] = mower_name
    setup_state["user_choices"]["log_level"] = log_level
    setup_state["feature_flags"]["debug_mode"] = debug_mode
    setup_state["feature_flags"]["simulation_mode"] = use_simulation

    setup_state["completed_sections"].append("basic_configuration")
    save_setup_state()

    print_success("Basic configuration completed!")


def setup_hardware_configuration(detected_hardware: Dict[str, bool]) -> None:
    """Configure hardware components."""
    print_header("Hardware Configuration")

    # Camera configuration
    print_subheader("Camera Configuration")
    use_camera = prompt_bool(
        "Use camera for obstacle detection?",
        default=detected_hardware.get("camera", False),
        help_text="The camera is used for visual obstacle detection and navigation.",
    )

    if use_camera:
        cam_width = prompt_value(
            "Camera width (pixels)",
            default=get_env_var("CAMERA_WIDTH", "640"),
            validator=lambda v, f: validate_int(v, f, 320, 1920),
        )
        cam_height = prompt_value(
            "Camera height (pixels)",
            default=get_env_var("CAMERA_HEIGHT", "480"),
            validator=lambda v, f: validate_int(v, f, 240, 1080),
        )
        cam_fps = prompt_value(
            "Camera FPS",
            default=get_env_var("CAMERA_FPS", "30"),
            validator=lambda v, f: validate_int(v, f, 1, 60),
        )

        update_env_var("USE_CAMERA", "True")
        update_env_var("CAMERA_WIDTH", cam_width)
        update_env_var("CAMERA_HEIGHT", cam_height)
        update_env_var("CAMERA_FPS", cam_fps)

        # Store in setup state
        setup_state["hardware_config"]["camera"] = {
            "enabled": True,
            "width": cam_width,
            "height": cam_height,
            "fps": cam_fps,
        }
    else:
        update_env_var("USE_CAMERA", "False")
        setup_state["hardware_config"]["camera"] = {"enabled": False}

    # GPS configuration
    print_subheader("GPS Configuration")
    use_gps = prompt_bool(
        "Use GPS for navigation?",
        default=detected_hardware.get("gps", False),
        help_text=("GPS provides absolute positioning for navigation and boundary mapping."),
    )

    if use_gps:
        gps_port = prompt_value(
            "GPS serial port",
            default=get_env_var("GPS_SERIAL_PORT", "/dev/ttyAMA0"),
            help_text="The serial port where your GPS module is connected.",
        )
        gps_baud = prompt_value(
            "GPS baud rate",
            default=get_env_var("GPS_BAUD_RATE", "115200"),
            validator=lambda v, f: validate_int(v, f, 9600, 921600),
        )

        update_env_var("GPS_SERIAL_PORT", gps_port)
        update_env_var("GPS_BAUD_RATE", gps_baud)

        # Ask about RTK correction
        use_rtk = prompt_bool(
            "Use RTK correction for high-precision GPS?",
            default=False,
            help_text=(
                "RTK correction provides centimeter-level accuracy but requires " "an NTRIP server subscription."
            ),
        )

        if use_rtk:
            print_info("To use RTK correction, you'll need NTRIP server credentials.")
            ntrip_user = prompt_value("NTRIP username", default=get_env_var("NTRIP_USER", ""))
            ntrip_pass = prompt_value(
                "NTRIP password",
                default=get_env_var("NTRIP_PASS", ""),
                secret=True,
            )
            ntrip_url = prompt_value("NTRIP server URL", default=get_env_var("NTRIP_URL", ""))
            ntrip_mount = prompt_value(
                "NTRIP mountpoint",
                default=get_env_var("NTRIP_MOUNTPOINT", ""),
            )

            update_env_var("NTRIP_USER", ntrip_user)
            update_env_var("NTRIP_PASS", ntrip_pass)
            update_env_var("NTRIP_URL", ntrip_url)
            update_env_var("NTRIP_MOUNTPOINT", ntrip_mount)

            setup_state["hardware_config"]["rtk"] = {
                "enabled": True,
                "server": ntrip_url,
            }
        else:
            setup_state["hardware_config"]["rtk"] = {"enabled": False}

        setup_state["hardware_config"]["gps"] = {
            "enabled": True,
            "port": gps_port,
            "baud_rate": gps_baud,
        }
    else:
        update_env_var("GPS_SERIAL_PORT", "")
        setup_state["hardware_config"]["gps"] = {"enabled": False}

    # Motor controller configuration
    print_subheader("Motor Controller Configuration")
    use_robohat = prompt_bool(
        "Use RoboHAT MM1 motor controller?",
        default=detected_hardware.get("robohat", False),
        help_text=("The RoboHAT MM1 is the recommended motor controller for this project."),
    )

    if use_robohat:
        mm1_port = prompt_value(
            "RoboHAT MM1 serial port",
            default=get_env_var("MM1_SERIAL_PORT", "/dev/ttyACM1"),
            help_text="The serial port where your RoboHAT MM1 is connected.",
        )

        update_env_var("MM1_SERIAL_PORT", mm1_port)
        setup_state["hardware_config"]["motor_controller"] = {
            "type": "robohat_mm1",
            "port": mm1_port,
        }
    else:
        print_warning("No motor controller selected. The mower will not be able to move.")
        setup_state["hardware_config"]["motor_controller"] = {"type": "none"}

    # Coral TPU configuration
    if detected_hardware.get("coral_tpu", False):
        print_subheader("Google Coral TPU Configuration")
        use_coral = prompt_bool(
            "Use Google Coral TPU for accelerated obstacle detection?",
            default=True,
            help_text=("The Coral TPU provides hardware acceleration for " "machine learning models."),
        )

        if use_coral:
            update_env_var("USE_CORAL_ACCELERATOR", "True")
            setup_state["hardware_config"]["coral_tpu"] = {"enabled": True}
        else:
            update_env_var("USE_CORAL_ACCELERATOR", "False")
            setup_state["hardware_config"]["coral_tpu"] = {"enabled": False}

    setup_state["completed_sections"].append("hardware_configuration")
    save_setup_state()

    print_success("Hardware configuration completed!")


def setup_mapping_and_navigation() -> None:
    print_header("Mapping & Navigation Configuration")
    # Placeholder for mapping and navigation setup
    print_info("Mapping and navigation setup is not yet implemented.")
    # Example:
    # home_lat_lng = prompt_value("Enter home base latitude,longitude (e.g., 40.7128,-74.0060)", ...)
    # update_env_var("HOME_LAT_LNG", home_lat_lng)
    # setup_state["user_choices"]["home_location"] = home_lat_lng

    if "mapping_navigation" not in setup_state["completed_sections"]:
        setup_state["completed_sections"].append("mapping_navigation")
    save_setup_state()
    print_success("Mapping & Navigation configuration placeholder completed.")


def setup_safety_features() -> None:
    print_header("Safety Features Configuration")

    config_json_path_env = os.environ.get('CONFIG_JSON_PATH')
    if config_json_path_env:
        main_config_path = Path(config_json_path_env)
    else:
        main_config_path = CONFIG_DIR / "main_config.json"
        ensure_directory(CONFIG_DIR) # Ensure config directory exists if using default

    current_config = load_main_config(main_config_path)
    safety_config = current_config.get("safety", {})
    e_stop_configured_value = safety_config.get("use_physical_emergency_stop")
    e_stop_pin_configured = safety_config.get("emergency_stop_gpio_pin")

    print_subheader("Physical Emergency Stop")

    use_e_stop: bool
    e_stop_pin: Optional[int] = None

    if e_stop_configured_value is True:
        print_info(f"Physical emergency stop is already enabled in {main_config_path}.")
        pin_to_report = str(e_stop_pin_configured) if e_stop_pin_configured is not None else "not specified (defaulting to 7)"
        print_info(f"Configured GPIO pin (BCM): {pin_to_report}")
        
        use_e_stop = True
        e_stop_pin = int(e_stop_pin_configured) if e_stop_pin_configured is not None else 7
        
        update_env_var("USE_PHYSICAL_EMERGENCY_STOP", "True")
        if e_stop_pin is not None: # Should always be true if e_stop_configured_value is True from script
             update_env_var("EMERGENCY_STOP_GPIO_PIN", str(e_stop_pin))

    elif e_stop_configured_value is False:
        print_info(f"Physical emergency stop is already disabled in {main_config_path}.")
        use_e_stop = False
        e_stop_pin = None
        update_env_var("USE_PHYSICAL_EMERGENCY_STOP", "False")
        # Remove from .env if it exists from a previous run
        update_env_var("EMERGENCY_STOP_GPIO_PIN", "") 

    else: # Not configured in main_config.json or safety section missing
        print_info(f"Physical emergency stop configuration not found or not set in {main_config_path}.")
        use_e_stop = prompt_bool(
            "Do you want to enable the physical emergency stop button?",
            default=True,
            help_text="A physical emergency stop button provides a critical safety mechanism. This is highly recommended."
        )
        
        current_config.setdefault("safety", {})["use_physical_emergency_stop"] = use_e_stop
        
        if use_e_stop:
            default_pin_str = str(e_stop_pin_configured) if e_stop_pin_configured is not None else "7"
            e_stop_pin_str = prompt_value(
                "Enter GPIO pin for emergency stop (BCM numbering)",
                default=default_pin_str,
                required=True,
                validator=lambda val, name: validate_int(val, name, min_value=0, max_value=27), # Typical RPi GPIO range
                field_name="Emergency Stop GPIO Pin",
                help_text="Use BCM numbering for the GPIO pin. Default is 7 (matches install script)."
            )
            e_stop_pin = int(e_stop_pin_str)
            current_config["safety"]["emergency_stop_gpio_pin"] = e_stop_pin
            update_env_var("EMERGENCY_STOP_GPIO_PIN", str(e_stop_pin))
        else:
            e_stop_pin = None
            # If disabling, ensure the pin is also removed from JSON config for clarity
            if "emergency_stop_gpio_pin" in current_config.get("safety", {}):
                del current_config["safety"]["emergency_stop_gpio_pin"]
            update_env_var("EMERGENCY_STOP_GPIO_PIN", "") # Clear from .env

        save_main_config(main_config_path, current_config)
        update_env_var("USE_PHYSICAL_EMERGENCY_STOP", str(use_e_stop))

    # Update setup_state
    setup_state["feature_flags"]["physical_emergency_stop"] = use_e_stop
    if use_e_stop and e_stop_pin is not None:
        setup_state["hardware_config"]["emergency_stop_gpio_pin"] = e_stop_pin
    elif "emergency_stop_gpio_pin" in setup_state.get("hardware_config", {}): # Clean up if disabled
        del setup_state["hardware_config"]["emergency_stop_gpio_pin"]

    print_info("Additional safety feature configurations can be added here (e.g., obstacle sensor sensitivity).")

    if "safety_features" not in setup_state["completed_sections"]:
        setup_state["completed_sections"].append("safety_features")
    save_setup_state()
    print_success("Safety features configuration updated!")


def setup_web_interface() -> None:
    """Configure web interface settings."""
    print_header("Web Interface Configuration")

    print_subheader("Web Server")

    enable_web = prompt_bool(
        "Enable web interface?",
        default=True,
        help_text=("The web interface allows remote control and monitoring of the mower."),
    )

    if enable_web:
        web_port = prompt_value(
            "Web server port",
            default=get_env_var("WEB_UI_PORT", "5000"),
            validator=lambda v, f: validate_int(v, f, 1024, 65535),
            help_text="The port on which the web interface will be accessible.",
        )

        # Security settings
        print_subheader("Security Settings")

        enable_ssl = prompt_bool(
            "Enable SSL/HTTPS?",
            default=True,
            help_text=("SSL/HTTPS encrypts communication between your browser and the mower."),
        )

        if enable_ssl:
            print_info("You'll need SSL certificates for HTTPS. " "You can use Let's Encrypt to get free certificates.")

            ssl_cert = prompt_value(
                "SSL certificate path",
                default=get_env_var("SSL_CERT_PATH", "config/ssl/cert.pem"),
                help_text="Path to your SSL certificate file.",
            )

            ssl_key = prompt_value(
                "SSL key path",
                default=get_env_var("SSL_KEY_PATH", "config/ssl/key.pem"),
                help_text="Path to your SSL key file.",
            )

            update_env_var("ENABLE_SSL", "True")
            update_env_var("SSL_CERT_PATH", ssl_cert)
            update_env_var("SSL_KEY_PATH", ssl_key)

            setup_state["feature_flags"]["ssl"] = True
        else:
            update_env_var("ENABLE_SSL", "False")
            setup_state["feature_flags"]["ssl"] = False

        # Authentication
        auth_required = prompt_bool(
            "Require authentication?",
            default=True,
            help_text=("Authentication requires users to log in before accessing " "the web interface."),
        )

        if auth_required:
            auth_user = prompt_value(
                "Username",
                default=get_env_var("AUTH_USERNAME", "admin"),
                required=True,
                help_text="Username for web interface login.",
            )

            auth_pass = prompt_value(
                "Password",
                default=get_env_var("AUTH_PASSWORD", ""),
                required=True,
                secret=True,
                help_text="Password for web interface login.",
            )

            update_env_var("AUTH_REQUIRED", "True")
            update_env_var("AUTH_USERNAME", auth_user)
            update_env_var("AUTH_PASSWORD", auth_pass)

            setup_state["feature_flags"]["authentication"] = True
        else:
            update_env_var("AUTH_REQUIRED", "False")
            setup_state["feature_flags"]["authentication"] = False

        # IP restrictions
        use_ip_restrict = prompt_bool(
            "Restrict access by IP address?",
            default=False,
            help_text="Limit access to specific IP addresses or networks.",
        )

        if use_ip_restrict:
            allowed_ips = prompt_value(
                "Allowed IPs (comma-separated)",
                default=get_env_var("ALLOWED_IPS", "127.0.0.1,192.168.1.0/24"),
                required=True,
                help_text=("List of IP addresses or CIDR ranges that can access " "the web interface."),
            )

            update_env_var("ALLOWED_IPS", allowed_ips)
            setup_state["feature_flags"]["ip_restriction"] = True
        else:
            setup_state["feature_flags"]["ip_restriction"] = False

        update_env_var("ENABLE_WEB_UI", "True")
        update_env_var("WEB_UI_PORT", web_port)

        setup_state["feature_flags"]["web_interface"] = True
        setup_state["user_choices"]["web_port"] = web_port
    else:
        update_env_var("ENABLE_WEB_UI", "False")
        setup_state["feature_flags"]["web_interface"] = False

    setup_state["completed_sections"].append("web_interface")
    save_setup_state()

    print_success("Web interface configuration completed!")


def setup_remote_access() -> None:
    """Configure remote access options."""
    print_header("Remote Access Configuration")

    print_info("Remote access allows you to control and monitor your mower from anywhere.")

    use_remote = prompt_bool(
        "Set up remote access?",
        default=True,
        help_text="Remote access requires additional configuration of your network.",
    )

    if use_remote:
        print_subheader("Remote Access Method")

        remote_method = prompt_choice(
            "Select remote access method",
            [
                "Dynamic DNS (DDNS)",
                "Cloudflare Tunnel",
                "NGROK",
                "None/Manual",
            ],
            default=1,  # DDNS
        )

        if remote_method == "Dynamic DNS (DDNS)":
            print_info("DDNS allows you to access your mower using a domain name " "even if your IP address changes.")
            print_help("You'll need an account with a DDNS provider like Duck DNS, " "No-IP, or DynDNS.")

            ddns_provider = prompt_value(
                "DDNS provider",
                default=get_env_var("DDNS_PROVIDER", "duckdns"),
                help_text=("The name of your DDNS provider (e.g., duckdns, noip, dyndns)."),
            )

            ddns_domain = prompt_value(
                "DDNS domain",
                default=get_env_var("DDNS_DOMAIN", ""),
                required=True,
                help_text="Your DDNS domain name (e.g., mymower.duckdns.org).",
            )

            ddns_token = prompt_value(
                "DDNS token/key",
                default=get_env_var("DDNS_TOKEN", ""),
                required=True,
                secret=True,
                help_text=("The token or key provided by your DDNS provider " "for authentication."),
            )

            update_env_var("DDNS_PROVIDER", ddns_provider)
            update_env_var("DDNS_DOMAIN", ddns_domain)
            update_env_var("DDNS_TOKEN", ddns_token)
            update_env_var("USE_DDNS", "True")

            setup_state["feature_flags"]["remote_access"] = "ddns"
            setup_state["user_choices"]["ddns_domain"] = ddns_domain

        elif remote_method == "Cloudflare Tunnel":
            print_info("Cloudflare Tunnel provides secure remote access without opening " "ports on your router.")
            print_help("You'll need a Cloudflare account and domain name.")

            cf_token = prompt_value(
                "Cloudflare API token",
                default=get_env_var("CLOUDFLARE_API_TOKEN", ""),
                required=True,
                secret=True,
                help_text="Your Cloudflare API token with Zone.DNS permissions.",
            )

            cf_zone = prompt_value(
                "Cloudflare zone ID",
                default=get_env_var("CLOUDFLARE_ZONE_ID", ""),
                required=True,
                help_text="Your Cloudflare zone ID for your domain.",
            )

            cf_domain = prompt_value(
                "Cloudflare domain",
                default=get_env_var("CLOUDFLARE_DOMAIN", ""),
                required=True,
                help_text="The domain name you want to use (e.g., mower.example.com).",
            )

            update_env_var("CLOUDFLARE_API_TOKEN", cf_token)
            update_env_var("CLOUDFLARE_ZONE_ID", cf_zone)
            update_env_var("CLOUDFLARE_DOMAIN", cf_domain)
            update_env_var("USE_CLOUDFLARE", "True")

            setup_state["feature_flags"]["remote_access"] = "cloudflare"
            setup_state["user_choices"]["cf_domain"] = cf_domain

        elif remote_method == "NGROK":
            print_info("NGROK provides temporary URLs for remote access without " "configuring your router.")
            print_help("You'll need an NGROK account and authtoken.")

            ngrok_token = prompt_value(
                "NGROK authtoken",
                default=get_env_var("NGROK_AUTHTOKEN", ""),
                required=True,
                secret=True,
                help_text="Your NGROK authtoken from your account dashboard.",
            )

            update_env_var("NGROK_AUTHTOKEN", ngrok_token)
            update_env_var("USE_NGROK", "True")

            setup_state["feature_flags"]["remote_access"] = "ngrok"
        else:
            print_info("You've chosen to set up remote access manually or not at all.")
            print_info("To access your mower remotely, you'll need to configure " "port forwarding on your router.")

            setup_state["feature_flags"]["remote_access"] = "manual"
    else:
        setup_state["feature_flags"]["remote_access"] = "none"

    setup_state["completed_sections"].append("remote_access")
    save_setup_state()

    print_success("Remote access configuration completed!")


def setup_scheduling() -> None:
    """Configure scheduling and automation."""
    print_header("Scheduling and Automation")

    print_subheader("Mowing Schedule")

    use_schedule = prompt_bool(
        "Set up automated mowing schedule?",
        default=True,
        help_text=("Automated scheduling allows the mower to operate on a regular schedule."),
    )

    if use_schedule:
        print_info("You can set up multiple mowing sessions per week.")
        print_help("For each day, you can specify start and end times for mowing.")

        # Create a basic schedule template
        schedule = {}
        days = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]

        for day in days:
            use_day = prompt_bool(f"Mow on {day}?", default=True)

            if use_day:
                start_time = prompt_value(
                    f"{day} start time (HH:MM)",
                    default="10:00",
                    validator=lambda v, f: bool(v.count(":") == 1 and all(part.isdigit() for part in v.split(":"))),
                    field_name="Start time",
                )

                end_time = prompt_value(
                    f"{day} end time (HH:MM)",
                    default="16:00",
                    validator=lambda v, f: bool(v.count(":") == 1 and all(part.isdigit() for part in v.split(":"))),
                    field_name="End time",
                )

                schedule[day.lower()] = {
                    "enabled": True,
                    "start": start_time,
                    "end": end_time,
                }
            else:
                # Save schedule to a JSON file
                schedule[day.lower()] = {"enabled": False}
        schedule_path = Path(CONFIG_DIR) / "mowing_schedule.json"
        ensure_directory(CONFIG_DIR)
        with open(schedule_path, "w", encoding="utf-8") as f:
            json.dump(schedule, f, indent=2)

        update_env_var("MOWING_SCHEDULE_PATH", str(schedule_path))
        update_env_var("USE_SCHEDULE", "True")

        setup_state["feature_flags"]["scheduling"] = True
        setup_state["user_choices"]["schedule_file"] = str(schedule_path)
    else:
        update_env_var("USE_SCHEDULE", "False")
        setup_state["feature_flags"]["scheduling"] = False

    # Weather integration
    print_subheader("Weather Integration")

    use_weather = prompt_bool(
        "Enable weather-aware scheduling?",
        default=True,
        help_text=("Weather-aware scheduling prevents mowing during rain or extreme weather."),
    )

    if use_weather:
        print_info("You'll need a Google Weather API key for weather data.")
        print_help(
            "You can get an API key from the Google Cloud Console. "
            "Enable the 'Weather API' (under Google Maps Platform) for your project."
        )

        weather_api_key = prompt_value(
            "Google Weather API Key",
            default=get_env_var("GOOGLE_WEATHER_API_KEY", ""),
            required=True,
            help_text="Your Google Weather API key.",
        )

        update_env_var("GOOGLE_WEATHER_API_KEY", weather_api_key)
        update_env_var("WEATHER_AWARE_SCHEDULING", "True")

        setup_state["feature_flags"]["weather_integration"] = True
    else:
        update_env_var("WEATHER_AWARE_SCHEDULING", "False")
        setup_state["feature_flags"]["weather_integration"] = False

    setup_state["completed_sections"].append("scheduling")
    save_setup_state()

    print_success("Scheduling and automation configuration completed!")


def setup_service_installation() -> None:
    """Configure systemd service installation for automatic startup."""
    print_header("Service Installation")

    print_info(
        "The autonomous mower can be configured to run as a system service, "
        "automatically starting when your Raspberry Pi boots."
    )


    install_service = prompt_bool(
        "Install mower as a system service for automatic startup?",
        default=True,
        help_text=(
            "This will install the mower.service file and enable it "
            "to start automatically on boot. Recommended for production use."
        ),
    )

    if install_service:
        try:
            import platform
            import subprocess
            from pathlib import Path

            if platform.system() != "Linux":
                print_warning(
                    "Service installation is only supported on Linux systems. Skipping service installation."
                )
                setup_state["feature_flags"]["service_installed"] = False
                return

            print_subheader("Installing Systemd Service")

            # Check if service files exist
            service_file = Path("mower.service")
            if not service_file.exists():
                print_error(
                    "Service file 'mower.service' not found in "
                    "current directory. Please ensure the service file exists "
                    "before running setup."
                )
                setup_state["feature_flags"]["service_installed"] = False
                return

            print_info("Installing service file to /etc/systemd/system/...")

            # Copy service file to systemd directory
            result = subprocess.run(
                ["sudo", "cp", str(service_file), "/etc/systemd/system/"],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                print_error(f"Failed to copy service file: {result.stderr}")
                setup_state["feature_flags"]["service_installed"] = False
                return

            # Set proper permissions
            result = subprocess.run(
                [
                    "sudo",
                    "chmod",
                    "644",
                    "/etc/systemd/system/mower.service",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                print_error(f"Failed to set service file permissions: {result.stderr}")
                setup_state["feature_flags"]["service_installed"] = False
                return

            # Reload systemd daemon
            print_info("Reloading systemd daemon...")
            result = subprocess.run(
                ["sudo", "systemctl", "daemon-reload"],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                print_error(f"Failed to reload systemd daemon: {result.stderr}")
                setup_state["feature_flags"]["service_installed"] = False
                return

            # Enable service to start on boot
            print_info("Enabling mower service to start on boot...")
            result = subprocess.run(
                ["sudo", "systemctl", "enable", "mower.service"],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                print_error(f"Failed to enable service: {result.stderr}")
                setup_state["feature_flags"]["service_installed"] = False
                return

            print_success("Mower service has been installed and enabled!")
            print_info("The service will start automatically on system boot.")
            print_info("You can manually control the service with:")
            print_info("  sudo systemctl start mower")
            print_info("  sudo systemctl stop mower")
            print_info("  sudo systemctl status mower")
            print_info("  sudo journalctl -u mower -f  # View logs")

            setup_state["feature_flags"]["service_installed"] = True

            # Ask if user wants to start the service now
            start_now = prompt_bool(
                "Start the mower service now?",
                default=False,
                help_text=(
                    "This will start the mower service immediately. "
                    "Make sure all configuration is complete before starting."
                ),
            )

            if start_now:
                print_info("Starting mower service...")
                result = subprocess.run(
                    ["sudo", "systemctl", "start", "mower.service"],
                    capture_output=True,
                    text=True,
                    check=False,
                )

                if result.returncode == 0:
                    print_success("Service started successfully!")

                    # Check service status
                    result = subprocess.run(
                        ["sudo", "systemctl", "is-active", "mower.service"],
                        capture_output=True,
                        text=True,
                        check=False,
                    )

                    if result.stdout.strip() == "active":
                        print_info("Service is running and active.")
                    else:
                        print_warning("Service may not be running properly. Check logs with:")
                        print_warning("  sudo journalctl -u mower -f")
                else:
                    print_error(f"Failed to start service: {result.stderr}")
                    print_info("You can try starting it manually later with:")
                    print_info("  sudo systemctl start mower")

        except Exception as e:
            print_error(f"An error occurred during service installation: {e}")
            print_warning("Service installation failed. You can install it manually later.")
            setup_state["feature_flags"]["service_installed"] = False

    else:
        print_info("Skipping service installation.")
        print_info("You can install the service manually later with:")
        print_info("  sudo cp mower.service /etc/systemd/system/")
        print_info("  sudo systemctl daemon-reload")
        print_info("  sudo systemctl enable mower.service")
        setup_state["feature_flags"]["service_installed"] = False

    setup_state["completed_sections"].append("service_installation")
    save_setup_state()

    print_success("Service installation configuration completed!")


def setup_final_verification() -> None:
    """Perform final verification and setup."""
    print_header("Final Verification and Setup")

    print_info(
        "Verifying configuration and setting up required directories..."
    )  # Ensure all required directories exist
    directories = [
        CONFIG_DIR,
        Path("logs"),
        Path("data"),
    ]

    for directory in directories:
        ensure_directory(directory)

    # Create empty configuration files if they don't exist
    if not (CONFIG_DIR / "user_polygon.json").exists():
        with open(CONFIG_DIR / "user_polygon.json", "w", encoding="utf-8") as f:
            json.dump({"type": "Polygon", "coordinates": []}, f)

    if not (CONFIG_DIR / "home_location.json").exists():
        with open(CONFIG_DIR / "home_location.json", "w", encoding="utf-8") as f:
            json.dump({"location": [0, 0]}, f)  # Summary of configuration
    print_subheader("Configuration Summary")

    mower_name = setup_state["user_choices"].get("mower_name", "AutonoMow")
    print(f"Mower Name: {mower_name}")
    sim_mode = setup_state["feature_flags"].get("simulation_mode", False)
    print(f"Simulation Mode: {'Enabled' if sim_mode else 'Disabled'}")

    # Hardware summary
    print("\nHardware Configuration:")
    hardware_config = setup_state.get("hardware_config", {})

    camera_enabled = hardware_config.get("camera", {}).get("enabled", False)
    print(f"  Camera: {'Enabled' if camera_enabled else 'Disabled'}")

    gps_enabled = hardware_config.get("gps", {}).get("enabled", False)
    print(f"  GPS: {'Enabled' if gps_enabled else 'Disabled'}")

    motor_type = hardware_config.get("motor_controller", {}).get("type", "none")
    print(f"  Motor Controller: {motor_type}")

    coral_enabled = hardware_config.get("coral_tpu", {}).get("enabled", False)
    print(f"  Coral TPU: {'Enabled' if coral_enabled else 'Disabled'}")

    # Feature summary
    print("\nEnabled Features:")
    feature_flags = setup_state.get("feature_flags", {})

    features = [
        ("Web Interface", feature_flags.get("web_interface", False)),
        (
            "Remote Access",
            feature_flags.get("remote_access", "none") != "none",
        ),
        ("Scheduling", feature_flags.get("scheduling", False)),
        (
            "Weather Integration",
            feature_flags.get("weather_integration", False),
        ),
        ("Safety Zones", feature_flags.get("safety_zones", False)),
        ("Tilt Sensor", feature_flags.get("tilt_sensor", False)),
        ("Rain Sensor", feature_flags.get("rain_sensor", False)),
        ("SSL/HTTPS", feature_flags.get("ssl", False)),
        ("Authentication", feature_flags.get("authentication", False)),
    ]

    for feature, enabled in features:
        print(f"  {feature}: {'Enabled' if enabled else 'Disabled'}")

    # Final confirmation
    print_subheader("Setup Complete")

    print(
        """
Your autonomous mower has been configured successfully! Here are the next steps:

1. Start the mower system with: python -m src.mower.main_controller
2. Access the web interface (if enabled) at: http://localhost:5000 (or https for SSL)
3. Use the web interface to define your mowing boundaries
4. Test the system in simulation mode before deploying to hardware

For more information, refer to the documentation in the docs/ directory.
    """
    )

    setup_state["completed_sections"].append("final_verification")
    save_setup_state()


def main() -> None:
    # Ensure .env file exists and is writable from the start
    ensure_env_file()

    if not install_dependencies(): # Install critical dependencies first
        print_error("Failed to install core dependencies. Setup cannot continue.")
        sys.exit(1)

    # Now that dependencies are installed, run permission checks
    if not run_enhanced_permission_checks():
        print_warning("Some permission checks failed. Please review the messages above.")
        if not prompt_bool("Continue with setup despite permission issues?", default=False):
            sys.exit(1)


    load_setup_state()
    welcome_screen()
    detected_hardware = setup_hardware_detection()
    setup_basic_configuration()
    setup_hardware_configuration(detected_hardware)
    setup_mapping_and_navigation()
    setup_safety_features()
    setup_web_interface()
    setup_remote_access()
    setup_scheduling()
    setup_service_installation()
    setup_final_verification()

    # Clean up setup state file
    if SETUP_STATE_FILE.exists():
        SETUP_STATE_FILE.unlink()
        print_info(f"Removed setup state file: {SETUP_STATE_FILE}")

    print_success("Setup wizard completed successfully!")


if __name__ == "__main__":
    # Ensure the script is run with sufficient permissions if it needs to install packages or modify system files
    # Note: python-dotenv installation is handled internally now.
    # For other operations like `raspi-config` or `systemctl`, sudo might be needed if called directly.
    # The wizard itself tries to avoid direct sudo calls, guiding user or using user-level configs.

    # Add a try-except block for graceful exit on Ctrl+C
    try:
        main()
    except KeyboardInterrupt:
        print_info("\nSetup wizard exited by user. Your progress has been saved.")
        save_setup_state() # Ensure state is saved on Ctrl+C
        sys.exit(0)
    except Exception as e:
        print_error(f"An unexpected error occurred: {e}")
        # Consider logging the full traceback for debugging
        # import traceback
        # print_error(traceback.format_exc())
        save_setup_state() # Attempt to save state even on error
        sys.exit(1)
