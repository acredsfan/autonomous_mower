import os
import shutil
from dotenv import load_dotenv, set_key  # type:ignore
from pathlib import Path


def prompt_choice(prompt, choices, default=None):
    print(prompt)
    for idx, choice in enumerate(choices, 1):
        print(f"  {idx}. {choice}")
    while True:
        sel = input(f"Enter choice [1-{len(choices)}]" +
                    (f" (default {default}): " if default else ": "))
        if not sel and default:
            return default
        if sel.isdigit() and 1 <= int(sel) <= len(choices):
            return choices[int(sel) - 1]
        print("Invalid selection.")


def validate_required(value, field_name):
    if value is None or str(value).strip() == "":
        print(f"[ERROR] {field_name} is required.")
        return False
    return True


def validate_float(value, field_name, min_value=None, max_value=None):
    try:
        val = float(value)
        if min_value is not None and val < min_value:
            print(f"[ERROR] {field_name} must be >= {min_value}.")
            return False
        if max_value is not None and val > max_value:
            print(f"[ERROR] {field_name} must be <= {max_value}.")
            return False
        return True
    except ValueError:
        print(f"[ERROR] {field_name} must be a number.")
        return False


def validate_int(value, field_name, min_value=None, max_value=None):
    try:
        val = int(value)
        if min_value is not None and val < min_value:
            print(f"[ERROR] {field_name} must be >= {min_value}.")
            return False
        if max_value is not None and val > max_value:
            print(f"[ERROR] {field_name} must be <= {max_value}.")
            return False
        return True
    except ValueError:
        print(f"[ERROR] {field_name} must be an integer.")
        return False


def validate_bool(value, field_name):
    if str(value).lower() not in ["true", "false", "yes", "no", "y", "n"]:
        print(f"[ERROR] {field_name} must be True or False (y/n).")
        return False
    return True


def validate_lat_lng(value, field_name):
    try:
        lat, lng = map(float, value.split(","))
        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            print(f"[ERROR] {field_name} must be valid latitude,longitude.")
            return False
        return True
    except Exception:
        print(
            f"[ERROR] {field_name} must be in format: lat,lng "
            f"(e.g. 39.1,-84.5)")
        return False


def print_section_header(title, description=None):
    print("\n" + "=" * 60)
    print(f"{title}")
    if description:
        import textwrap
        for line in textwrap.wrap(description, width=79):
            print(line)
    print("=" * 60)


def prompt_value(
    prompt,
    default=None,
    required=False,
    extra_info=None,
    validator=None,
    field_name=None,
    help_text=None
):
    if extra_info:
        print(extra_info)
    if help_text:
        import textwrap
        for line in textwrap.wrap(help_text, width=79):
            print(f"[HELP] {line}")
    while True:
        val = input(
            f"{prompt}" + (f" (default: {default}): " if default else ": ")
        )
        if not val and default is not None:
            val = default
        if required and not validate_required(val, field_name or prompt):
            continue
        if validator and not validator(val, field_name or prompt):
            continue
        return val


def prompt_bool(prompt, default=None, help_text=None):
    if help_text:
        import textwrap
        for line in textwrap.wrap(help_text, width=79):
            print(f"[HELP] {line}")
    while True:
        val = input(
            f"{prompt} (y/n)" +
            (f" (default: {default}): " if default is not None else ": ")
        )
        if not val and default is not None:
            return default
        if val.lower() in ["y", "yes", "true"]:
            return True
        if val.lower() in ["n", "no", "false"]:
            return False
        print("Please enter 'y' or 'n'.")


def ensure_env_exists():
    env_path = Path(".env")
    example_path = Path(".env.example")
    if not env_path.exists():
        if example_path.exists():
            shutil.copy(example_path, env_path)
            print(".env file created from .env.example.")
        else:
            env_path.touch()
            print("Blank .env file created.")
    return env_path


def update_env_var(env_path, key, value):
    set_key(str(env_path), key, value)


