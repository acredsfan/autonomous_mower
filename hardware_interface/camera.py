# camera.py - Pi 4

import os
import time
import threading
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
from dotenv import load_dotenv
import sys
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)
from utilities import LoggerConfigInfo as LoggerConfig

# Initialize logger
logging = LoggerConfig.get_logger(__name__)

# Load environment variables from .env file
load_dotenv()
PI5_IP = os.getenv("OBJECT_DETECTION_IP")  # IP address of the Pi 5

# Initialize GStreamer
Gst.init(None)

def gst_pipeline_thread():
    """Function that runs the GStreamer pipeline to stream video to Pi 5."""
    pipeline_str = f"""
        libcamerasrc ! 
        video/x-raw,width=640,height=480,framerate=30/1 ! 
        videoconvert ! 
        x264enc tune=zerolatency bitrate=500 speed-preset=superfast ! 
        rtph264pay config-interval=1 pt=96 ! 
        udpsink host={PI5_IP} port=5000
    """
    pipeline = Gst.parse_launch(pipeline_str)

    # Start the pipeline
    pipeline.set_state(Gst.State.PLAYING)

    # Run the pipeline
    bus = pipeline.get_bus()
    while True:
        message = bus.timed_pop_filtered(10000, Gst.MessageType.ERROR | Gst.MessageType.EOS)
        if message:
            if message.type == Gst.MessageType.ERROR:
                err, debug = message.parse_error()
                logging.error(f"GStreamer Error: {err}, {debug}")
                break
            elif message.type == Gst.MessageType.EOS:
                logging.info("GStreamer End of Stream")
                break
        time.sleep(0.1)
    pipeline.set_state(Gst.State.NULL)

if __name__ == "__main__":
    # Start GStreamer pipeline in a separate thread
    gst_thread = threading.Thread(target=gst_pipeline_thread)
    gst_thread.daemon = True
    gst_thread.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt: Stopping the application.")






# # camera.py



# import io
# import os
# import time
# import threading
# from threading import Condition
# from http import server
# import numpy as np
# import tflite_runtime.interpreter as tflite
# from dotenv import load_dotenv
# import requests
# from PIL import Image, ImageDraw, ImageFont

# from utilities import LoggerConfigInfo as LoggerConfig
# from hardware_interface.camera_instance import get_camera_instance

# # Initialize logger
# logging = LoggerConfig.get_logger(__name__)

# # Load environment variables from .env file
# load_dotenv()
# PATH_TO_OBJECT_DETECTION_MODEL = os.getenv("OBSTACLE_MODEL_PATH")
# PI5_IP = os.getenv("OBJECT_DETECTION_IP")  # IP address of the Pi 5
# LABEL_MAP_PATH = os.getenv("LABEL_MAP_PATH")  # Path to label map file
# MIN_CONF_THRESHOLD = float(os.getenv('MIN_CONF_THRESHOLD', '0.5'))

# # Initialize TFLite interpreter for local detection
# interpreter = tflite.Interpreter(model_path=PATH_TO_OBJECT_DETECTION_MODEL)
# interpreter.allocate_tensors()
# input_details = interpreter.get_input_details()
# output_details = interpreter.get_output_details()
# height = input_details[0]['shape'][1]
# width = input_details[0]['shape'][2]
# floating_model = (input_details[0]['dtype'] == np.float32)
# input_mean = 127.5
# input_std = 127.5

# # Load labels
# with open(LABEL_MAP_PATH, 'r') as f:
#     labels = [line.strip() for line in f.readlines()]
# if labels[0] == '???':
#     del(labels[0])

# # Get the camera instance
# camera = get_camera_instance()

# # A flag to indicate whether to use remote detection
# use_remote_detection = True

# # Condition variable for thread synchronization
# frame_condition = Condition()
# frame = None

# class StreamingOutput(object):
#     def __init__(self):
#         self.frame = None
#         self.condition = Condition()

#     def set_frame(self, frame):
#         with self.condition:
#             self.frame = frame
#             self.condition.notify_all()

# output = StreamingOutput()

# def capture_frames():
#     """Capture frames from Picamera2 and process them."""
#     while True:
#         # Capture the frame
#         frame = camera.capture_array()
#         # Process the frame
#         processed_frame = process_frame(frame)
#         # Encode the frame as JPEG
#         img = Image.fromarray(processed_frame)
#         buf = io.BytesIO()
#         img.save(buf, format='JPEG')
#         frame_bytes = buf.getvalue()
#         # Set the frame in the output
#         output.set_frame(frame_bytes)


