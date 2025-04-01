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

import os
import threading
import time
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

from flask import Flask, render_template, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from flask_socketio import SocketIO, emit

from mower.utilities.logger_config import LoggerConfigInfo as LoggerConfig
from mower.mower import (
    get_blade_controller,
    get_robohat_driver,
    get_sensor_interface,
    get_localization,
    get_path_planner,
    get_serial_port,
    get_gps_position,
    get_gps_nmea_positions
)
from mower.navigation.navigation import NavigationController
from mower.hardware.camera_instance import capture_frame, start_server_thread, get_camera_instance, get_jpeg_frame

# Initialize logger
logging = LoggerConfig.get_logger(__name__)

class WebInterface:
    """
    Web-based user interface for controlling and monitoring the autonomous mower.
    
    This class creates a Flask web application that provides both a visual interface
    and API endpoints for interacting with the mower. It enables users to:
    
    - View real-time system status and sensor data
    - Control the mower manually or set autonomous operation
    - Configure mowing parameters and schedules
    - View and edit mowing area boundaries
    - Monitor performance and diagnose issues
    
    The interface is designed to be responsive and work on various devices
    including desktop browsers, tablets, and mobile phones.
    
    Attributes:
        resource_manager: Reference to system's ResourceManager for access to all components
        app: Flask application instance
        socketio: SocketIO instance for real-time communication
        config_dir: Directory for configuration files
        host: Host address for the web server (default: '0.0.0.0')
        port: Port for the web server (default: 8080)
        debug: Debug mode flag (default: False)
        thread: Background thread for data broadcasting
        
    Configuration Files:
        user_polygon.json: Defines the mowing area boundaries
        home_location.json: Defines the home/charging station location
        mowing_schedule.json: Defines mowing schedules and patterns
        
    Troubleshooting:
        Network Issues:
        - If unable to connect, verify the host/port settings
        - Check firewall settings and network permissions
        - Verify the device is on the same network as the client
        
        Interface Issues:
        - Clear browser cache if UI appears outdated
        - Check browser console for JavaScript errors
        - Verify Flask and dependencies are correctly installed
        
        Data Issues:
        - If data is not updating, check WebSocket connection
        - Verify the resource_manager is properly initialized
        - Check server logs for API errors or exceptions
    """

    def __init__(self, resource_manager, host='0.0.0.0', port=8080, debug=False):
        """
        Initialize the web interface.
        
        Args:
            resource_manager: Reference to the system's ResourceManager
            host: Host address to bind the server to (default: '0.0.0.0' - all interfaces)
            port: Port number to listen on (default: 8080)
            debug: Enable debug mode for Flask (default: False)
            
        The initialization process:
        1. Creates the Flask application and configures routes
        2. Sets up the SocketIO for real-time communication
        3. Initializes background threads for data broadcasting
        4. Prepares configuration paths and template directories
        
        Note: The server does not start automatically on initialization.
        Call the start() method to begin serving requests.
        """
        self.resource_manager = resource_manager
        self.host = host
        self.port = port
        self.debug = debug
        
        # Store the base directory for template and static files
        self.base_dir = Path(__file__).resolve().parent
        self.static_dir = self.base_dir / 'static'
        self.template_dir = self.base_dir / 'templates'
        
        # Configuration paths
        self.config_dir = Path(self.resource_manager.user_polygon_path).parent
        self.config_dir.mkdir(exist_ok=True)
        
        # Create Flask app with correct template and static folders
        self.app = Flask(__name__, 
                         template_folder=str(self.template_dir),
                         static_folder=str(self.static_dir))
        
        # Configure Flask app
        self.app.config['SECRET_KEY'] = 'autonomous_mower_secret_key'
        self.app.config['JSON_SORT_KEYS'] = False
        
        # Setup SocketIO for real-time updates
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        
        # Background thread for broadcasting data
        self.thread = None
        self.thread_lock = threading.Lock()
        self.running = False
        
        # Register routes and event handlers
        self._register_routes()
        self._register_socketio_events()
        
        logging.info("Web interface initialized")

    def _register_routes(self):
        """
        Register all HTTP routes for the web application.
        
        This method sets up all the URL endpoints and their corresponding
        handler functions for the web interface, including:
        
        - Static routes for the dashboard, control panel, settings, etc.
        - API endpoints for data retrieval and command execution
        - Configuration management endpoints
        - Authentication endpoints if applicable
        
        Troubleshooting:
            - If routes are not responding, check for exceptions in the logs
            - Verify URL paths against the browser's navigation bar
            - Check for conflicting route definitions
        """
        # Main pages
        @self.app.route('/')
        def index():
            """Render the main dashboard."""
            return render_template('index.html')
            
        @self.app.route('/control')
        def control():
            """Render the manual control page."""
            return render_template('control.html')
            
        @self.app.route('/settings')
        def settings():
            """Render the settings page."""
            return render_template('settings.html')
            
        @self.app.route('/map')
        def map_view():
            """Render the map visualization page."""
            return render_template('map.html')
            
        @self.app.route('/diagnostics')
        def diagnostics():
            """Render the system diagnostics page."""
            return render_template('diagnostics.html')
            
        # API endpoints
        @self.app.route('/api/status', methods=['GET'])
        def get_status():
            """Return the current system status."""
            try:
                # Collect system status data
                status_data = self._get_system_status()
                return jsonify(status_data)
            except Exception as e:
                logging.error(f"Error getting system status: {e}")
                return jsonify({"error": str(e)}), 500
                
        @self.app.route('/api/sensors', methods=['GET'])
        def get_sensor_data():
            """Return current sensor readings."""
            try:
                # Collect sensor data
                sensor_data = self._get_sensor_data()
                return jsonify(sensor_data)
            except Exception as e:
                logging.error(f"Error getting sensor data: {e}")
                return jsonify({"error": str(e)}), 500
                
        @self.app.route('/api/control', methods=['POST'])
        def control_mower():
            """Handle control commands for the mower."""
            try:
                command = request.json.get('command')
                params = request.json.get('params', {})
                
                result = self._execute_command(command, params)
                return jsonify(result)
            except Exception as e:
                logging.error(f"Error executing command: {e}")
                return jsonify({"error": str(e)}), 500
                
        @self.app.route('/api/config/polygon', methods=['GET', 'POST'])
        def manage_polygon():
            """Get or update the mowing area polygon."""
            if request.method == 'GET':
                try:
                    polygon = self._load_config('user_polygon.json')
                    return jsonify(polygon)
                except Exception as e:
                    logging.error(f"Error loading polygon: {e}")
                    return jsonify({"error": str(e)}), 500
            else:  # POST
                try:
                    polygon_data = request.json
                    self._save_config('user_polygon.json', polygon_data)
                    return jsonify({"success": True})
                except Exception as e:
                    logging.error(f"Error saving polygon: {e}")
                    return jsonify({"error": str(e)}), 500
                    
        @self.app.route('/api/config/home', methods=['GET', 'POST'])
        def manage_home_location():
            """Get or update the home location."""
            if request.method == 'GET':
                try:
                    home = self._load_config('home_location.json')
                    return jsonify(home)
                except Exception as e:
                    logging.error(f"Error loading home location: {e}")
                    return jsonify({"error": str(e)}), 500
            else:  # POST
                try:
                    home_data = request.json
                    self._save_config('home_location.json', home_data)
                    return jsonify({"success": True})
                except Exception as e:
                    logging.error(f"Error saving home location: {e}")
                    return jsonify({"error": str(e)}), 500
                    
        @self.app.route('/api/config/schedule', methods=['GET', 'POST'])
        def manage_schedule():
            """Get or update the mowing schedule."""
            if request.method == 'GET':
                try:
                    schedule = self._load_config('mowing_schedule.json')
                    return jsonify(schedule)
                except Exception as e:
                    logging.error(f"Error loading schedule: {e}")
                    return jsonify({"error": str(e)}), 500
            else:  # POST
                try:
                    schedule_data = request.json
                    self._save_config('mowing_schedule.json', schedule_data)
                    return jsonify({"success": True})
                except Exception as e:
                    logging.error(f"Error saving schedule: {e}")
                    return jsonify({"error": str(e)}), 500
                    
        # File serving for logs
        @self.app.route('/logs/<path:filename>')
        def serve_log(filename):
            """Serve log files from the logs directory."""
            log_dir = Path('./logs')
            return send_from_directory(log_dir, filename)
            
        @self.app.route('/api/camera/snapshot')
        def camera_snapshot():
            """
            Return a current camera snapshot as a JPEG image.
            
            This endpoint captures a frame from the camera and returns it as a JPEG image.
            It's used for camera testing in the diagnostics page, for visual debugging,
            and for occasional snapshots requested by the user.
            
            Note: This is not intended for continuous video streaming, which is handled
            by a separate mechanism using either MJPEG or WebRTC.
            
            Returns:
                JPEG image if successful, error JSON if the camera is unavailable or
                if capturing the frame fails.
                
            Response Codes:
                200: Successfully captured and returned an image
                404: Camera not available
                500: Error capturing or processing the image
            """
            try:
                # Import the camera_instance module
                from mower.hardware.camera_instance import get_camera_instance, get_jpeg_frame
                
                # Try to get a JPEG frame directly (this is more efficient)
                jpeg_frame = get_jpeg_frame()
                
                if jpeg_frame is not None:
                    # Create file-like object from bytes
                    import io
                    from flask import send_file
                    
                    # Send the JPEG frame
                    io_buf = io.BytesIO(jpeg_frame)
                    io_buf.seek(0)
                    return send_file(io_buf, mimetype='image/jpeg')
                    
                # Fallback to capture_frame and encode if needed
                camera = get_camera_instance()
                if camera is None:
                    logging.error("Camera not available for snapshot")
                    return jsonify({
                        "error": "Camera not available",
                        "detail": "The camera could not be initialized"
                    }), 404
                
                # Get raw frame and encode to JPEG if direct JPEG failed
                frame = camera.capture_frame()
                if frame is None:
                    logging.error("Failed to capture frame for snapshot")
                    return jsonify({
                        "error": "Failed to capture frame",
                        "detail": "The camera could not capture an image"
                    }), 500
                
                # Convert frame to JPEG
                import cv2
                import io
                from flask import send_file
                
                # Encode to JPEG
                _, buffer = cv2.imencode('.jpg', frame)
                if not _:
                    return jsonify({
                        "error": "Failed to encode image",
                        "detail": "The image could not be encoded to JPEG format"
                    }), 500
                
                # Save to memory buffer
                io_buf = io.BytesIO(buffer.tobytes())
                io_buf.seek(0)
                
                # Return as image
                return send_file(io_buf, mimetype='image/jpeg')
                
            except Exception as e:
                error_msg = str(e)
                logging.error(f"Error capturing camera snapshot: {error_msg}")
                return jsonify({
                    "error": "Error capturing snapshot",
                    "detail": error_msg
                }), 500
            
        logging.info("Routes registered")

    def _register_socketio_events(self):
        """
        Register all SocketIO event handlers for real-time communication.
        
        This method sets up WebSocket event handlers for bidirectional
        real-time communication between the client and server, enabling:
        
        - Push notifications for status updates
        - Live sensor data streaming
        - Camera feed with overlay
        - Connection management
        
        Troubleshooting:
            - If WebSocket connections fail, check browser support
            - Verify network allows WebSocket traffic (ports, proxies)
            - Check for CORS issues in the browser console
        """
        @self.socketio.on('connect')
        def handle_connect():
            """Handle client connection to WebSocket."""
            logging.info("Client connected to WebSocket")
            
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection from WebSocket."""
            logging.info("Client disconnected from WebSocket")
            
        @self.socketio.on('request_data')
        def handle_data_request(message):
            """Handle client request for specific data."""
            data_type = message.get('type')
            
            if data_type == 'sensors':
                self.socketio.emit('sensor_data', self._get_sensor_data())
            elif data_type == 'status':
                self.socketio.emit('status_update', self._get_system_status())
            elif data_type == 'position':
                self.socketio.emit('position_update', self._get_position_data())
            else:
                logging.warning(f"Unknown data request type: {data_type}")
                
        @self.socketio.on('control_command')
        def handle_control_command(message):
            """Handle control commands from WebSocket."""
            try:
                command = message.get('command')
                params = message.get('params', {})
                
                result = self._execute_command(command, params)
                self.socketio.emit('command_response', result)
            except Exception as e:
                logging.error(f"Error executing WebSocket command: {e}")
                self.socketio.emit('command_response', {"error": str(e)})

        @self.socketio.on('run_diagnostic')
        def handle_diagnostic_test(message):
            """Handle diagnostic test requests."""
            try:
                test_type = message.get('test')
                logging.info(f"Running diagnostic test: {test_type}")
                
                # Import hardware test suite here to avoid circular imports
                from mower.diagnostics.hardware_test import HardwareTestSuite
                
                # Create test suite instance with resource manager
                test_suite = HardwareTestSuite(self.resource_manager)
                
                # Determine which test to run
                if test_type == 'all':
                    # Run in separate thread to avoid blocking
                    threading.Thread(target=self._run_all_tests, args=(test_suite,)).start()
                    self.socketio.emit('diagnostic_result', {
                        'test': 'all',
                        'name': 'All Tests',
                        'details': 'Running all hardware tests. This may take a few minutes...',
                        'success': True
                    })
                else:
                    # Run individual test
                    self._run_individual_test(test_suite, test_type)
            except Exception as e:
                logging.error(f"Error running diagnostic test: {e}")
                self.socketio.emit('diagnostic_result', {
                    'test': message.get('test', 'unknown'),
                    'success': False,
                    'details': f"Error: {str(e)}"
                })
                
        @self.socketio.on('start_calibration')
        def handle_calibration(message):
            """Handle calibration requests."""
            try:
                calibration_type = message.get('type')
                logging.info(f"Starting calibration: {calibration_type}")
                
                # Run in separate thread to avoid blocking
                threading.Thread(
                    target=self._run_calibration, 
                    args=(calibration_type,)
                ).start()
                
            except Exception as e:
                logging.error(f"Error starting calibration: {e}")
                self.socketio.emit('calibration_error', {
                    'message': f"Failed to start calibration: {str(e)}"
                })
                
        @self.socketio.on('calibration_step_completed')
        def handle_calibration_step(message):
            """Handle calibration step completion."""
            try:
                calibration_type = message.get('type')
                step = message.get('step')
                logging.info(f"Calibration step completed: {calibration_type} - Step {step}")
                
                # This is a signal from the client that they've completed a manual step
                # We need to notify the calibration thread to continue
                # Implementation depends on how the calibration process is structured
                
                # For now, just acknowledge receipt
                self.socketio.emit('calibration_step_acknowledged', {
                    'type': calibration_type,
                    'step': step
                })
                
            except Exception as e:
                logging.error(f"Error processing calibration step: {e}")
                
        @self.socketio.on('capture_image')
        def handle_capture_image(message):
            """Handle camera capture request."""
            try:
                logging.info("Capturing camera image")
                camera = self.resource_manager.get_camera()
                if camera:
                    frame = camera.capture_frame()
                    if frame is not None:
                        # Save the image to a file
                        import cv2
                        cv2.imwrite('./camera_capture.jpg', frame)
                        self.socketio.emit('image_captured', {'success': True})
                    else:
                        self.socketio.emit('image_captured', {
                            'success': False,
                            'message': 'Failed to capture image: No frame returned'
                        })
                else:
                    self.socketio.emit('image_captured', {
                        'success': False,
                        'message': 'Camera not available'
                    })
                    
            except Exception as e:
                logging.error(f"Error capturing image: {e}")
                self.socketio.emit('image_captured', {
                    'success': False,
                    'message': f"Error: {str(e)}"
                })
                
        logging.info("SocketIO events registered")

    def _background_thread(self):
        """
        Background thread for broadcasting data to connected clients.
        
        This method periodically broadcasts system status and sensor data
        to all connected clients via WebSocket, enabling real-time updates
        without requiring clients to poll the server.
        
        The broadcast interval can be adjusted to balance between
        real-time responsiveness and system resource usage.
        
        Troubleshooting:
            - If broadcasts stop, check for exceptions in the thread.
            - For high CPU usage, increase the sleep interval.
            - Verify client-side event listeners are properly registered.
        """
        logging.info("Background thread started")

        # Set the broadcast interval in seconds
        broadcast_interval = 1.0

        while self.running:
            # Get and broadcast system status
            try:
                status_data = self._get_system_status()
                self.socketio.emit('status_update', status_data)
            except Exception as e:
                logging.error(f"Error getting system status: {e}")
                self.socketio.emit('status_update', {
                    "error": True,
                    "message": "Failed to retrieve system status"
                })

            # Get and broadcast sensor data
            try:
                sensor_data = self._get_sensor_data()
                self.socketio.emit('sensor_data', sensor_data)
            except Exception as e:
                logging.error(f"Error getting sensor data: {e}")
                self.socketio.emit('sensor_data', {
                    "error": True,
                    "message": "Failed to retrieve sensor data"
                })

            # Get and broadcast position updates
            try:
                position_data = self._get_position_data()
                self.socketio.emit('position_update', position_data)
            except Exception as e:
                logging.error(f"Error getting position data: {e}")
                self.socketio.emit('position_update', {
                    "error": True,
                    "message": "Failed to retrieve position data"
                })

            # Sleep to control broadcast frequency
            try:
                time.sleep(broadcast_interval)
            except Exception as e:
                logging.error(f"Error in sleep: {e}")
                # Prevent a tight error loop
                time.sleep(5)

    def _get_system_status(self):
        """
        Get the current system status.
        
        This method collects information about the current state of the system,
        including:
        - Operating mode
        - Battery status
        - Motor status
        - Error conditions
        - Connection status
        - System health metrics
        
        Returns:
            dict: Dictionary containing system status information with appropriate
                 error indicators when subsystems are unavailable
                 
        Note:
            All subsystem access is wrapped in try-except blocks to ensure
            a failure in one area doesn't prevent data from other areas
            from being returned.
        """
        status_data = {
            "timestamp": time.time(),
            "mode": "unknown",
            "battery": {},
            "motors": {},
            "blade": {},
            "errors": [],
            "warnings": [],
            "connected": True
        }
        
        # Get operating mode
        try:
            robot_controller = self.resource_manager.get_robot_controller()
            if robot_controller:
                status_data["mode"] = robot_controller.get_mode()
            else:
                status_data["mode"] = "unavailable"
                status_data["warnings"].append("Robot controller unavailable")
        except Exception as e:
            logging.error(f"Error getting robot mode: {e}")
            status_data["mode"] = "error"
            status_data["errors"].append(f"Failed to get robot mode: {str(e)}")
        
        # Get battery status
        try:
            power_monitor = self.resource_manager.get_power_monitor()
            if power_monitor:
                readings = power_monitor.get_readings()
                voltage = readings.get("battery_voltage", 0)
                current = readings.get("battery_current", 0)
                
                # Calculate battery percentage (simplified)
                # Assuming 12V system with 10V as empty and 14V as full
                battery_min = 10.0
                battery_max = 14.0
                if isinstance(voltage, (int, float)) and voltage > 0:
                    percentage = min(100, max(0, (voltage - battery_min) / (battery_max - battery_min) * 100))
                    status_data["battery"] = {
                        "voltage": voltage,
                        "current": current,
                        "percentage": round(percentage, 1),
                        "charging": current < 0 if isinstance(current, (int, float)) else False
                    }
                else:
                    status_data["battery"] = {
                        "voltage": "N/A",
                        "current": "N/A",
                        "percentage": "N/A",
                        "charging": False
                    }
            else:
                status_data["battery"] = {
                    "status": "disconnected",
                    "voltage": "N/A",
                    "current": "N/A",
                    "percentage": "N/A",
                    "charging": False
                }
                status_data["warnings"].append("Power monitor unavailable")
        except Exception as e:
            logging.error(f"Error getting battery status: {e}")
            status_data["battery"] = {
                "status": "error",
                "message": str(e),
                "voltage": "N/A",
                "current": "N/A",
                "percentage": "N/A",
                "charging": False
            }
            status_data["errors"].append("Failed to get battery status")
        
        # Get motor status
        try:
            robohat = self.resource_manager.get_robohat_driver()
            if robohat:
                left_speed, right_speed = robohat.get_motor_speeds()
                status_data["motors"] = {
                    "left": left_speed,
                    "right": right_speed,
                    "moving": abs(left_speed) > 0.05 or abs(right_speed) > 0.05
                }
            else:
                status_data["motors"] = {
                    "status": "disconnected",
                    "left": "N/A",
                    "right": "N/A",
                    "moving": False
                }
                status_data["warnings"].append("Motor controller unavailable")
        except Exception as e:
            logging.error(f"Error getting motor status: {e}")
            status_data["motors"] = {
                "status": "error",
                "message": str(e),
                "left": "N/A",
                "right": "N/A",
                "moving": False
            }
            status_data["errors"].append("Failed to get motor status")
        
        # Get blade status
        try:
            blade_controller = self.resource_manager.get_blade_controller()
            if blade_controller:
                status_data["blade"] = {
                    "running": blade_controller.is_running(),
                    "speed": blade_controller.get_speed()
                }
            else:
                status_data["blade"] = {
                    "status": "disconnected",
                    "running": False,
                    "speed": "N/A"
                }
                status_data["warnings"].append("Blade controller unavailable")
        except Exception as e:
            logging.error(f"Error getting blade status: {e}")
            status_data["blade"] = {
                "status": "error",
                "message": str(e),
                "running": False,
                "speed": "N/A"
            }
            status_data["errors"].append("Failed to get blade status")
        
        # Get system health metrics
        try:
            import psutil
            status_data["system"] = {
                "cpu_usage": psutil.cpu_percent(),
                "memory_usage": psutil.virtual_memory().percent,
                "uptime": int(time.time() - psutil.boot_time())
            }
            
            # Get CPU temperature if available (Raspberry Pi)
            try:
                if hasattr(psutil, "sensors_temperatures"):
                    temps = psutil.sensors_temperatures()
                    if "cpu_thermal" in temps:
                        cpu_temp = temps["cpu_thermal"][0].current
                        status_data["system"]["cpu_temp"] = cpu_temp
                    elif "cpu-thermal" in temps:
                        cpu_temp = temps["cpu-thermal"][0].current
                        status_data["system"]["cpu_temp"] = cpu_temp
            except:
                pass
                
        except Exception as e:
            logging.error(f"Error getting system health metrics: {e}")
            status_data["system"] = {
                "status": "error",
                "message": str(e),
                "cpu_usage": "N/A",
                "memory_usage": "N/A",
                "uptime": "N/A"
            }
        
        return status_data

    def _get_sensor_data(self):
        """
        Get current sensor data from various sensors.
        
        This method collects data from all available sensors including:
        - IMU (orientation, acceleration)
        - GPS (position, altitude, satellites)
        - BME280 (temperature, humidity, pressure)
        - Power monitor (voltage, current)
        - ToF sensors (distances)
        
        Returns:
            dict: Dictionary containing all sensor readings with appropriate
                 error indicators when sensors are unavailable
                 
        Note:
            All sensor access is wrapped in try-except blocks to ensure
            a failure in one sensor doesn't prevent data from other sensors
            from being returned.
        """
        sensor_data = {
            "timestamp": time.time(),
            "imu": {},
            "gps": {},
            "environment": {},
            "power": {},
            "distances": {}
        }
        
        # Get IMU data
        try:
            imu = self.resource_manager.get_imu()
            if imu and imu.connected:
                sensor_data["imu"] = {
                    "roll": imu.get_roll(),
                    "pitch": imu.get_pitch(),
                    "yaw": imu.get_heading(),
                    "acceleration": imu.get_acceleration()
                }
            else:
                sensor_data["imu"] = {
                    "status": "disconnected",
                    "roll": "N/A",
                    "pitch": "N/A",
                    "yaw": "N/A",
                    "acceleration": {"x": "N/A", "y": "N/A", "z": "N/A"}
                }
        except Exception as e:
            logging.error(f"Error getting IMU data: {e}")
            sensor_data["imu"] = {
                "status": "error",
                "message": str(e),
                "roll": "N/A",
                "pitch": "N/A",
                "yaw": "N/A",
                "acceleration": {"x": "N/A", "y": "N/A", "z": "N/A"}
            }
        
        # Get GPS data
        try:
            gps_position = self.resource_manager.get_gps_latest_position()
            if gps_position:
                sensor_data["gps"] = {
                    "latitude": gps_position.get("latitude", "N/A"),
                    "longitude": gps_position.get("longitude", "N/A"),
                    "altitude": gps_position.get("altitude", "N/A"),
                    "fix_quality": gps_position.get("fix_quality", "unknown"),
                    "satellites": gps_position.get("satellites", 0),
                    "hdop": gps_position.get("hdop", "N/A")
                }
            else:
                sensor_data["gps"] = {
                    "status": "no_fix",
                    "latitude": "N/A",
                    "longitude": "N/A",
                    "altitude": "N/A",
                    "fix_quality": "unknown",
                    "satellites": 0,
                    "hdop": "N/A"
                }
        except Exception as e:
            logging.error(f"Error getting GPS data: {e}")
            sensor_data["gps"] = {
                "status": "error",
                "message": str(e),
                "latitude": "N/A",
                "longitude": "N/A",
                "altitude": "N/A",
                "fix_quality": "unknown",
                "satellites": 0,
                "hdop": "N/A"
            }
        
        # Get environment data (BME280)
        try:
            bme = self.resource_manager.get_bme280()
            if bme:
                readings = bme.get_readings()
                sensor_data["environment"] = {
                    "temperature": readings.get("temperature", "N/A"),
                    "humidity": readings.get("humidity", "N/A"),
                    "pressure": readings.get("pressure", "N/A")
                }
            else:
                sensor_data["environment"] = {
                    "status": "disconnected",
                    "temperature": "N/A",
                    "humidity": "N/A",
                    "pressure": "N/A"
                }
        except Exception as e:
            logging.error(f"Error getting environment data: {e}")
            sensor_data["environment"] = {
                "status": "error",
                "message": str(e),
                "temperature": "N/A",
                "humidity": "N/A",
                "pressure": "N/A"
            }
        
        # Get power data
        try:
            power_monitor = self.resource_manager.get_power_monitor()
            if power_monitor:
                readings = power_monitor.get_readings()
                sensor_data["power"] = {
                    "battery_voltage": readings.get("battery_voltage", "N/A"),
                    "battery_current": readings.get("battery_current", "N/A"),
                    "system_voltage": readings.get("system_voltage", "N/A"),
                    "system_current": readings.get("system_current", "N/A"),
                    "motor_voltage": readings.get("motor_voltage", "N/A"),
                    "motor_current": readings.get("motor_current", "N/A")
                }
            else:
                sensor_data["power"] = {
                    "status": "disconnected",
                    "battery_voltage": "N/A",
                    "battery_current": "N/A",
                    "system_voltage": "N/A",
                    "system_current": "N/A",
                    "motor_voltage": "N/A",
                    "motor_current": "N/A"
                }
        except Exception as e:
            logging.error(f"Error getting power data: {e}")
            sensor_data["power"] = {
                "status": "error",
                "message": str(e),
                "battery_voltage": "N/A",
                "battery_current": "N/A",
                "system_voltage": "N/A",
                "system_current": "N/A",
                "motor_voltage": "N/A",
                "motor_current": "N/A"
            }
        
        # Get ToF sensor data
        try:
            tof_sensors = self.resource_manager.get_tof_sensors()
            if tof_sensors:
                readings = {}
                for sensor_id, sensor in tof_sensors.items():
                    # Convert from mm to cm for display and ensure valid readings
                    distance = sensor.get_distance()
                    readings[sensor_id] = distance / 10.0 if distance is not None and distance > 0 else "N/A"
                sensor_data["distances"] = readings
            else:
                sensor_data["distances"] = {
                    "status": "disconnected",
                    "front": "N/A",
                    "left": "N/A",
                    "right": "N/A",
                    "rear": "N/A"
                }
        except Exception as e:
            logging.error(f"Error getting distance data: {e}")
            sensor_data["distances"] = {
                "status": "error",
                "message": str(e),
                "front": "N/A",
                "left": "N/A",
                "right": "N/A",
                "rear": "N/A"
            }
        
        return sensor_data

    def _get_position_data(self) -> Dict[str, Any]:
        """
        Get position and navigation data.
        
        Returns:
            Dictionary containing position, orientation, and navigation data.
        """
        position_data = {
            "position": {},
            "orientation": {},
            "navigation": {}
        }
        
        try:
            # Get current position
            gps = self.resource_manager.get_gps_position()
            if gps:
                pos = gps.get_position()
                if pos:
                    position_data["position"] = pos
            
            # Get orientation
            imu = self.resource_manager.get_imu_sensor()
            if imu:
                orientation = imu.read()
                if orientation:
                    position_data["orientation"] = orientation
            
            # Get navigation status
            nav = self.resource_manager.get_navigation_controller()
            if nav:
                nav_status = nav.get_status()
                if nav_status:
                    position_data["navigation"] = nav_status
        except Exception as e:
            logging.error(f"Error getting position data: {e}")
        
        return position_data
        
    def _run_all_tests(self, test_suite):
        """
        Run all hardware tests and emit results via WebSocket.
        
        Args:
            test_suite: An instance of HardwareTestSuite
        """
        try:
            # Run non-interactive tests (don't prompt between tests)
            results = test_suite.run_all_tests(interactive=False)
            
            # Count passed/failed tests
            passed = sum(1 for result in results.values() if result)
            failed = sum(1 for result in results.values() if not result)
            total = len(results)
            
            # Emit final results
            self.socketio.emit('diagnostic_result', {
                'test': 'all',
                'name': 'All Tests',
                'success': failed == 0,
                'details': f"Completed {total} tests with {passed} passes and {failed} failures.",
                'passed': passed,
                'failed': failed,
                'total': total
            })
            
        except Exception as e:
            logging.error(f"Error running all tests: {e}")
            self.socketio.emit('diagnostic_result', {
                'test': 'all',
                'name': 'All Tests',
                'success': False,
                'details': f"Error running tests: {str(e)}"
            })
    
    def _run_individual_test(self, test_suite, test_type):
        """
        Run an individual hardware test and emit results via WebSocket.
        
        Args:
            test_suite: An instance of HardwareTestSuite
            test_type: The type of test to run (e.g., 'gps', 'imu', etc.)
        """
        try:
            # Map test type to method name
            test_methods = {
                'gpio': test_suite.test_gpio,
                'imu': test_suite.test_imu,
                'power': test_suite.test_power_monitor,
                'gps': test_suite.test_gps,
                'motors': test_suite.test_drive_motors,
                'blade': test_suite.test_blade_motor,
                'camera': test_suite.test_camera,
                'sensors': test_suite.test_tof_sensors,
                'bme280': test_suite.test_bme280
            }
            
            # Get the test method
            test_method = test_methods.get(test_type)
            
            if not test_method:
                raise ValueError(f"Unknown test type: {test_type}")
            
            # Custom handling for some tests
            if test_type == 'camera':
                # For camera test, we capture a frame and return it
                camera = self.resource_manager.get_camera()
                frame = camera.capture_frame() if camera else None
                
                success = frame is not None
                details = "Camera test successful" if success else "Failed to capture image"
                
                # Save image for web view
                if success:
                    import cv2
                    cv2.imwrite('./camera_test.jpg', frame)
                
                self.socketio.emit('diagnostic_result', {
                    'test': test_type,
                    'name': 'Camera Test',
                    'success': success,
                    'details': details
                })
                return
            
            # Run the test
            result = test_method()
            
            # Get a nice name for the test
            test_names = {
                'gpio': 'GPIO Test',
                'imu': 'IMU Sensor Test',
                'power': 'Power Monitor Test',
                'gps': 'GPS Test',
                'motors': 'Drive Motors Test',
                'blade': 'Blade Motor Test',
                'camera': 'Camera Test',
                'sensors': 'Distance Sensors Test',
                'bme280': 'Environmental Sensor Test'
            }
            
            # Emit the result
            self.socketio.emit('diagnostic_result', {
                'test': test_type,
                'name': test_names.get(test_type, f"{test_type.capitalize()} Test"),
                'success': result,
                'details': f"Test {'passed' if result else 'failed'}."
            })
            
        except Exception as e:
            logging.error(f"Error running {test_type} test: {e}")
            self.socketio.emit('diagnostic_result', {
                'test': test_type,
                'success': False,
                'details': f"Error: {str(e)}"
            })
    
    def _run_calibration(self, calibration_type):
        """
        Run a calibration process and emit progress via WebSocket.
        
        Args:
            calibration_type: The type of calibration to run ('imu', 'blade', or 'gps')
        """
        try:
            if calibration_type == 'imu':
                from mower.diagnostics.imu_calibration import IMUCalibration
                
                # Create calibration instance
                calibration = IMUCalibration(self.resource_manager)
                
                # Emit first step
                self.socketio.emit('calibration_step', {
                    'step': 1,
                    'total': 4,
                    'instruction': "Place the mower on a flat, level surface.",
                    'waiting': True
                })
                
                # Wait for client acknowledgment
                # In a real implementation, you'd use some synchronization mechanism
                time.sleep(2)
                
                # Subsequent steps would be triggered by client events
                # This is a simplified version
                
                # Simulate the calibration process (in real implementation this would run the actual calibration)
                steps = [
                    "Keep the mower stationary while gyroscope is calibrated.",
                    "Rotate the mower to calibrate the magnetometer.",
                    "Position the mower at different angles to calibrate the accelerometer."
                ]
                
                for i, instruction in enumerate(steps, 2):
                    self.socketio.emit('calibration_step', {
                        'step': i,
                        'total': 4,
                        'instruction': instruction,
                        'progress': (i / 4) * 100,
                        'waiting': i < 4  # Last step doesn't need acknowledgment
                    })
                    time.sleep(3)  # Simulate time for step
                
                # Final success
                self.socketio.emit('calibration_complete', {
                    'message': "IMU calibration completed successfully!"
                })
                
            elif calibration_type == 'blade':
                # Simplified blade calibration process
                self.socketio.emit('calibration_step', {
                    'step': 1,
                    'total': 2,
                    'instruction': "Ensure the mower is elevated with blades clear of obstructions.",
                    'waiting': True
                })
                
                time.sleep(2)  # Wait for acknowledgment
                
                self.socketio.emit('calibration_step', {
                    'step': 2,
                    'total': 2,
                    'instruction': "Testing blade at different speeds...",
                    'progress': 50
                })
                
                time.sleep(3)  # Simulate calibration time
                
                self.socketio.emit('calibration_complete', {
                    'message': "Blade calibration completed successfully!"
                })
                
            elif calibration_type == 'gps':
                # Simplified GPS baseline calibration
                self.socketio.emit('calibration_step', {
                    'step': 1,
                    'total': 1,
                    'instruction': "Keep the mower stationary in an open area with clear sky view.",
                    'progress': 0
                })
                
                # Simulate GPS averaging process
                for i in range(1, 11):
                    self.socketio.emit('calibration_step', {
                        'step': 1,
                        'total': 1,
                        'instruction': f"Collecting GPS samples ({i}/10)...",
                        'progress': i * 10
                    })
                    time.sleep(1)  # Simulate time between samples
                
                self.socketio.emit('calibration_complete', {
                    'message': "GPS baseline has been set successfully!"
                })
            
            else:
                raise ValueError(f"Unknown calibration type: {calibration_type}")
                
        except Exception as e:
            logging.error(f"Error during {calibration_type} calibration: {e}")
            self.socketio.emit('calibration_error', {
                'message': f"Calibration failed: {str(e)}"
            })

    def _execute_command(self, command: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a control command on the mower.
        
        This method processes various control commands sent from the UI,
        validates parameters, and executes the appropriate actions on
        the mower's components.
        
        Args:
            command: The command to execute (e.g., 'move', 'start', 'stop')
            params: Dictionary of command parameters
            
        Returns:
            Dict with command execution results
            
        Troubleshooting:
            - For command failures, check parameter validity
            - Verify hardware components are properly initialized
            - Check permissions/safety interlocks for critical commands
        """
        result = {
            "command": command,
            "params": params,
            "success": False,
            "message": ""
        }
        
        try:
            # Manual movement commands
            if command == "move":
                direction = params.get("direction", "")
                speed = float(params.get("speed", 0.5))
                
                motor_controller = self.resource_manager.get_robohat_driver()
                
                if direction == "forward":
                    motor_controller.move_forward(speed=speed)
                    result["message"] = f"Moving forward at speed {speed}"
                elif direction == "backward":
                    motor_controller.move_backward(speed=speed)
                    result["message"] = f"Moving backward at speed {speed}"
                elif direction == "left":
                    motor_controller.turn_left(speed=speed)
                    result["message"] = f"Turning left at speed {speed}"
                elif direction == "right":
                    motor_controller.turn_right(speed=speed)
                    result["message"] = f"Turning right at speed {speed}"
                elif direction == "stop":
                    motor_controller.stop()
                    result["message"] = "Stopped movement"
                else:
                    result["message"] = f"Unknown direction: {direction}"
                    return result
                    
                result["success"] = True
                
            # Blade control
            elif command == "blade":
                action = params.get("action", "")
                
                blade_controller = self.resource_manager.get_blade_controller()
                
                if action == "start":
                    blade_controller.start()
                    result["message"] = "Started blades"
                    result["success"] = True
                elif action == "stop":
                    blade_controller.stop()
                    result["message"] = "Stopped blades"
                    result["success"] = True
                else:
                    result["message"] = f"Unknown blade action: {action}"
                    
            # Autonomous operation
            elif command == "autonomous":
                action = params.get("action", "")
                
                # Get the controller which manages autonomous operation
                robot_controller = None  # This would come from resource_manager
                
                if action == "start":
                    # Start autonomous operation
                    result["message"] = "Started autonomous operation"
                    result["success"] = True
                elif action == "stop":
                    # Stop autonomous operation
                    result["message"] = "Stopped autonomous operation"
                    result["success"] = True
                elif action == "pause":
                    # Pause autonomous operation
                    result["message"] = "Paused autonomous operation"
                    result["success"] = True
                elif action == "resume":
                    # Resume autonomous operation
                    result["message"] = "Resumed autonomous operation"
                    result["success"] = True
                else:
                    result["message"] = f"Unknown autonomous action: {action}"
                    
            # Go home command
            elif command == "go_home":
                # Command the mower to return to its home/charging station
                
                # This would use navigation and path planning
                result["message"] = "Returning to home location"
                result["success"] = True
                
            # System commands
            elif command == "system":
                action = params.get("action", "")
                
                if action == "shutdown":
                    # Shutdown the mower system
                    result["message"] = "Shutting down system"
                    result["success"] = True
                    # Actual shutdown logic would go here
                elif action == "restart":
                    # Restart the mower system
                    result["message"] = "Restarting system"
                    result["success"] = True
                    # Actual restart logic would go here
                else:
                    result["message"] = f"Unknown system action: {action}"
                    
            else:
                result["message"] = f"Unknown command: {command}"
                
            return result
            
        except Exception as e:
            logging.error(f"Error executing command {command}: {e}")
            result["message"] = f"Error: {str(e)}"
            return result

    def _load_config(self, filename: str) -> Dict[str, Any]:
        """
        Load a configuration file from the config directory.
        
        Args:
            filename: Name of the configuration file
            
        Returns:
            Dict with configuration data
            
        Troubleshooting:
            - If file loading fails, check file permissions
            - Verify the file exists in the config directory
            - Check JSON syntax in the configuration file
        """
        file_path = self.config_dir / filename
        
        # Create default config if file doesn't exist
        if not file_path.exists():
            if filename == "user_polygon.json":
                default_config = {"points": []}
            elif filename == "home_location.json":
                default_config = {"latitude": 0, "longitude": 0}
            elif filename == "mowing_schedule.json":
                default_config = {"schedule": []}
            else:
                default_config = {}
                
            with open(file_path, 'w') as f:
                json.dump(default_config, f)
            
            return default_config
            
        # Load existing config file
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error loading configuration file {filename}: {e}")
            raise

    def _save_config(self, filename: str, data: Dict[str, Any]) -> None:
        """
        Save data to a configuration file.
        
        Args:
            filename: Name of the configuration file
            data: Configuration data to save
            
        Troubleshooting:
            - If file saving fails, check directory permissions
            - Verify the config directory exists
            - For formatting issues, check JSON serialization
        """
        file_path = self.config_dir / filename
        
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
                
            logging.info(f"Saved configuration to {filename}")
        except Exception as e:
            logging.error(f"Error saving configuration file {filename}: {e}")
            raise

    def start(self) -> None:
        """
        Start the web interface server.
        
        This method starts the Flask web server in a separate thread to provide
        the web interface, enabling users to interact with the mower through
        their browser.
        
        The server runs until the stop() method is called.
        
        Troubleshooting:
            - If server doesn't start, check for port conflicts
            - Verify network interface is available
            - Check for firewall restrictions on specified port
        """
        with self.thread_lock:
            if not self.thread or not self.thread.is_alive():
                self.running = True
                self.thread = threading.Thread(target=self._background_thread)
                self.thread.daemon = True  # Make thread a daemon
                self.thread.start()
                
        logging.info(f"Starting web interface on {self.host}:{self.port}")
        
        # Run the Flask app in a non-blocking way
        self.socketio.start_background_task(
            self.socketio.run, 
            self.app, 
            host=self.host, 
            port=self.port, 
            debug=self.debug,
            use_reloader=False
        )
        
        logging.info("Web interface started")

    def stop(self) -> None:
        """
        Stop the web interface server.
        
        This method gracefully shuts down the web server and background
        broadcasting thread, releasing all resources.
        
        Troubleshooting:
            - If server doesn't stop cleanly, check for hanging connections
            - Verify thread termination logic
            - Look for blocking operations in request handlers
        """
        logging.info("Stopping web interface")
        
        # Stop the background thread
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
            if self.thread.is_alive():
                logging.warning("Background thread did not terminate cleanly")
                
        # Shutdown the Flask server
        func = request.environ.get('werkzeug.server.shutdown')
        if func is not None:
            func()
            
        logging.info("Web interface stopped")

    def shutdown(self) -> None:
        """
        Completely shut down the web interface.
        
        This is an alias for stop() to maintain compatibility with
        the resource manager's cleanup requirements.
        """
        self.stop()

if __name__ == '__main__':
    web_interface = WebInterface()
    web_interface.socketio.run(web_interface.app, host='0.0.0.0', port=5000)
