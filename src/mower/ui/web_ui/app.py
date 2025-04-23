"""Flask web interface for the autonomous mower."""

import os
from flask import (  # type:ignore
    Flask,
    jsonify,
    render_template,
    request,
    redirect,
    session
)
from flask_cors import CORS  # type:ignore
from flask_limiter import Limiter  # type:ignore
from flask_limiter.util import get_remote_address  # type:ignore
from flask_socketio import SocketIO, emit  # type:ignore
from flask_wtf.csrf import CSRFProtect  # type:ignore

from mower.navigation.path_planner import PatternType
from mower.utilities.logger_config import LoggerConfigInfo
from mower.ui.web_ui.auth import init_auth
from mower.ui.web_ui.permissions import init_permissions, require_permission, Permission
from mower.ui.web_ui.i18n import init_babel, get_supported_languages


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

    # Get configuration manager via global function
    config_manager = get_config_manager()
    web_ui_config = config_manager.get_config_section('web_ui')

    # Initialize CSRF protection
    csrf = CSRFProtect(app)

    # Initialize rate limiting
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=["200 per day", "50 per hour"],
        storage_uri="memory://"
    )

    # Configure CORS with more restrictive settings
    allowed_origins = os.environ.get('CORS_ALLOWED_ORIGINS', '*')
    CORS(app, resources={r"/*": {"origins": allowed_origins}})

    # Initialize Socket.IO with more restrictive CORS settings
    socketio = SocketIO(
        app, 
        cors_allowed_origins=allowed_origins,
        cookie=True
    )

    # Initialize authentication
    init_auth(app, web_ui_config)

    # Initialize permission management
    init_permissions(app, web_ui_config)

    # Initialize internationalization
    init_babel(app)

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
        google_maps_api_key = os.environ.get('GOOGLE_MAPS_API_KEY', '')
        return render_template('area.html', google_maps_api_key=google_maps_api_key)

    @app.route('/map')
    def map_view():
        """Render the map view page."""
        google_maps_api_key = os.environ.get('GOOGLE_MAPS_API_KEY', '')
        return render_template('map.html', google_maps_api_key=google_maps_api_key)

    @app.route('/diagnostics')
    def diagnostics():
        """Render the diagnostics page."""
        return render_template('diagnostics.html')

    @app.route('/settings')
    def settings():
        """Render the settings page."""
        return render_template('settings.html')

    @app.route('/wizard')
    def setup_wizard():
        """Render the setup wizard page."""
        return render_template('wizard.html')

    @app.route('/schedule')
    def schedule():
        """Render the schedule and automation page."""
        return render_template('schedule.html')

    @app.route('/system-health')
    def system_health():
        """Render the system health monitoring page."""
        return render_template('system_health.html')

    @app.route('/language/<lang_code>')
    def set_language(lang_code):
        """Set the user interface language.

        Args:
            lang_code: The language code to set (e.g., 'en', 'es', 'fr').

        Returns:
            A redirect to the previous page or the home page.
        """
        # Validate language code
        supported_langs = [lang['code'] for lang in get_supported_languages()]
        if lang_code in supported_langs:
            session['language'] = lang_code

        # Redirect to the previous page or home
        next_page = request.args.get('next') or request.referrer or '/'
        return redirect(next_page)

    @app.route('/api/languages', methods=['GET'])
    def get_languages():
        """Get the list of supported languages.

        Returns:
            A JSON response with the list of supported languages.
        """
        languages = get_supported_languages()
        current_lang = session.get('language', request.accept_languages.best_match(
            [lang['code'] for lang in languages]
        ))

        return jsonify({
            'success': True,
            'languages': languages,
            'current': current_lang
        })

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
    @limiter.limit("10 per minute")
    @require_permission(Permission.EDIT_SETTINGS)
    def save_settings():
        """Save mower settings."""
        try:
            from mower.ui.web_ui.validation import (
                validate_json_request,
                validate_pattern_type,
                validate_numeric_range
            )

            # Validate JSON request
            is_valid, error_msg, data = validate_json_request(request)
            if not is_valid:
                logger.warning(f"Invalid settings request: {error_msg}")
                return jsonify({'success': False, 'error': error_msg}), 400

            settings = data.get('settings', {})
            if not isinstance(settings, dict):
                return jsonify({'success': False, 'error': 'Settings must be a dictionary'}), 400

            mowing = settings.get('mowing', {})
            if not isinstance(mowing, dict):
                return jsonify({'success': False, 'error': 'Mowing settings must be a dictionary'}), 400

            path_planner = mower.resource_manager.get_path_planner()

            # Validate and update pattern planner settings
            if 'pattern' in mowing:
                pattern = mowing['pattern']
                is_valid, error_msg = validate_pattern_type(pattern)
                if not is_valid:
                    return jsonify({'success': False, 'error': error_msg}), 400

                path_planner.pattern_config.pattern_type = PatternType[pattern]

            if 'spacing' in mowing:
                try:
                    spacing = float(mowing['spacing'])
                    is_valid, error_msg = validate_numeric_range(spacing, 0.1, 2.0, "Spacing")
                    if not is_valid:
                        return jsonify({'success': False, 'error': error_msg}), 400

                    path_planner.pattern_config.spacing = spacing
                except ValueError:
                    return jsonify({'success': False, 'error': 'Spacing must be a number'}), 400

            if 'angle' in mowing:
                try:
                    angle = float(mowing['angle'])
                    is_valid, error_msg = validate_numeric_range(angle, 0.0, 359.0, "Angle")
                    if not is_valid:
                        return jsonify({'success': False, 'error': error_msg}), 400

                    path_planner.pattern_config.angle = angle
                except ValueError:
                    return jsonify({'success': False, 'error': 'Angle must be a number'}), 400

            if 'overlap' in mowing:
                try:
                    overlap = float(mowing['overlap'])
                    is_valid, error_msg = validate_numeric_range(overlap, 0.0, 0.5, "Overlap")
                    if not is_valid:
                        return jsonify({'success': False, 'error': error_msg}), 400

                    path_planner.pattern_config.overlap = overlap
                except ValueError:
                    return jsonify({'success': False, 'error': 'Overlap must be a number'}), 400

            # Log the successful settings update
            logger.info(f"Settings updated successfully: {mowing}")
            return jsonify({'success': True})
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/save-wizard-settings', methods=['POST'])
    @limiter.limit("10 per minute")
    def save_wizard_settings():
        """Save settings from the setup wizard."""
        try:
            from mower.ui.web_ui.validation import validate_json_request

            # Validate JSON request
            is_valid, error_msg, data = validate_json_request(request)
            if not is_valid:
                logger.warning(f"Invalid wizard settings request: {error_msg}")
                return jsonify({'success': False, 'error': error_msg}), 400

            wizard_settings = data.get('settings', {})
            if not isinstance(wizard_settings, dict):
                return jsonify({'success': False, 'error': 'Settings must be a dictionary'}), 400

            # Process area settings
            if 'area' in wizard_settings:
                area = wizard_settings['area']

                # Save boundary if provided
                if area.get('boundary'):
                    mower.save_boundary(area['boundary'])
                    logger.info(f"Saved boundary with {len(area['boundary'])} points")

                # Save home location if provided
                if area.get('home'):
                    mower.set_home_location(area['home'])
                    logger.info(f"Set home location to {area['home']}")

                # Save no-go zones if provided
                if area.get('noGoZones'):
                    mower.save_no_go_zones(area['noGoZones'])
                    logger.info(f"Saved {len(area['noGoZones'])} no-go zones")

            # Process schedule settings
            if 'schedule' in wizard_settings:
                schedule = wizard_settings['schedule']

                # Convert to the format expected by the mower
                mowing_schedule = {}
                for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
                    day_lower = day.lower()
                    if day in schedule.get('days', []):
                        # If day is selected, add the time range
                        mowing_schedule[day_lower] = [{
                            'start': schedule.get('startTime', '10:00'),
                            'end': schedule.get('endTime', '16:00')
                        }]
                    else:
                        # If day is not selected, set empty schedule
                        mowing_schedule[day_lower] = []

                # Save the schedule
                mower.save_mowing_schedule(mowing_schedule)
                logger.info(f"Saved mowing schedule: {mowing_schedule}")

            # Process mowing settings
            if 'mowing' in wizard_settings:
                mowing = wizard_settings['mowing']
                path_planner = mower.resource_manager.get_path_planner()

                # Update pattern type
                if 'pattern' in mowing:
                    try:
                        path_planner.pattern_config.pattern_type = PatternType[mowing['pattern']]
                        logger.info(f"Set mowing pattern to {mowing['pattern']}")
                    except (KeyError, ValueError) as e:
                        logger.warning(f"Invalid pattern type: {mowing['pattern']}, error: {e}")

                # Update other mowing settings
                if 'cutHeight' in mowing:
                    # Store in configuration
                    config_manager = get_config_manager()
                    config_manager.set_config_value('mowing', 'blade_height', mowing['cutHeight'])
                    logger.info(f"Set blade height to {mowing['cutHeight']}mm")

                if 'overlap' in mowing:
                    path_planner.pattern_config.overlap = mowing['overlap']
                    logger.info(f"Set path overlap to {mowing['overlap']}")

            # Process system settings
            if 'system' in wizard_settings:
                system = wizard_settings['system']
                config_manager = get_config_manager()

                # Update mower name
                if 'name' in system and system['name']:
                    config_manager.set_config_value('mower', 'name', system['name'])
                    logger.info(f"Set mower name to {system['name']}")

                # Update safety settings
                if 'obstacleDetection' in system:
                    config_manager.set_config_value('safety', 'obstacle_detection_enabled', 
                                                   system['obstacleDetection'])

                if 'rainSensor' in system:
                    config_manager.set_config_value('safety', 'rain_sensor_enabled', 
                                                   system['rainSensor'])

                if 'childLock' in system:
                    config_manager.set_config_value('safety', 'child_lock_enabled', 
                                                   system['childLock'])

                # Update notification settings
                if 'notifications' in system:
                    notifications = system['notifications']
                    config_manager.set_config_value('notifications', 'notify_start', 
                                                   notifications.get('notifyStart', True))
                    config_manager.set_config_value('notifications', 'notify_complete', 
                                                   notifications.get('notifyComplete', True))
                    config_manager.set_config_value('notifications', 'notify_errors', 
                                                   notifications.get('notifyErrors', True))

            # Log the successful wizard completion
            logger.info("Setup wizard completed successfully")
            return jsonify({'success': True})
        except Exception as e:
            logger.error(f"Failed to save wizard settings: {e}")
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
    @limiter.limit("10 per minute")
    @require_permission(Permission.EDIT_BOUNDARY)
    def save_area():
        """Save the mowing area configuration."""
        try:
            from mower.ui.web_ui.validation import (
                validate_json_request,
                validate_coordinates
            )

            # Validate JSON request
            is_valid, error_msg, data = validate_json_request(request)
            if not is_valid:
                logger.warning(f"Invalid area request: {error_msg}")
                return jsonify({'success': False, 'error': error_msg}), 400

            coordinates = data.get('coordinates')
            if not coordinates:
                return jsonify({'success': False, 'error': 'No coordinates provided'}), 400

            # Validate coordinates
            is_valid, error_msg = validate_coordinates(coordinates)
            if not is_valid:
                logger.warning(f"Invalid coordinates: {error_msg}")
                return jsonify({'success': False, 'error': error_msg}), 400

            path_planner = mower.resource_manager.get_path_planner()
            path_planner.pattern_config.boundary_points = coordinates

            # Log the successful area update
            logger.info(f"Mowing area updated with {len(coordinates)} boundary points")
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
    @require_permission(Permission.CONTROL_MOWER)
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
    @limiter.limit("10 per minute")
    @require_permission(Permission.EDIT_BOUNDARY)
    def save_boundary():
        """Save the yard boundary."""
        try:
            from mower.ui.web_ui.validation import (
                validate_json_request,
                validate_coordinates
            )

            # Validate JSON request
            is_valid, error_msg, data = validate_json_request(request)
            if not is_valid:
                logger.warning(f"Invalid boundary request: {error_msg}")
                return jsonify({'success': False, 'error': error_msg}), 400

            boundary = data.get('boundary')
            if not boundary:
                msg = 'No boundary provided'
                return jsonify({'success': False, 'error': msg}), 400

            # Validate boundary coordinates
            is_valid, error_msg = validate_coordinates(boundary)
            if not is_valid:
                logger.warning(f"Invalid boundary coordinates: {error_msg}")
                return jsonify({'success': False, 'error': error_msg}), 400

            mower.save_boundary(boundary)

            # Log the successful boundary update
            logger.info(f"Yard boundary updated with {len(boundary)} points")
            return jsonify({'success': True})
        except Exception as e:
            logger.error(f"Failed to save boundary: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    # No-Go Zones Management
    @app.route('/api/no-go-zones', methods=['POST'])
    @limiter.limit("10 per minute")
    @require_permission(Permission.EDIT_BOUNDARY)
    def save_no_go_zones():
        """Save no-go zones."""
        try:
            from mower.ui.web_ui.validation import (
                validate_json_request,
                validate_coordinates
            )

            # Validate JSON request
            is_valid, error_msg, data = validate_json_request(request)
            if not is_valid:
                logger.warning(f"Invalid no-go zones request: {error_msg}")
                return jsonify({'success': False, 'error': error_msg}), 400

            zones = data.get('zones')
            if not zones:
                msg = 'No zones provided'
                return jsonify({'success': False, 'error': msg}), 400

            if not isinstance(zones, list):
                return jsonify({'success': False, 'error': 'Zones must be a list'}), 400

            # Validate each zone's coordinates
            for i, zone in enumerate(zones):
                is_valid, error_msg = validate_coordinates(zone)
                if not is_valid:
                    logger.warning(f"Invalid coordinates in zone {i+1}: {error_msg}")
                    return jsonify({
                        'success': False, 
                        'error': f"Invalid coordinates in zone {i+1}: {error_msg}"
                    }), 400

            mower.save_no_go_zones(zones)

            # Log the successful no-go zones update
            logger.info(f"No-go zones updated: {len(zones)} zones defined")
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
    @limiter.limit("10 per minute")
    @require_permission(Permission.EDIT_SCHEDULE)
    def set_schedule():
        """Set the mowing schedule."""
        try:
            from mower.ui.web_ui.validation import (
                validate_json_request,
                validate_schedule
            )

            # Validate JSON request
            is_valid, error_msg, data = validate_json_request(request)
            if not is_valid:
                logger.warning(f"Invalid schedule request: {error_msg}")
                return jsonify({'success': False, 'error': error_msg}), 400

            schedule = data.get('schedule')
            if not schedule:
                msg = 'No schedule provided'
                return jsonify({'success': False, 'error': msg}), 400

            # Validate schedule format
            is_valid, error_msg = validate_schedule(schedule)
            if not is_valid:
                logger.warning(f"Invalid schedule format: {error_msg}")
                return jsonify({'success': False, 'error': error_msg}), 400

            mower.set_mowing_schedule(schedule)

            # Log the successful schedule update
            logger.info("Mowing schedule updated successfully")
            return jsonify({'success': True})
        except Exception as e:
            logger.error(f"Failed to set schedule: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/save_schedule', methods=['POST'])
    @limiter.limit("10 per minute")
    @require_permission(Permission.EDIT_SCHEDULE)
    def save_schedule():
        """Save the mowing schedule from the schedule page."""
        try:
            from mower.ui.web_ui.validation import validate_json_request

            # Validate JSON request
            is_valid, error_msg, data = validate_json_request(request)
            if not is_valid:
                logger.warning(f"Invalid schedule request: {error_msg}")
                return jsonify({'success': False, 'error': error_msg}), 400

            schedule_data = data.get('schedule')
            if not schedule_data:
                msg = 'No schedule data provided'
                return jsonify({'success': False, 'error': msg}), 400

            # Convert the schedule format if needed
            formatted_schedule = {}
            for day, hours in schedule_data.items():
                # Sort hours to ensure they're in order
                hours.sort()

                # Group consecutive hours into time slots
                time_slots = []
                if hours:
                    start_hour = hours[0]
                    end_hour = start_hour

                    for hour in hours[1:]:
                        if hour == end_hour + 1:
                            # Continue the current slot
                            end_hour = hour
                        else:
                            # End the current slot and start a new one
                            time_slots.append({
                                'start': f"{start_hour:02d}:00",
                                'end': f"{end_hour + 1:02d}:00"
                            })
                            start_hour = hour
                            end_hour = hour

                    # Add the last slot
                    time_slots.append({
                        'start': f"{start_hour:02d}:00",
                        'end': f"{end_hour + 1:02d}:00"
                    })

                formatted_schedule[day] = time_slots

            # Save the formatted schedule
            mower.set_mowing_schedule(formatted_schedule)

            # Log the successful schedule update
            logger.info("Mowing schedule updated successfully")
            return jsonify({'success': True})
        except Exception as e:
            logger.error(f"Failed to save schedule: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/get_automation_rules', methods=['GET'])
    def get_automation_rules():
        """Get the automation rules."""
        try:
            # Get automation rules from config or database
            config_manager = get_config_manager()
            rules = config_manager.get_config_value('automation', 'rules', [])

            return jsonify({'success': True, 'rules': rules})
        except Exception as e:
            logger.error(f"Failed to get automation rules: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/save_automation_rule', methods=['POST'])
    @limiter.limit("10 per minute")
    @require_permission(Permission.EDIT_SCHEDULE)
    def save_automation_rule():
        """Save an automation rule."""
        try:
            from mower.ui.web_ui.validation import validate_json_request

            # Validate JSON request
            is_valid, error_msg, data = validate_json_request(request)
            if not is_valid:
                logger.warning(f"Invalid rule request: {error_msg}")
                return jsonify({'success': False, 'error': error_msg}), 400

            rule = data.get('rule')
            if not rule:
                msg = 'No rule data provided'
                return jsonify({'success': False, 'error': msg}), 400

            # Validate rule format
            if 'name' not in rule:
                return jsonify({'success': False, 'error': 'Rule must have a name'}), 400

            if 'conditions' not in rule or not isinstance(rule['conditions'], list):
                return jsonify({'success': False, 'error': 'Rule must have conditions array'}), 400

            if 'actions' not in rule or not isinstance(rule['actions'], list):
                return jsonify({'success': False, 'error': 'Rule must have actions array'}), 400

            # Get existing rules
            config_manager = get_config_manager()
            rules = config_manager.get_config_value('automation', 'rules', [])

            # Check if we're updating an existing rule
            rule_index = data.get('index')
            if rule_index is not None and rule_index >= 0 and rule_index < len(rules):
                # Update existing rule
                rules[rule_index] = rule
                logger.info(f"Updated automation rule: {rule['name']}")
            else:
                # Add new rule
                rules.append(rule)
                logger.info(f"Added new automation rule: {rule['name']}")

            # Save updated rules
            config_manager.set_config_value('automation', 'rules', rules)

            return jsonify({'success': True})
        except Exception as e:
            logger.error(f"Failed to save automation rule: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/delete_automation_rule', methods=['POST'])
    @limiter.limit("10 per minute")
    @require_permission(Permission.EDIT_SCHEDULE)
    def delete_automation_rule():
        """Delete an automation rule."""
        try:
            from mower.ui.web_ui.validation import validate_json_request

            # Validate JSON request
            is_valid, error_msg, data = validate_json_request(request)
            if not is_valid:
                logger.warning(f"Invalid rule deletion request: {error_msg}")
                return jsonify({'success': False, 'error': error_msg}), 400

            rule_index = data.get('index')
            if rule_index is None:
                return jsonify({'success': False, 'error': 'No rule index provided'}), 400

            # Get existing rules
            config_manager = get_config_manager()
            rules = config_manager.get_config_value('automation', 'rules', [])

            # Check if the index is valid
            if rule_index < 0 or rule_index >= len(rules):
                return jsonify({'success': False, 'error': 'Invalid rule index'}), 400

            # Delete the rule
            deleted_rule = rules.pop(rule_index)

            # Save updated rules
            config_manager.set_config_value('automation', 'rules', rules)

            logger.info(f"Deleted automation rule: {deleted_rule.get('name', 'Unknown')}")
            return jsonify({'success': True})
        except Exception as e:
            logger.error(f"Failed to delete automation rule: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/system-health', methods=['GET'])
    def get_system_health():
        """Get system health data."""
        try:
            import psutil
            import platform
            from datetime import datetime, timedelta

            # Get CPU usage
            cpu_usage = psutil.cpu_percent(interval=0.5)

            # Get memory usage
            memory = psutil.virtual_memory()
            memory_usage = {
                'total': round(memory.total / (1024 * 1024)),  # MB
                'used': round(memory.used / (1024 * 1024)),    # MB
                'percent': memory.percent
            }

            # Get disk usage
            disk = psutil.disk_usage('/')
            disk_usage = {
                'total': round(disk.total / (1024 * 1024 * 1024), 1),  # GB
                'used': round(disk.used / (1024 * 1024 * 1024), 1),    # GB
                'percent': disk.percent
            }

            # Get CPU temperature (if available)
            cpu_temp = None
            if hasattr(psutil, 'sensors_temperatures'):
                temps = psutil.sensors_temperatures()
                if temps and 'cpu_thermal' in temps:
                    cpu_temp = temps['cpu_thermal'][0].current
                elif temps and 'coretemp' in temps:
                    cpu_temp = temps['coretemp'][0].current

            # Get system uptime
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time
            uptime_str = f"{uptime.days}d {uptime.seconds // 3600}h {(uptime.seconds // 60) % 60}m"

            # Get system info
            system_info = {
                'kernel_version': platform.release(),
                'python_version': platform.python_version(),
                'app_version': '1.0.0',  # Replace with actual version
                'hostname': platform.node()
            }

            # Get network info
            network_info = {}
            net_io = psutil.net_io_counters()
            network_info['bytes_sent'] = net_io.bytes_sent
            network_info['bytes_recv'] = net_io.bytes_recv

            # Get hardware health (simulated for now)
            # In a real implementation, this would come from actual hardware sensors
            hardware_health = {
                'motors': {
                    'left': {'temp': 35, 'status': 'good'},
                    'right': {'temp': 36, 'status': 'good'},
                    'blade': {'temp': 40, 'status': 'good'}
                },
                'sensors': {
                    'gps': {'status': '8 satellites', 'health': 'good'},
                    'imu': {'status': 'Calibrated', 'health': 'good'},
                    'camera': {'status': 'Active', 'health': 'good'}
                },
                'power': {
                    'battery': {'health': '92%', 'status': 'good'},
                    'charging': {'status': 'Normal', 'health': 'good'},
                    'consumption': {'value': '5.2 W', 'health': 'good'}
                },
                'network': {
                    'wifi': {'signal': '-67 dBm', 'health': 'good'},
                    'latency': {'value': '45 ms', 'health': 'good'}
                }
            }

            # Generate historical data (simulated for now)
            # In a real implementation, this would come from a database
            timestamps = []
            cpu_data = []
            memory_data = []
            temp_data = []

            # Generate data points for the last 24 hours
            for i in range(24):
                time_point = datetime.now() - timedelta(hours=24-i)
                timestamps.append(time_point.strftime('%H:%M'))
                cpu_data.append(max(10, min(90, cpu_usage + (i % 10) - 5)))
                memory_data.append(max(20, min(80, memory.percent + (i % 15) - 7)))
                if cpu_temp:
                    temp_data.append(max(30, min(70, cpu_temp + (i % 8) - 4)))
                else:
                    temp_data.append(40 + (i % 10))

            # Compile all data
            system_health = {
                'cpu_usage': cpu_usage,
                'memory_usage': memory_usage,
                'disk_usage': disk_usage,
                'cpu_temp': cpu_temp,
                'uptime': uptime_str,
                'system_info': system_info,
                'network_info': network_info,
                'hardware_health': hardware_health,
                'historical_data': {
                    'timestamps': timestamps,
                    'cpu': cpu_data,
                    'memory': memory_data,
                    'temperature': temp_data
                }
            }

            return jsonify({'success': True, 'data': system_health})
        except Exception as e:
            logger.error(f"Failed to get system health data: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/save-thresholds', methods=['POST'])
    @limiter.limit("10 per minute")
    @require_permission(Permission.EDIT_SETTINGS)
    def save_alert_thresholds():
        """Save alert thresholds for system monitoring."""
        try:
            from mower.ui.web_ui.validation import validate_json_request

            # Validate JSON request
            is_valid, error_msg, data = validate_json_request(request)
            if not is_valid:
                logger.warning(f"Invalid thresholds request: {error_msg}")
                return jsonify({'success': False, 'error': error_msg}), 400

            thresholds = data.get('thresholds')
            if not thresholds:
                return jsonify({'success': False, 'error': 'No thresholds provided'}), 400

            # Validate thresholds
            required_fields = ['cpu', 'memory', 'temperature', 'battery']
            for field in required_fields:
                if field not in thresholds:
                    return jsonify({'success': False, 'error': f'Missing {field} thresholds'}), 400

                if 'warning' not in thresholds[field] or 'critical' not in thresholds[field]:
                    return jsonify({'success': False, 'error': f'Missing warning or critical threshold for {field}'}), 400

            # Save thresholds to configuration
            config_manager = get_config_manager()
            config_manager.set_config_value('monitoring', 'alert_thresholds', thresholds)

            logger.info(f"Alert thresholds updated: {thresholds}")
            return jsonify({'success': True})
        except Exception as e:
            logger.error(f"Failed to save alert thresholds: {e}")
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
            # Validate data
            if not isinstance(data, dict):
                raise ValueError("Invalid data format: expected a dictionary")

            # Validate command
            if 'command' not in data:
                raise ValueError("Missing required field: command")

            command = data.get('command')
            if not isinstance(command, str):
                raise ValueError("Command must be a string")

            # Validate params
            params = data.get('params', {})
            if not isinstance(params, dict):
                raise ValueError("Parameters must be a dictionary")

            # Handle emergency stop separately
            if command == 'emergency_stop':
                mower.emergency_stop()
                emit('command_response', {
                    'command': command,
                    'success': True,
                    'message': 'Emergency stop activated'
                })
            # Handle other valid commands
            elif command in ['move', 'blade']:
                # Execute the command
                result = mower.execute_command(command, params)

                # Check if there was an error
                if 'error' in result:
                    emit('command_response', {
                        'command': command,
                        'success': False,
                        'error': result['error']
                    })
                else:
                    emit('command_response', {
                        'command': command,
                        'success': True,
                        'result': result
                    })
            else:
                # Invalid command
                emit('command_response', {
                    'command': command,
                    'success': False,
                    'error': f"Unknown command: {command}. Valid commands are: move, blade, emergency_stop"
                })
        except ValueError as e:
            # Handle validation errors
            cmd = command if 'command' in locals() else 'unknown'
            error_msg = f"Validation error for command {cmd}: {str(e)}"
            logger.error(error_msg)
            emit(
                'command_response',
                {
                    'command': cmd,
                    'success': False,
                    'error': str(e)
                }
            )
        except Exception as e:
            # Handle other errors
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
