"""
Web interface for the autonomous mower.

This module provides a web-based user interface for controlling and monitoring
the autonomous mower. It uses Flask to create a web server that serves HTML
pages and provides REST API endpoints for real-time mower interaction.

Features:
- Dashboard with live sensor data and system status
- Manual control interface for direct mower operation
- Configuration management for mowing parameters
- Map visualization for path planning and navigation
- Live camera stream with obstacle detection overlay
- System logs and diagnostic information
- Safety monitoring and alerts
"""

from flask import Flask, jsonify, render_template
from flask_cors import CORS
from flask_socketio import SocketIO, emit

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

    # Route handlers
    @app.route('/')
    def index():
        """Render the dashboard page."""
        return render_template('index.html')

    @app.route('/control')
    def control():
        """Render the manual control page."""
        return render_template('control.html')

    @app.route('/map')
    def map_view():
        """Render the map view page."""
        return render_template('map.html')

    @app.route('/diagnostics')
    def diagnostics():
        """Render the diagnostics page."""
        return render_template('diagnostics.html')

    @app.route('/settings')
    def settings():
        """Render the settings page."""
        return render_template('settings.html')

    @app.route('/api/status')
    def get_status():
        """Get the current status of the mower."""
        try:
            status = mower.get_status()
            safety_status = mower.get_safety_status()
            return jsonify({
                'status': status,
                'safety': safety_status,
                'battery_level': mower.get_battery_level(),
                'position': mower.get_position()
                })
        except Exception as e:
            logger.error(f"Failed to get status: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/safety')
    def get_safety_status():
        """Get the current safety status."""
        try:
            return jsonify(mower.get_safety_status())
        except Exception as e:
            logger.error(f"Failed to get safety status: {e}")
            return jsonify({'error': str(e)}), 500

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

    # WebSocket event handlers
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection."""
        logger.info("Client connected to web interface")
        # Send initial data
        emit('status_update', mower.get_status())
        emit('safety_status', mower.get_safety_status())

    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection."""
        logger.info("Client disconnected from web interface")

    @socketio.on('request_data')
    def handle_data_request(data):
        """Handle data request from client."""
        try:
            if data.get('type') == 'safety':
                emit('safety_status', mower.get_safety_status())
            elif data.get('type') == 'all':
                emit('status_update', mower.get_status())
                emit('safety_status', mower.get_safety_status())
                emit('sensor_data', mower.get_sensor_data())
        except Exception as e:
            logger.error(f"Error handling data request: {e}")
            emit('error', {'message': str(e)})

    @socketio.on('control_command')
    def handle_control_command(data):
        """Handle control commands from client."""
        try:
            command = data.get('command')
            params = data.get('params', {})

            if command == 'emergency_stop':
                mower.emergency_stop()
                emit('command_response', {
                    'command': command,
                    'success': True,
                    'message': 'Emergency stop activated'
                    })
            else:
                # Handle other commands...
                result = mower.execute_command(command, params)
                emit('command_response', {
                    'command': command,
                    'success': True,
                    'result': result
                    })
        except Exception as e:
            logger.error(f"Error executing command {data.get('command')}: {e}")
            emit('command_response', {
                'command': data.get('command'),
                'success': False,
                'message': str(e)
                })

    # Background task for sending updates
    def send_updates():
        """Send periodic updates to connected clients."""
        while True:
            try:
                socketio.sleep(0.1)  # 100ms interval
                status = mower.get_status()
                safety_status = mower.get_safety_status()
                sensor_data = mower.get_sensor_data()

                socketio.emit('status_update', status)
                socketio.emit('safety_status', safety_status)
                socketio.emit('sensor_data', sensor_data)
            except Exception as e:
                logger.error(f"Error in update loop: {e}")
                socketio.sleep(1)  # Wait longer on error

    socketio.start_background_task(send_updates)

    return app, socketio


if __name__ == '__main__':
    # This is just for testing the web interface directly
    from mower.mower import Mower
    mower = Mower()
    app, socketio = create_app(mower)
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
