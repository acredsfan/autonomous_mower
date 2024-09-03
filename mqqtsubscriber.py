# MQQT subscriber for optional remote RPi 5 with AI Kit to process data from Camera and Sensors and make code improvements
import paho.mqtt.client as mqtt

def on_message(client, userdata, message):
    print(f"Received message: {message.payload.decode()} on topic {message.topic}")

client = mqtt.Client()
client.connect("pi5_ip_address", 1883, 60)
client.subscribe("mower/status")
client.on_message = on_message
client.loop_forever()
