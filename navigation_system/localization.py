# This module is responsible for estimating the robot's position and orientation within its environment. 
# It will take sensor data, such as from the GPS module and the MPU-9250 Compass Module, and use it to compute the robot's location and heading. 
# This may involve implementing sensor fusion algorithms, such as a Kalman filter or a particle filter, to combine the data from multiple sensors and 
# obtain a more accurate estimate of the robot's pose.

# localization.py
import math
import sensor_interface

# Global variables
current_latitude = 0
current_longitude = 0
current_altitude = 0
current_heading = 0


def gps_to_meters(lat1, lon1, lat2, lon2):
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


def estimate_position():
    global current_latitude, current_longitude, current_altitude

    gps_data = sensor_interface.read_gps()

    try:
        # Assuming the GPS data format is NMEA0183 and it starts with $GPGGA
        if gps_data.startswith('$GPGGA'):
            lat, lon, alt = parse_gpgga(gps_data)
            current_latitude = lat
            current_longitude = lon
            current_altitude = alt
    except Exception as e:
        print(f"Error parsing GPS data: {e}")


def parse_gpgga(gpgga_str):
    """
    Parse NMEA0183 GPGGA string and return latitude, longitude, and altitude.
    """
    gpgga_data = gpgga_str.split(',')

    lat = float(gpgga_data[2]) / 100
    lat = int(lat) + (lat - int(lat)) * 100 / 60

    if gpgga_data[3] == 'S':
        lat = -lat

    lon = float(gpgga_data[4]) / 100
    lon = int(lon) + (lon - int(lon)) * 100 / 60

    if gpgga_data[5] == 'W':
        lon = -lon

    alt = float(gpgga_data[9])

    return lat, lon, alt


def estimate_orientation():
    global current_heading

    compass_data = sensor_interface.read_mpu9250_compass()

    try:
        current_heading = math.degrees(math.atan2(compass_data['y'], compass_data['x']))
        if current_heading < 0:
            current_heading += 360
    except Exception as e:
        print(f"Error estimating orientation: {e}")


def get_current_position():
    return current_latitude, current_longitude, current_altitude


def get_current_orientation():
    return current_heading


def update():
    estimate_position()
    estimate_orientation()


if __name__ == '__main__':
    sensor_interface.init_sensors()

    while True:
        update()
        lat, lon, alt = get_current_position()
        heading = get_current_orientation()

        print(f"Latitude: {lat}, Longitude: {lon}, Altitude: {alt}, Heading: {heading}")
        time.sleep(1)