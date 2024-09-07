from flask import Flask, render_template, request, jsonify, send_from_directory, Response, g
import json
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from hardware_interface import BladeController, SensorInterface, RoboHATController
import os
import threading
from navigation_system import PathPlanning, GpsNmeaPositions, GpsLatestPosition  # Updated import
import datetime
import logging
from dotenv import load_dotenv
from flask_socketio import SocketIO, emit
import cv2
import base64
from flask_cors import CORS

from hardware_interface.camera import get_camera_instance

# Initialize logging
logging.basicConfig(filename='main.log', level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')


#Initialize Flask and SocketIO
app = Flask(__name__, template_folder='/home/pi/autonomous_mower/user_interface/web_interface/templates')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', engineio_logger=True, ping_timeout=30)
CORS(app)

#Load environment variables
dotenv_path = '/home/pi/autonomous_mower/.env'
load_dotenv(dotenv_path)
google_maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY")

#Initialize other components
position_reader = GpsLatestPosition  # Initialize position reader
blade_controller = BladeController()
path_planning = PathPlanning()

# Configuration placeholder (replace with actual configuration)
class Config:
    MM1_SERIAL_PORT = '/dev/ttyUSB0'
    MM1_MAX_FORWARD = 2000
    MM1_MAX_REVERSE = 1000
    MM1_STOPPED_PWM = 1500
    MM1_STEERING_MID = 1500
    AUTO_RECORD_ON_THROTTLE = True
    JOYSTICK_DEADZONE = 0.1

cfg = Config()

# Initialize RoboHATDriver
robohat_driver = RoboHATController(cfg, debug=True)

# Define a flag for stopping the sensor update thread
stop_sensor_thread = False

mowing_status = "Not mowing"
next_scheduled_mow = "2023-05-06 12:00:00"

def gen():
    camera = get_camera_instance()
    while True:
        frame = camera.get_frame()
        if frame is not None:
            success, buffer = cv2.imencode('.jpg', frame)
            if success:
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        else:
            print("Failed to get the frame from the camera.")

@app.route('/')
def index():
    next_scheduled_mow = calculate_next_scheduled_mow()
    return render_template('index.html', google_maps_api_key=google_maps_api_key, next_scheduled_mow=next_scheduled_mow)

@app.route('get_sensor_data', methods=['GET'])
def get_sensor_data():
    sensor_data = SensorInterface.sensor_data
    return jsonify(sensor_data)

@app.route('/video_feed')
def video_feed():
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

@socketio.on('request_frame')
def handle_frame_request():
    camera = get_camera_instance()  # Retrieve SingletonCamera using the accessor function
    frame = camera.get_frame()
    if frame is not None:
        success, buffer = cv2.imencode('.jpg', frame)
        if success:
            frame_data = base64.b64encode(buffer).decode('utf-8')
            emit('update_frame', {'frame': frame_data})
        else:
            print("Failed to encode the frame as JPEG.")
    else:
        print("Failed to get the frame from the camera.")

@app.route('/start-mowing', methods=['POST'])
def start_mowing():
    # Trigger start mowing actions
    # Example: robohat_driver.run(0.5, 0.5) for forward movement at half speed
    return jsonify({'message': 'Mower started.'})

@app.route('/stop-mowing', methods=['POST'])
def stop_mowing():
    # Trigger stop mowing actions
    robohat_driver.run(0, 0)
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
    # Save the coordinates to the file
    coordinates = request.get_json()
    with open('user_polygon.json', 'w') as f:
        json.dump(coordinates, f)
    return jsonify({'message': 'Area saved.'})

@app.route('/api/gps', methods=['GET'])
def get_gps():
    lines = GpsNmeaPositions  # Read NMEA lines from GPS
    positions = position_reader.run(lines)  # Convert NMEA lines to positions
    if positions:
        latitude, longitude = positions[-1]
        return jsonify({'latitude': latitude, 'longitude': longitude})
    else:
        return jsonify({'error': 'No GPS data available'})

@app.route('/save_settings', methods=['POST'])
def save_settings():
    # Get the mowing days and hours from the request
    data = request.get_json()
    mow_days = data['mowDays']
    mow_hours = data['mowHours']

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
    robohat_driver.run(steering, throttle)
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
    next_mow = datetime.datetime.now()
    if mow_days is None or mow_hours is None:
        return "Not scheduled"

    # Convert mow_days to a list of integers (0 = Monday, 1 = Tuesday, etc.)
    mow_days_int = [datetime.datetime.strptime(day, "%A").weekday() for day in mow_days]

    # Get the current date and time
    now = datetime.datetime.now()

    # Find the next scheduled mow
    for day_offset in range(7):
        next_day = (now.weekday() + day_offset) % 7
        if next_day in mow_days_int:
            next_mow_date = now + datetime.timedelta(days=day_offset)
            
            # Use the first hour in the list as an example; adjust as needed
            first_hour = int(mow_hours[0])
            next_mow_date = next_mow_date.replace(hour=first_hour, minute=0, second=0, microsecond=0)
            
            if next_mow_date > now:
                return next_mow_date.strftime("%Y-%m-%d %H:%M:%S")

    return "Not scheduled"

def start_mower_blades():
    # Toggle the mower blades
    BladeController.set_speed(75)

def stop_mower_blades():
    # Toggle the mower blades
    BladeController.set_speed(0)

def stop_motors():
    # Stop the motors
    robohat_driver.run(0, 0)

def start_web_interface():
    global stop_sensor_thread
    # Start the sensor update thread
    sensor_thread = threading.Thread(target=SensorInterface.update_sensors)
    sensor_thread.start()

    socketio.run(app, host='0.0.0.0', port=90, threaded=True)

    # Set the flag to stop the sensor update thread
    stop_sensor_thread = True
    sensor_thread.join() # Wait for the thread to finish

if __name__ == '__main__':
    start_web_interface()