def configure_google_maps(env_path):
    print_section_header(
        "[Google Maps Settings]",
        ("Configure your Google Maps integration for the mower's web UI. "
         "You can get your API key and map ID from the Google Cloud Console. "
         "For map centering, right-click your location on "
         "https://www.google.com/maps and select 'What's here?' "
         "to get coordinates."))
    gmaps_key = prompt_value(
        "Google Maps API Key",
        os.getenv("GOOGLE_MAPS_API_KEY"),
        required=True,
        extra_info=(
            "Get an API key at: "
            ("https://developers.google.com/maps/documentation/"
             "javascript/get-api-key")
        ),
        field_name="Google Maps API Key")
    update_env_var(env_path, "GOOGLE_MAPS_API_KEY", gmaps_key)
    gmaps_map_id = prompt_value(
        "Google Maps Map ID",
        os.getenv("GOOGLE_MAPS_MAP_ID"),
        required=False,
        field_name="Google Maps Map ID"
    )
    update_env_var(env_path, "GOOGLE_MAPS_MAP_ID", gmaps_map_id)
    lat = prompt_value(
        "Default map latitude",
        os.getenv("MAP_DEFAULT_LAT", "39.095657"),
        required=True,
        validator=validate_float,
        field_name="Default map latitude",
        help_text="Latitude for the center of your mowing area."
    )
    update_env_var(env_path, "MAP_DEFAULT_LAT", lat)
    lng = prompt_value(
        "Default map longitude",
        os.getenv("MAP_DEFAULT_LNG", "-84.515959"),
        required=True,
        validator=validate_float,
        field_name="Default map longitude",
        help_text="Longitude for the center of your mowing area."
    )
    update_env_var(env_path, "MAP_DEFAULT_LNG", lng)


def configure_ntrip(env_path):
    print("\n[NTRIP Server for RTK GPS]")
    ntrip_user = prompt_value("NTRIP user", os.getenv("NTRIP_USER"))
    ntrip_pass = prompt_value("NTRIP password", os.getenv("NTRIP_PASS"))
    ntrip_url = prompt_value("NTRIP URL", os.getenv("NTRIP_URL"))
    ntrip_mount = prompt_value(
        "NTRIP mountpoint",
        os.getenv("NTRIP_MOUNTPOINT"))
    ntrip_port = prompt_value("NTRIP port", os.getenv("NTRIP_PORT"))
    update_env_var(env_path, "NTRIP_USER", ntrip_user)
    update_env_var(env_path, "NTRIP_PASS", ntrip_pass)
    update_env_var(env_path, "NTRIP_URL", ntrip_url)
    update_env_var(env_path, "NTRIP_MOUNTPOINT", ntrip_mount)
    update_env_var(env_path, "NTRIP_PORT", ntrip_port)


def configure_gps(env_path):
    print("\n[GPS Settings]")
    gps_port = prompt_value(
        "GPS serial port",
        os.getenv(
            "GPS_SERIAL_PORT",
            "/dev/ttyACM0"))
    gps_baud = prompt_value(
        "GPS baud rate", os.getenv(
            "GPS_BAUD_RATE", "115200"))
    gps_timeout = prompt_value(
        "GPS timeout (seconds)", os.getenv(
            "GPS_TIMEOUT", "1"))
    update_env_var(env_path, "GPS_SERIAL_PORT", gps_port)
    update_env_var(env_path, "GPS_BAUD_RATE", gps_baud)
    update_env_var(env_path, "GPS_TIMEOUT", gps_timeout)


def configure_web_ui(env_path):
    print("\n[Web UI Settings]")
    template_folder = prompt_value(
        "Web UI template folder",
        os.getenv("TEMPLATE_FOLDER"))
    update_env_var(env_path, "TEMPLATE_FOLDER", template_folder)


def configure_weather(env_path):
    print("\n[Weather API Settings]")
    weather_api = prompt_value(
        "OpenWeatherMap API key",
        os.getenv("OPEN_WEATHER_MAP_API"))
    update_env_var(env_path, "OPEN_WEATHER_MAP_API", weather_api)


def configure_robohat(env_path):
    print("\n[RoboHAT MM1 Settings]")
    mm1_port = prompt_value(
        "RoboHAT MM1 serial port",
        os.getenv(
            "MM1_SERIAL_PORT",
            "/dev/ttyACM1"))
    update_env_var(env_path, "MM1_SERIAL_PORT", mm1_port)


