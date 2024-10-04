from flask_cors import CORS
import requests
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv
import datetime
import threading
from flask import Flask, render_template, request, jsonify, Response
import json
import sys
import os
import utm
from pyngrok import ngrok

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(project_root)

from utilities import LoggerConfigInfo as LoggerConfig
from hardware_interface.sensor_interface import get_sensor_interface
from hardware_interface.blade_controller import BladeController
from hardware_interface.robohat import RoboHATController
from hardware_interface.serial_port import SerialPort
from navigation_system.gps import GpsPosition, GpsLatestPosition
from obstacle_detection.local_obstacle_detection import start_processing

# Initialize logger
logging = LoggerConfig.get_logger(__name__)

# Initialize Flask and SocketIO
app = Flask(
    __name__,
    template_folder=(
        '/home/pi/autonomous_mower/user_interface/web_interface/templates')
)
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='threading',
    engineio_logger=True,
    ping_timeout=30
)
CORS(app)

# Load environment variables from .env in project_root directory
dotenv_path = os.path.join(project_root, '.env')
load_dotenv(dotenv_path)

# Initialize other components
from navigation_system.path_planning import PathPlanning
from navigation_system.localization import Localization

# Read serial port configurations from environment variables
serial_port_path = os.getenv("GPS_SERIAL_PORT", "/dev/ttyACM0")  # Default to /dev/ttyACM0
serial_baudrate = int(os.getenv("GPS_BAUD_RATE", "9600"))
serial_timeout = float(os.getenv("GPS_SERIAL_TIMEOUT", "1"))
ngrok_url = os.getenv("NGROK_URL")
use_ngrok = os.getenv("USE_NGROK", "False").lower() == "true"

# Initialize SerialPort and GpsPosition with environment configurations
serial_port = SerialPort(port=serial_port_path, baudrate=serial_baudrate, timeout=serial_timeout)
gps_position = GpsPosition(serial_port=serial_port, debug=True)
gps_position.start()
position_reader = GpsLatestPosition(gps_position_instance=gps_position, debug=True)

blade_controller = BladeController()
localization = Localization()
path_planning = PathPlanning(localization)
sensor_interface = get_sensor_interface()

# Initialize RoboHATController with gps_latest_position
robohat_driver = RoboHATController(gps_latest_position=position_reader)

# Define a flag for stopping the sensor update thread
stop_thread = False

mowing_status = "Not mowing"
next_scheduled_mow = "2023-05-06 12:00:00"


def utm_to_latlon(easting, northing, zone_number, zone_letter):
    lat, lng = utm.to_latlon(easting, northing, zone_number, zone_letter)
    return lat, lng


@app.route('/')
def index():
    next_scheduled_mow = calculate_next_scheduled_mow()
    return render_template('index.html',
                           google_maps_api_key=os.getenv("GOOGLE_MAPS_API_KEY"),
                           next_scheduled_mow=next_scheduled_mow)


@app.route('/status')
def status():
    # Collect status information from your sensors or system
    status_info = {
        'mowing_status': mowing_status,
        'next_scheduled_mow': next_scheduled_mow,
        'battery-voltage': sensor_interface.sensor_data.get('battery', {}).get('voltage', 'N/A'),
        'battery-current': sensor_interface.sensor_data.get('battery', {}).get('current', 'N/A'),
        'battery-charge-level': sensor_interface.sensor_data.get('battery_charge', 'N/A'),
        'solar-voltage': sensor_interface.sensor_data.get('solar', {}).get('voltage', 'N/A'),
        'solar-current': sensor_interface.sensor_data.get('solar', {}).get('current', 'N/A'),
        'speed': sensor_interface.sensor_data.get('speed', 'N/A'),
        'heading': sensor_interface.sensor_data.get('heading', 'N/A'),
        'temperature': sensor_interface.sensor_data.get('bme280', {}).get('temperature', 'N/A'),
        'humidity': sensor_interface.sensor_data.get('bme280', {}).get('humidity', 'N/A'),
        'pressure': sensor_interface.sensor_data.get('bme280', {}).get('pressure', 'N/A'),
        'left-distance': sensor_interface.sensor_data.get('left_distance', 'N/A'),
        'right-distance': sensor_interface.sensor_data.get('right_distance', 'N/A')
    }
    return render_template('status.html', status=status_info)


