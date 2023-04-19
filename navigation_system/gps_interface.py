# This module is responsible for interfacing with the Neo-8M GPS Module and processing the GPS data. 
# It will include functions to initialize the GPS module, read the raw GPS data (latitude, longitude, altitude, and possibly other relevant data), 
# and convert the data into a format that can be used by the other modules in the navigation system, 
# such as converting latitude and longitude into a local coordinate system (e.g., meters from a reference point).

# gps_interface.py
import serial
from gps import GPS

class GPSInterface:
    def __init__(self, port='/dev/serial0', baud_rate=9600, timeout=1):
        self.serial = serial.Serial(port, baud_rate, timeout=timeout)
        self.serial.flush()
        self.gps = GPS()

    def read_gps_data(self):
        raw_data = self.serial.readline().decode('utf-8', errors='ignore').strip()
        if raw_data:
            self.gps.update(raw_data)

        return {
            'latitude': self.gps.latitude,
            'longitude': self.gps.longitude,
            'altitude': self.gps.altitude,
            'speed': self.gps.speed,
            'timestamp': self.gps.timestamp,
            'satellites': self.gps.satellites,
            'quality': self.gps.fix_quality,
            'pdop': self.gps.pdop,
            'hdop': self.gps.hdop,
            'vdop': self.gps.vdop,
            'raw_data': raw_data
        }

    def close(self):
        self.serial.close()
