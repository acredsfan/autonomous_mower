from sensor_interface import get_sensor_data
from navigation_system import GpsLatestPosition
from hardware_interface import SensorInterface

import paho.mqtt.client as mqtt

# MQTT broker details
MQTT_BROKER = "192.168.86.90"
MQTT_PORT = 1883
MQTT_KEEPALIVE = 60

# Create MQTT client
client = mqtt.Client()

# Connect to MQTT broker
client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)

# Retrieve sensor data, location, and status
sensor_data = get_sensor_data()

# Publish sensor data, location
client.publish("sensor_data", sensor_data)
client.publish("location", location)

# Disconnect from MQTT broker
client.disconnect()