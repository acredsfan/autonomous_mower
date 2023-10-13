# Import required modules
import math
import time
from navigation_system.gps_interface import GPSInterface
import logging
import json
from constants import EARTH_RADIUS, polygon_coordinates, min_lat, max_lat, min_lng, max_lng
from hardware_interface.sensor_interface import SensorInterface

class Localization:
    logging.info(f'Entering Function or Method')
    def __init__(self):
        logging.info(f'Entering Function or Method')
        logging.basicConfig(filename='main.log', level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
        self.gps = GPSInterface()
        self.yard_boundary = polygon_coordinates
        print(self.yard_boundary)
        self.current_latitude = 0
        self.current_longitude = 0
        self.current_altitude = 0
        self.current_heading = 0
        self.min_lat = min_lat
        self.max_lat = max_lat
        self.min_lng = min_lng
        self.max_lng = max_lng
        self.sensor_interface = SensorInterface()

    def load_json_file(self, file_name):
        logging.info(f'Entering Function or Method')
        try:
            with open(file_name) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.exception('An error occurred')
            logging.warning(f"Could not load {file_name}: {e}")
        return []

    def estimate_position(self):
        logging.info(f'Entering estimate_position()')
        data = self.gps.read_gps_data()
        logging.info(f'GPS data for estimate_position(): {data}')
        if data:
            self.current_latitude = data['latitude']
            self.current_longitude = data['longitude']
            self.current_altitude = data['altitude']
            print(f"Current position: {self.current_latitude}, {self.current_longitude}, {self.current_altitude}")
        else:
            logging.warning("GPS data is None.")

    def estimate_orientation(self):
        try:
            compass_data = self.sensor_interface.read_mpu9250_compass()
            
            # Check if compass_data is None
            if compass_data is not None:
                logging.info(f'Compass data: {compass_data}')
                x, y, z = compass_data['x'], compass_data['y'], compass_data['z']

                # Calculate the orientation angle in degrees
                self.current_heading = math.degrees(math.atan2(y, x))

                if self.current_heading < 0:
                    self.current_heading += 360
            else:
                logging.warning("Compass data is None.")
        except Exception as e:
            logging.exception('An error occurred')
            logging.error(f"Error estimating orientation: {e}")

    def update(self):
        logging.info(f'Entering Function or Method')
        self.estimate_position()
        self.estimate_orientation()
        lat, lon = self.current_latitude, self.current_longitude
        if not self.is_within_yard(lat, lon):
            logging.warning("Outside yard boundary!")

    def is_within_yard(self, lat, lon):
        logging.info(f'Entering Function or Method')
        if self.min_lat <= lat <= self.max_lat and self.min_lng <= lon <= self.max_lng:
            return True
        return False

if __name__ == '__main__':
    localization = Localization()
    while True:
        localization.update()
        print(f"Latitude: {localization.current_latitude}, Longitude: {localization.current_longitude}, Altitude: {localization.current_altitude}, Heading: {localization.current_heading}")
        time.sleep(1)