def configure_imu(env_path):
    print("\n[IMU Settings]")
    imu_port = prompt_value(
        "IMU serial port",
        os.getenv(
            "IMU_SERIAL_PORT",
            "/dev/ttyAMA2"))
    imu_baud = prompt_value(
        "IMU baud rate", os.getenv(
            "IMU_BAUD_RATE", "3000000"))
    update_env_var(env_path, "IMU_SERIAL_PORT", imu_port)
    update_env_var(env_path, "IMU_BAUD_RATE", imu_baud)


def configure_obstacle_detection(env_path):
    print("\n[Obstacle Detection Settings]")
    model_path = prompt_value(
        "Obstacle model path",
        os.getenv("OBSTACLE_MODEL_PATH"))
    label_map = prompt_value("Label map path", os.getenv("LABEL_MAP_PATH"))
    min_conf = prompt_value(
        "Minimum confidence threshold", os.getenv(
            "MIN_CONF_THRESHOLD", "0.5"))
    update_env_var(env_path, "OBSTACLE_MODEL_PATH", model_path)
    update_env_var(env_path, "LABEL_MAP_PATH", label_map)
    update_env_var(env_path, "MIN_CONF_THRESHOLD", min_conf)


def configure_coral(env_path):
    print("\n[Coral Accelerator Settings]")
    use_coral = prompt_bool(
        "Use Coral Accelerator?",
        os.getenv(
            "USE_CORAL_ACCELERATOR",
            "True") == "True")
    edge_tpu_model = prompt_value(
        "Edge TPU model path",
        os.getenv("EDGE_TPU_MODEL_PATH"))
    update_env_var(env_path, "USE_CORAL_ACCELERATOR", str(use_coral))
    update_env_var(env_path, "EDGE_TPU_MODEL_PATH", edge_tpu_model)


def configure_camera_streaming(env_path):
    print("\n[Camera Streaming Settings]")
    udp_port = prompt_value(
        "UDP port for streaming", os.getenv(
            "UDP_PORT", "8000"))
    fps = prompt_value("Streaming FPS", os.getenv("STREAMING_FPS", "30"))
    resolution = prompt_value(
        "Streaming resolution (e.g. 640x480)", os.getenv(
            "STREAMING_RESOLUTION", "640x480"))
    buffer_size = prompt_value(
        "Frame buffer size", os.getenv(
            "FRAME_BUFFER_SIZE", "5"))
    update_env_var(env_path, "UDP_PORT", udp_port)
    update_env_var(env_path, "STREAMING_FPS", fps)
    update_env_var(env_path, "STREAMING_RESOLUTION", resolution)
    update_env_var(env_path, "FRAME_BUFFER_SIZE", buffer_size)


def configure_remote_detection(env_path):
    print("\n[Remote Detection/Path Planning Settings]")
    use_remote_det = prompt_bool(
        "Use remote detection?", os.getenv(
            "USE_REMOTE_DETECTION", "True") == "True")
    use_remote_path = prompt_bool(
        "Use remote path planning?", os.getenv(
            "USE_REMOTE_PATH_PLANNING", "True") == "True")
    rpi5_ip = prompt_value("Remote RPi5 IP address", os.getenv("RPI5_IP"))
    mqtt_port = prompt_value("MQTT port", os.getenv("MQTT_PORT", "1883"))
    client_id = prompt_value(
        "MQTT client ID", os.getenv(
            "CLIENT_ID", "MowerClient"))
    update_env_var(env_path, "USE_REMOTE_DETECTION", str(use_remote_det))
    update_env_var(env_path, "USE_REMOTE_PATH_PLANNING", str(use_remote_path))
    update_env_var(env_path, "RPI5_IP", rpi5_ip)
    update_env_var(env_path, "MQTT_PORT", mqtt_port)
    update_env_var(env_path, "CLIENT_ID", client_id)


