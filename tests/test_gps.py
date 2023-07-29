import gpsd
import time

# Connect to the local gpsd
gpsd.connect()

# Get gps position
packet = gpsd.get_current()

# Print some data
print("Latitude: ", packet.lat)
print("Longitude: ", packet.lon)
print("Altitude: ", packet.alt)
print("Speed: ", packet.speed)