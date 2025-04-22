#!/usr/bin/env python3
"""
Autonomous Mower Setup Wizard

This script provides an interactive setup process for the autonomous mower system.
It guides users through configuring all necessary settings, collecting tokens and
credentials, and setting up the environment based on their specific needs.
"""

import os
import sys
import json
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Union, Tuple

# Try to import dotenv, install if not available
try:
    from dotenv import load_dotenv, set_key
except ImportError:
    print("Installing python-dotenv...")
    os.system(f"{sys.executable} -m pip install python-dotenv")
    from dotenv import load_dotenv, set_key

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


def color_text(text: str, color: str) -> str:
    """Add color to terminal text."""
    return f"{COLORS.get(color, '')}{text}{COLORS['RESET']}"


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
    import textwrap
    for line in textwrap.wrap(message, width=76):
        print(f"{color_text('?', 'MAGENTA')} {line}")


def ensure_directory(path: Path) -> None:
    """Ensure a directory exists."""
    if not path.exists():
        path.mkdir(parents=True)
        print_info(f"Created directory: {path}")


def ensure_env_file() -> None:
    """Ensure .env file exists, create from example if needed."""
    if not ENV_FILE.exists():
        if ENV_EXAMPLE.exists():
            shutil.copy(ENV_EXAMPLE, ENV_FILE)
            print_info(f"Created {ENV_FILE} from {ENV_EXAMPLE}")
        else:
            ENV_FILE.touch()
            print_info(f"Created empty {ENV_FILE}")


def save_setup_state() -> None:
    """Save the current setup state to a file."""
    with open(SETUP_STATE_FILE, 'w') as f:
        json.dump(setup_state, f, indent=2)
    print_info(f"Setup progress saved to {SETUP_STATE_FILE}")


def load_setup_state() -> bool:
    """Load setup state from file if it exists."""
    global setup_state
    if SETUP_STATE_FILE.exists():
        try:
            with open(SETUP_STATE_FILE, 'r') as f:
                setup_state = json.load(f)
            print_info(f"Loaded setup progress from {SETUP_STATE_FILE}")
            return True
        except Exception as e:
            print_warning(f"Failed to load setup state: {e}")
    return False


def update_env_var(key: str, value: str) -> None:
    """Update an environment variable in the .env file."""
    set_key(str(ENV_FILE), key, value)


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
            sel = input(f"Enter choice [1-{len(choices)}]" +
                      (f" (default: {default}): " if default else ": "))
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
                import getpass
                val = getpass.getpass(f"{prompt}" + (f" (default: [hidden]): " if default else ": "))
            else:
                val = input(f"{prompt}" + (f" (default: {default}): " if default else ": "))

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


def prompt_bool(prompt: str, default: Optional[bool] = None, help_text: Optional[str] = None) -> bool:
    """Prompt for a yes/no response."""
    if help_text:
        print_help(help_text)

    default_str = None
    if default is not None:
        default_str = "y" if default else "n"

    while True:
        try:
            val = input(f"{prompt} (y/n)" +
                      (f" (default: {default_str}): " if default_str else ": "))

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


def validate_float(value: str, field_name: str, min_value: Optional[float] = None, max_value: Optional[float] = None) -> bool:
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


def validate_int(value: str, field_name: str, min_value: Optional[int] = None, max_value: Optional[int] = None) -> bool:
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
    except Exception:
        print_error(f"{field_name} must be in format: lat,lng (e.g. 39.1,-84.5)")
        return False


