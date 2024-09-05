import sys
import os
import time

# Adjust the system path to include the parent directory if needed
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the necessary classes from your gps.py
from gps import GpsPosition, GpsLatestPosition
from hardware_interface.sensor_interface import SensorInterface
from donkeycar.parts.serial_port import SerialPort

# MQTT and other dependencies
import paho.mqtt.client as mqtt

# MQTT broker details
MQTT_BROKER = "192.168.86.90"
MQTT_PORT = 1883
MQTT_KEEPALIVE = 60

# Create MQTT client
client = mqtt.Client()

# Connect to MQTT broker
client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)

# Initialize GPS with your specific settings
serial_port = SerialPort('/dev/ttyUSB0', baudrate=115200, timeout=0.5)
gps_position = GpsPosition(serial_port, "NTRIP_USER", "NTRIP_PASS", "NTRIP_URL", "MOUNTPOINT", 2101, debug=True)

# Example usage of GpsLatestPosition to get the latest position
gps_latest = GpsLatestPosition()
while True:
    # Fetch latest GPS coordinates
    latest_position = gps_position.run()  # Run can be replaced with run_threaded if running in a threaded mode

    if latest_position:
        timestamp, x, y = latest_position
        print(f"Current GPS Position: X: {x}, Y: {y}")

        # Publish location to MQTT broker
        client.publish("location", f"{x}, {y}")

    # Simulating sensor data update from SensorInterface
    sensor_data = SensorInterface.update_sensors()

    # Publish sensor data to MQTT broker
    client.publish("sensor_data", str(sensor_data))

    time.sleep(1)  # Adjust sleep time as needed

# Disconnect from MQTT broker
client.disconnect()