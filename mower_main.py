import paho.mqtt.client as mqtt
import json
import time
import dotenv
import os
from hardware_interface.sensor_interface import get_sensor_interface
import random
import sys

# Load environment variables
dotenv.load_dotenv()

# Add the path to the sys path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

# MQTT settings
BROKER = os.getenv("MQTT_BROKER")

# Simulated sensor data (replace with real sensor integrations)
def get_sensor_data():
    return {
        "camera": "image_data",  # Placeholder, integrate camera feed or LiDAR here
        "position": {"x": random.uniform(0, 10), "y": random.uniform(0, 10)},
        "obstacles": random.choice([True, False])  # Simulated obstacle detection
    }

# MQTT callbacks
def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    client.subscribe(COMMAND_TOPIC)

def on_message(client, userdata, msg):
    command = json.loads(msg.payload.decode())
    print(f"Received command: {command}")
    # Execute movement based on command received
    execute_command(command)

def execute_command(command):
    # Placeholder for movement code
    print(f"Executing command: {command}")
    # Add code to control motors, etc.

# MQTT setup
client = mqtt.Client(CLIENT_ID)
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT, 60)

# Main loop
client.loop_start()
try:
    while True:
        sensor_data = get_sensor_data()
        client.publish(SENSOR_TOPIC, json.dumps(sensor_data))
        time.sleep(1)  # Adjust based on desired update frequency
except KeyboardInterrupt:
    client.loop_stop()
    client.disconnect()
