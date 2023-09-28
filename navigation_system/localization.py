# Import required modules
import math
import time
from navigation_system import GPSInterface
import logging
import json
from constants import EARTH_RADIUS, polygon_coordinates

class Localization:
    def __init__(self):
        logging.basicConfig(filename='main.log', level=logging.DEBUG)
        self.gps = GPSInterface()
        self.yard_boundary = polygon_coordinates
        self.current_latitude = 0
        self.current_longitude = 0
        self.current_altitude = 0
        self.current_heading = 0

    def load_json_file(self, file_name):
        try:
            with open(file_name) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.warning(f"Could not load {file_name}: {e}")
            return []

    def estimate_position(self):
        data = self.gps.read_gps_data()
        if data:
            self.current_latitude = data['latitude']
            self.current_longitude = data['longitude']
            self.current_altitude = data['altitude']

    def estimate_orientation(self):
        from hardware_interface.sensor_interface import sensor_interface
        try:
            compass_data = sensor_interface.sensor_data['compass']
            self.current_heading = math.degrees(math.atan2(compass_data['y'], compass_data['x']))
            if self.current_heading < 0:
                self.current_heading += 360
        except Exception as e:
            logging.error(f"Error estimating orientation: {e}")

    def update(self):
        self.estimate_position()
        self.estimate_orientation()
        lat, lon = self.current_latitude, self.current_longitude
        if not self.is_within_yard(lat, lon):
            logging.warning("Outside yard boundary!")

    def is_within_yard(self, lat, lon):
        for boundary in self.yard_boundary:
            if boundary['min_lat'] <= lat <= boundary['max_lat'] and boundary['min_lng'] <= lon <= boundary['max_lng']:
                return True
        return False

if __name__ == '__main__':
    localization = Localization()
    while True:
        localization.update()
        print(f"Latitude: {localization.current_latitude}, Longitude: {localization.current_longitude}, Altitude: {localization.current_altitude}, Heading: {localization.current_heading}")
        time.sleep(1)