@app.route('/get_sensor_data', methods=['GET'])
def get_sensor_data():
    sensor_data = sensor_interface.sensor_data
    return jsonify(sensor_data)


@app.route('/control', methods=['GET', 'POST'])
def control():
    if request.method == 'GET':
        # Render the control.html template
        return render_template('control.html')
    elif request.method == 'POST':
        # Handle control commands
        data = request.get_json()
        steering = data.get('steering', 0)
        throttle = data.get('throttle', 0)
        robohat_driver.set_steering_throttle(steering, throttle)
        return jsonify({'status': 'success'})


@socketio.on('request_status')
def handle_status_request():
    sensor_data = sensor_interface.sensor_data
    # Prepare the data in the format expected by the client
    data = {
        'battery': sensor_data.get('battery', {}),
        'battery_charge': sensor_data.get('battery_charge', 'N/A'),
        'solar': sensor_data.get('solar', {}),
        'speed': sensor_data.get('speed', 'N/A'),
        'heading': sensor_data.get('heading', 'N/A'),
        'bme280': sensor_data.get('bme280', {}),
        'left_distance': sensor_data.get('left_distance', 'N/A'),
        'right_distance': sensor_data.get('right_distance', 'N/A')
    }
    emit('update_status', data)


@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


def gen_frames():
    from hardware_interface.camera_instance import camera
    import io
    from PIL import Image
    while True:
        frame = camera.capture_array()
        img = Image.fromarray(frame)
        img = img.convert('RGB')
        buf = io.BytesIO()
        img.save(buf, format='JPEG')
        frame_bytes = buf.getvalue()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')


@app.route('/camera_route')
def camera_route():
    return render_template('camera.html')


@app.route('/start-mowing', methods=['POST'])
def start_mowing():
    # Trigger start mowing actions
    import robot_test
    robot_test.start_mowing()
    return jsonify({'message': 'Mower started.'})

@app.route('/stop-mowing', methods=['POST'])
def stop_mowing():
    import robot_test
    robot_test.stop_mowing()
    return jsonify({'message': 'Mower stopped.'})

@app.route('/get-mowing-area', methods=['GET'])
def get_mowing_area():
    # Check if the file exists
    if os.path.exists('user_polygon.json'):
        # Load the coordinates from the file
        with open('user_polygon.json', 'r') as f:
            coordinates = json.load(f)
        return jsonify(coordinates)
    else:
        return jsonify({'message': 'No area saved yet.'})

@app.route('/area', methods=['GET'])
def area():
    google_maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    return render_template('area.html', google_maps_api_key=google_maps_api_key)


@app.route('/settings', methods=['GET'])
def settings():
    return render_template('settings.html')


@app.route('/get-path', methods=['GET'])
def get_path():
    start, goal = path_planning.get_start_and_goal()
    path = path_planning.get_path(start, goal)
    return jsonify(path)


@app.route('/save-mowing-area', methods=['POST'])
def save_mowing_area():
    data = request.get_json()
    if not isinstance(data, list):
        return jsonify({'message': 'Invalid data format. Expected a list of coordinates.'}), 400

    # Validate each coordinate object
    for coord in data:
        if not ('lat' in coord and 'lng' in coord):
            return jsonify({'message': 'Each coordinate must have "lat" and "lng".'}), 400
        if not (isinstance(coord['lat'], (int, float)) and isinstance(coord['lng'], (int, float))):
            return jsonify({'message': '"lat" and "lng" must be numbers.'}), 400

    with open('user_polygon.json', 'w') as f:
        json.dump(data, f)
    logging.info('Mowing area saved successfully.')
    return jsonify({'message': 'Mowing area saved.'})


