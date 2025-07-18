"""
API routes for the web interface.

This module contains the API endpoint definitions separated from the main app.py
to improve maintainability and reduce the size of the main application file.
"""

from flask import Blueprint, jsonify, request
from mower.navigation.path_planner import PatternType
from mower.ui.web_ui.decorators import api_error_handler, validate_json_request
from mower.utilities.logger_config import LoggerConfigInfo

logger = LoggerConfigInfo.get_logger(__name__)


def create_api_blueprint(mower):
    """Create the API blueprint with all routes."""
    api = Blueprint('api', __name__, url_prefix='/api')

    @api.route("/get-settings", methods=["GET"])
    @api_error_handler
    def get_settings():
        """Get current mower settings."""
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

    @api.route("/save-settings", methods=["POST"])
    @api_error_handler
    @validate_json_request(required_fields=["settings"])
    def save_settings():
        """Save mower settings."""
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

    @api.route("/mower/status", methods=["GET"])
    @api_error_handler
    def get_mower_status():
        """Get the current status of the mower."""
        status = {
            "mode": mower.get_mode(),
            "battery": mower.get_battery_level(),
        }
        return jsonify(status)

    @api.route("/safety")
    @api_error_handler
    def get_safety_status():
        """Get the current safety status."""
        return jsonify(mower.get_safety_status())

    @api.route("/start")
    @api_error_handler
    def start_mowing():
        """Start the mowing operation."""
        mower.start()
        return jsonify({"status": "success"})

    @api.route("/stop")
    @api_error_handler
    def stop_mowing():
        """Stop the mowing operation."""
        mower.stop()
        return jsonify({"status": "success"})

    @api.route("/boundary", methods=["GET"])
    @api_error_handler
    def get_boundary():
        """Get the yard boundary and no-go zones."""
        boundary = mower.get_boundary()
        no_go_zones = mower.get_no_go_zones()
        return jsonify({
            "success": True,
            "boundary": boundary,
            "no_go_zones": no_go_zones,
        })

    @api.route("/boundary", methods=["POST"])
    @api_error_handler
    @validate_json_request(required_fields=["boundary"])
    def save_boundary():
        """Save the yard boundary."""
        data = request.get_json()
        boundary = data.get("boundary")
        mower.save_boundary(boundary)
        return jsonify({"success": True})

    @api.route("/schedule", methods=["GET"])
    @api_error_handler
    def get_schedule():
        """Get the mowing schedule."""
        schedule = mower.get_mowing_schedule()
        return jsonify({"success": True, "schedule": schedule})

    @api.route("/schedule", methods=["POST"])
    @api_error_handler
    @validate_json_request(required_fields=["schedule"])
    def set_schedule():
        """Set the mowing schedule."""
        data = request.get_json()
        schedule = data.get("schedule")
        mower.set_mowing_schedule(schedule)
        return jsonify({"success": True})

    return api