def welcome_screen() -> None:
    """Display welcome screen and introduction."""
    print_header("Autonomous Mower Setup Wizard")
    print("""
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
    """)
    input("Press Enter to continue...")


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
        print_warning("Failed to check for camera")

    # Check for GPS (serial device)
    try:
        if os.path.exists("/dev/ttyAMA0") or os.path.exists("/dev/ttyACM0"):
            hardware["gps"] = True
            print_success("Potential GPS device detected")
        else:
            print_warning("No GPS device detected")
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
        help_text="A unique name for your mower. This will be used in logs and the web interface."
    )
    update_env_var("MOWER_NAME", mower_name)

    print_subheader("Logging")
    log_level = prompt_choice(
        "Select log level",
        ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=2  # INFO
    )
    update_env_var("LOG_LEVEL", log_level)

    debug_mode = prompt_bool(
        "Enable debug mode?",
        default=False,
        help_text="Debug mode provides additional logging and diagnostic information."
    )
    update_env_var("DEBUG_MODE", str(debug_mode))

    print_subheader("Simulation Mode")
    use_simulation = prompt_bool(
        "Use simulation mode?",
        default=False,
        help_text="Simulation mode allows testing without physical hardware. Recommended for initial setup and testing."
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
        help_text="The camera is used for visual obstacle detection and navigation."
    )

    if use_camera:
        cam_width = prompt_value(
            "Camera width (pixels)",
            default=get_env_var("CAMERA_WIDTH", "640"),
            validator=lambda v, f: validate_int(v, f, 320, 1920)
        )
        cam_height = prompt_value(
            "Camera height (pixels)",
            default=get_env_var("CAMERA_HEIGHT", "480"),
            validator=lambda v, f: validate_int(v, f, 240, 1080)
        )
        cam_fps = prompt_value(
            "Camera FPS",
            default=get_env_var("CAMERA_FPS", "30"),
            validator=lambda v, f: validate_int(v, f, 1, 60)
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
            "fps": cam_fps
        }
    else:
        update_env_var("USE_CAMERA", "False")
        setup_state["hardware_config"]["camera"] = {"enabled": False}

    # GPS configuration
    print_subheader("GPS Configuration")
    use_gps = prompt_bool(
        "Use GPS for navigation?",
        default=detected_hardware.get("gps", False),
        help_text="GPS provides absolute positioning for navigation and boundary mapping."
    )

    if use_gps:
        gps_port = prompt_value(
            "GPS serial port",
            default=get_env_var("GPS_SERIAL_PORT", "/dev/ttyAMA0"),
            help_text="The serial port where your GPS module is connected."
        )
        gps_baud = prompt_value(
            "GPS baud rate",
            default=get_env_var("GPS_BAUD_RATE", "115200"),
            validator=lambda v, f: validate_int(v, f, 9600, 921600)
        )

        update_env_var("GPS_SERIAL_PORT", gps_port)
        update_env_var("GPS_BAUD_RATE", gps_baud)

        # Ask about RTK correction
        use_rtk = prompt_bool(
            "Use RTK correction for high-precision GPS?",
            default=False,
            help_text="RTK correction provides centimeter-level accuracy but requires an NTRIP server subscription."
        )

        if use_rtk:
            print_info("To use RTK correction, you'll need NTRIP server credentials.")
            ntrip_user = prompt_value("NTRIP username", default=get_env_var("NTRIP_USER", ""))
            ntrip_pass = prompt_value("NTRIP password", default=get_env_var("NTRIP_PASS", ""), secret=True)
            ntrip_url = prompt_value("NTRIP server URL", default=get_env_var("NTRIP_URL", ""))
            ntrip_mount = prompt_value("NTRIP mountpoint", default=get_env_var("NTRIP_MOUNTPOINT", ""))

            update_env_var("NTRIP_USER", ntrip_user)
            update_env_var("NTRIP_PASS", ntrip_pass)
            update_env_var("NTRIP_URL", ntrip_url)
            update_env_var("NTRIP_MOUNTPOINT", ntrip_mount)

            setup_state["hardware_config"]["rtk"] = {
                "enabled": True,
                "server": ntrip_url
            }
        else:
            setup_state["hardware_config"]["rtk"] = {"enabled": False}

        setup_state["hardware_config"]["gps"] = {
            "enabled": True,
            "port": gps_port,
            "baud_rate": gps_baud
        }
    else:
        update_env_var("GPS_SERIAL_PORT", "")
        setup_state["hardware_config"]["gps"] = {"enabled": False}

    # Motor controller configuration
    print_subheader("Motor Controller Configuration")
    use_robohat = prompt_bool(
        "Use RoboHAT MM1 motor controller?",
        default=detected_hardware.get("robohat", False),
        help_text="The RoboHAT MM1 is the recommended motor controller for this project."
    )

    if use_robohat:
        mm1_port = prompt_value(
            "RoboHAT MM1 serial port",
            default=get_env_var("MM1_SERIAL_PORT", "/dev/ttyACM1"),
            help_text="The serial port where your RoboHAT MM1 is connected."
        )

        update_env_var("MM1_SERIAL_PORT", mm1_port)
        setup_state["hardware_config"]["motor_controller"] = {
            "type": "robohat_mm1",
            "port": mm1_port
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
            help_text="The Coral TPU provides hardware acceleration for machine learning models."
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
    """Configure mapping and navigation settings."""
    print_header("Mapping and Navigation")

    # Check if GPS is enabled in setup state
    gps_enabled = setup_state.get("hardware_config", {}).get("gps", {}).get("enabled", False)

    if not gps_enabled:
        print_warning("GPS is not enabled. Some mapping features will be limited.")

    # Home location
    print_subheader("Home Location")
    print_info("The home location is where the mower will return when it's finished or needs to charge.")

    if gps_enabled:
        print_help("You can specify the home location as GPS coordinates (latitude,longitude).")
        home_coords = prompt_value(
            "Home location coordinates (latitude,longitude)",
            default=f"{get_env_var('HOME_LAT', '0.0')},{get_env_var('HOME_LON', '0.0')}",
            validator=validate_lat_lng,
            field_name="Home location"
        )

        lat, lon = map(float, home_coords.split(","))
        update_env_var("HOME_LAT", str(lat))
        update_env_var("HOME_LON", str(lon))

        # Also set default map center for web UI
        update_env_var("MAP_DEFAULT_LAT", str(lat))
        update_env_var("MAP_DEFAULT_LNG", str(lon))

        setup_state["user_choices"]["home_location"] = {"lat": lat, "lon": lon}
    else:
        print_info("Since GPS is disabled, the home location will be set relative to the starting position.")
        setup_state["user_choices"]["home_location"] = {"relative": True}

    # Google Maps integration for web UI
    print_subheader("Google Maps Integration")
    use_google_maps = prompt_bool(
        "Use Google Maps in the web interface?",
        default=True,
        help_text="Google Maps provides a visual interface for setting boundaries and monitoring the mower."
    )

    if use_google_maps:
        print_info("To use Google Maps, you'll need an API key from the Google Cloud Console.")
        print_help("You can get an API key at: https://developers.google.com/maps/documentation/javascript/get-api-key")

        gmaps_key = prompt_value(
            "Google Maps API Key",
            default=get_env_var("GOOGLE_MAPS_API_KEY", ""),
            required=True,
            field_name="Google Maps API Key"
        )

        update_env_var("GOOGLE_MAPS_API_KEY", gmaps_key)
        setup_state["feature_flags"]["google_maps"] = True
    else:
        setup_state["feature_flags"]["google_maps"] = False

    # Path planning settings
    print_subheader("Path Planning")

    pattern_type = prompt_choice(
        "Select mowing pattern",
        ["PARALLEL", "SPIRAL", "RANDOM", "ADAPTIVE"],
        default=1  # PARALLEL
    )

    spacing = prompt_value(
        "Path spacing (meters)",
        default=get_env_var("PATH_PLANNING_SPACING", "0.3"),
        validator=lambda v, f: validate_float(v, f, 0.1, 1.0),
        help_text="The distance between parallel paths. Smaller values provide more thorough coverage but take longer."
    )

    update_env_var("PATH_PLANNING_PATTERN_TYPE", pattern_type)
    update_env_var("PATH_PLANNING_SPACING", spacing)

    setup_state["user_choices"]["mowing_pattern"] = {
        "type": pattern_type,
        "spacing": float(spacing)
    }

    setup_state["completed_sections"].append("mapping_and_navigation")
    save_setup_state()

    print_success("Mapping and navigation configuration completed!")


def setup_safety_features() -> None:
    """Configure safety features."""
    print_header("Safety Features")

    # Emergency stop
    print_subheader("Emergency Stop")
    print_info("The emergency stop button is a critical safety feature that immediately stops the mower.")

    e_stop_pin = prompt_value(
        "Emergency stop GPIO pin",
        default=get_env_var("EMERGENCY_STOP_PIN", "7"),
        validator=lambda v, f: validate_int(v, f, 1, 40),
        help_text="The GPIO pin where the emergency stop button is connected. The button should be normally closed (NC)."
    )

    update_env_var("EMERGENCY_STOP_PIN", e_stop_pin)

    # Obstacle detection
    print_subheader("Obstacle Detection")

    # Check if camera is enabled in setup state
    camera_enabled = setup_state.get("hardware_config", {}).get("camera", {}).get("enabled", False)

    if camera_enabled:
        min_conf = prompt_value(
            "Minimum confidence threshold for obstacle detection",
            default=get_env_var("MIN_CONF_THRESHOLD", "0.5"),
            validator=lambda v, f: validate_float(v, f, 0.1, 1.0),
            help_text="Lower values detect more objects but may have false positives. Higher values are more selective."
        )

        update_env_var("MIN_CONF_THRESHOLD", min_conf)

        setup_state["user_choices"]["obstacle_detection"] = {
            "enabled": True,
            "confidence_threshold": float(min_conf)
        }
    else:
        print_warning("Camera is not enabled. Visual obstacle detection will not be available.")
        setup_state["user_choices"]["obstacle_detection"] = {"enabled": False}

    # Safety zones
    print_subheader("Safety Zones")
    print_info("Safety zones define areas where the mower should not operate or should use extra caution.")

    use_safety_zones = prompt_bool(
        "Configure safety zones?",
        default=True,
        help_text="Safety zones include no-mow zones, children play areas, and pet zones."
    )

    if use_safety_zones:
        safe_buffer = prompt_value(
            "Safe zone buffer (meters)",
            default=get_env_var("SAFE_ZONE_BUFFER", "1.0"),
            validator=lambda v, f: validate_float(v, f, 0.5, 5.0),
            help_text="The distance the mower will maintain from defined safety zones."
        )

        update_env_var("SAFE_ZONE_BUFFER", safe_buffer)

        print_info("Safety zones can be configured in the web interface after setup.")
        setup_state["feature_flags"]["safety_zones"] = True
    else:
        setup_state["feature_flags"]["safety_zones"] = False

    # Battery safety
    print_subheader("Battery Safety")

    batt_low = prompt_value(
        "Battery low threshold (%)",
        default=get_env_var("BATTERY_LOW_THRESHOLD", "20"),
        validator=lambda v, f: validate_int(v, f, 5, 50),
        help_text="When battery level falls below this percentage, the mower will return to the charging station."
    )

    batt_critical = prompt_value(
        "Battery critical threshold (%)",
        default=get_env_var("BATTERY_CRITICAL_THRESHOLD", "10"),
        validator=lambda v, f: validate_int(v, f, 1, int(batt_low) - 1),
        help_text="When battery level falls below this percentage, the mower will enter emergency shutdown."
    )

    update_env_var("BATTERY_LOW_THRESHOLD", batt_low)
    update_env_var("BATTERY_CRITICAL_THRESHOLD", batt_critical)

    # Tilt sensor
    print_subheader("Tilt Sensor")

    use_tilt = prompt_bool(
        "Enable tilt sensor?",
        default=True,
        help_text="The tilt sensor prevents the mower from operating on steep slopes."
    )

    if use_tilt:
        max_slope = prompt_value(
            "Maximum slope angle (degrees)",
            default=get_env_var("MAX_SLOPE_ANGLE", "15"),
            validator=lambda v, f: validate_int(v, f, 5, 45),
            help_text="The maximum slope angle the mower can safely operate on."
        )

        update_env_var("TILT_SENSOR_ENABLED", "True")
        update_env_var("MAX_SLOPE_ANGLE", max_slope)

        setup_state["feature_flags"]["tilt_sensor"] = True
        setup_state["user_choices"]["max_slope"] = int(max_slope)
    else:
        update_env_var("TILT_SENSOR_ENABLED", "False")
        setup_state["feature_flags"]["tilt_sensor"] = False

    # Rain sensor
    print_subheader("Rain Sensor")

    use_rain = prompt_bool(
        "Enable rain sensor?",
        default=True,
        help_text="The rain sensor prevents the mower from operating in wet conditions."
    )

    update_env_var("RAIN_SENSOR_ENABLED", str(use_rain))
    setup_state["feature_flags"]["rain_sensor"] = use_rain

    setup_state["completed_sections"].append("safety_features")
    save_setup_state()

    print_success("Safety features configuration completed!")


def setup_web_interface() -> None:
    """Configure web interface settings."""
    print_header("Web Interface Configuration")

    print_subheader("Web Server")

    enable_web = prompt_bool(
        "Enable web interface?",
        default=True,
        help_text="The web interface allows remote control and monitoring of the mower."
    )

    if enable_web:
        web_port = prompt_value(
            "Web server port",
            default=get_env_var("WEB_UI_PORT", "5000"),
            validator=lambda v, f: validate_int(v, f, 1024, 65535),
            help_text="The port on which the web interface will be accessible."
        )

        # Security settings
        print_subheader("Security Settings")

        enable_ssl = prompt_bool(
            "Enable SSL/HTTPS?",
            default=True,
            help_text="SSL/HTTPS encrypts communication between your browser and the mower."
        )

        if enable_ssl:
            print_info("You'll need SSL certificates for HTTPS. You can use Let's Encrypt to get free certificates.")

            ssl_cert = prompt_value(
                "SSL certificate path",
                default=get_env_var("SSL_CERT_PATH", "config/ssl/cert.pem"),
                help_text="Path to your SSL certificate file."
            )

            ssl_key = prompt_value(
                "SSL key path",
                default=get_env_var("SSL_KEY_PATH", "config/ssl/key.pem"),
                help_text="Path to your SSL key file."
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
            help_text="Authentication requires users to log in before accessing the web interface."
        )

        if auth_required:
            auth_user = prompt_value(
                "Username",
                default=get_env_var("AUTH_USERNAME", "admin"),
                required=True,
                help_text="Username for web interface login."
            )

            auth_pass = prompt_value(
                "Password",
                default=get_env_var("AUTH_PASSWORD", ""),
                required=True,
                secret=True,
                help_text="Password for web interface login."
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
            help_text="Limit access to specific IP addresses or networks."
        )

        if use_ip_restrict:
            allowed_ips = prompt_value(
                "Allowed IPs (comma-separated)",
                default=get_env_var("ALLOWED_IPS", "127.0.0.1,192.168.1.0/24"),
                required=True,
                help_text="List of IP addresses or CIDR ranges that can access the web interface."
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
        help_text="Remote access requires additional configuration of your network."
    )

    if use_remote:
        print_subheader("Remote Access Method")

        remote_method = prompt_choice(
            "Select remote access method",
            ["Dynamic DNS (DDNS)", "Cloudflare Tunnel", "NGROK", "None/Manual"],
            default=1  # DDNS
        )

        if remote_method == "Dynamic DNS (DDNS)":
            print_info("DDNS allows you to access your mower using a domain name even if your IP address changes.")
            print_help("You'll need an account with a DDNS provider like Duck DNS, No-IP, or DynDNS.")

            ddns_provider = prompt_value(
                "DDNS provider",
                default=get_env_var("DDNS_PROVIDER", "duckdns"),
                help_text="The name of your DDNS provider (e.g., duckdns, noip, dyndns)."
            )

            ddns_domain = prompt_value(
                "DDNS domain",
                default=get_env_var("DDNS_DOMAIN", ""),
                required=True,
                help_text="Your DDNS domain name (e.g., mymower.duckdns.org)."
            )

            ddns_token = prompt_value(
                "DDNS token/key",
                default=get_env_var("DDNS_TOKEN", ""),
                required=True,
                secret=True,
                help_text="The token or key provided by your DDNS provider for authentication."
            )

            update_env_var("DDNS_PROVIDER", ddns_provider)
            update_env_var("DDNS_DOMAIN", ddns_domain)
            update_env_var("DDNS_TOKEN", ddns_token)
            update_env_var("USE_DDNS", "True")

            setup_state["feature_flags"]["remote_access"] = "ddns"
            setup_state["user_choices"]["ddns_domain"] = ddns_domain

        elif remote_method == "Cloudflare Tunnel":
            print_info("Cloudflare Tunnel provides secure remote access without opening ports on your router.")
            print_help("You'll need a Cloudflare account and domain name.")

            cf_token = prompt_value(
                "Cloudflare API token",
                default=get_env_var("CLOUDFLARE_API_TOKEN", ""),
                required=True,
                secret=True,
                help_text="Your Cloudflare API token with Zone.DNS permissions."
            )

            cf_zone = prompt_value(
                "Cloudflare zone ID",
                default=get_env_var("CLOUDFLARE_ZONE_ID", ""),
                required=True,
                help_text="Your Cloudflare zone ID for your domain."
            )

            cf_domain = prompt_value(
                "Cloudflare domain",
                default=get_env_var("CLOUDFLARE_DOMAIN", ""),
                required=True,
                help_text="The domain name you want to use (e.g., mower.example.com)."
            )

            update_env_var("CLOUDFLARE_API_TOKEN", cf_token)
            update_env_var("CLOUDFLARE_ZONE_ID", cf_zone)
            update_env_var("CLOUDFLARE_DOMAIN", cf_domain)
            update_env_var("USE_CLOUDFLARE", "True")

            setup_state["feature_flags"]["remote_access"] = "cloudflare"
            setup_state["user_choices"]["cf_domain"] = cf_domain

        elif remote_method == "NGROK":
            print_info("NGROK provides temporary URLs for remote access without configuring your router.")
            print_help("You'll need an NGROK account and authtoken.")

            ngrok_token = prompt_value(
                "NGROK authtoken",
                default=get_env_var("NGROK_AUTHTOKEN", ""),
                required=True,
                secret=True,
                help_text="Your NGROK authtoken from your account dashboard."
            )

            update_env_var("NGROK_AUTHTOKEN", ngrok_token)
            update_env_var("USE_NGROK", "True")

            setup_state["feature_flags"]["remote_access"] = "ngrok"
        else:
            print_info("You've chosen to set up remote access manually or not at all.")
            print_info("To access your mower remotely, you'll need to configure port forwarding on your router.")

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
        help_text="Automated scheduling allows the mower to operate on a regular schedule."
    )

    if use_schedule:
        print_info("You can set up multiple mowing sessions per week.")
        print_help("For each day, you can specify start and end times for mowing.")

        # Create a basic schedule template
        schedule = {}
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        for day in days:
            use_day = prompt_bool(f"Mow on {day}?", default=True)

            if use_day:
                start_time = prompt_value(
                    f"{day} start time (HH:MM)",
                    default="10:00",
                    validator=lambda v, f: bool(v.count(":") == 1 and all(part.isdigit() for part in v.split(":"))),
                    field_name="Start time"
                )

                end_time = prompt_value(
                    f"{day} end time (HH:MM)",
                    default="16:00",
                    validator=lambda v, f: bool(v.count(":") == 1 and all(part.isdigit() for part in v.split(":"))),
                    field_name="End time"
                )

                schedule[day.lower()] = {"enabled": True, "start": start_time, "end": end_time}
            else:
                schedule[day.lower()] = {"enabled": False}

        # Save schedule to a JSON file
        schedule_path = Path(CONFIG_DIR) / "mowing_schedule.json"
        ensure_directory(CONFIG_DIR)

        with open(schedule_path, 'w') as f:
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
        help_text="Weather-aware scheduling prevents mowing during rain or extreme weather."
    )

    if use_weather:
        print_info("You'll need an OpenWeatherMap API key for weather data.")
        print_help("You can get a free API key at: https://openweathermap.org/api")

        weather_api = prompt_value(
            "OpenWeatherMap API key",
            default=get_env_var("OPEN_WEATHER_MAP_API", ""),
            required=True,
            help_text="Your OpenWeatherMap API key."
        )

        update_env_var("OPEN_WEATHER_MAP_API", weather_api)
        update_env_var("WEATHER_AWARE_SCHEDULING", "True")

        setup_state["feature_flags"]["weather_integration"] = True
    else:
        update_env_var("WEATHER_AWARE_SCHEDULING", "False")
        setup_state["feature_flags"]["weather_integration"] = False

    setup_state["completed_sections"].append("scheduling")
    save_setup_state()

    print_success("Scheduling and automation configuration completed!")


