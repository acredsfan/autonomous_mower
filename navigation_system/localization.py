from constants import polygon_coordinates, min_lat, max_lat, min_lng, max_lng
from navigation_system.gps import GpsNmeaPositions, GpsLatestPosition
import math
import time
import json
import sys
import os
from utils import LoggerConfig
import utm


def utm_to_latlon(easting, northing, zone_number, zone_letter):
    """Convert UTM coordinates to latitude and longitude."""
    lat, lon = utm.to_latlon(easting, northing, zone_number, zone_letter)
    return lat, lon


# Initialize logger
LoggerConfig.configure_logging()
logging = LoggerConfig.get_logger(__name__)

# Add the parent directory to the system path for importing modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class Localization:
    """Handles localization by estimating position and orientation."""

    def __init__(self):
        # Initialize GPS-related objects and set default values for position
        # and boundaries
        self.position_reader = GpsNmeaPositions(debug=False)
        self.latest_position = GpsLatestPosition(debug=False)
        self.position = None
        # Define the yard boundary coordinates
        self.yard_boundary = polygon_coordinates
        self.current_latitude = 0.0
        self.current_longitude = 0.0
        self.current_altitude = 0.0
        self.current_heading = 0.0
        self.min_lat = min_lat
        self.max_lat = max_lat
        self.min_lng = min_lng
        self.max_lng = max_lng

    def load_json_file(self, file_name):
        """Load data from a JSON file."""
        try:
            with open(file_name) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            logging.exception("An error occurred while loading JSON file")
            return []

    def estimate_position(self):
        """Estimate the current position using GPS data."""
        try:
            lines = self.position_reader.get_lines()
            positions = self.position_reader.run(lines)
            # Convert NMEA lines to positions
            if positions:
                ts, self.current_latitude, self.current_longitude = positions[-1]
                logging.info(
                    f"Current position: {self.current_latitude}, "
                    f"{self.current_longitude}, {self.current_altitude}"
                )
            else:
                logging.warning("GPS data is None.")
        except Exception as e:
            logging.exception(f"An error occurred while estimating position: {e}")

    def estimate_orientation(self):
        """Estimate the current orientation using compass data."""
        from hardware_interface import SensorInterface

        try:
            compass_data = SensorInterface.update_sensors().get("compass")
            if compass_data is not None:
                x, y, z = compass_data
                self.current_heading = math.degrees(math.atan2(y, x))
                if self.current_heading < 0:
                    self.current_heading += 360
            else:
                logging.warning("Compass data is None.")
        except Exception:
            logging.exception("An error occurred while estimating orientation")

    def update(self):
        """Update the position and orientation of the mower."""
        self.estimate_position()
        self.estimate_orientation()
        if not self.is_within_yard(self.current_latitude, self.current_longitude):
            logging.warning("Outside yard boundary!")

    def is_within_yard(self, lat, lon):
        """Check if the current position is within the yard boundary."""
        return (
            self.min_lat <= lat <= self.max_lat and self.min_lng <= lon <= self.max_lng
        )


def main():
    """Run the Localization update loop."""
    localization = Localization()
    try:
        while True:
            localization.update()
            print(
                f"Latitude: {localization.current_latitude}, "
                f"Longitude: {localization.current_longitude}, "
                f"Altitude: {localization.current_altitude}, "
                f"Heading: {localization.current_heading}"
            )
            time.sleep(1)
    except KeyboardInterrupt:
        print("Program terminated by user.")


if __name__ == "__main__":
    main()
