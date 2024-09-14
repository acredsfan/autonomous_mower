from constants import polygon_coordinates, min_lat, max_lat, min_lng, max_lng
from navigation_system.gps import GpsNmeaPositions, GpsLatestPosition
import math
import time
import json
import sys
import os
from utils import LoggerConfig
import utm
from hardware_interface.sensor_interface import SensorInterface
sensor_interface = SensorInterface()


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
        """Estimate the current position using GPS UTM data
        fused with IMU data from the BNO085."""
        """Fuse GPS and IMU data for position estimation."""
        # Get latest GPS and IMU data
        gps_data = self.latest_position.get_latest_position()
        imu_data = sensor_interface.update_sensors()

        if gps_data and imu_data:
            # Extract relevant data
            gps_lat, gps_lon = gps_data['latitude'], gps_data['longitude']
            imu_heading = imu_data['heading']

            # Simple complementary filter
            alpha = 0.95  # Adjust this value to tune the filter

            # If this is the first GPS reading, initialize the fused position
            if self.fused_position is None:
                self.fused_position = (gps_lat, gps_lon)

            # Predict position based on IMU heading and previous fused position
            predicted_lat, predicted_lon = self.predict_position(
                self.fused_position,
                imu_heading,
                self.time_since_last_update
            )

            # Update fused position using the complementary filter
            self.fused_position = (
                alpha * predicted_lat + (1 - alpha) * gps_lat,
                alpha * predicted_lon + (1 - alpha) * gps_lon
            )

            self.time_since_last_update = 0  # Reset timer

        else:
            # If GPS is unavailable,
            # rely solely on IMU for short-term prediction
            if imu_data:
                predicted_lat, predicted_lon = self.predict_position(
                    self.fused_position,
                    imu_heading,
                    self.time_since_last_update
                )
                self.fused_position = (predicted_lat, predicted_lon)
                self.time_since_last_update += 1  # Increment timer
        return self.fused_position

    def predict_position(self, position, heading, time_delta):
        """Predict the next position based on the current position,
        heading, and time."""
        # Convert heading to radians
        heading_rad = math.radians(heading)

        # Calculate distance traveled based on speed and time
        speed = sensor_interface.update_sensors().get("speed")
        distance = speed * time_delta

        # Calculate the change in latitude and longitude
        lat, lon = position
        lat_change = distance * math.cos(heading_rad)
        lon_change = distance * math.sin(heading_rad)

        # Predict the next position
        predicted_lat = lat + lat_change
        predicted_lon = lon + lon_change

        return predicted_lat, predicted_lon

    def estimate_orientation(self):
        """Estimate the current orientation using compass data."""
        try:
            compass_data = sensor_interface.update_sensors().get("compass")
            if compass_data is not None:
                x, y, z = compass_data
                self.current_heading = math.degrees(math.atan2(y, x))
                if self.current_heading < 0:
                    self.current_heading += 360
            else:
                logging.warning("Compass data is None.")
        except Exception:
            logging.exception("An error occurred while "
                              "estimating orientation")

    def update(self):
        """Update the position and orientation of the mower."""
        self.estimate_position()
        self.estimate_orientation()
        if not self.is_within_yard(
            self.current_latitude,
            self.current_longitude
        ):
            logging.warning("Outside yard boundary!")

    def is_within_yard(self, lat, lon):
        """Check if the current position is within the yard boundary."""
        return (
            self.min_lat <= lat <= self.max_lat and
            self.min_lng <= lon <= self.max_lng
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
