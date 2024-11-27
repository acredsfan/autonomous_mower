from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit

import os
import threading
import datetime
import json
import time
import paho.mqtt.client as mqtt
from dotenv import load_dotenv

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
from mower.hardware.camera_instance import capture_frame, start_server_thread

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
        self.path_planner = get_path_planner()
        self.planned_path = []
        self.load_existing_data()

    def load_existing_data(self):
        # Load existing mowing area and planned path
        self.path_planner.load_mowing_area_polygon()
        self.path_planner.gps_polygon_to_utm_polygon()
        self.path_planner.generate_grid_from_polygon(grid_size=1.0)
        waypoints = self.path_planner.create_pattern()
        self.planned_path = self.path_planner.create_waypoint_map()

    def _initialize_flask(self):
        """Initialize Flask application and extensions."""
        template_folder = os.getenv('TEMPLATE_FOLDER',
                                    '/home/pi/autonomous_mower/src/mower/ui/web_ui/templates')
        self.app = Flask(__name__, template_folder=template_folder)
        self.socketio = SocketIO(self.app, cors_allowed_origins="*", async_mode='threading')
        CORS(self.app)

    def _load_environment_variables(self):
        """Load and set environment variables."""
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        dotenv_path = os.path.join(project_root, '.env')
        load_dotenv(dotenv_path)

        self.use_remote_planning = os.getenv("USE_REMOTE_PATH_PLANNING", "False").lower() == "true"
        self.use_ngrok = os.getenv("USE_NGROK", "False").lower() == "true"
        self.mqtt_config = {
            'broker': self._get_ip_address(),
            'port': int(os.getenv("MQTT_PORT", 1883)),
            'client_id': os.getenv("CLIENT_ID", "mower"),
            'topics': {
                'path': 'mower/path',
                'sensor': 'mower/sensor_data',
                'command': 'mower/commands',
            },
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
        self.serial_port = get_serial_port()
        self.gps_position = get_gps_position()
        self.gps_position.start()
        self.position_reader = get_gps_nmea_positions()

    def _init_controllers(self):
        """Initialize various controller components."""
        self.blade_controller = get_blade_controller()
        self.localization = get_localization()
        self.path_planning = get_path_planner()
        self.robohat_driver = get_robohat_driver()
        self.sensor_interface = get_sensor_interface()
        self.safety_monitor = self.sensor_interface.get_safety_monitor()
        self.navigation_controller = NavigationController(
            self.position_reader,
            self.robohat_driver,
            self.sensor_interface
        )

    def _init_sensors(self):
        """Initialize sensor interfaces and monitoring."""
        self.sensor_interface = get_sensor_interface()
        self.safety_monitor = self.sensor_interface.get_safety_monitor()
        self.sensor_thread = threading.Thread(target=self._monitor_sensors, daemon=True)
        self.sensor_thread.start()

    def _init_camera(self):
        """Initialize camera components."""
        try:
            start_server_thread()
            self.camera_enabled = True
            self.streaming_fps = int(os.getenv('STREAMING_FPS', 15))
            self.stream_active = False
            self.active_streams = set()
            self.camera_thread = threading.Thread(target=self._process_camera, daemon=True)
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
                    if frame:
                        self.socketio.emit('video_frame', frame, namespace='/video')
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
        self.app.route('/')(self.index)
        self.app.route('/status')(self.status)
        self.app.route('/control', methods=['GET', 'POST'])(self.control)
        self.app.route('/camera')(self.camera_route)
        self.app.route('/api/sensor-status')(self.get_sensor_status)
        self.app.route('/api/gps', methods=['GET'])(self.get_gps)
        self.app.route('/api/mowing-area', methods=['GET', 'POST'])(self.handle_mowing_area)
        self.app.route('/api/home-location', methods=['GET', 'POST'])(self.handle_home_location)
        self.app.route('/api/robot-position', methods=['GET'])(self.get_robot_position)
        self.app.route('/api/planned-path', methods=['GET'])(self.get_planned_path)
        self.socketio.on('connect', namespace='/video')(self.handle_video_connect)
        self.socketio.on('disconnect', namespace='/video')(self.handle_video_disconnect)
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
                    'timestamp': datetime.datetime.now().isoformat(),
                })
            except Exception as e:
                logging.error(f"Sensor monitoring error: {e}")
            time.sleep(0.5)

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
            return render_template('error.html')

    def get_sensor_status(self):
        """API endpoint to get sensor status."""
        try:
            sensor_data = self.sensor_interface.get_sensor_data()
            safety_status = self.safety_monitor.get_safety_status()
            return jsonify({
                'sensor_data': sensor_data,
                'safety_status': safety_status,
                'timestamp': datetime.datetime.now().isoformat(),
            })
        except Exception as e:
            logging.error(f"Error getting sensor status: {e}")
            return jsonify({'error': str(e)}), 500

    def get_gps(self):
        """API endpoint to get GPS data."""
        try:
            position = self.gps_position.read()
            return jsonify(position)
        except Exception as e:
            logging.error(f"Error getting GPS data: {e}")
            return jsonify({'error': str(e)}), 500

    def handle_mowing_area(self):
        if request.method == 'GET':
            mowing_area_polygon = self.get_mowing_area_polygon()
            return jsonify({'polygon': mowing_area_polygon})
        elif request.method == 'POST':
            data = request.get_json()
            if data and 'polygon' in data:
                self.save_mowing_area_polygon(data['polygon'])
                # Regenerate planned path
                self.load_existing_data()
                return jsonify({'status': 'success'})
            else:
                return jsonify({'error': 'Invalid data provided'}), 400

    def handle_home_location(self):
        if request.method == 'GET':
            home_location = self.get_home_location()
            return jsonify({'location': home_location})
        elif request.method == 'POST':
            data = request.get_json()
            if data and 'location' in data:
                self.save_home_location(data['location'])
                return jsonify({'status': 'success'})
            else:
                return jsonify({'error': 'Invalid data provided'}), 400

    def get_planned_path(self):
        return jsonify(self.planned_path)

        # Helper methods to get and save data

    def get_mowing_area_polygon(self):
        if os.path.exists('user_polygon.json'):
            with open('user_polygon.json', 'r') as f:
                polygon_data = json.load(f)
            return polygon_data
        else:
            return []

    def save_mowing_area_polygon(self, polygon):
        with open('user_polygon.json', 'w') as f:
            json.dump(polygon, f)

    def get_home_location(self):
        if os.path.exists('home_location.json'):
            with open('home_location.json', 'r') as f:
                location_data = json.load(f)
            return location_data
        else:
            return None

    def save_home_location(self, location):
        with open('home_location.json', 'w') as f:
            json.dump(location, f)


    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """Handle MQTT connection."""
        logging.info(f"Connected to MQTT broker with result code {rc}")
        for topic in self.mqtt_config['topics'].values():
            client.subscribe(topic)

    def _on_mqtt_message(self, client, userdata, msg):
        """Handle MQTT message."""
        topic = msg.topic
        payload = msg.payload.decode()
        logging.info(f"MQTT message received on topic {topic}: {payload}")
        # Process message here

    def _on_mqtt_publish(self, client, userdata, mid):
        """Handle MQTT publish acknowledgment."""
        logging.info(f"MQTT message published with mid: {mid}")

    def _handle_control_command(self, data: Dict[str, Any]) -> str:
        """Handle control commands received."""
        logging.info(f"Received control command: {json.dumps(data)}")
        # Implement actual control handling logic here
        return jsonify({'status': 'success'})

    def _get_status_info(self) -> Dict[str, Any]:
        """Get status information for the status page."""
        status_info = {
            'mowing_status': self.mowing_status,
            'next_scheduled_mow': self.next_scheduled_mow,
        }
        return status_info

    # WebSocket Handlers
    def handle_video_connect(self):
        """Handle WebSocket video connect."""
        logging.info("Video client connected")
        self.active_streams.add(request.sid)

    def handle_video_disconnect(self):
        """Handle WebSocket video disconnect."""
        logging.info("Video client disconnected")
        self.active_streams.remove(request.sid)

    def handle_status_request(self):
        """Handle WebSocket status request."""
        status_info = self._get_status_info()
        self.socketio.emit('status_update', status_info)

    def _calculate_next_scheduled_mow(self) -> datetime.datetime:
        """Calculate the next scheduled mow (stub method)."""
        # Implement your logic to calculate the next mowing time
        return datetime.datetime.now() + datetime.timedelta(days=1)


if __name__ == '__main__':
    web_interface = WebInterface()
    web_interface.socketio.run(web_interface.app, host='0.0.0.0', port=5000)