@app.route('/api/gps', methods=['GET'])
def get_gps():
    #logging.info("Starting get_gps")
    try:
        position = position_reader.run()
        # logging.info(f"position: {position}")

        if position and len(position) == 5:
            ts, easting, northing, zone_number, zone_letter = position
            lat, lng = utm.to_latlon(easting, northing, zone_number, zone_letter)
            return jsonify({'latitude': lat, 'longitude': lng})
        else:
            return jsonify({'error': 'No GPS data available'}), 404
    except Exception as e:
        logging.error(f"Error in get_gps: {e}")
        return jsonify({'error': 'Server error'}), 500


@app.route('/save_settings', methods=['POST'])
def save_settings():
    data = request.get_json()
    mow_days = data.get('mowDays', [])
    mow_hours = data.get('mowHours', [])

    # Validate mow_days
    valid_days = [
        'Monday',
        'Tuesday',
        'Wednesday',
        'Thursday',
        'Friday',
        'Saturday',
        'Sunday']
    if not all(day in valid_days for day in mow_days):
        return jsonify({'message': 'Invalid days provided.'}), 400

    # Validate mow_hours
    if not all(isinstance(hour, int) and 0 <=
               hour <= 23 for hour in mow_hours):
        return jsonify({'message': 'Invalid hours provided.'}), 400

    # Save the mowing days and hours to a JSON file
    with open('mowing_schedule.json', 'w') as f:
        json.dump({'mowDays': mow_days, 'mowHours': mow_hours}, f)

    return jsonify({'message': 'Settings saved.'})


@app.route('/get_google_maps_api_key', methods=['GET'])
def get_google_maps_api_key():
    # Fetch the API key from environment or configuration
    google_maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY")

    if google_maps_api_key:
        return jsonify({"api_key": google_maps_api_key})
    else:
        return jsonify({"error": "API key not found"}), 404


@app.route('/get_map_id', methods=['GET'])
def get_map_id():
    # Fetch the map ID from the environment
    map_id = os.getenv("GOOGLE_MAPS_MAP_ID")

    if map_id:
        return jsonify({"map_id": map_id})
    else:
        return jsonify({"error": "Map ID not found"}), 404
    
@app.route('/get_obj_det_ip', methods=['GET'])
def get_obj_det_ip():
    # Fetch the map ID from the environment
    obj_det_id = os.getenv("OBJECT_DETECTION_IP")

    if obj_det_id:
        return jsonify({"object_detection_ip": obj_det_id})
    else:
        return jsonify({"error": "Object Detection IP not found"}), 404


@app.route('/get_default_coordinates', methods=['GET'])
def get_default_coordinates():
    # Fetch the default LAT and LNG from the environment
    default_lat = os.getenv("MAP_DEFAULT_LAT")
    default_lng = os.getenv("MAP_DEFAULT_LNG")

    if default_lat and default_lng:
        try:
            default_lat = float(default_lat)
            default_lng = float(default_lng)
            logging.info(f"default_lat: {default_lat}, type: {type(default_lat)}")
            logging.info(f"default_lng: {default_lng}, type: {type(default_lng)}")
            return jsonify({"lat": default_lat, "lng": default_lng})
        except ValueError:
            logging.error("Invalid default coordinates")
            return jsonify({"error": "Invalid default coordinates"}), 400
    else:
        logging.error("Default coordinates not found")
        return jsonify({"error": "Default coordinates not found"}), 404


def get_schedule():
    # Check if the schedule file exists
    if os.path.exists('mowing_schedule.json'):
        # Load the mowing days and hours from the JSON file
        with open('mowing_schedule.json', 'r') as f:
            schedule = json.load(f)
        return schedule['mowDays'], schedule['mowHours']
    else:
        # Return default values if the schedule is not set
        return None, None

@app.route('/stop', methods=['POST'])
def stop():
    robohat_driver.run(0, 0)
    return jsonify({'status': 'stopped'})

