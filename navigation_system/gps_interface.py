"""
GPS interface module. 

Provides interface to GPSD for getting GPS data.

Class GPSInterface:

    Initializes connection to GPSD on creation.

    Method read_gps_data():
        Gets current GPS data from GPSD.
        Returns dict with GPS info if fix, else None.

    Method close():
        Closes connection to GPSD.

"""
import gpsd
import time
import logging

# Initialize logging
logging.basicConfig(filename='main.log', level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')

class GPSInterface:
    def __init__(self):
        gpsd.connect()

    def read_gps_data(self):
        packet = gpsd.get_current()
        if packet.mode >= 2:  # 2D or 3D fix
            return {
                'latitude': packet.lat,
                'longitude': packet.lon,
                'altitude': packet.alt,
                'speed': packet.hspeed,  # Horizontal speed
                'timestamp': packet.time,
                'mode': packet.mode,
            }
        else:
            return None

    def close(self):
        self.gpsd.close()