# def detect_obstacles_local(image):
#     """Perform local image classification using TFLite."""
#     # Resize the image to the required input size
#     image_resized = image.resize((width, height))
#     input_data = np.expand_dims(image_resized, axis=0)
#     if floating_model:
#         input_data = (np.float32(input_data) - input_mean) / input_std
#     else:
#         input_data = np.uint8(input_data)
#     interpreter.set_tensor(input_details[0]['index'], input_data)
#     interpreter.invoke()
#     # Get the output probabilities
#     output_data = interpreter.get_tensor(output_details[0]['index'])[0]
#     # Get the top predicted class index
#     top_k = 1  # You can get more predictions by increasing this value
#     top_indices = np.argsort(-output_data)[:top_k]
#     detected_objects = []
#     for idx in top_indices:
#         class_name = labels[idx]
#         score = output_data[idx]
#         detected_objects.append({'name': class_name, 'score': score})
#     return detected_objects


# def detect_obstacles_remote(image):
#     """Send the image to Pi 5 for remote detection."""
#     try:
#         # Convert image to bytes
#         img_byte_arr = io.BytesIO()
#         image.save(img_byte_arr, format='JPEG')
#         img_bytes = img_byte_arr.getvalue()

#         response = requests.post(f'http://{PI5_IP}:5000/detect',
#                                  files={'image': ('image.jpg', img_bytes, 'image/jpeg')},
#                                  timeout=1)
#         if response.status_code == 200:
#             result = response.json()
#             return result.get('obstacle_detected', False)
#         else:
#             logging.warning("Failed to get a valid response from Pi 5.")
#             return False
#     except (requests.ConnectionError, requests.Timeout):
#         logging.warning("Pi 5 not reachable. Falling back to local detection.")
#         global use_remote_detection
#         use_remote_detection = False
#         return False

# def process_frame(frame):
#     """Process frames for obstacle detection and annotate them."""
#     image = Image.fromarray(frame)
#     if use_remote_detection:
#         obstacle_detected = detect_obstacles_remote(image)
#     else:
#         detected_objects = detect_obstacles_local(image)
#         # Draw bounding boxes on the image
#         draw = ImageDraw.Draw(image)
#         for obj in detected_objects:
#             xmin, ymin, xmax, ymax = obj['box']
#             draw.rectangle([xmin, ymin, xmax, ymax], outline='red', width=2)
#             label = f"{obj['name']}: {int(obj['score'] * 100)}%"
#             # Optional: Use a truetype font if available
#             try:
#                 font = ImageFont.truetype("arial.ttf", 15)
#             except IOError:
#                 font = ImageFont.load_default()
#             text_size = draw.textsize(label, font=font)
#             text_location = (xmin + 5, ymin + 5)
#             draw.rectangle([xmin, ymin, xmin + text_size[0] + 10, ymin + text_size[1] + 10],
#                            fill='red')
#             draw.text(text_location, label, fill='white', font=font)
#         obstacle_detected = len(detected_objects) > 0
#     # You can use obstacle_detected flag in your robot control logic
#     return np.array(image)

# def start_processing():
#     thread = threading.Thread(target=capture_frames)
#     thread.daemon = True
#     thread.start()

# class StreamingHandler(server.BaseHTTPRequestHandler):
#     def do_GET(self):
#         if self.path == '/video_feed':
#             self.send_response(200)
#             self.send_header('Age', '0')
#             self.send_header('Cache-Control', 'no-cache, private')
#             self.send_header('Pragma', 'no-cache')
#             self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
#             self.end_headers()
#             try:
#                 while True:
#                     with output.condition:
#                         output.condition.wait()
#                         frame = output.frame
#                         self.wfile.write(b'--FRAME\r\n')
#                         self.send_header('Content-Type', 'image/jpeg')
#                         self.send_header('Content-Length', str(len(frame)))
#                         self.end_headers()
#                         self.wfile.write(frame)
#                         self.wfile.write(b'\r\n')
#             except Exception as e:
#                 logging.warning('Removed streaming client %s: %s', self.client_address, str(e))
#         else:
#             self.send_error(404)
#             self.end_headers()

# def start_streaming_server():
#     address = ('', 8000)
#     server_instance = server.ThreadingHTTPServer(address, StreamingHandler)
#     server_thread = threading.Thread(target=server_instance.serve_forever)
#     server_thread.daemon = True
#     server_thread.start()

# if __name__ == "__main__":
#     start_processing()
#     start_streaming_server()
#     try:
#         while True:
#             time.sleep(1)
#     except KeyboardInterrupt:
#         camera.stop()