def configure_security(env_path):
    print("\n[Security Settings]")
    enable_ssl = prompt_bool(
        "Enable SSL?", os.getenv(
            "ENABLE_SSL", "True") == "True")
    ssl_cert = prompt_value(
        "SSL certificate path",
        os.getenv("SSL_CERT_PATH"))
    ssl_key = prompt_value("SSL key path", os.getenv("SSL_KEY_PATH"))
    auth_required = prompt_bool(
        "Require authentication?", os.getenv(
            "AUTH_REQUIRED", "True") == "True")
    auth_user = prompt_value(
        "Auth username", os.getenv(
            "AUTH_USERNAME", "admin"))
    auth_pass = prompt_value("Auth password", os.getenv("AUTH_PASSWORD"))
    allowed_ips = prompt_value(
        "Allowed IPs (comma-separated)",
        os.getenv("ALLOWED_IPS"))
    update_env_var(env_path, "ENABLE_SSL", str(enable_ssl))
    update_env_var(env_path, "SSL_CERT_PATH", ssl_cert)
    update_env_var(env_path, "SSL_KEY_PATH", ssl_key)
    update_env_var(env_path, "AUTH_REQUIRED", str(auth_required))
    update_env_var(env_path, "AUTH_USERNAME", auth_user)
    update_env_var(env_path, "AUTH_PASSWORD", auth_pass)
    update_env_var(env_path, "ALLOWED_IPS", allowed_ips)


def configure_wifi(env_path):
    print("\n[WiFi Scanning Settings]")
    wifi_scan = prompt_value(
        "WiFi networks to scan (all or comma-separated SSIDs)",
        os.getenv("Wifi_Networks_to_Scan", "all")
    )
    update_env_var(env_path, "Wifi_Networks_to_Scan", wifi_scan)


def configure_mower(env_path):
    print("\n[Mower Settings]")
    mower_name = prompt_value(
        "Mower name", os.getenv(
            "MOWER_NAME", "AutonoMow"))
    log_level = prompt_value("Log level", os.getenv("LOG_LEVEL", "INFO"))
    debug_mode = prompt_bool(
        "Enable debug mode?", os.getenv(
            "DEBUG_MODE", "False") == "True")
    update_env_var(env_path, "MOWER_NAME", mower_name)
    update_env_var(env_path, "LOG_LEVEL", log_level)
    update_env_var(env_path, "DEBUG_MODE", str(debug_mode))


def configure_hardware(env_path):
    print("\n[Hardware Settings]")
    use_sim = prompt_bool(
        "Use simulation mode?",
        os.getenv(
            "USE_SIMULATION",
            "False") == "True")
    imu_addr = prompt_value(
        "IMU I2C address", os.getenv(
            "IMU_ADDRESS", "0x68"))
    update_env_var(env_path, "USE_SIMULATION", str(use_sim))
    update_env_var(env_path, "IMU_ADDRESS", imu_addr)


def configure_camera(env_path):
    print("\n[Camera Settings]")
    cam_width = prompt_value("Camera width", os.getenv("CAMERA_WIDTH", "640"))
    cam_height = prompt_value(
        "Camera height", os.getenv(
            "CAMERA_HEIGHT", "480"))
    cam_fps = prompt_value("Camera FPS", os.getenv("CAMERA_FPS", "30"))
    cam_index = prompt_value("Camera index", os.getenv("CAMERA_INDEX", "0"))
    use_cam = prompt_bool(
        "Use camera?",
        os.getenv(
            "USE_CAMERA",
            "True") == "True")
    update_env_var(env_path, "CAMERA_WIDTH", cam_width)
    update_env_var(env_path, "CAMERA_HEIGHT", cam_height)
    update_env_var(env_path, "CAMERA_FPS", cam_fps)
    update_env_var(env_path, "CAMERA_INDEX", cam_index)
    update_env_var(env_path, "USE_CAMERA", str(use_cam))


