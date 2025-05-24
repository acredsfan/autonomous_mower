"""
Data collection UI controller.

This module provides web UI interface for the data collection functionality.
"""
import logging
import os
import json

from flask import Blueprint, render_template, jsonify, request

from mower.data_collection.collector import DataCollector

logger = logging.getLogger(__name__)

datacollection_bp = Blueprint(
    "datacollection",
    __name__,
    url_prefix="/datacollection")


class DataCollectionController:
    """Controller for data collection UI functionality."""

    def __init__(self, data_collector: DataCollector):
        """Initialize data collection controller.

        Args:
            data_collector: Instance of DataCollector to interface with
        """
        self.data_collector = data_collector
        self._register_routes()

    def _register_routes(self) -> None:
        """Register routes with Flask blueprint."""
        # GET routes
        datacollection_bp.route("/")(self.index)
        datacollection_bp.route("/status")(self.get_status)
        datacollection_bp.route("/sessions")(self.get_sessions)
        datacollection_bp.route(
            "/sessions/<session_id>")(self.get_session_details)

        # POST routes
        datacollection_bp.route(
            "/start",
            methods=["POST"])(
            self.start_collection)
        datacollection_bp.route(
            "/stop",
            methods=["POST"])(
            self.stop_collection)
        datacollection_bp.route(
            "/pattern",
            methods=["POST"])(
            self.change_pattern)
        datacollection_bp.route(
            "/interval",
            methods=["POST"])(
            self.set_interval)

    def index(self):
        """Render data collection UI page."""
        return render_template(
            "datacollection.html",
            title="Data Collection",
            status=self.data_collector.get_session_status()
        )

    def get_status(self):
        """Get current data collection status."""
        return jsonify(self.data_collector.get_session_status())

    def start_collection(self):
        """Start data collection session."""
        session_name = request.form.get("session_name", "")
        session_id = self.data_collector.start_collection(session_name)

        if session_id:
            return jsonify({
                "success": True,
                "message": f"Data collection started with session ID: {session_id}",
                "session_id": session_id
            })
        else:
            return jsonify({
                "success": False,
                "message": "Failed to start data collection"
            }), 500

    def stop_collection(self):
        """Stop data collection session."""
        stats = self.data_collector.stop_collection()

        if stats.get("status") == "not_running":
            return jsonify({
                "success": False,
                "message": "No data collection session in progress"
            }), 400

        return jsonify({
            "success": True,
            "message": "Data collection stopped",
            "stats": stats
        })

    def change_pattern(self):
        """Change data collection pattern."""
        pattern = request.form.get("pattern", "")

        if not pattern:
            return jsonify({
                "success": False,
                "message": "Pattern name is required"
            }), 400

        success = self.data_collector.change_collection_pattern(pattern)

        if success:
            return jsonify({
                "success": True,
                "message": f"Pattern changed to {pattern}"
            })
        else:
            return jsonify({
                "success": False,
                "message": f"Failed to change to pattern {pattern}"
            }), 400

    def set_interval(self):
        """Set image capture interval."""
        try:
            interval = float(request.form.get("interval", "5"))

            if interval <= 0:
                return jsonify({
                    "success": False,
                    "message": "Interval must be positive"
                }), 400

            self.data_collector.set_image_interval(interval)

            return jsonify({
                "success": True,
                "message": f"Image capture interval set to {interval} seconds"
            })

        except ValueError:
            return jsonify({
                "success": False,
                "message": "Invalid interval value"}), 400

    def get_sessions(self):
        """Get list of data collection sessions."""
        try:
            sessions = []
            base_path = self.data_collector.base_storage_path

            # List directories in the base path
            if os.path.exists(base_path):
                for item in os.listdir(base_path):
                    full_path = os.path.join(base_path, item)

                    # Check if it's a directory and has a session info file
                    if os.path.isdir(full_path):
                        info_path = os.path.join(
                            full_path, "session_info.json")
                        if os.path.exists(info_path):
                            try:
                                with open(info_path, 'r') as f:
                                    session_info = json.load(f)

                                # Add path and directory name to session info
                                session_info['directory'] = item
                                session_info['path'] = full_path
                                sessions.append(session_info)
                            except Exception as e:
                                logger.error(
                                    f"Error reading session info {info_path}: {e}")

            # Sort sessions by start time (newest first)
            sessions.sort(key=lambda x: x.get('start_time', ''), reverse=True)

            return jsonify({
                "success": True,
                "sessions": sessions
            })
        except Exception as e:
            logger.error(f"Error retrieving sessions: {e}")
            return jsonify({
                "success": False,
                "message": f"Error retrieving sessions: {str(e)}",
                "sessions": []
            }), 500

    def get_session_details(self, session_id: str):
        """Get details of a specific data collection session."""
        try:
            base_path = self.data_collector.base_storage_path

            # Look for the session directory
            session_path = None
            session_info = None

            for item in os.listdir(base_path):
                full_path = os.path.join(base_path, item)

                if os.path.isdir(full_path):
                    info_path = os.path.join(full_path, "session_info.json")
                    if os.path.exists(info_path):
                        try:
                            with open(info_path, 'r') as f:
                                info = json.load(f)

                            if info.get('session_id') == session_id:
                                session_path = full_path
                                session_info = info
                                break
                        except Exception as e:
                            logger.error(
                                f"Error reading session info {info_path}: {e}")

            if not session_info:
                return jsonify({
                    "success": False,
                    "message": f"Session {session_id} not found"
                }), 404

            # Count images in the directory
            image_count = 0
            image_list = []

            for file in os.listdir(session_path):
                if file.endswith('.jpg') or file.endswith('.jpeg'):
                    image_count += 1
                    # Use relative path for images to be accessible via web
                    rel_path = os.path.join(
                        'data/collected_images',
                        os.path.basename(session_path),
                        file)
                    image_list.append({
                        "name": file,
                        "path": rel_path.replace('\\', '/')
                    })

            # Sort images by name
            image_list.sort(key=lambda x: x['name'])

            # Add image count to session info
            session_info['image_count'] = image_count
            # Just include first 10 images for preview
            session_info['images'] = image_list[:10]
            session_info['directory'] = os.path.basename(session_path)

            return jsonify({
                "success": True,
                "session_id": session_id,
                "details": session_info
            })

        except Exception as e:
            logger.error(f"Error retrieving session details: {e}")
            return jsonify({
                "success": False,
                "message": f"Error retrieving session details: {str(e)}",
                "session_id": session_id,
                "details": {}
            }), 500