def setup_final_verification() -> None:
    """Perform final verification and setup."""
    print_header("Final Verification and Setup")

    print_info("Verifying configuration and setting up required directories...")

    # Ensure all required directories exist
    directories = [
        CONFIG_DIR,
        Path("logs"),
        Path("data"),
    ]

    for directory in directories:
        ensure_directory(directory)

    # Create empty configuration files if they don't exist
    if not (CONFIG_DIR / "user_polygon.json").exists():
        with open(CONFIG_DIR / "user_polygon.json", 'w') as f:
            json.dump({"type": "Polygon", "coordinates": []}, f)

    if not (CONFIG_DIR / "home_location.json").exists():
        with open(CONFIG_DIR / "home_location.json", 'w') as f:
            json.dump({"location": [0, 0]}, f)

    # Summary of configuration
    print_subheader("Configuration Summary")

    print(f"Mower Name: {setup_state['user_choices'].get('mower_name', 'AutonoMow')}")
    print(f"Simulation Mode: {'Enabled' if setup_state['feature_flags'].get('simulation_mode', False) else 'Disabled'}")

    # Hardware summary
    print("\nHardware Configuration:")
    hardware_config = setup_state.get("hardware_config", {})

    print(f"  Camera: {'Enabled' if hardware_config.get('camera', {}).get('enabled', False) else 'Disabled'}")
    print(f"  GPS: {'Enabled' if hardware_config.get('gps', {}).get('enabled', False) else 'Disabled'}")
    print(f"  Motor Controller: {hardware_config.get('motor_controller', {}).get('type', 'none')}")
    print(f"  Coral TPU: {'Enabled' if hardware_config.get('coral_tpu', {}).get('enabled', False) else 'Disabled'}")

    # Feature summary
    print("\nEnabled Features:")
    feature_flags = setup_state.get("feature_flags", {})

    features = [
        ("Web Interface", feature_flags.get("web_interface", False)),
        ("Remote Access", feature_flags.get("remote_access", "none") != "none"),
        ("Scheduling", feature_flags.get("scheduling", False)),
        ("Weather Integration", feature_flags.get("weather_integration", False)),
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

    print("""
Your autonomous mower has been configured successfully! Here are the next steps:

1. Start the mower system with: python -m mower.main_controller
2. Access the web interface (if enabled) at: http://localhost:5000 (or https for SSL)
3. Use the web interface to define your mowing boundaries
4. Test the system in simulation mode before deploying to hardware

For more information, refer to the documentation in the docs/ directory.
    """)

    setup_state["completed_sections"].append("final_verification")
    save_setup_state()


def main() -> None:
    """Main function to run the setup wizard."""
    try:
        # Ensure .env file exists
        ensure_env_file()

        # Load environment variables
        load_dotenv(dotenv_path=ENV_FILE, override=True)

        # Check if we have a saved state
        has_state = load_setup_state()

        if not has_state:
            # Start fresh
            welcome_screen()
            detected_hardware = setup_hardware_detection()
            setup_basic_configuration()
            setup_hardware_configuration(detected_hardware)
            setup_mapping_and_navigation()
            setup_safety_features()
            setup_web_interface()
            setup_remote_access()
            setup_scheduling()
            setup_final_verification()
        else:
            # Resume from saved state
            print_header("Resume Setup")
            print_info(f"Resuming setup from saved state.")

            completed = setup_state.get("completed_sections", [])

            print_info(f"Completed sections: {', '.join(completed)}")

            # Determine what's left to do
            detected_hardware = setup_state.get("hardware_config", {})

            if "basic_configuration" not in completed:
                setup_basic_configuration()

            if "hardware_configuration" not in completed:
                setup_hardware_configuration(detected_hardware)

            if "mapping_and_navigation" not in completed:
                setup_mapping_and_navigation()

            if "safety_features" not in completed:
                setup_safety_features()

            if "web_interface" not in completed:
                setup_web_interface()

            if "remote_access" not in completed:
                setup_remote_access()

            if "scheduling" not in completed:
                setup_scheduling()

            if "final_verification" not in completed:
                setup_final_verification()

        # Clean up setup state file
        if SETUP_STATE_FILE.exists():
            SETUP_STATE_FILE.unlink()
            print_info(f"Removed setup state file: {SETUP_STATE_FILE}")

        print_success("Setup wizard completed successfully!")

    except KeyboardInterrupt:
        print("\n\nSetup interrupted. Your progress has been saved.")
        print(f"Run this script again to continue from where you left off.")
        sys.exit(0)
    except Exception as e:
        print_error(f"An error occurred: {e}")
        print("Your progress has been saved. Run this script again to continue.")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
