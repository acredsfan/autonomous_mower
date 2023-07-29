from flask import Flask, render_template, request, jsonify, send_from_directory, Response
import sys
import json
sys.path.append('/home/pi/autonomous_mower')
from hardware_interface import MotorController, SensorInterface, BladeController
import subprocess
import os
from dotenv import load_dotenv
from camera import VideoCamera
import time
import threading
from navigation_system import PathPlanning, GPSInterface

app = Flask(__name__)
sensors = SensorInterface()
gps = GPSInterface()

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
path_planning = PathPlanning()

dotenv_path = os.path.join(os.path.dirname(__file__),'home' ,'pi', 'autonomous_mower', '.env')
load_dotenv(dotenv_path)
google_maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY")

first_request = True

def update_sensors():
    global battery_charge, solar_status, speed, heading, temperature, humidity, pressure, left_distance, right_distance

    while not stop_sensor_thread:
        # Update sensor values
        battery_charge = {"battery_voltage": sensors.read_ina3221(3)}
        solar_status = {"Solar Panel Voltage": sensors.read_ina3221(1)}
        speed = {"speed": gps.read_gps_data()}
        heading = {"heading": sensors.read_mpu9250_compass()}
        bme280_data = sensors.read_bme280()
        if bme280_data is not None:
            temperature = bme280_data['temperature_f']
            humidity = bme280_data['humidity']
            pressure = bme280_data['pressure']
        left_distance = {"left_distance": sensors.read_vl53l0x_left()}
        right_distance = {"right_distance": sensors.read_vl53l0x_right()}

        time.sleep(1)  # Wait for 1 second before updating again

@app.route('/static/<path:path>')
def send_js(path):
    return send_from_directory('static', path)

@app.route('/sensor-data')
def sensor_data():
    # Retrieve the latest sensor data
    bme280_data = sensors.read_bme280()
    sensor_data = {
        'battery_voltage': sensors.read_ina3221(3),
        'solar_voltage': sensors.read_ina3221(1),
        'speed': gps.read_gps_data(),
        'heading': sensors.read_mpu9250_compass(),
        'temperature': bme280_data['temperature_f'],
        'humidity': bme280_data['humidity'],
        'pressure': bme280_data['pressure'],
        'left_distance': sensors.read_vl53l0x_left(),
        'right_distance': sensors.read_vl53l0x_right()
    }

    return jsonify(sensor_data)

@app.route('/')
def index():
#    sensor_data = get_sensor_data()
    return render_template('status.html', battery_charge=battery_charge, solar_status=solar_status, speed=speed, heading=heading, temperature=temperature, humidity=humidity, pressure=pressure, left_distance=left_distance, right_distance=right_distance, mowing_status=mowing_status, next_scheduled_mow=next_scheduled_mow)

@app.route('/status')
def status():
#    sensor_data = get_sensor_data()
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
  return Response(gen(VideoCamera()), mimetype='multipart/x-mixed-replace; boundary=frame')

# Add routes for AJAX requests here
@app.route('/move', methods=['POST'])
def move():
    direction = request.json.get('direction')
    if direction == 'forward':
        MotorController.move_mower("forward",100,100)
    elif direction == 'backward':
        MotorController.move_mower("backward",90,90)
    elif direction == 'left':
        MotorController.move_mower("left",100,100)
    elif direction == 'right':
        MotorController.move_mower("right",100,100)
    elif direction == 'stop':
        MotorController.stop_motors()
        return jsonify({'error': 'Invalid direction. Please use "forward", "backward", "left", or "right".'}), 400
    return jsonify({'message': f'Moving {direction}.'})

@app.route('/toggle-mower-blades', methods=['POST'])
def toggle_mower_blades():
    state = request.json.get('state')
    if state == 'on':
        BladeController.set_speed(90)
    elif state == 'off':
        BladeController.set_speed(0)
    else:
        return jsonify({'error': 'Invalid state. Please use "on" or "off".'}), 400
    return jsonify({'message': f'Mower blades toggled {state}.'})

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
    # Load the coordinates from the file
    with open('user_polygon.json', 'r') as f:
        coordinates = json.load(f)
    return jsonify(coordinates)

@app.route('/get-path', methods=['GET'])
def get_path():
    start = ... #Determine start position
    goal = ... #Determine goal position
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

def gen(camera):
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

if __name__ == '__main__':
    # Start the sensor update thread
    sensor_thread = threading.Thread(target=update_sensors)
    sensor_thread.start()

    app.run(host='0.0.0.0', port=90, debug=True)

    # Set the flag to stop the sensor update thread
    stop_sensor_thread = True
    sensor_thread.join()  # Wait for the thread to finish