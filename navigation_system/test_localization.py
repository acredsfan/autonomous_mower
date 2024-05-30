import sys
sys.path.append("..")
from navigation_system.gps import GPS, GpsNmeaPositions  # Updated import
import logging
from hardware_interface.sensor_interface import SensorInterface
import math

# Initialize logging
logging.basicConfig(filename='test_localization.log', level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')

# Initialize GPS and Position Reader
gps = GPS(port='/dev/ttyUSB0', baudrate=115200)
position_reader = GpsNmeaPositions(debug=False)

def estimate_position():
    logging.info('Entering Function or Method')
    lines = gps.run()  # Read NMEA lines from GPS
    positions = position_reader.run(lines)  # Convert NMEA lines to positions
    if positions:
        ts, current_latitude, current_longitude = positions[-1]
        current_altitude = None  # Update this if altitude information is available
        print(f"Current position: {current_latitude}, {current_longitude}, {current_altitude}")
    else:
        logging.warning("GPS data is None.")
        current_latitude, current_longitude, current_altitude = None, None, None
    return current_latitude, current_longitude, current_altitude

def estimate_orientation():
    try:
        compass_data = SensorInterface.read_mpu9250_compass()
        
        if compass_data is not None:
            x, y, z = compass_data['x'], compass_data['y'], compass_data['z']

            # Calculate the orientation angle in degrees
            current_heading = math.degrees(math.atan2(y, x))

            if current_heading < 0:
                current_heading += 360
        else:
            logging.warning("Compass data is None.")
            current_heading = None
    except Exception as e:
        logging.exception('An error occurred')
        logging.error(f"Error estimating orientation: {e}")
        current_heading = None
    return current_heading

print('Testing localization')
current_latitude, current_longitude, current_altitude = estimate_position()
current_heading = estimate_orientation()
print(f"Current position: {current_latitude}, {current_longitude}, {current_altitude}")
print(f"Current heading: {current_heading}")
