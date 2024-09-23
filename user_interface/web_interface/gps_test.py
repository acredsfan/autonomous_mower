from flask import Flask, jsonify
import logging
import utm
import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(project_root)

from navigation_system.gps import GpsPosition, GpsLatestPosition
from hardware_interface.serial_port import SerialPort

# Initialize the serial port
serial_port = SerialPort(port='/dev/ttyACM0', baudrate=9600, timeout=1)

# Create an instance of GpsPosition
gps_position = GpsPosition(serial_port=serial_port, debug=True)
gps_position.start()  # Start the GPS reading thread

# Now create an instance of GpsLatestPosition, passing gps_position as argument
position_reader = GpsLatestPosition(gps_position_instance=gps_position, debug=True)

app = Flask(__name__)

@app.route('/api/gps', methods=['GET'])
def get_gps():
    logging.info("Starting get_gps")
    positions = position_reader.run()
    logging.info(f"positions: {positions}")

    if positions:
        # positions is a tuple like (timestamp, easting, northing)
        # Extract easting and northing
        easting, northing = positions[1], positions[2]
        # If you know the UTM zone, you can specify it; otherwise, set force_zone_number to True
        lat, lon = utm.to_latlon(easting, northing, force_zone_number=True)
        return jsonify({'latitude': lat, 'longitude': lon})
    else:
        return jsonify({'error': 'No GPS data available'}), 404

if __name__ == '__main__':
    app.run(debug=True)
