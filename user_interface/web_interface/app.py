from flask import Flask, render_template, request, jsonify, send_from_directory
import sys
import json
sys.path.append('/home/pi/autonomous_mower')
from hardware_interface.motor_controller import MotorController
from hardware_interface.relay_controller import RelayController
import subprocess
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst
import os
from dotenv import load_dotenv

app = Flask(__name__)
Gst.init(None)

# Replace this with your actual sensor data and other information
sensor_data = "Sample sensor data"
mowing_status = "Not mowing"
next_scheduled_mow = "2023-05-06 12:00:00"
live_view_url = "http://pimowbot.local:8080/stream.mjpg"

dotenv_path = os.path.join(os.path.dirname(__file__),'home' ,'pi', 'autonomous_mower', '.env')
load_dotenv(dotenv_path)
google_maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY")

# Define the libcamera-vid command
libcamera_cmd = ["gst-launch-1.0", "libcamerasrc", "!", "video/x-raw", "colorimetry=bt709", "format=NV12", "width=1280", "width=720", "framerate=30/1", "!", "jpegenc", "!", "multipartmux", "!", "tcpserversink", "host=0.0.0.0", "port=8080"]
                                  
# Initialize the libcamera-vid subprocess
libcamera_process = None
# Initialize the GStreamer pipeline
pipeline = None

# Initialize the motor and relay controllers
MotorController.init_motor_controller()
#RelayController.init_relay_controller()

first_request = True

@app.route('/static/<path:path>')
def send_js(path):
    return send_from_directory('static', path)

@app.route('/')
def index():
    return render_template('status.html', sensor_data=sensor_data, mowing_status=mowing_status, next_scheduled_mow=next_scheduled_mow, live_view_url=live_view_url)


@app.route('/status')
def status():
    return render_template('status.html', sensor_data=sensor_data, mowing_status=mowing_status, next_scheduled_mow=next_scheduled_mow, live_view_url=live_view_url)


@app.route('/control')
def control():
    return render_template('control.html', live_view_url=live_view_url)


@app.route('/area')
def area():
    return render_template('area.html', google_maps_api_key=google_maps_api_key)


@app.route('/settings')
def settings():
    return render_template('settings.html')

@app.route('/camera')
def camera():
    return render_template('camera.html')


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
        data = json.load(f)

    # Return the coordinates
    return jsonify(data)


@app.route('/save-mowing-area', methods=['POST'])
def save_mowing_area():
    # Get the data from the request
    data = request.get_json()

    # Print the data to console for debugging
    print(data)

    # Save the data to a file
    with open('user_polygon.json', 'w') as f:
        json.dump(data, f)

    return jsonify({'message': 'Mowing area saved'})


@app.route('/save_settings', methods=['POST'])
def save_settings():
    mow_days = request.form.get('mow_days')
    mow_hours = request.form.get('mow_hours')
    # Add code to save the settings
    return jsonify(success=True)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)