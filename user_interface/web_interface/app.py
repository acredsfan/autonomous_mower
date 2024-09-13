from utils import LoggerConfig
from hardware_interface.camera import get_camera_instance
from PIL import Image
from io import BytesIO
from flask_cors import CORS
import base64
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv
import datetime
# Updated import
from navigation_system import PathPlanning, GpsNmeaPositions, GpsLatestPosition
import threading
from hardware_interface import (
    BladeController,
    SensorInterface,
    RoboHATController)
from flask import Flask, render_template, request, jsonify, Response
import json
import sys
import os
import utm

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


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
    ping_timeout=30)
CORS(app)

# Load environment variables
dotenv_path = '/home/pi/autonomous_mower/.env'
load_dotenv(dotenv_path)
google_maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY")

# Initialize other components
position_reader = GpsLatestPosition()  # Initialize position reader
blade_controller = BladeController()
path_planning = PathPlanning()
sensor_interface = SensorInterface()


# Initialize RoboHATDriver
robohat_driver = RoboHATController(debug=True)

# Define a flag for stopping the sensor update thread
stop_thread = False

mowing_status = "Not mowing"
next_scheduled_mow = "2023-05-06 12:00:00"


def utm_to_latlon(easting, northing, zone_number, zone_letter):
    lat, lon = utm.to_latlon(easting, northing, zone_number, zone_letter)
    return lat, lon


def gen():
    camera = get_camera_instance()
    while True:
        frame = camera.get_frame()
        if frame is not None:
            try:
                # Convert frame (numpy array) to an image using Pillow
                image = Image.fromarray(frame)
                buffer = BytesIO()
                image.save(buffer, format="JPEG")
                frame = buffer.getvalue()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            except Exception as e:
                logging.error(f"Error encoding frame for streaming: {e}")
        else:
            logging.error("Failed to get the frame from the camera.")


@app.route('/')
def index():
    next_scheduled_mow = calculate_next_scheduled_mow()
    return render_template('index.html',
                           google_maps_api_key=google_maps_api_key,
                           next_scheduled_mow=next_scheduled_mow)


@app.route('/get_sensor_data', methods=['GET'])
def get_sensor_data():
    sensor_data = sensor_interface.sensor_data
    return jsonify(sensor_data)


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
    return Response(
        gen(),
        mimetype='multipart/x-mixed-replace; boundary=frame')


@socketio.on('request_frame')
def handle_frame_request():
    # Retrieve SingletonCamera using the accessor function
    camera = get_camera_instance()
    frame = camera.get_frame()
    if frame is not None:
        try:
            # Convert the frame to an image and then to a base64-encoded string
            image = Image.fromarray(frame)
            buffer = BytesIO()
            image.save(buffer, format="JPEG")
            frame_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
            emit('update_frame', {'frame': frame_data})
        except Exception as e:
            logging.error(
                f"Error encoding frame for WebSocket transmission: {e}")
    else:
        logging.error("Failed to get the frame from the camera.")


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


@app.route('/get-path', methods=['GET'])
def get_path():
    start, goal = path_planning.get_start_and_goal()
    path = path_planning.get_path(start, goal)
    return jsonify(path)


@app.route('/save-mowing-area', methods=['POST'])
def save_mowing_area():
    data = request.get_json()
    coordinates = data.get('mowingAreaCoordinates', [])
    with open('user_polygon.json', 'w') as f:
        json.dump(coordinates, f)
    return jsonify({'message': 'Area saved.'})


@app.route('/api/gps', methods=['GET'])
def get_gps():
    gps_nmea_positions = GpsNmeaPositions()
    lines = gps_nmea_positions.get_lines()
    positions = position_reader.run(lines)

    if positions:
        ts, easting, northing, zone_number, zone_letter = positions[-1]
        lat, lon = utm.to_latlon(easting, northing, zone_number, zone_letter)
        return jsonify({'latitude': lat, 'longitude': lon})
    else:
        return jsonify({'error': 'No GPS data available'})


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


@app.route('/control', methods=['POST'])
def control():
    data = request.json
    steering = data.get('steering', 0)
    throttle = data.get('throttle', 0)
    robohat_driver.run_threaded(steering, throttle)
    return jsonify({'status': 'success'})


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


def stop_motors():
    # Stop the motors
    robohat_driver.run(0, 0)


def start_web_interface():
    global stop_sensor_thread
    # Start the sensor update thread
    sensor_thread = threading.Thread(
        target=sensor_interface.update_sensors, daemon=True)
    sensor_thread.start()

    socketio.run(app, host='0.0.0.0', port=90)

    # Set the flag to stop the sensor update thread
    sensor_interface.stop_thread = True

    sensor_thread.join()  # Wait for the thread to finish


if __name__ == '__main__':
    start_web_interface()
