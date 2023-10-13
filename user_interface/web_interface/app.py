from flask import Flask, render_template, request, jsonify, send_from_directory, Response, g
import sys
import json
sys.path.append('/home/pi/autonomous_mower')
from hardware_interface import MotorController, BladeController
import subprocess
import os
from obstacle_detection import camera_processing
import threading
from navigation_system import PathPlanning, GPSInterface
import datetime
import logging
import dotenv
from dotenv import load_dotenv
from flask_socketio import SocketIO, emit
from user_interface.web_interface.camera import SingletonCamera
import time
from hardware_interface.sensor_interface import sensor_interface
from flask_cors import CORS



# Initialize logging
logging.basicConfig(filename='main.log', level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')

try:
    camera = SingletonCamera()
except Exception as e:
    print(f"Failed to initialize camer in app: {e}")

app = Flask(__name__, template_folder='/home/pi/autonomous_mower/user_interface/web_interface/templates')
@app.before_request
def before_request():
    g.camera = camera
sensors = sensor_interface
gps = GPSInterface()
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', engineio_logger=True, ping_timeout=30)
CORS(app)

# Define variables to hold sensor values
battery_charge = {}
solar_status = {}
speed = {}
heading = {}
temperature = 0
humidity = 0
pressure = 0
left_distance = {}
right_distance = {}

# Define a flag for stopping the sensor update thread
stop_sensor_thread = False

mowing_status = "Not mowing"
next_scheduled_mow = "2023-05-06 12:00:00"
gps = GPSInterface()
motor_controller = MotorController()
blade_controller = BladeController()
path_planning = PathPlanning()

dotenv_path = '/home/pi/autonomous_mower/.env'
load_dotenv(dotenv_path)
google_maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY")

first_request = True

def start_web_interface():
    # Start the sensor update thread
    global camera
    sensor_thread = threading.Thread(target=update_sensors)
    sensor_thread.start()

    app.run(host='0.0.0.0', port=90, debug=False)

    # Set the flag to stop the sensor update thread
    stop_sensor_thread = True
    sensor_thread.join()  # Wait for the thread to finish

def update_sensors():
    global battery_charge, solar_status, speed, heading, temperature, humidity, pressure, left_distance, right_distance

    while not stop_sensor_thread:
        # Update sensor values
        battery_charge = {"battery_voltage": sensors.sensor_data['battery']}
        solar_status = {"Solar Panel Voltage": sensors.sensor_data['solar']}
        speed = {"speed": gps.read_gps_data()['speed']}
        gps_data = gps.read_gps_data()
        if gps_data is not None:
            speed = {"speed": gps_data['speed']}
        else:
            speed = {"speed": None}
        heading = {"heading": sensors.sensor_data['compass']}
        bme280_data = sensors.sensor_data['bme280']
        if bme280_data is not None:
            temperature = bme280_data['temperature_f']
            humidity = bme280_data['humidity']
            pressure = bme280_data['pressure']
        left_distance = {"left_distance": sensors.sensor_data['ToF_Left']}
        right_distance = {"right_distance": sensors.sensor_data['ToF_Right']}
        time.sleep(3)  # Wait for 3 second before updating again

@app.route('/static/<path:path>')
def send_js(path):
    return send_from_directory('static', path)

@app.route('/sensor-data')
def sensor_data():
    # Retrieve the latest sensor data
    bme280_data = sensors.read_bme280()
    gps_data = gps.read_gps_data()
    if gps_data is not None:
        speed = gps_data['speed']
    else:
        speed = None

    sensor_data = {
        'battery_voltage': sensors.read_ina3221(3),
        'solar_voltage': sensors.read_ina3221(1),
        'speed': speed,
        'heading': sensors.read_mpu9250_compass(),
        'temperature': bme280_data['temperature_f'] if bme280_data else None,
        'humidity': bme280_data['humidity'] if bme280_data else None,
        'pressure': bme280_data['pressure'] if bme280_data else None,
        'left_distance': sensors.read_vl53l0x_left(),
        'right_distance': sensors.read_vl53l0x_right()
    }

    return jsonify(sensor_data)

@app.route('/')
def index():
#    sensor_data = get_sensor_data()
    next_scheduled_mow = calculate_next_scheduled_mow()
    return render_template('status.html', battery_charge=battery_charge, solar_status=solar_status, speed=speed, heading=heading, temperature=temperature, humidity=humidity, pressure=pressure, left_distance=left_distance, right_distance=right_distance, mowing_status=mowing_status, next_scheduled_mow=next_scheduled_mow)

@app.route('/status')
def status():
#    sensor_data = get_sensor_data()
    next_scheduled_mow = calculate_next_scheduled_mow()
    return render_template('status.html', battery_charge=battery_charge, solar_status=solar_status, speed=speed, heading=heading, temperature=temperature, humidity=humidity, pressure=pressure, left_distance=left_distance, right_distance=right_distance, mowing_status=mowing_status, next_scheduled_mow=next_scheduled_mow)

@app.route('/control')
def control():
    return render_template('control.html')


@app.route('/area')
def area():
    return render_template('area.html', google_maps_api_key=google_maps_api_key)

@app.route('/settings')
def settings():
    return render_template('settings.html')

@app.route('/camera')
def camera():
    return render_template('camera.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@socketio.on('move')
def handle_move(direction):
    if direction == 'forward':
        motor_controller.move_mower("forward", 100, 100)
    elif direction == 'backward':
        motor_controller.move_mower("backward", 100, 100)
    elif direction == 'left':
        motor_controller.move_mower("left", 100, 100)
    elif direction == 'right':
        motor_controller.move_mower("right", 100, 100)
    elif direction == 'stop':
        motor_controller.stop_motors()
    emit('message', {'data': f'Moving {direction}'})

@socketio.on('toggle_blades')
def handle_toggle_blades(state):
    if state == 'on':
        blade_controller.set_speed(90)
    elif state == 'off':
        blade_controller.set_speed(0)
    emit('message', {'data': f'Blades toggled {state}'})

@socketio.on('request_status')
def handle_status_request():
    global battery_charge, solar_status, speed, heading, temperature, humidity, pressure, left_distance, right_distance
    sensor_data = {
        'battery_voltage': battery_charge,
        'solar_voltage': solar_status,
        'speed': speed,
        'heading': heading,
        'temperature': temperature,
        'humidity': humidity,
        'pressure': pressure,
        'left_distance': left_distance,
        'right_distance': right_distance
    }
    emit('update_status', sensor_data)

@app.route('/start-mowing', methods=['POST'])
def start_mowing():
    global mowing_requested
    mowing_requested = True
    return jsonify({'message': 'Mower started.'})


@app.route('/stop-mowing', methods=['POST'])
def stop_mowing():
    toggle_mower_blades()
    stop_motors()
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
    data = gps.read_gps_data()
    if data:
        return jsonify({'latitude': data['latitude'], 'longitude': data['longitude']})
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

@socketio.on('request_frame')
def handle_frame_request():
    frame = camera.get_frame()  # Use the single instance
    emit('update_frame', {'frame': frame})
    
def gen(camera):
    while True:
        frame = camera.get_frame()  # Use the single instance

        # Perform obstacle detection on the frame
        obstacle_label = camera_processing.classify_obstacle(frame)
        print(f"Detected obstacle type: {obstacle_label}")

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')
    
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
    
def set_motor_direction(direction):
    # Set the motor direction
    MotorController.set_direction(direction)

def start_mower_blades():
    # Toggle the mower blades
    BladeController.set_speed(75)

def stop_mower_blades():
    # Toggle the mower blades
    BladeController.set_speed(0)

def stop_motors():
    # Stop the motors
    MotorController.stop_motors()

def start_web_interface():
    global stop_sensor_thread
    # Start the sensor update thread
    sensor_thread = threading.Thread(target=update_sensors)
    sensor_thread.start()

    socketio.run(app, host='0.0.0.0', port=90, threaded=True)

    # Set the flag to stop the sensor update thread
    stop_sensor_thread = True
    sensor_thread.join() # Wait for the thread to finish