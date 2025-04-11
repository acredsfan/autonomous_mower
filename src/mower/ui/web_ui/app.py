"""Flask web interface for the autonomous mower."""

from flask import (
    Flask,
    jsonify,
    render_template,
    request
)
from flask_cors import CORS
from flask_socketio import SocketIO, emit

from mower.navigation.path_planner import PatternType
from mower.utilities.logger_config import LoggerConfigInfo


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

    @app.route('/area')
    def area():
        """Render the area configuration page."""
        return render_template('area.html')

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

    @app.route('/api/get-settings', methods=['GET'])
    def get_settings():
        """Get current mower settings."""
        try:
            path_planner = mower.resource_manager.get_path_planner()
            settings = {
                'mowing': {
                    'pattern': path_planner.pattern_config.pattern_type.name,
                    'spacing': path_planner.pattern_config.spacing,
                    'angle': path_planner.pattern_config.angle,
                    'overlap': path_planner.pattern_config.overlap
                }
            }
            return jsonify({'success': True, 'data': settings})
        except Exception as e:
            logger.error(f"Failed to get settings: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/save-settings', methods=['POST'])
    def save_settings():
        """Save mower settings."""
        try:
            data = request.get_json()
            settings = data.get('settings', {})
            mowing = settings.get('mowing', {})
            
            path_planner = mower.resource_manager.get_path_planner()
            
            # Update pattern planner settings
            if 'pattern' in mowing:
                path_planner.pattern_config.pattern_type = (
                    PatternType[mowing['pattern']]
                )
            if 'spacing' in mowing:
                path_planner.pattern_config.spacing = float(mowing['spacing'])
            if 'angle' in mowing:
                path_planner.pattern_config.angle = float(mowing['angle'])
            if 'overlap' in mowing:
                path_planner.pattern_config.overlap = float(mowing['overlap'])
            
            return jsonify({'success': True})
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/get-area', methods=['GET'])
    def get_area():
        """Get the current mowing area configuration."""
        try:
            path_planner = mower.resource_manager.get_path_planner()
            area_data = {
                'boundary_points': path_planner.pattern_config.boundary_points
            }
            return jsonify({'success': True, 'data': area_data})
        except Exception as e:
            logger.error(f"Failed to get mowing area: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/save-area', methods=['POST'])
    def save_area():
        """Save the mowing area configuration."""
        try:
            data = request.get_json()
            coordinates = data.get('coordinates')
            if not coordinates:
                return jsonify({'success': False,
                               'error': 'No coordinates provided'}), 400

            path_planner = mower.resource_manager.get_path_planner()
            path_planner.pattern_config.boundary_points = coordinates
            return jsonify({'success': True})
        except Exception as e:
            logger.error(f"Failed to save mowing area: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/get-path', methods=['GET'])
    def get_current_path():
        """Get the current planned path."""
        try:
            path_planner = mower.resource_manager.get_path_planner()
            path = path_planner.current_path
            return jsonify({'success': True, 'path': path})
        except Exception as e:
            logger.error(f"Failed to get path: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/home', methods=['GET'])
    def get_home():
        """Get the home location."""
        try:
            home = mower.get_home_location()
            return jsonify({'success': True, 'location': home})
        except Exception as e:
            logger.error(f"Failed to get home location: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/home', methods=['POST'])
    def set_home():
        """Set the home location."""
        try:
            data = request.get_json()
            location = data.get('location')
            if not location:
                msg = 'No location provided'
                return jsonify({'success': False, 'error': msg}), 400
            mower.set_home_location(location)
            return jsonify({'success': True})
        except Exception as e:
            logger.error(f"Failed to set home: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/mower/status', methods=['GET'])
    def get_mower_status():
        """Get the current status of the mower."""
        try:
            status = {
                'mode': mower.get_mode(),
                'battery': mower.get_battery_level()
            }
            return jsonify(status)
        except Exception as e:
            error_msg = 'Failed to get mower status: {}'.format(str(e))
            logger.error(error_msg)
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

    # Boundary Management
    @app.route('/api/boundary', methods=['GET'])
    def get_boundary():
        """Get the yard boundary and no-go zones."""
        try:
            boundary = mower.get_boundary()
            no_go_zones = mower.get_no_go_zones()
            return jsonify({
                'success': True,
                'boundary': boundary,
                'no_go_zones': no_go_zones
            })
        except Exception as e:
            logger.error("Failed to get boundary: {}".format(e))
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/boundary', methods=['POST'])
    def save_boundary():
        """Save the yard boundary."""
        try:
            data = request.get_json()
            boundary = data.get('boundary')
            if not boundary:
                msg = 'No boundary provided'
                return jsonify({'success': False, 'error': msg}), 400
            mower.save_boundary(boundary)
            return jsonify({'success': True})
        except Exception as e:
            logger.error(f"Failed to save boundary: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    # No-Go Zones Management
    @app.route('/api/no-go-zones', methods=['POST'])
    def save_no_go_zones():
        """Save no-go zones."""
        try:
            data = request.get_json()
            zones = data.get('zones')
            if not zones:
                msg = 'No zones provided'
                return jsonify({'success': False, 'error': msg}), 400
            mower.save_no_go_zones(zones)
            return jsonify({'success': True})
        except Exception as e:
            logger.error(f"Failed to save no-go zones: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    # Schedule Management
    @app.route('/api/schedule', methods=['GET'])
    def get_schedule():
        """Get the mowing schedule."""
        try:
            schedule = mower.get_mowing_schedule()
            return jsonify({'success': True, 'schedule': schedule})
        except Exception as e:
            logger.error(f"Failed to get schedule: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/schedule', methods=['POST'])
    def set_schedule():
        """Set the mowing schedule."""
        try:
            data = request.get_json()
            schedule = data.get('schedule')
            if not schedule:
                msg = 'No schedule provided'
                return jsonify({'success': False, 'error': msg}), 400
            mower.set_mowing_schedule(schedule)
            return jsonify({'success': True})
        except Exception as e:
            logger.error(f"Failed to set schedule: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    # WebSocket event handlers
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection."""
        logger.info("Client connected")
        emit('status_update', mower.get_status())
        emit('path_update', mower.get_current_path())

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
            # Handle error case
            cmd = command if 'command' in locals() else 'unknown'
            error_parts = [
                "Error handling command",
                cmd,
                str(e)
            ]
            error_msg = " - ".join(error_parts)
            logger.error(error_msg)
            emit(
                'command_response',
                {
                    'command': cmd,
                    'success': False,
                    'error': str(e)
                }
            )

    @socketio.on('request_path_update')
    def handle_path_update():
        """Send current path to client."""
        try:
            path_planner = mower.resource_manager.get_path_planner()
            path = path_planner.current_path
            emit('path_update', path)
        except Exception as e:
            logger.error(f"Error sending path update: {e}")

    @socketio.on('error')
    def handle_error(error_data):
        """Handle error events from the client."""
        error_type = error_data.get('type')
        error_msg = error_data.get('message')
        logger.error(
            'Error received from client - Type: {}, Message: {}'.format(
                error_type, error_msg
            )
        )

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
