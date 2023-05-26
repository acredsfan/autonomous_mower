from flask import Flask, render_template, request, jsonify, send_from_directory, Response
import cv2
import threading
import numpy as np

app = Flask(__name__)

# Replace this with your actual sensor data and other information
sensor_data = "Sample sensor data"
mowing_status = "Not mowing"
next_scheduled_mow = "2023-05-06 12:00:00"
live_view_url = "http://pimowbot.local:8080/stream.mjpg"

# Initialize the camera capture
camera = cv2.VideoCapture(0)
camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
camera.set(cv2.CAP_PROP_FPS, 30)

# Initialize the MJPEG streaming thread
streaming_thread = None
streaming = False

def generate_frames():
    camera = cv2.VideoCapture(0)  # Use 0 for built-in camera, or the specific camera number if you have more than one camera
    while True:
        success, frame = camera.read()  # read the camera frame
        if not success:
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')  # concat frame one by one and show result


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
    return render_template('area.html')

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
    # Add code to handle motor movement
    return jsonify({'message': f'Moving {direction}.'})

@app.route('/start-mowing', methods=['POST'])
def start_mowing():
    # Add code to start mowing
    return jsonify({'message': 'Mower started.'})

@app.route('/stop-mowing', methods=['POST'])
def stop_mowing():
    # Add code to stop mowing
    return jsonify({'message': 'Mower stopped.'})

@app.route('/get-mowing-area', methods=['GET'])
def get_mowing_area():
    # Load the coordinates from the file
    # Add code to load and return mowing area coordinates
    return jsonify(data)

@app.route('/save-mowing-area', methods=['POST'])
def save_mowing_area():
    # Get the data from the request
    data = request.get_json()
    # Add code to save mowing area coordinates
    return jsonify({'message': 'Mowing area saved'})

@app.route('/save_settings', methods=['POST'])
def save_settings():
    mow_days = request.form.get('mow_days')
    mow_hours = request.form.get('mow_hours')
    # Add code to save the settings
    return jsonify(success=True)

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)