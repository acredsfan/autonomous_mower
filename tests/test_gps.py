import gpsd
import time

# Connect to the local gpsd
gpsd.connect()

while True:
    # Get gps position
    packet = gpsd.get_current()

    print("Latitude: ", packet.lat)
    print("Longitude: ", packet.lon)
    print("Altitude: ", packet.alt)
    print("Speed: ", packet.speed)
    
    # Wait for a bit before getting the next packet
    time.sleep(1)
