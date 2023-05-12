# This module is responsible for estimating the robot's position and orientation within its environment. 
# It will take sensor data, such as from the GPS module and the MPU-9250 Compass Module, and use it to compute the robot's location and heading. 
# This may involve implementing sensor fusion algorithms, such as a Kalman filter or a particle filter, to combine the data from multiple sensors and 
# obtain a more accurate estimate of the robot's pose.

# localization.py
import math
import sensor_interface
import gpsd

# Global variables
current_latitude = 0
current_longitude = 0
current_altitude = 0
current_heading = 0

class Localization:
    def __init__(self, port='/dev/serial0', baud_rate=9600, timeout=1):
        self.gpsd = gpsd.GPSD(port=port, baudrate=baud_rate, timeout=timeout)

    def gps_to_meters(self, lat1, lon1, lat2, lon2):
        """
        Convert the difference between two GPS coordinates (latitude and longitude) to meters.
        """
        R = 6371e3  # Earth's radius in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        distance = R * c
        return distance


    def estimate_position(self):
        global current_latitude, current_longitude, current_altitude

        data = self.gpsd.next()
        if data['class'] == 'TPV':
            current_latitude = data['lat']
            current_longitude = data['lon']
            current_altitude = data['alt']


    def estimate_orientation(self):
        global current_heading

        compass_data = sensor_interface.read_mpu9250_compass()

        try:
            current_heading = math.degrees(math.atan2(compass_data['y'], compass_data['x']))
            if current_heading < 0:
                current_heading += 360
        except Exception as e:
            print(f"Error estimating orientation: {e}")


    def get_current_position(self):
        return current_latitude, current_longitude, current_altitude


    def get_current_orientation(self):
        return current_heading


    def update(self):
        self.estimate_position()
        self.estimate_orientation()


    if __name__ == '__main__':
        localization = Localization()

        while True:
            localization.update()
            lat, lon, alt = localization.get_current_position()
            heading = localization.get_current_orientation()

            print(f"Latitude: {lat}, Longitude: {lon}, Altitude: {alt}, Heading: {heading}")
            time.sleep(1)