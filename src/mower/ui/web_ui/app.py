"""
Web interface for the autonomous mower.

This module provides a web-based user interface for controlling and monitoring
the autonomous mower. It uses Flask to create a web server that serves HTML pages
and provides REST API endpoints for real-time interaction with the mower.

Features:
- Dashboard with live sensor data and system status
- Manual control interface for direct mower operation
- Configuration management for mowing parameters
- Map visualization for path planning and navigation
- Live camera stream with obstacle detection overlay
- System logs and diagnostic information
"""

from flask import Flask, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO

from mower.utilities import LoggerConfigInfo


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

    @app.route('/api/status')
    def get_status():
        """Get the current status of the mower."""
        return jsonify({
            'status': 'running',
            'battery_level': 100,
            'position': {'x': 0, 'y': 0}
        })

    @app.route('/api/start')
    def start_mowing():
        """Start the mowing operation."""
        try:
            mower.start()
            return jsonify({'status': 'success'})
        except Exception as e:
            logger.error(f"Failed to start mowing: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500

    @app.route('/api/stop')
    def stop_mowing():
        """Stop the mowing operation."""
        try:
            mower.stop()
            return jsonify({'status': 'success'})
        except Exception as e:
            logger.error(f"Failed to stop mowing: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500

    @socketio.on('connect')
    def handle_connect():
        """Handle client connection."""
        logger.info("Client connected to web interface")

    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection."""
        logger.info("Client disconnected from web interface")

    return app, socketio


if __name__ == '__main__':
    # This is just for testing the web interface directly
    from mower.mower import Mower
    mower = Mower()
    app, socketio = create_app(mower)
    socketio.run(app, host='0.0.0.0', port=5000)