def configure_ml(env_path):
    print("\n[Machine Learning Settings]")
    ml_model_path = prompt_value("ML model path", os.getenv("ML_MODEL_PATH"))
    det_model = prompt_value(
        "Detection model filename",
        os.getenv("DETECTION_MODEL"))
    tpu_model = prompt_value(
        "TPU detection model filename",
        os.getenv("TPU_DETECTION_MODEL"))
    label_map = prompt_value("Label map path", os.getenv("LABEL_MAP_PATH"))
    min_conf = prompt_value(
        "Minimum confidence threshold", os.getenv(
            "MIN_CONF_THRESHOLD", "0.5"))
    use_remote_det = prompt_bool(
        "Use remote detection?", os.getenv(
            "USE_REMOTE_DETECTION", "False") == "True")
    update_env_var(env_path, "ML_MODEL_PATH", ml_model_path)
    update_env_var(env_path, "DETECTION_MODEL", det_model)
    update_env_var(env_path, "TPU_DETECTION_MODEL", tpu_model)
    update_env_var(env_path, "LABEL_MAP_PATH", label_map)
    update_env_var(env_path, "MIN_CONF_THRESHOLD", min_conf)
    update_env_var(env_path, "USE_REMOTE_DETECTION", str(use_remote_det))


def configure_web_ui_config(env_path):
    print("\n[Web UI Configuration]")
    web_port = prompt_value("Web UI port", os.getenv("WEB_UI_PORT", "5000"))
    enable_web = prompt_bool(
        "Enable Web UI?", os.getenv(
            "ENABLE_WEB_UI", "True") == "True")
    update_env_var(env_path, "WEB_UI_PORT", web_port)
    update_env_var(env_path, "ENABLE_WEB_UI", str(enable_web))


def configure_database(env_path):
    print("\n[Database Settings]")
    db_path = prompt_value(
        "Database path",
        os.getenv(
            "DATABASE_PATH",
            "./data/mower.db"))
    update_env_var(env_path, "DATABASE_PATH", db_path)


def configure_path_planning(env_path):
    print("\n[Path Planning Settings]")
    default_speed = prompt_value(
        "Default speed", os.getenv(
            "DEFAULT_SPEED", "0.5"))
    max_speed = prompt_value("Max speed", os.getenv("MAX_SPEED", "1.0"))
    turn_speed = prompt_value("Turn speed", os.getenv("TURN_SPEED", "0.3"))
    avoid_dist = prompt_value(
        "Avoidance distance (cm)", os.getenv(
            "AVOIDANCE_DISTANCE", "40"))
    stop_dist = prompt_value(
        "Stop distance (cm)", os.getenv(
            "STOP_DISTANCE", "20"))
    home_lat = prompt_value("Home latitude", os.getenv("HOME_LAT", "0.0"))
    home_lon = prompt_value("Home longitude", os.getenv("HOME_LON", "0.0"))
    update_env_var(env_path, "DEFAULT_SPEED", default_speed)
    update_env_var(env_path, "MAX_SPEED", max_speed)
    update_env_var(env_path, "TURN_SPEED", turn_speed)
    update_env_var(env_path, "AVOIDANCE_DISTANCE", avoid_dist)
    update_env_var(env_path, "STOP_DISTANCE", stop_dist)
    update_env_var(env_path, "HOME_LAT", home_lat)
    update_env_var(env_path, "HOME_LON", home_lon)


def configure_config_paths(env_path):
    print("\n[Config File Paths]")
    config_dir = prompt_value(
        "Config directory", os.getenv(
            "CONFIG_DIR", "config"))
    user_poly = prompt_value(
        "User polygon path",
        os.getenv(
            "USER_POLYGON_PATH",
            "config/user_polygon.json"))
    home_loc = prompt_value(
        "Home location path",
        os.getenv(
            "HOME_LOCATION_PATH",
            "config/home_location.json"))
    mowing_sched = prompt_value(
        "Mowing schedule path",
        os.getenv(
            "MOWING_SCHEDULE_PATH",
            "config/mowing_schedule.json"))
    update_env_var(env_path, "CONFIG_DIR", config_dir)
    update_env_var(env_path, "USER_POLYGON_PATH", user_poly)
    update_env_var(env_path, "HOME_LOCATION_PATH", home_loc)
    update_env_var(env_path, "MOWING_SCHEDULE_PATH", mowing_sched)


def configure_schedule(env_path):
    print("\n[Schedule Settings]")
    mowing_sched = prompt_value(
        "Mowing schedule file",
        os.getenv(
            "MOWING_SCHEDULE",
            "./data/schedule.json"))
    update_env_var(env_path, "MOWING_SCHEDULE", mowing_sched)


