import gpsd
import time
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG, filename='gps_debug.log', filemode='w',
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Connect to the local gpsd
try:
    gpsd.connect()
except Exception as e:
    logging.error(f"Failed to connect to gpsd: {e}")

# Get gps position
try:
    packet = gpsd.get_current()
    # Print some data
    print("Latitude: ", packet.lat)
    print("Longitude: ", packet.lon)
    print("Altitude: ", packet.alt)
    print("Speed: ", packet.hspeed)
    logging.info(f"GPS Data: Lat: {packet.lat}, Lon: {packet.lon}, Alt: {packet.alt}, Speed: {packet.hspeed}")
except Exception as e:
    logging.error(f"Failed to get GPS data: {e}")