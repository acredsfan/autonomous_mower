"""Flask web interface for the autonomous mower."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv, set_key

# Critical imports with error handling
try:
    from flask import Flask, Response, jsonify, render_template, request, send_file, make_response
    from flask_cors import CORS
    from flask_socketio import SocketIO, emit
except ImportError as e:
    print(f"CRITICAL: Missing required Flask dependencies: {e}")
    print("Please install with: pip install -e .[dev]")
    sys.exit(1)

try:
    from flask_babel import Babel
except ImportError:
    print("WARNING: flask-babel not installed. Translation features will be disabled.")
    Babel = None

# Import data collection integration
from mower.data_collection.integration import integrate_data_collection
from mower.navigation.path_planner import PatternType
from mower.ui.web_ui.i18n import init_babel  # Import the babel init function
from mower.ui.web_ui.simulation_helper import get_simulated_sensor_data
from mower.utilities.logger_config import LoggerConfigInfo

# Load environment variables for camera streaming
load_dotenv()

# Camera streaming configuration from environment
STREAMING_FPS = int(os.getenv("STREAMING_FPS", 30))
FRAME_TIME = 1.0 / STREAMING_FPS  # Calculate sleep time based on FPS
JPEG_QUALITY = int(os.getenv("JPEG_QUALITY", 95))  # Higher quality for better image

# Load environment variables from .env if available
ROOT_DIR = Path(__file__).resolve().parents[4]
env_path = ROOT_DIR / ".env"
load_dotenv(env_path)

# Initialize logger
logger = LoggerConfigInfo.get_logger(__name__)

# Check if we should use simulation mode (ONLY if explicitly requested)
# Removed automatic Windows detection - simulation should be explicit only
USE_SIMULATION = os.environ.get("USE_SIMULATION", "").lower() in ("true", "1", "yes")
if USE_SIMULATION:
    logger.info("Running in simulation mode - using simulated sensor data (explicitly enabled)")
else:
    logger.info("Running in hardware mode - showing N/A for failed sensors (simulation disabled)")


def create_app(mower_resource_manager_instance):
    """Create the Flask application.

    Args:
        mower_resource_manager_instance: The mower resource manager instance.

    Returns:
        The Flask application instance and SocketIO instance.
    """
    logger.info("Creating Flask app - v2")
    mower = mower_resource_manager_instance
    logger.info(f"create_app called with mower type: {type(mower)}")

    # Configure template folder from environment or use default
    template_folder = os.environ.get("TEMPLATE_FOLDER", str(Path(__file__).parent / "templates"))
    app = Flask(__name__, template_folder=template_folder)
    # Enable CORS for all routes with enhanced headers for Cloudflare Access
    CORS(app, 
         resources={r"/*": {"origins": "*"}},
         supports_credentials=True,
         allow_headers=["Content-Type", "Authorization", "Access-Control-Allow-Credentials", "CF-Access-Client-Id", "CF-Access-Client-Secret"])
    
    socketio = SocketIO(
        app, 
        cors_allowed_origins="*", 
        cors_credentials=True,
        ping_timeout=20, 
        ping_interval=25, 
        logger=True, 
        engineio_logger=True,
        transports=['polling', 'websocket']  # Ensure both transports available for Cloudflare
    )

    # Integrate data collection functionality
    try:
        integrate_data_collection(app, mower_resource_manager_instance)
        logger.info("Data collection module integrated successfully")
    except Exception as e:
        logger.error(f"Failed to integrate data collection module: {e}")

    # Initialize Babel for translations using the version-agnostic approach
    # This uses the implementation from i18n.py which works with any
    # Flask-Babel version
    try:
        # Try to use the i18n module first
        init_babel(app)
        logger.info("Initialized Babel from i18n module")
    except Exception as e:
        logger.warning(f"Could not initialize Babel from i18n module: {e}")

        # Only try direct initialization if Babel is available
        if Babel is not None:
            try:
                # Define locale selector function
                def get_locale():
                    """Select the best match for supported languages."""
                    return request.accept_languages.best_match(["en", "es", "fr"])

                # Create Babel instance
                babel_instance = Babel(app)

                # Try different Flask-Babel versions' initialization methods
                try:
                    # Flask-Babel >= 2.0
                    babel_instance.init_app(app, locale_selector=get_locale)
                    logger.info("Initialized Babel with locale_selector parameter")
                except TypeError:
                    try:
                        # Flask-Babel < 2.0
                        babel_instance.localeselector(get_locale)
                        logger.info("Initialized Babel with localeselector decorator")
                    except Exception as e2:
                        logger.error(f"Failed to initialize Babel (legacy fallback): {e2}")
            except Exception as e3:
                logger.error(f"Failed to initialize Babel directly: {e3}")
        else:
            logger.warning("Babel not installed - translations disabled")

    # Route handlers
    @app.route("/")
    def index():
        """Render the dashboard page."""
        return render_template("index.html")

    @app.route("/control")
    def control():
        """Render the manual control page."""
        return render_template("control.html")

    @app.route("/area")
    def area():
        """Render the area configuration page."""
        return render_template("area.html")

    @app.route("/map")
    def map_view():
        """Render the map view page."""
        # Use API key from environment or configuration
        google_maps_api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")

        print(f"DEBUG: map_view() - Using Google Maps API key: {google_maps_api_key}")

        if not google_maps_api_key:
            logger.warning("GOOGLE_MAPS_API_KEY not set in environment. Map functionality will be limited.")
            # Check if a .env file exists but hasn't been loaded
            env_file = Path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../../.env"))
            if env_file.exists():
                logger.warning(
                    f".env file exists at {env_file} but may not be loaded. Consider restarting the service."
                )
                print("WARNING: .env file exists but may not be loaded. Please restart the service.")

        map_center_lat = 0.0
        map_center_lng = 0.0
        try:
            sensor_data = mower.get_sensor_data()
            if sensor_data and "gps" in sensor_data:
                gps_data = sensor_data["gps"]
                map_center_lat = gps_data.get("latitude", 0.0)
                map_center_lng = gps_data.get("longitude", 0.0)
        except Exception as e:
            logger.warning(f"Failed to get GPS coordinates for map center: {e}")

        return render_template(
            "map.html",
            google_maps_api_key=google_maps_api_key,
            map_center_lat=map_center_lat,
            map_center_lng=map_center_lng,
        )

    @app.route("/diagnostics")
    def diagnostics():
        """Render the diagnostics page."""
        return render_template("diagnostics.html")

    @app.route("/settings")
    def settings():
        """Render the settings page."""
        return render_template("settings.html")

    @app.route("/schedule")
    def schedule():
        """Render the mowing schedule page."""
        return render_template("schedule.html")

    @app.route("/system_health")
    def system_health():
        """Render the system health page."""
        return render_template("system_health.html")

    @app.route("/setup_wizard")
    def setup_wizard():
        """Render the setup wizard page."""
        return render_template("setup_wizard.html")

    @app.route("/camera")
    def camera():
        """Render the camera feed page."""
        return render_template("camera.html")

    @app.route("/video_feed")
    def video_feed():
        """Stream camera feed as multipart response."""
        try:
            camera = mower.get_camera()

            if camera is None:
                # Generate a test pattern when no camera is available
                def generate_test_pattern():
                    """Generate a test pattern with timestamp."""
                    from datetime import datetime

                    import cv2
                    import numpy as np

                    while True:
                        # Create a 640x480 test pattern
                        frame = np.zeros((480, 640, 3), dtype=np.uint8)

                        # Add some visual elements
                        cv2.rectangle(frame, (50, 50), (590, 430), (0, 255, 0), 2)
                        cv2.putText(
                            frame, "Camera Not Available", (150, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2
                        )
                        cv2.putText(
                            frame,
                            f"Time: {datetime.now().strftime('%H:%M:%S')}",
                            (200, 250),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.7,
                            (255, 255, 0),
                            2,
                        )
                        cv2.putText(frame, "Test Pattern", (250, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

                        # Add some moving elements
                        import time

                        x = int((time.time() % 10) * 50) + 50
                        cv2.circle(frame, (x, 350), 20, (255, 0, 255), -1)

                        # Convert to JPEG
                        _, buffer = cv2.imencode(".jpg", frame)
                        frame_bytes = buffer.tobytes()

                        # Yield the frame in multipart response
                        yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")

                        # 30 FPS timing - 1/30 = 0.033 seconds
                        socketio.sleep(0.033)

                return Response(generate_test_pattern(), mimetype="multipart/x-mixed-replace; boundary=frame")

            def generate_frames():
                """Generate camera frames."""
                # Initialize camera if not already done - prevents double-visit issue
                if hasattr(camera, 'initialize') and callable(camera.initialize):
                    try:
                        if not camera.initialize():
                            logger.warning("Camera initialization failed, using fallback")
                    except Exception as e:
                        logger.error(f"Camera initialization error: {e}")
                
                while True:
                    # Get frame from camera
                    try:
                        # Try get_frame() first (returns raw frame)
                        frame = camera.get_frame()
                    except (AttributeError, TypeError):
                        try:
                            # Fall back to capture_frame() (returns JPEG bytes)
                            jpeg_bytes = camera.capture_frame()
                            if jpeg_bytes is None:
                                continue

                            # If we got JPEG bytes directly, yield them
                            yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + jpeg_bytes + b"\r\n")

                            # Use configured FPS timing for JPEG stream
                            socketio.sleep(FRAME_TIME)
                            continue
                        except Exception:
                            # If both methods fail, try get_last_frame()
                            try:
                                jpeg_bytes = camera.get_last_frame()
                                if jpeg_bytes is None:
                                    continue

                                # If we got JPEG bytes directly, yield them
                                yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + jpeg_bytes + b"\r\n")

                                # Use configured FPS timing for fallback JPEG stream
                                socketio.sleep(FRAME_TIME)
                                continue
                            except Exception:
                                logger.error("All camera frame methods failed")
                                socketio.sleep(1)  # Longer delay on error
                                continue

                    if frame is None:
                        socketio.sleep(0.1)
                        continue

                    # Convert frame to JPEG
                    try:
                        import cv2

                        # Encode to JPEG with configurable quality for better image clarity
                        # Higher JPEG quality reduces pixelation at the cost of bandwidth
                        _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
                        frame_bytes = buffer.tobytes()

                        # Yield the frame in multipart response
                        yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")

                        # Use configured FPS timing from environment
                        socketio.sleep(FRAME_TIME)
                    except Exception as e:
                        logger.error(f"Error encoding frame: {e}")
                        socketio.sleep(0.5)  # Delay on error

            return Response(
                generate_frames(),
                mimetype="multipart/x-mixed-replace; boundary=frame",
            )

        except Exception as e:
            logger.error(f"Failed to stream video: {e}")
            # Return a placeholder image instead of failing
            placeholder_img = os.path.join(app.static_folder, "images/camera-placeholder.jpg")
            if os.path.exists(placeholder_img):
                return send_file(placeholder_img, mimetype="image/jpeg")
            else:
                return "Video stream unavailable", 503

    @app.route("/api/get-settings", methods=["GET"])
    def get_settings():
        """Get current mower settings."""
        try:
            path_planner = mower.get_path_planner()
            settings = {
                "mowing": {
                    "pattern": path_planner.pattern_config.pattern_type.name,
                    "spacing": path_planner.pattern_config.spacing,
                    "angle": path_planner.pattern_config.angle,
                    "overlap": path_planner.pattern_config.overlap,
                }
            }
            return jsonify({"success": True, "data": settings})
        except Exception as e:
            logger.error(f"Failed to get settings: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/save-settings", methods=["POST"])
    def save_settings():
        """Save mower settings."""
        try:
            data = request.get_json()
            settings = data.get("settings", {})
            mowing = settings.get("mowing", {})

            path_planner = mower.get_path_planner()

            # Update pattern planner settings
            if "pattern" in mowing:
                path_planner.pattern_config.pattern_type = PatternType[mowing["pattern"]]
            if "spacing" in mowing:
                path_planner.pattern_config.spacing = float(mowing["spacing"])
            if "angle" in mowing:
                path_planner.pattern_config.angle = float(mowing["angle"])
            if "overlap" in mowing:
                path_planner.pattern_config.overlap = float(mowing["overlap"])

            return jsonify({"success": True})
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/calibrate_tof", methods=["POST"])
    def calibrate_tof():
        """Calibrate ToF sensors by recording current ground distances."""
        try:
            sensor_data = mower.get_sensor_data()
            tof = sensor_data.get("tof", {}) if sensor_data else {}
            left = tof.get("front_left") or tof.get("left")
            right = tof.get("front_right") or tof.get("right")

            if left is None or right is None:
                return jsonify({"success": False, "error": "ToF readings unavailable"}), 400

            env_file = ROOT_DIR / ".env"
            set_key(str(env_file), "TOF_GROUND_CUTOFF_LEFT", str(left))
            set_key(str(env_file), "TOF_GROUND_CUTOFF_RIGHT", str(right))
            os.environ["TOF_GROUND_CUTOFF_LEFT"] = str(left)
            os.environ["TOF_GROUND_CUTOFF_RIGHT"] = str(right)

            return jsonify({"success": True, "left": left, "right": right})
        except Exception as e:
            logger.error(f"Failed to calibrate ToF sensors: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/get-area", methods=["GET"])
    def get_area():
        """Get the current mowing area configuration."""
        try:
            path_planner = mower.get_path_planner()
            area_data = {"boundary_points": path_planner.pattern_config.boundary_points}
            return jsonify({"success": True, "data": area_data})
        except Exception as e:
            logger.error(f"Failed to get mowing area: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/save-area", methods=["POST"])
    def save_area():
        """Save the mowing area configuration."""
        try:
            data = request.get_json()
            coordinates = data.get("coordinates")
            if not coordinates:
                return (
                    jsonify({"success": False, "error": "No coordinates provided"}),
                    400,
                )

            # First try to use the pattern_config approach
            try:
                path_planner = mower.get_path_planner()
                if hasattr(path_planner, "pattern_config"):
                    path_planner.pattern_config.boundary_points = coordinates
                    logger.info(f"Successfully saved boundary with {len(coordinates)} points using pattern_config")
                    return jsonify({"success": True, "message": "Boundary saved successfully (pattern_config)"})
                # If pattern_config doesn't exist, try with set_boundary_points
                elif hasattr(path_planner, "set_boundary_points"):
                    path_planner.set_boundary_points(coordinates)
                    logger.info(f"Successfully saved boundary with {len(coordinates)} points using set_boundary_points")
                    return jsonify({"success": True, "message": "Boundary saved successfully (set_boundary_points)"})
                # Last resort: save directly to mower
                else:
                    mower.save_boundary(coordinates)
                    logger.info(f"Successfully saved boundary with {len(coordinates)} points using mower.save_boundary")
                    return jsonify({"success": True, "message": "Boundary saved successfully (mower.save_boundary)"})
            except Exception as e:
                # Try the fallback option directly
                logger.warning(f"Primary save approach failed: {e}. Trying fallback...")
                try:
                    mower.save_boundary(coordinates)
                    logger.info(f"Successfully saved boundary with {len(coordinates)} points using fallback")
                    return jsonify({"success": True, "message": "Boundary saved successfully (fallback)"})
                except Exception as fallback_e:
                    logger.error(f"Fallback save approach failed: {fallback_e}")
                    raise fallback_e
        except Exception as e:
            logger.error(f"Failed to save mowing area: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/get-path", methods=["GET"])
    def get_current_path():
        """Get the current planned path."""
        try:
            path_planner = mower.get_path_planner()
            path = path_planner.current_path
            return jsonify({"success": True, "path": path})
        except Exception as e:
            logger.error(f"Failed to get path: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/home", methods=["GET"])
    def get_home():
        """Get the home location."""
        try:
            home = mower.get_home_location()
            return jsonify({"success": True, "location": home})
        except Exception as e:
            logger.error(f"Failed to get home location: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/home", methods=["POST"])
    def set_home():
        """Set the home location."""
        try:
            data = request.get_json()
            location = data.get("location")
            if not location:
                msg = "No location provided"
                return jsonify({"success": False, "error": msg}), 400
            mower.set_home_location(location)
            return jsonify({"success": True})
        except Exception as e:
            logger.error(f"Failed to set home: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/mower/status", methods=["GET"])
    def get_mower_status():
        """Get the current status of the mower."""
        try:
            status = {
                "mode": mower.get_mode(),
                "battery": mower.get_battery_level(),
            }
            return jsonify(status)
        except Exception as e:
            error_msg = "Failed to get mower status: {}".format(str(e))
            logger.error(error_msg)
            return jsonify({"error": str(e)}), 500

    @app.route("/api/safety")
    def get_safety_status():
        """Get the current safety status."""
        try:
            return jsonify(mower.get_safety_status())
        except Exception as e:
            logger.error(f"Failed to get safety status: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/start")
    def start_mowing():
        """Start the mowing operation."""
        try:
            mower.start()
            return jsonify({"status": "success"})
        except Exception as e:
            logger.error(f"Failed to start mowing: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route("/api/stop")
    def stop_mowing():
        """Stop the mowing operation."""
        try:
            mower.stop()
            return jsonify({"status": "success"})
        except Exception as e:
            logger.error(f"Failed to stop mowing: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500

    # Boundary Management
    @app.route("/api/boundary", methods=["GET"])
    def get_boundary():
        """Get the yard boundary and no-go zones."""
        try:
            boundary = mower.get_boundary()
            no_go_zones = mower.get_no_go_zones()
            return jsonify(
                {
                    "success": True,
                    "boundary": boundary,
                    "no_go_zones": no_go_zones,
                }
            )
        except Exception as e:
            logger.error("Failed to get boundary: {}".format(e))
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/boundary", methods=["POST"])
    def save_boundary():
        """Save the yard boundary."""
        try:
            data = request.get_json()
            boundary = data.get("boundary")
            if not boundary:
                msg = "No boundary provided"
                return jsonify({"success": False, "error": msg}), 400
            mower.save_boundary(boundary)
            return jsonify({"success": True})
        except Exception as e:
            logger.error(f"Failed to save boundary: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    # No-Go Zones Management
    @app.route("/api/no-go-zones", methods=["POST"])
    def save_no_go_zones():
        """Save no-go zones."""
        try:
            data = request.get_json()
            zones = data.get("zones")
            if not zones:
                msg = "No zones provided"
                return jsonify({"success": False, "error": msg}), 400
            mower.save_no_go_zones(zones)
            return jsonify({"success": True})
        except Exception as e:
            logger.error(f"Failed to save no-go zones: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    # Schedule Management
    @app.route("/api/schedule", methods=["GET"])
    def get_schedule():
        """Get the mowing schedule."""
        try:
            schedule = mower.get_mowing_schedule()
            return jsonify({"success": True, "schedule": schedule})
        except Exception as e:
            logger.error(f"Failed to get schedule: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/schedule", methods=["POST"])
    def set_schedule():
        """Set the mowing schedule."""
        try:
            data = request.get_json()
            schedule = data.get("schedule")
            if not schedule:
                msg = "No schedule provided"
                return jsonify({"success": False, "error": msg}), 400
            mower.set_mowing_schedule(schedule)
            return jsonify({"success": True})
        except Exception as e:
            logger.error(f"Failed to set schedule: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    # Language support
    @app.route("/api/languages", methods=["GET"])
    def get_languages():
        """Get available UI languages."""
        try:
            # Define supported languages with their display names
            languages = {
                "en": {"name": "English", "active": True},
                "es": {"name": "Español", "active": True},
                "fr": {"name": "Français", "active": True},
            }

            # Get current language from request or default to English
            current_lang = request.accept_languages.best_match(["en", "es", "fr"]) or "en"

            return jsonify(
                {
                    "success": True,
                    "current": current_lang,
                    "available": languages,
                }
            )
        except Exception as e:
            logger.error(f"Failed to get languages: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    # Static file route with enhanced CORS headers for Cloudflare Access
    @app.route("/static/<path:filename>")
    def static_files(filename):
        """Serve static files with proper CORS headers for Cloudflare Access."""
        from flask import make_response, send_from_directory

        try:
            response = make_response(send_from_directory(app.static_folder, filename))
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, CF-Access-Client-Id, CF-Access-Client-Secret"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Vary"] = "Origin"
            return response
        except Exception as e:
            logger.error(f"Error serving static file {filename}: {e}")
            return jsonify({"error": "File not found"}), 404

    # OPTIONS route for preflight CORS requests
    @app.route("/static/<path:filename>", methods=["OPTIONS"])
    def static_files_options(filename):
        """Handle preflight OPTIONS requests for static files."""
        response = make_response()
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, CF-Access-Client-Id, CF-Access-Client-Secret"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response

    # WebSocket event handlers
    @socketio.on("connect")
    def handle_connect(auth=None):
        """Handle client connection."""
        logger.info("Client connected")
        try:
            emit("status_update", mower.get_status())
            # Use the path_planner directly instead of calling
            # get_current_path()
            path_planner = mower.get_path_planner()
            emit("path_update", path_planner.current_path)
        except Exception as e:
            logger.error(f"Error in handle_connect: {e}")

    @socketio.on("disconnect")
    def handle_disconnect():
        """Handle client disconnection."""
        logger.info("Client disconnected from web interface")

    @socketio.on("request_data")
    def handle_data_request(data):
        """Handle data request from client."""
        try:
            data_type = data.get("type", "")

            # For simulation mode, generate simulated data when needed
            if USE_SIMULATION:
                sim_data = get_simulated_sensor_data()

                if data_type == "safety":
                    emit("safety_status", sim_data["imu"]["safety_status"])
                    return
                elif data_type == "sensor_data":
                    emit("sensor_data", sim_data)
                    return
                elif data_type == "all":
                    emit("status_update", mower.get_status())
                    emit("safety_status", sim_data["imu"]["safety_status"])
                    emit("sensor_data", sim_data)
                    return

            # Standard data handling when not in simulation mode
            if data_type == "safety":
                emit("safety_status", mower.get_safety_status())
            elif data_type == "sensor_data":
                emit("sensor_data", mower.get_sensor_data())
            elif data_type == "system_info":
                # Get system information like uptime, CPU temperature, etc.
                system_info = {
                    "softwareVersion": "1.0.0",
                    "hardwareModel": "Autonomous Mower v1",
                    "uptime": "0d 0h 0m",  # Should be calculated from system uptime
                    "cpuTemp": "45",  # Should come from actual system monitoring
                    "cpuUsage": "10",  # Should come from actual system monitoring
                    "memoryUsage": "25",  # Should come from actual system monitoring
                    "diskUsage": "30",  # Should come from actual system monitoring
                }
                emit("system_info", system_info)
            elif data_type == "calibration_status":
                # Get calibration status
                calibration_status = {
                    "imu": "Uncalibrated" if not USE_SIMULATION else "Simulated",
                    "blade": "Uncalibrated" if not USE_SIMULATION else "Simulated",
                    "gps": "Not Set" if not USE_SIMULATION else "Simulated",
                }
                emit("calibration_update", calibration_status)
            elif data_type == "all":
                emit("status_update", mower.get_status())
                emit("safety_status", mower.get_safety_status())
                emit("sensor_data", mower.get_sensor_data())
        except Exception as e:
            logger.error(f"Error handling data request: {e}")
            emit("error", {"message": str(e)})

    @socketio.on("control_command")
    def handle_control_command(data):
        """Handle control commands from client."""
        try:
            command = data.get("command")
            params = data.get("params", {})

            if command == "emergency_stop":
                mower.emergency_stop()
                emit(
                    "command_response",
                    {
                        "command": command,
                        "success": True,
                        "message": "Emergency stop activated",
                    },
                )
            elif command == "save_settings":
                # Special case for save_settings using the same logic as the
                # REST endpoint
                try:
                    settings = params.get("settings", {})
                    mowing = settings.get("mowing", {})

                    path_planner = mower.get_path_planner()

                    # Update pattern planner settings
                    if "pattern" in mowing:
                        path_planner.pattern_config.pattern_type = PatternType[mowing["pattern"]]
                    if "spacing" in mowing:
                        path_planner.pattern_config.spacing = float(mowing["spacing"])
                    if "angle" in mowing:
                        path_planner.pattern_config.angle = float(mowing["angle"])
                    if "overlap" in mowing:
                        path_planner.pattern_config.overlap = float(mowing["overlap"])

                    emit(
                        "command_response",
                        {
                            "command": command,
                            "success": True,
                            "message": "Settings saved successfully",
                        },
                    )
                except Exception as e:
                    logger.error(f"Failed to save settings: {e}")
                    emit(
                        "command_response",
                        {"command": command, "success": False, "error": str(e)},
                    )
            else:
                # Handle other commands...
                result = mower.execute_command(command, params)
                emit(
                    "command_response",
                    {"command": command, "success": True, "result": result},
                )
        except Exception as e:
            # Handle error case
            cmd = command if "command" in locals() else "unknown"
            error_parts = ["Error handling command", cmd, str(e)]
            error_msg = " - ".join(error_parts)
            logger.error(error_msg)
            emit(
                "command_response",
                {"command": cmd, "success": False, "error": str(e)},
            )

    @socketio.on("request_path_update")
    def handle_path_update():
        """Send current path to client."""
        try:
            path_planner = mower.get_path_planner()
            path = path_planner.current_path
            emit("path_update", path)
        except Exception as e:
            logger.error(f"Error sending path update: {e}")

    @socketio.on("error")
    def handle_error(error_data):
        """Handle error events from the client."""
        error_type = error_data.get("type")
        error_msg = error_data.get("message")
        logger.error(
            "Error received from client - Type: {}, Message: {}".format(error_type, error_msg)
        )  # Background task for sending updates

    def send_updates():
        """Send periodic updates to connected clients."""
        logger.info("Starting send_updates background task.")
        while True:
            try:
                socketio.sleep(0.1)  # 100ms interval
                logger.debug("send_updates loop running.")

                # Get status data
                try:
                    status = mower.get_status()
                except Exception as e:
                    logger.error(f"Error getting mower status: {e}")
                    status = {"state": "error", "initialized": False, "resources_available": [], "error": str(e)}

                # Get safety status - use real or simulated based on mode
                try:
                    if USE_SIMULATION:
                        sim_data = get_simulated_sensor_data()
                        safety_status = sim_data.get("imu", {}).get("safety_status", {"is_safe": True})
                        sensor_data = sim_data
                    else:
                        logger.debug("Not in simulation mode, getting real sensor data...")
                        sensor_interface = mower.get_sensor_interface()
                        logger.debug(f"APP.PY send_updates: Retrieved sensor_interface: {sensor_interface}")
                        if (
                            sensor_interface
                            and hasattr(sensor_interface, "get_safety_status")
                            and hasattr(sensor_interface, "get_sensor_data")
                        ):
                            logger.debug("Using sensor_interface for data collection...")
                            safety_status = sensor_interface.get_safety_status()
                            sensor_data = sensor_interface.get_sensor_data()
                        else:
                            logger.debug(
                                "App.py:send_updates - Using mower (DummyResourceManager) methods for data collection."
                            )
                            safety_status = mower.get_safety_status()  # This calls DummyRM.get_safety_status
                            sensor_data = mower.get_sensor_data()  # This calls DummyRM.get_sensor_data which reads JSON
                        logger.info(f"App.py:send_updates - Data fetched by DummyResourceManager: {sensor_data}")
                except Exception as e:
                    logger.error(
                        f"App.py:send_updates - Error getting safety or sensor data via DummyResourceManager: {e}",
                        exc_info=True,
                    )
                    safety_status = {"is_safe": True, "error": str(e), "source": "app.py_exception_fallback"}
                    # Provide fallback sensor data instead of empty dict
                    sensor_data = {
                        "imu": {
                            "heading": 0.0,
                            "roll": 0.0,
                            "pitch": 0.0,
                            "safety_status": {
                                "emergency_stop_active": False,
                                "obstacle_detected_nearby": False,
                                "low_battery_warning": False,
                                "system_error": True,
                            },
                            "error": str(e),
                        },
                        "environment": {"temperature": 20.0, "humidity": 50.0, "pressure": 1013.25, "error": str(e)},
                        "tof": {"left": 100.0, "right": 100.0, "error": str(e)},
                        "power": {
                            "voltage": 12.0,
                            "current": 1.0,
                            "power": 12.0,
                            "percentage": 80.0,
                            "status": "Error - using fallback data",
                            "error": str(e),
                        },
                    }

                # Ensure sensor_data is never empty
                if not sensor_data:
                    logger.warning("Sensor data is empty, providing minimal fallback...")
                    sensor_data = {
                        "imu": {"heading": 1000, "roll": 88.8, "pitch": 88.8},
                        "environment": {"temperature": 203.0, "humidity": 150.0, "pressure": 0.25},
                        "tof": {"left": 1080.0, "right": 1080.0},
                        "power": {"voltage": 50.0, "current": 450.0, "power": 150.0, "percentage": 800.0},
                    }

                # Always emit valid data
                try:
                    socketio.emit("status_update", status)
                except Exception as e:
                    logger.error(f"Error emitting status_update: {e}")
                try:
                    socketio.emit("safety_status", safety_status)
                except Exception as e:
                    logger.error(f"Error emitting safety_status: {e}")
                try:
                    logger.info(f"App.py:send_updates - Emitting sensor_data via SocketIO: {sensor_data}")
                    socketio.emit("sensor_data", sensor_data)
                    # logger.debug(f"Emitted sensor_data: {sensor_data}") # Redundant with info log
                except Exception as e:
                    logger.error(f"App.py:send_updates - Error emitting sensor_data via SocketIO: {e}", exc_info=True)

            except Exception as e:
                logger.error(f"App.py:send_updates - Error in update loop: {e}", exc_info=True)
                socketio.sleep(1)  # Wait longer on error

    if not hasattr(app, "update_thread_started") or not app.update_thread_started:
        socketio.start_background_task(send_updates)
        app.update_thread_started = True

    return app, socketio


def save_area_command_handler(params, mower):
    """Handle the save_area command with robust fallbacks."""
    coordinates = params.get("coordinates", [])
    logger.info(f"Handling save_area command with {len(coordinates)} points")

    if not coordinates:
        logger.warning("No coordinates provided in save_area command")
        return {"success": False, "error": "No coordinates provided"}

    # Try all possible methods to save the boundary
    try:
        # Method 1: Using path_planner.set_boundary_points
        path_planner = mower.get_path_planner()
        if hasattr(path_planner, "set_boundary_points"):
            result = path_planner.set_boundary_points(coordinates)
            if result:
                logger.info("Successfully saved boundary using set_boundary_points")
                return {"success": True, "message": "Boundary saved successfully (set_boundary_points)"}

        # Method 2: Using pattern_config directly
        if hasattr(path_planner, "pattern_config"):
            path_planner.pattern_config.boundary_points = coordinates
            logger.info("Successfully saved boundary using pattern_config")
            return {"success": True, "message": "Boundary saved successfully (pattern_config)"}

        # Method 3: Using mower.save_boundary
        if hasattr(mower, "save_boundary"):
            mower.save_boundary(coordinates)
            logger.info("Successfully saved boundary using mower.save_boundary")
            return {"success": True, "message": "Boundary saved successfully (mower.save_boundary)"}

        # If we get here, none of the methods worked
        logger.error("No suitable method found to save boundary")
        return {"success": False, "error": "No suitable method found to save boundary"}

    except Exception as e:
        logger.error(f"Error saving boundary: {e}")
        return {"success": False, "error": f"Error saving boundary: {str(e)}"}


if __name__ == "__main__":
    # This is just for testing the web interface directly
    from mower.main_controller import ResourceManager

    mower = ResourceManager()
    app, socketio = create_app(mower)

    # Start the background task only if it's not already running
    if not hasattr(app, "update_thread_started") or not app.update_thread_started:
        socketio.start_background_task(send_updates)
        app.update_thread_started = True

    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
