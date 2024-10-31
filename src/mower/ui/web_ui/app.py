import datetime
import json
import os
import threading
import time
from typing import Dict, Any, Tuple

import paho.mqtt.client as mqtt
import utm
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from pyngrok import ngrok

from mower.utilities.logger_config import (
    LoggerConfigInfo as LoggerConfig
)
from mower.hardware.blade_controller import (
    BladeController
)
from mower.hardware.camera_instance import (
    capture_frame,
    start_server_thread
)
from mower.hardware.robohat import RoboHATDriver
from mower.hardware.sensor_interface import (
    get_sensor_interface,
    EnhancedSensorInterface,
    SafetyMonitor
)
from mower.hardware.serial_port import SerialPort
from mower.navigation.gps import GpsLatestPosition
from mower.navigation.gps import GpsPosition
from mower.navigation.localization import Localization
from mower.navigation.navigation import NavigationController
from mower.navigation.path_planning import PathPlanner
from mower.robot import mow_yard
from src.mower.navigation.gps import GpsNmeaPositions


# Initialize logging
logging = LoggerConfig.get_logger(__name__)


class WebInterface:
    """Main web interface handler for the autonomous mower."""

    def __init__(self):
        """Initialize the web interface and all required components."""
        self._initialize_flask()
        self._load_environment_variables()
        self._initialize_components()
        self._initialize_mqtt()
        self._setup_routes()

    def _initialize_flask(self):
        """Initialize Flask application and extensions."""
        self.app = Flask(
            __name__,
            template_folder=(
                '/home/pi/autonomous_mower/user_interface/web_interface/'
                'templates'
            )
        )
        self.socketio = SocketIO(
            self.app,
            cors_allowed_origins="*",
            async_mode='threading'
        )
        CORS(self.app)

    def _load_environment_variables(self):
        """Load and set environment variables."""
        project_root = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
        dotenv_path = os.path.join(project_root, '.env')
        load_dotenv(dotenv_path)

        self.use_remote_planning = (
            os.getenv("USE_REMOTE_PATH_PLANNING", "False").lower() == "true"
        )
        self.use_ngrok = os.getenv("USE_NGROK", "False").lower() == "true"

        # MQTT configuration
        self.mqtt_config = {
            'broker': self._get_ip_address(),
            'port': int(os.getenv("MQTT_PORT", 1883)),
            'client_id': os.getenv("CLIENT_ID", "mower"),
            'topics': {
                'path': 'mower/path',
                'sensor': 'mower/sensor_data',
                'command': 'mower/commands'
            }
        }

    def _initialize_components(self):
        """Initialize hardware and software components."""
        try:
            self._init_serial_and_gps()
            self._init_controllers()
            self._init_sensors()
            self._init_camera()

            self.path_data = {"path": []}
            self.mowing_status = "Not mowing"
            self.next_scheduled_mow = self._calculate_next_scheduled_mow()

        except Exception as e:
            logging.error(f"Component initialization error: {e}")
            raise

    def _init_serial_and_gps(self):
        """Initialize serial communication and GPS components."""
        serial_config = {
            'port': os.getenv("GPS_SERIAL_PORT", "/dev/ttyACM0"),
            'baudrate': int(os.getenv("GPS_BAUD_RATE", "9600")),
            'timeout': float(os.getenv("GPS_SERIAL_TIMEOUT", "1"))
        }

        self.serial_port = SerialPort(**serial_config)
        self.gps_position = GpsPosition(
            serial_port=self.serial_port, debug=True
        )
        self.gps_position.start()
        self.position_reader = GpsNmeaPositions(
            gps_position_instance=self.gps_position,
            debug=True
        )

    def _init_controllers(self):
        """Initialize various controller components."""
        self.blade_controller = BladeController()
        self.localization = Localization()
        self.path_planning = PathPlanner(self.localization)
        self.robohat_driver = RoboHATDriver()

        # Initialize sensor interface
        self.sensor_interface = get_sensor_interface()
        self.safety_monitor = SafetyMonitor(self.sensor_interface)

        self.navigation_controller = NavigationController(
            self.position_reader,
            self.robohat_driver,
            self.sensor_interface
        )

    def _init_sensors(self):
        """Initialize and start sensor monitoring."""
        self.sensor_interface = EnhancedSensorInterface()
        self.safety_monitor = SafetyMonitor(self.sensor_interface)

        # Start sensor monitoring thread
        self.sensor_thread = threading.Thread(
            target=self._monitor_sensors,
            daemon=True
        )
        self.sensor_thread.start()

    def _init_camera(self):
        """Initialize camera components."""
        try:
            start_server_thread()
            self.camera_enabled = True
            self.streaming_fps = int(os.getenv('STREAMING_FPS', 15))
            self.stream_active = False
            self.active_streams = set()

            # Start camera processing
            self.camera_thread = threading.Thread(
                target=self._process_camera,
                daemon=True
            )
            self.camera_thread.start()
            logging.info("Camera system initialized successfully")

        except Exception as e:
            logging.error(f"Camera initialization error: {e}")
            self.camera_enabled = False

    def _process_camera(self):
        """Process camera frames in background thread."""
        while True:
            try:
                if self.active_streams:
                    frame = capture_frame()
                    if frame is not None:
                        self.socketio.emit(
                            'video_frame',
                            frame,
                            namespace='/video'
                        )
                time.sleep(1 / self.streaming_fps)
            except Exception as e:
                logging.error(f"Camera processing error: {e}")
                time.sleep(1)  # Delay before retry

    def _initialize_mqtt(self):
        """Initialize MQTT client and connections."""
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_message = self._on_mqtt_message
        self.mqtt_client.on_publish = self._on_mqtt_publish

        self.mqtt_client.connect(
            self.mqtt_config['broker'],
            self.mqtt_config['port'],
            60
        )
        self.mqtt_client.loop_start()

    def _setup_routes(self):
        """Set up Flask routes and WebSocket handlers."""
        # Main routes
        self.app.route('/')(self.index)
        self.app.route('/status')(self.status)
        self.app.route('/control', methods=['GET', 'POST'])(self.control)
        self.app.route('/camera')(self.camera_route)

        # API routes
        self.app.route('/api/sensor-status')(self.get_sensor_status)
        self.app.route('/api/gps', methods=['GET'])(self.get_gps)
        self.app.route('/api/mowing-area', methods=['GET', 'POST'])(
            self.handle_mowing_area
        )

        # WebSocket handlers
        self.socketio.on(
            'connect',
            namespace='/video'
        )(self.handle_video_connect)
        self.socketio.on(
            'disconnect',
            namespace='/video'
        )(self.handle_video_disconnect)
        self.socketio.on('request_status')(self.handle_status_request)

    def _get_ip_address(self) -> str:
        """Get the current IP address of the device."""
        return os.popen("hostname -I").read().split()[0]

    def _monitor_sensors(self):
        """Monitor sensors and emit updates via WebSocket."""
        while True:
            try:
                sensor_data = self.sensor_interface.get_sensor_data()
                safety_status = self.safety_monitor.get_safety_status()

                self.socketio.emit('sensor_update', {
                    'sensor_data': sensor_data,
                    'safety_status': safety_status,
                    'timestamp': datetime.datetime.now().isoformat()
                })

            except Exception as e:
                logging.error(f"Sensor monitoring error: {e}")

            time.sleep(0.5)

    # Route handlers
    def index(self):
        """Handle main page request."""
        return render_template(
            'index.html',
            google_maps_api_key=os.getenv("GOOGLE_MAPS_API_KEY"),
            next_scheduled_mow=self.next_scheduled_mow
        )

    def status(self):
        """Handle status page request."""
        status_info = self._get_status_info()
        return render_template('status.html', status=status_info)

    def control(self):
        """Handle control page request and commands."""
        if request.method == 'GET':
            return render_template('control.html')

        data = request.get_json()
        return self._handle_control_command(data)

    def camera_route(self):
        """Handle camera page request."""
        if not getattr(self, 'camera_enabled', False):
            return render_template(
                'error.html',
                message="Camera system is not available"
            )
        return render_template('camera.html')

    # API handlers
    def get_sensor_status(self):
        """Get current sensor status."""
        return jsonify(self.sensor_interface.get_sensor_status())

    def get_gps(self):
        """Get current GPS position."""
        try:
            position = self.position_reader.run()
            if position and len(position) == 5:
                lat, lon = self._convert_utm_to_latlon(position)
                return jsonify({'latitude': lat, 'longitude': lon})
            return jsonify({'error': 'No GPS data available'}), 404

        except Exception as e:
            logging.error(f"GPS error: {e}")
            return jsonify({'error': 'Server error'}), 500

    # WebSocket handlers
    def handle_video_connect(self, auth):
        """Handle video WebSocket connection."""
        if not getattr(self, 'camera_enabled', False):
            emit('camera_error', {
                'message': 'Camera system is not available'
            })
            return

        client_id = request.sid
        self.active_streams.add(client_id)
        logging.info(f"Video client connected: {client_id}")

    def handle_video_disconnect(self):
        """Handle video streaming disconnection."""
        try:
            client_id = request.sid
            self.active_streams.discard(client_id)
            logging.info(f"Video client disconnected: {client_id}")

        except Exception as e:
            logging.error(f"Video disconnection error: {e}")

    def handle_status_request(self):
        """Handle status request via WebSocket."""
        sensor_data = self.sensor_interface.get_sensor_data()
        emit('update_status', self._format_status_data(sensor_data))

    # Helper methods
    def _get_status_info(self) -> Dict[str, Any]:
        """Get comprehensive status information."""
        sensor_data = self.sensor_interface.get_sensor_data()
        return {
            'mowing_status': self.mowing_status,
            'next_scheduled_mow': self.next_scheduled_mow,
            'sensor_data': sensor_data,
            'safety_status': self.safety_monitor.get_safety_status()
        }

    def _calculate_next_scheduled_mow(self) -> str:
        '''Calculate the next scheduled mow date.
        Based on the inputs recored in mowing_schedule.json file.
        json is fromatted as:
        {"mowDays": [], "mowHours": [], "patternType": "checkerboard"}
        '''
        try:
            with open('mowing_schedule.json', 'r') as f:
                schedule = json.load(f)
                mow_days = schedule.get('mowDays', [])
                mow_hours = schedule.get('mowHours', [])

            if not mow_days or not mow_hours:
                return "No schedule set"

            return f"Next mow: {mow_days[0]} at {mow_hours[0]}"

        except Exception as e:
            logging.error(f"Next mow calculation error: {e}")
            return "Error calculating next mow"

    def _handle_control_command(self, data: Dict) -> Tuple[Dict, int]:
        """Process control commands."""
        try:
            steering = float(data.get('steering', 0))
            throttle = float(data.get('throttle', 0))

            if not self.safety_monitor.get_safety_status()['is_safe']:
                return jsonify({
                    'status': 'error',
                    'message': 'Cannot execute command - safety check failed'
                }), 400

            self.robohat_driver.run(-steering, throttle)
            return jsonify({'status': 'success'})

        except Exception as e:
            logging.error(f"Control error: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

    def _convert_utm_to_latlon(
        self,
        utm_data: Tuple[float, float, float, float, str]
    ) -> Tuple[float, float]:
        """Convert UTM coordinates to latitude/longitude."""
        _, easting, northing, zone_number, zone_letter = utm_data
        return utm.to_latlon(easting, northing, zone_number, zone_letter)

    def _format_status_data(self, sensor_data: Dict) -> Dict:
        """Format sensor data for status updates."""
        return {
            'battery': sensor_data.get('battery', {}),
            'battery_charge': sensor_data.get('battery_charge', 'N/A'),
            'solar': sensor_data.get('solar', {}),
            'speed': sensor_data.get('speed', 'N/A'),
            'heading': sensor_data.get('heading', 'N/A'),
            'bme280': sensor_data.get('bme280', {}),
            'distances': {
                'left': sensor_data.get('left_distance', 'N/A'),
                'right': sensor_data.get('right_distance', 'N/A')
            }
        }

    def start(self):
        """Start the web interface."""
        if self.use_ngrok:
            self._start_ngrok()

        self.socketio.run(self.app, host='0.0.0.0', port=8080)

    def _start_ngrok(self):
        """Start ngrok tunnel if enabled."""
        try:
            tunnel = ngrok.connect(8080)
            logging.info(f"Ngrok tunnel URL: {tunnel.public_url}")
        except Exception as e:
            logging.error(f"Ngrok tunnel error: {e}")

    # MQTT event handlers
    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """Handle MQTT connection event."""
        logging.info(f"Connected to MQTT broker with result code {rc}")
        self.mqtt_client.subscribe(self.mqtt_config['topics']['command'])

    def _on_mqtt_message(self, client, userdata, message):
        """Handle incoming MQTT messages."""
        try:
            payload = json.loads(message.payload.decode('utf-8'))
            self._handle_mqtt_command(payload)

        except Exception as e:
            logging.error(f"MQTT message error: {e}")

    def _on_mqtt_publish(self, client, userdata, mid):
        """Handle MQTT publish event."""
        logging.info(f"Message published with ID: {mid}")

    def _handle_mqtt_command(self, command: Dict):
        """Handle incoming MQTT commands."""
        if command.get('command') == 'start_mowing':
            self._start_mowing()
        elif command.get('command') == 'stop_mowing':
            self._stop_mowing()
        else:
            logging.warning(f"Unknown command: {command}")

    def _start_mowing(self):
        """Start the autonomous mowing process."""
        if self.mowing_status == "Mowing":
            return

        self.mowing_status = "Mowing"
        self.path_data = self._get_path_data()
        self._publish_path_data()
        mow_yard()


# Start the web interface thread to avoid multiprocessing issues
def start_web_interface():
    # Check if the web interface has already been started
    if getattr(WebInterface, 'web_interface', None):
        return
    # If not started, initialize and start the web interface
    WebInterface.web_interface = WebInterface()
    WebInterface.web_interface.start()


if __name__ == '__main__':
    start_web_interface()
