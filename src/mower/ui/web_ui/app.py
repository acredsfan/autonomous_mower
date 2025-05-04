"""Flask web interface for the autonomous mower."""

from flask import Flask, jsonify, render_template, request, Response, send_file
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from flask_babel import Babel
import os

from mower.navigation.path_planner import PatternType
from mower.utilities.logger_config import LoggerConfigInfo
from mower.ui.web_ui.i18n import init_babel  # Import the babel init function

# Initialize logger
logger = LoggerConfigInfo.get_logger(__name__)


def create_app(mower):
    """Create the Flask application.

    Args:
        mower: The mower instance to control.

    Returns:
        The Flask application instance.
    """
    app = Flask(__name__)
    CORS(app)
    socketio = SocketIO(app, cors_allowed_origins="*")

    # Initialize Babel for translations using the version-agnostic approach
    # This uses the implementation from i18n.py which works with any
    # Flask-Babel version
    try:
        init_babel(app)
        logger.info("Initialized Babel from i18n module")
    except Exception as e:
        # Fallback to legacy initialization if needed
        logger.warning(f"Could not initialize Babel from i18n module: {e}")
        babel = Babel(app)

        # Define locale selector function instead of using decorator
        def get_locale():
            """Select the best match for supported languages."""
            return request.accept_languages.best_match(["en", "es", "fr"])

        # Try different Flask-Babel versions' initialization methods
        try:
            # Flask-Babel >= 2.0
            babel.init_app(app, locale_selector=get_locale)
            logger.info("Initialized Babel with locale_selector parameter")
        except TypeError:
            try:
                # Flask-Babel < 2.0
                babel.init_app(app)
                babel.localeselector(get_locale)
                logger.info("Initialized Babel with localeselector decorator")
            except Exception as e2:
                logger.error(f"Failed to initialize Babel: {e2}")

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
        # Use a default API key or retrieve from environment/config
        # For development purposes, we'll use a placeholder API key
        google_maps_api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
        return render_template("map.html", google_maps_api_key=google_maps_api_key)

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
            camera = mower.resource_manager.get_camera()

            def generate_frames():
                """Generate camera frames."""
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
                            yield (
                                b"--frame\r\n"
                                b"Content-Type: image/jpeg\r\n\r\n"
                                + jpeg_bytes
                                + b"\r\n"
                            )

                            # Add a small delay
                            socketio.sleep(0.05)
                            continue
                        except Exception:
                            # If both methods fail, try get_last_frame()
                            try:
                                jpeg_bytes = camera.get_last_frame()
                                if jpeg_bytes is None:
                                    continue

                                # If we got JPEG bytes directly, yield them
                                yield (
                                    b"--frame\r\n"
                                    b"Content-Type: image/jpeg\r\n\r\n"
                                    + jpeg_bytes
                                    + b"\r\n"
                                )

                                # Add a small delay
                                socketio.sleep(0.05)
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

                        _, buffer = cv2.imencode(".jpg", frame)
                        frame_bytes = buffer.tobytes()

                        # Yield the frame in multipart response
                        yield (
                            b"--frame\r\n"
                            b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
                        )

                        # Add a small delay
                        socketio.sleep(0.05)
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
            placeholder_img = os.path.join(
                app.static_folder, "images/camera-placeholder.jpg"
            )
            if os.path.exists(placeholder_img):
                return send_file(placeholder_img, mimetype="image/jpeg")
            else:
                return "Video stream unavailable", 503

    @app.route("/api/get-settings", methods=["GET"])
    def get_settings():
        """Get current mower settings."""
        try:
            path_planner = mower.resource_manager.get_path_planner()
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

            path_planner = mower.resource_manager.get_path_planner()

            # Update pattern planner settings
            if "pattern" in mowing:
                path_planner.pattern_config.pattern_type = PatternType[
                    mowing["pattern"]
                ]
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

    @app.route("/api/get-area", methods=["GET"])
    def get_area():
        """Get the current mowing area configuration."""
        try:
            path_planner = mower.resource_manager.get_path_planner()
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

            path_planner = mower.resource_manager.get_path_planner()
            path_planner.pattern_config.boundary_points = coordinates
            return jsonify({"success": True})
        except Exception as e:
            logger.error(f"Failed to save mowing area: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/get-path", methods=["GET"])
    def get_current_path():
        """Get the current planned path."""
        try:
            path_planner = mower.resource_manager.get_path_planner()
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
            current_lang = (
                request.accept_languages.best_match(["en", "es", "fr"]) or "en"
            )

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

    # WebSocket event handlers
    @socketio.on("connect")
    def handle_connect(auth=None):
        """Handle client connection."""
        logger.info("Client connected")
        try:
            emit("status_update", mower.get_status())
            # Use the path_planner directly instead of calling
            # get_current_path()
            path_planner = mower.resource_manager.get_path_planner()
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
            if data.get("type") == "safety":
                emit("safety_status", mower.get_safety_status())
            elif data.get("type") == "all":
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
            path_planner = mower.resource_manager.get_path_planner()
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
            "Error received from client - Type: {}, Message: {}".format(
                error_type, error_msg
            )
        )  # Background task for sending updates

    def send_updates():
        """Send periodic updates to connected clients."""
        while True:
            try:
                socketio.sleep(0.1)  # 100ms interval
                status = mower.get_status()
                safety_status = mower.get_safety_status()
                sensor_data = mower.get_sensor_data()

                # Get location data for map updates
                location = mower.get_gps_location()
                position_data = {
                    "gps": {
                        "latitude": location[0],
                        "longitude": location[1],
                        "fix": location != (0.0, 0.0),
                    },
                    "currentPosition": location,
                    "homePosition": mower.get_home_location(),
                    "waypoints": mower.get_path() if hasattr(mower, "get_path") else [],
                }

                socketio.emit("status_update", status)
                socketio.emit("safety_status", safety_status)
                socketio.emit("sensor_data", sensor_data)
                socketio.emit("position_update", position_data)
            except Exception as e:
                logger.error(f"Error in update loop: {e}")
                socketio.sleep(1)  # Wait longer on error

    socketio.start_background_task(send_updates)

    @app.route("/api/<command>", methods=["POST"])
    def handle_command(command):
        """Generic handler for commands sent from the frontend."""
        try:
            data = request.get_json() or {}
            logger.info(f"Received command: {command} with data: {data}")

            # Map frontend commands to mower methods
            command_handlers = {
                "generate_pattern": lambda params: {
                    "success": True,
                    "path": (
                        mower.resource_manager.get_path_planner().generate_pattern(
                            params.get("pattern_type", "PARALLEL"),
                            params.get("settings", {}),
                        )
                    ),
                    "coverage": 0.85,  # Example coverage value
                },
                "save_area": lambda params: (
                    {"success": True, "message": "Boundary saved successfully"}
                    if (
                        mower.resource_manager.get_path_planner().set_boundary_points(
                            params.get("coordinates", [])
                        )
                    )
                    else {"success": False, "error": "Failed to save boundary"}
                ),
                "set_home": lambda params: (
                    {
                        "success": True,
                        "message": "Home location set successfully",
                    }
                    if mower.set_home_location(params.get("location", {}))
                    else {
                        "success": False,
                        "error": "Failed to set home location",
                    }
                ),
                "save_no_go_zones": lambda params: (
                    {
                        "success": True,
                        "message": "No-go zones saved successfully",
                    }
                    if mower.save_no_go_zones(params.get("zones", []))
                    else {
                        "success": False,
                        "error": "Failed to save no-go zones",
                    }
                ),
                "get_area": lambda params: {
                    "success": True,
                    "data": {
                        "boundary_points": (
                            mower.resource_manager.get_path_planner().pattern_config.boundary_points
                        )
                    },
                },
                "get_home": lambda params: {
                    "success": True,
                    "location": mower.get_home_location(),
                },
                "get_boundary": lambda params: {
                    "success": True,
                    "boundary": mower.get_boundary(),
                    "no_go_zones": mower.get_no_go_zones(),
                },
                "get_settings": lambda params: {
                    "success": True,
                    "data": {
                        "mowing": {
                            "pattern": (
                                mower.resource_manager.get_path_planner().pattern_config.pattern_type.name
                            ),
                            "spacing": (
                                mower.resource_manager.get_path_planner().pattern_config.spacing
                            ),
                            "angle": (
                                mower.resource_manager.get_path_planner().pattern_config.angle
                            ),
                            "overlap": (
                                mower.resource_manager.get_path_planner().pattern_config.overlap
                            ),
                        }
                    },
                },
            }

            # Execute the command if it exists
            if command in command_handlers:
                logger.info(f"Executing command: {command}")
                try:
                    result = command_handlers[command](data)
                    return jsonify(result)
                except AttributeError as e:
                    logger.error(f"Attribute error in command handler: {e}")
                    if "set_boundary_points" in str(e):
                        # Fallback for older API
                        if command == "save_area":
                            mower.save_boundary(data.get("coordinates", []))
                            return jsonify(
                                {
                                    "success": True,
                                    "message": "Boundary saved successfully",
                                }
                            )
                    elif "generate_pattern" in str(e):
                        # Fallback for pattern generation
                        return jsonify(
                            {
                                "success": True,
                                "path": [],  # Return empty path
                                "message": "Pattern generation not fully implemented",
                            }
                        )
                    return jsonify({"success": False, "error": str(e)}), 500
            else:
                logger.warning(f"Unknown command: {command}")
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": f"Unknown command: {command}",
                        }
                    ),
                    400,
                )

        except Exception as e:
            logger.error(f"Error handling command {command}: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    return app, socketio


if __name__ == "__main__":
    # This is just for testing the web interface directly
    from mower.mower import Mower

    mower = Mower()
    app, socketio = create_app(mower)
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