@app.route('/save-home-location', methods=['POST'])
def save_home_location():
    # Save the home location coordinates to a JSON file
    home_location = request.get_json()
    with open('home_location.json', 'w') as f:
        json.dump(home_location, f)
    return jsonify({'message': 'Home location saved.'})

@app.route('/get-home-location', methods=['GET'])
def get_home_location():
    # Retrieve the home location from the JSON file
    if os.path.exists('home_location.json'):
        with open('home_location.json', 'r') as f:
            home_location = json.load(f)
        return jsonify(home_location)
    else:
        return jsonify({'message': 'No home location set yet.'})

def calculate_next_scheduled_mow():
    # Get the mowing days and hours from the schedule file
    mow_days, mow_hours = get_schedule()

    # Calculate the next scheduled mow
    next_mow_date = datetime.datetime.now()
    if mow_days is None or mow_hours is None:
        return "Not scheduled"

    # Convert mow_days to a list of integers (0 = Monday, 1 = Tuesday, etc.)
    mow_days_int = [datetime.datetime.strptime(
        day, "%A").weekday() for day in mow_days]

    # Get the current date and time
    now = datetime.datetime.now()

    # Find the next scheduled mow
    for day_offset in range(7):
        next_day = (now.weekday() + day_offset) % 7
        if next_day in mow_days_int:
            next_mow_date = now + datetime.timedelta(days=day_offset)

            # Use the first hour in the list as an example; adjust as needed
            first_hour = int(mow_hours[0])
            next_mow_date = next_mow_date.replace(
                hour=first_hour, minute=0, second=0, microsecond=0)

            if next_mow_date > now:
                return next_mow_date.strftime("%Y-%m-%d %H:%M:%S")

    return "Not scheduled"

def start_mower_blades():
    # Toggle the mower blades
    BladeController.set_speed(75)

def stop_mower_blades():
    # Toggle the mower blades
    BladeController.set_speed(0)

@app.route('/toggle_blades', methods=['POST'])
def toggle_blades():
    data = request.get_json()
    state = data.get('state')
    if state == 'on':
        start_mower_blades()
    elif state == 'off':
        stop_mower_blades()
    else:
        return jsonify({'message': 'Invalid state provided.'}), 400
    return jsonify({'message': f'Blades turned {state}.'})


@app.route('/check-polygon-points', methods=['POST'])
def check_polygon_points():
    # Load the saved polygon points
    if os.path.exists('user_polygon.json'):
        with open('user_polygon.json', 'r') as f:
            coordinates = json.load(f)
    else:
        return jsonify({'message': 'No polygon points saved.'}), 400

    # Iterate over each point and navigate to it
    success = True
    for point in coordinates:
        lat = point['lat']
        lng = point['lng']
        target_location = (lat, lng)
        result = robohat_driver.navigate_to_location(target_location)
        if not result:
            success = False
            break  # Stop if navigation failed

    if success:
        return jsonify({'message': 'Robot has visited all polygon points.'})
    else:
        return jsonify({'message': 'Failed to navigate to all polygon points.'}), 500


def stop_motors():
    # Stop the motors
    robohat_driver.run(0, 0)


def start_camera():
    start_processing()


def start_web_interface():
    global stop_sensor_thread
    # Start the sensor update thread
    sensor_thread = threading.Thread(
        target=sensor_interface.update_sensors, daemon=True)
    sensor_thread.start()

    # Start the camera processing and streaming server
    camera_thread = threading.Thread(target=start_camera, daemon=True)
    camera_thread.start()
    logging.info("Camera started.")

    # Start Ngrok tunnel for remote access if use_ngrok is set to True
    if use_ngrok:
        logging.info("Starting Ngrok tunnel...")
        ngrok_tunnel = ngrok.connect(8080)
        logging.info(f"Ngrok tunnel URL: {ngrok_tunnel.public_url}")

    socketio.run(app, host='0.0.0.0', port=8080)

    # Set the flag to stop the sensor update thread
    sensor_interface.stop_thread = True

    sensor_thread.join()  # Wait for the thread to finish


if __name__ == '__main__':
    start_web_interface()
