import sys
sys.path.append("..")
from navigation_system.gps_interface import GPSInterface
import logging
from hardware_interface.sensor_interface import SensorInterface
import math

def estimate_position():
    logging.info(f'Entering Function or Method')
    data = GPSInterface.read_gps_data()
    if data:
        current_latitude = data['latitude']
        current_longitude = data['longitude']
        current_altitude = data['altitude']
        print(f"Current position: {current_latitude}, {current_longitude}, {current_altitude}")
    else:
        logging.warning("GPS data is None.")

def estimate_orientation():
    try:
        compass_data = SensorInterface.read_mpu9250_compass()
        
        # Check if compass_data is None
        if compass_data is not None:
            x, y, z = compass_data['x'], compass_data['y'], compass_data['z']

            # Calculate the orientation angle in degrees
            current_heading = math.degrees(math.atan2(y, x))

            if current_heading < 0:
                current_heading += 360
        else:
            logging.warning("Compass data is None.")
    except Exception as e:
        logging.exception('An error occurred')
        logging.error(f"Error estimating orientation: {e}")

print ('testing localization')
estimate_position()
estimate_orientation()
print(f"Current position: {current_latitude}, {current_longitude}, {current_altitude}")
print(f"Current heading: {current_heading}")