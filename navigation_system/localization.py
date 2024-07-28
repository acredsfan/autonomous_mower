import math
import time
import json
import logging
from navigation_system.gps import GpsNmeaPositions, GpsLatestPosition
from hardware_interface.sensor_interface import SensorInterface
from hardware_interface import RoboHATController
from constants import EARTH_RADIUS, polygon_coordinates, min_lat, max_lat, min_lng, max_lng

# Configure logging
logging.basicConfig(filename='main.log', level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')

class Localization:
    def __init__(self, cfg):
        self.gps = GpsNmeaPositions()
        self.latest_position = GpsLatestPosition()
        self.motor_controller = RoboHATController(cfg)
        self.position_reader = GpsNmeaPositions()
        self.position = None
        self.yard_boundary = polygon_coordinates  # Define your yard boundary coordinates here
        self.current_latitude = 0
        self.current_longitude = 0
        self.current_altitude = 0
        self.current_heading = 0
        self.sensor_interface = SensorInterface()
        self.min_lat = min_lat
        self.max_lat = max_lat
        self.min_lng = min_lng
        self.max_lng = max_lng

    def load_json_file(self, file_name):
        """Load data from a JSON file."""
        try:
            with open(file_name) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.exception('An error occurred while loading JSON file')
            return []

    def estimate_position(self):
        """Estimate the current position using GPS data."""
        lines = self.gps.run()  # Read NMEA lines from GPS
        positions = self.position_reader.run(lines)  # Convert NMEA lines to positions
        if positions:
            ts, self.current_latitude, self.current_longitude = positions[-1]
            logging.info(f"Current position: {self.current_latitude}, {self.current_longitude}, {self.current_altitude}")
        else:
            logging.warning("GPS data is None.")

    def estimate_orientation(self):
        """Estimate the current orientation using compass data."""
        try:
            compass_data = self.sensor_interface.read_mpu9250_compass()
            if compass_data is not None:
                x, y, z = compass_data
                self.current_heading = math.degrees(math.atan2(y, x))
                if self.current_heading < 0:
                    self.current_heading += 360
            else:
                logging.warning("Compass data is None.")
        except Exception as e:
            logging.exception('An error occurred while estimating orientation')

    def update(self):
        """Update the position and orientation of the mower."""
        self.estimate_position()
        self.estimate_orientation()
        if not self.is_within_yard(self.current_latitude, self.current_longitude):
            logging.warning("Outside yard boundary!")

    def is_within_yard(self, lat, lon):
        """Check if the current position is within the yard boundary."""
        return self.min_lat <= lat <= self.max_lat and self.min_lng <= lon <= self.max_lng

if __name__ == '__main__':
    class Config:
        MM1_SERIAL_PORT = '/dev/ttyUSB0'
        MM1_MAX_FORWARD = 2000
        MM1_MAX_REVERSE = 1000
        MM1_STOPPED_PWM = 1500
        MM1_STEERING_MID = 1500
        AUTO_RECORD_ON_THROTTLE = True
        JOYSTICK_DEADZONE = 0.1

    cfg = Config()
    localization = Localization(cfg)
    try:
        while True:
            localization.update()
            print(f"Latitude: {localization.current_latitude}, Longitude: {localization.current_longitude}, Altitude: {localization.current_altitude}, Heading: {localization.current_heading}")
            time.sleep(1)
    except KeyboardInterrupt:
        print("Program terminated by user.")