def configure_maintenance(env_path):
    print("\n[Maintenance Settings]")
    blade_limit = prompt_value(
        "Blade hours limit", os.getenv(
            "BLADE_HOURS_LIMIT", "100"))
    maint_interval = prompt_value(
        "Maintenance check interval", os.getenv(
            "MAINTENANCE_CHECK_INTERVAL", "50"))
    blade_runtime = prompt_value(
        "Blade runtime hours", os.getenv(
            "BLADE_RUNTIME_HOURS", "0"))
    motor_runtime = prompt_value(
        "Motor runtime hours", os.getenv(
            "MOTOR_RUNTIME_HOURS", "0"))
    next_maint = prompt_value(
        "Next maintenance date (YYYY-MM-DD)",
        os.getenv(
            "NEXT_MAINTENANCE_DATE",
            ""))
    maint_alert = prompt_value(
        "Maintenance alert days", os.getenv(
            "MAINTENANCE_ALERT_DAYS", "7"))
    update_env_var(env_path, "BLADE_HOURS_LIMIT", blade_limit)
    update_env_var(env_path, "MAINTENANCE_CHECK_INTERVAL", maint_interval)
    update_env_var(env_path, "BLADE_RUNTIME_HOURS", blade_runtime)
    update_env_var(env_path, "MOTOR_RUNTIME_HOURS", motor_runtime)
    update_env_var(env_path, "NEXT_MAINTENANCE_DATE", next_maint)
    update_env_var(env_path, "MAINTENANCE_ALERT_DAYS", maint_alert)


def configure_safety(env_path):
    print("\n[Safety Settings]")
    e_stop_pin = prompt_value(
        "Emergency stop GPIO pin", os.getenv(
            "EMERGENCY_STOP_PIN", "7"))
    watchdog = prompt_value(
        "Watchdog timeout (seconds)", os.getenv(
            "WATCHDOG_TIMEOUT", "15"))
    batt_low = prompt_value(
        "Battery low threshold (%)", os.getenv(
            "BATTERY_LOW_THRESHOLD", "20"))
    batt_crit = prompt_value(
        "Battery critical threshold (%)", os.getenv(
            "BATTERY_CRITICAL_THRESHOLD", "10"))
    max_slope = prompt_value(
        "Max slope angle (deg)", os.getenv(
            "MAX_SLOPE_ANGLE", "15"))
    rain_sensor = prompt_bool(
        "Enable rain sensor?",
        os.getenv(
            "RAIN_SENSOR_ENABLED",
            "True") == "True")
    tilt_sensor = prompt_bool(
        "Enable tilt sensor?",
        os.getenv(
            "TILT_SENSOR_ENABLED",
            "True") == "True")
    update_env_var(env_path, "EMERGENCY_STOP_PIN", e_stop_pin)
    update_env_var(env_path, "WATCHDOG_TIMEOUT", watchdog)
    update_env_var(env_path, "BATTERY_LOW_THRESHOLD", batt_low)
    update_env_var(env_path, "BATTERY_CRITICAL_THRESHOLD", batt_crit)
    update_env_var(env_path, "MAX_SLOPE_ANGLE", max_slope)
    update_env_var(env_path, "RAIN_SENSOR_ENABLED", str(rain_sensor))
    update_env_var(env_path, "TILT_SENSOR_ENABLED", str(tilt_sensor))


def configure_sensor_validation(env_path):
    print("\n[Sensor Validation Settings]")
    sensor_interval = prompt_value(
        "Sensor check interval (seconds)", os.getenv(
            "SENSOR_CHECK_INTERVAL", "5"))
    gps_min_sat = prompt_value(
        "GPS min satellites", os.getenv(
            "GPS_MIN_SATELLITES", "6"))
    gps_max_hdop = prompt_value(
        "GPS max HDOP", os.getenv(
            "GPS_MAX_HDOP", "2.0"))
    imu_calib = prompt_bool(
        "IMU calibration required?",
        os.getenv(
            "IMU_CALIBRATION_REQUIRED",
            "True") == "True")
    update_env_var(env_path, "SENSOR_CHECK_INTERVAL", sensor_interval)
    update_env_var(env_path, "GPS_MIN_SATELLITES", gps_min_sat)
    update_env_var(env_path, "GPS_MAX_HDOP", gps_max_hdop)
    update_env_var(env_path, "IMU_CALIBRATION_REQUIRED", str(imu_calib))


