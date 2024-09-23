from flask import Flask, jsonify
import logging
import utm
import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(project_root)


from navigation_system.gps import GpsLatestPosition

position_reader = GpsLatestPosition()

app = Flask(__name__)


@app.route('/api/gps', methods=['GET'])
def get_gps():
    logging.info("Starting get_gps")
    positions = position_reader.run()
    logging.info(f"positions: {positions}")

    if positions:
        lat, lon = utm.to_latlon(*positions, force_zone_number=True)
        return jsonify({'latitude': lat, 'longitude': lon})
    else:
        return jsonify({'error': 'No GPS data available'}), 404


if __name__ == '__main__':
    app.run(debug=True)
