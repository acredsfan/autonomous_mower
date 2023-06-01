from flask import Flask, render_template, request, jsonify, send_from_directory, Response
import sys
import json
sys.path.append('/home/pi/autonomous_mower')
from hardware_interface import MotorController, sensor_interface
import subprocess
import os
from dotenv import load_dotenv
from camera import VideoCamera

app = Flask(__name__)
sensors = sensor_interface.SensorInterface()

# Replace this with your actual sensor data and other information
battery_charge = {"battery_voltage": sensors.read_ina3221(3)}
solar_status = {"Solar Panel Voltage": sensors.read_ina3221(1)}
speed = {"speed": sensors.read_mpu9250_accel()}
heading = {"heading": sensors.read_mpu9250_compass()}
bme280_data = sensors.read_bme280()
temperature = bme280_data['temperature_f']
humidity = bme280_data['humidity']
pressure = bme280_data['pressure']
left_distance = {"left_distance": sensors.read_vl53l0x_left()}
right_distance = {"right_distance": sensors.read_vl53l0x_right()}
mowing_status = "Not mowing"
next_scheduled_mow = "2023-05-06 12:00:00"

dotenv_path = os.path.join(os.path.dirname(__file__),'home' ,'pi', 'autonomous_mower', '.env')
load_dotenv(dotenv_path)
google_maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY")

first_request = True

@app.route('/static/<path:path>')
def send_js(path):
    return send_from_directory('static', path)

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
    return Response(gen(VideoCamera()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# Add routes for AJAX requests here
@app.route('/move', methods=['POST'])
def move():
    direction = request.json.get('direction')
    if direction == 'forward':
        set_motor_direction('forward')
    elif direction == 'backward':
        set_motor_direction('backward')
    elif direction == 'left':
        set_motor_direction('left')
    elif direction == 'right':
        set_motor_direction('right')
    else:
        return jsonify({'error': 'Invalid direction. Please use "forward", "backward", "left", or "right".'}), 400
    return jsonify({'message': f'Moving {direction}.'})


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

@app.route('/save-mowing-area', methods=['POST'])
def save_mowing_area():
    # Save the coordinates to the file
    coordinates = request.get_json()
    with open('user_polygon.json', 'w') as f:
        json.dump(coordinates, f)
    return jsonify({'message': 'Area saved.'})

def set_motor_direction(direction):
    # Set the motor direction
    MotorController.set_direction(direction)

def toggle_mower_blades():
    # Toggle the mower blades
    RelayController.toggle_relay()

def stop_motors():
    # Stop the motors
    MotorController.stop_motors()

def gen(camera):
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=90, debug=True)