def configure_collision_detection(env_path):
    print("\n[Collision Detection Settings]")
    collision_enabled = prompt_bool(
        "Enable collision detection?", os.getenv(
            "COLLISION_DETECTION_ENABLED", "True") == "True")
    impact_thresh = prompt_value(
        "Impact threshold (G)", os.getenv(
            "IMPACT_THRESHOLD_G", "2.0"))
    tilt_thresh = prompt_value(
        "Tilt threshold (deg)", os.getenv(
            "TILT_THRESHOLD_DEG", "45"))
    update_env_var(
        env_path,
        "COLLISION_DETECTION_ENABLED",
        str(collision_enabled))
    update_env_var(env_path, "IMPACT_THRESHOLD_G", impact_thresh)
    update_env_var(env_path, "TILT_THRESHOLD_DEG", tilt_thresh)


def configure_safety_zones(env_path):
    print("\n[Safety Zones]")
    safe_buffer = prompt_value(
        "Safe zone buffer (meters)", os.getenv(
            "SAFE_ZONE_BUFFER", "1.0"))
    no_mow = prompt_value(
        "No-mow zones (JSON list)",
        os.getenv(
            "NO_MOW_ZONES",
            "[]"))
    play_zones = prompt_value(
        "Children play zones (JSON list)", os.getenv(
            "CHILDREN_PLAY_ZONES", "[]"))
    pet_zones = prompt_value(
        "Pet zones (JSON list)", os.getenv(
            "PET_ZONES", "[]"))
    update_env_var(env_path, "SAFE_ZONE_BUFFER", safe_buffer)
    update_env_var(env_path, "NO_MOW_ZONES", no_mow)
    update_env_var(env_path, "CHILDREN_PLAY_ZONES", play_zones)
    update_env_var(env_path, "PET_ZONES", pet_zones)


def configure_backup_recovery(env_path):
    print("\n[Backup and Recovery Settings]")
    backup_interval = prompt_value(
        "Backup interval (seconds)", os.getenv(
            "BACKUP_INTERVAL", "3600"))
    max_backups = prompt_value(
        "Max backup files", os.getenv(
            "MAX_BACKUP_FILES", "7"))
    recovery_mode = prompt_bool(
        "Enable recovery mode?", os.getenv(
            "RECOVERY_MODE", "False") == "True")
    update_env_var(env_path, "BACKUP_INTERVAL", backup_interval)
    update_env_var(env_path, "MAX_BACKUP_FILES", max_backups)
    update_env_var(env_path, "RECOVERY_MODE", str(recovery_mode))


def main():
    print("\n=== Autonomous Mower Environment Configurator ===\n")
    print(
        "This tool will guide you through configuring your .env file for all "
        "mower features.\nYou can skip any optional field by pressing Enter.\n"
    )
    env_path = ensure_env_exists()
    load_dotenv(dotenv_path=env_path, override=True)
    configure_google_maps(env_path)
    configure_ntrip(env_path)
    configure_gps(env_path)
    configure_web_ui(env_path)
    configure_weather(env_path)
    configure_robohat(env_path)
    configure_imu(env_path)
    configure_obstacle_detection(env_path)
    configure_coral(env_path)
    configure_camera_streaming(env_path)
    configure_remote_detection(env_path)
    configure_security(env_path)
    configure_wifi(env_path)
    configure_mower(env_path)
    configure_hardware(env_path)
    configure_camera(env_path)
    configure_ml(env_path)
    configure_web_ui_config(env_path)
    configure_database(env_path)
    configure_path_planning(env_path)
    configure_config_paths(env_path)
    configure_schedule(env_path)
    configure_maintenance(env_path)
    configure_safety(env_path)
    configure_sensor_validation(env_path)
    configure_collision_detection(env_path)
    configure_safety_zones(env_path)
    configure_backup_recovery(env_path)
    print(
        "\n[INFO] .env updated! You can re-run this tool anytime to update "
        "environment settings."
    )
    print("[INFO] For help, see the README or documentation in the 'docs/' "
          "folder.")


if __name__ == "__main__":
    main()
