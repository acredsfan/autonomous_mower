from flask import Flask, render_template, request, jsonify
import sys
sys.path.append('/home/pi/autonomous_mower')
from hardware_interface.motor_controller import MotorController
from hardware_interface.relay_controller import RelayController

app = Flask(__name__)

# Replace this with your actual sensor data and other information
sensor_data = "Sample sensor data"
mowing_status = "Not mowing"
next_scheduled_mow = "2023-05-06 12:00:00"
live_view_url = "/static/live_view.jpg"

# Initialize the motor and relay controllers
MotorController.init_motor_controller()
#RelayController.init_relay_controller()

def init_web_interface():
    # Initialize the web interface
    # Add code here to initialize the web interface
    pass

def start_web_interface():
    # Start the web interface
    # Add code here to start the web interface
    pass

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
    return render_template('area.html')


@app.route('/settings')
def settings():
    return render_template('settings.html')

@app.route('/camera')
def camera():
    return render_template('camera_stream.html')


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


@app.route('/save_mowing_area', methods=['POST'])
def save_mowing_area():
    global mowing_area
    mowing_area = request.json['coordinates']
    return jsonify(success=True)


@app.route('/save_settings', methods=['POST'])
def save_settings():
    mow_days = request.form.get('mow_days')
    mow_hours = request.form.get('mow_hours')
    # Add code to save the settings
    return jsonify(success=True)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)