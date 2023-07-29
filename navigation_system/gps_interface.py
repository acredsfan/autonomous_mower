import gpsd
import time

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