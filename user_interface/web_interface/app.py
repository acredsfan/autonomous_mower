from flask import Flask, render_template, request, jsonify, send_from_directory
import sys
import json
sys.path.append('/home/pi/autonomous_mower')
from hardware_interface import MotorController, sensor_interface
import subprocess
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst
import os
from dotenv import load_dotenv

app = Flask(__name__)
Gst.init(None)
sensors = sensor_interface.SensorInterface()

# # Replace this with your actual sensor data and other information
# battery_charge = {"battery_voltage": sensors.read_ina3221(3)}
# solar_status = {"Solar Panel Voltage": sensors.read_ina3221(1)}
# speed = {"speed": sensors.read_mpu9250_gyro()}
# heading = {"heading": sensors.read_mpu9250_compass()}
# temperature = {"temperature": sensors.read_bme280()}
# humidity = {"humidity": 0}
# pressure = {"pressure": 0}
# left_distance = {"left_distance": 0}
# right_distance = {"right_distance": 0}
# mowing_status = "Not mowing"
# next_scheduled_mow = "2023-05-06 12:00:00"

dotenv_path = os.path.join(os.path.dirname(__file__),'home' ,'pi', 'autonomous_mower', '.env')
load_dotenv(dotenv_path)
google_maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY")

# Define the gstreamer pipeline for h.264 RTSP streaming
gst_pipeline = ("rtspsrc location=rtsp://pimowbot.local:8554/stream ! "
                "rtph264depay ! h264parse ! avdec_h264 ! "
                "videoconvert ! autovideosink")

# Initialize the libcamera-vid subprocess
libcamera_process = None
# Initialize the GStreamer pipeline
pipeline = Gst.parse_launch(gst_pipeline)

# Initialize the motor and relay controllers
#MotorController.init_motor_controller()
#RelayController.init_relay_controller()

first_request = True

@app.route('/static/<path:path>')
def send_js(path):
    return send_from_directory('static', path)

@app.route('/')
def index():
    sensor_data = get_sensor_data()
    return render_template('status.html', **sensor_data, mowing_status=mowing_status, next_scheduled_mow=next_scheduled_mow)

@app.route('/status')
def status():
    sensor_data = get_sensor_data()
    return render_template('status.html', **sensor_data, mowing_status=mowing_status, next_scheduled_mow=next_scheduled_mow)

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

def start_libcamera():
    global libcamera_process
    if libcamera_process is not None:
        # If the libcamera-vid subprocess is already running, kill it
        libcamera_process.kill()
    libcamera_cmd = ["gst-launch-1.0", "libcamerasrc", "!", "video/x-raw", 
                     "!", "videoconvert", 
                     "!", "x264enc", "tune=zerolatency", "bitrate=500", 
                     "!", "rtph264pay", "pt=96", "config-interval=1", 
                     "!", "udpsink", "host=0.0.0.0", "port=80", "sync=false"]
    libcamera_process = subprocess.Popen(libcamera_cmd)

def get_sensor_data():
    """Get all sensor data."""
    sensor_data = {}
    sensor_data["battery_charge"] = sensors.read_ina3221(3)
    sensor_data["solar_status"] = sensors.read_ina3221(1)
    sensor_data["speed"] = sensors.read_mpu9250_gyro()
    sensor_data["heading"] = sensors.read_mpu9250_compass()
    sensor_data["temperature"] = sensors.read_bme280["temperature"]
    sensor_data["humidity"] = sensors.read_bme280["humidity"]
    sensor_data["pressure"] = sensors.read_bme280["pressure"]
    sensor_data["left_distance"] = sensors.read_vl53l0x_left()
    sensor_data["right_distance"] = sensors.read_vl53l0x_right()
    return sensor_data

if __name__ == '__main__':
    start_libcamera()
    app.run(host='0.0.0.0', port=80, debug=True)
