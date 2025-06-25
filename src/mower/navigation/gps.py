import argparse
import json
import operator
import os
import threading
import time
import urllib.parse
import urllib.request
from functools import reduce
from typing import Any, Dict, List, Optional, Tuple  # Added List, Dict, Any

import pynmea2
import utm

from mower.utilities.logger_config import LoggerConfigInfo
from mower.utilities.text_writer import CsvLogger

logger = LoggerConfigInfo.get_logger(__name__)

# --- Google Geocoding API Configuration ---
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")
GEOCODING_API_URL = "https://maps.googleapis.com/maps/api/geocode/json"

if not GOOGLE_MAPS_API_KEY:
    logger.warning(
        "GOOGLE_MAPS_API_KEY environment variable not found. "
        "Geocoding functionality (address_to_coordinates) will be unavailable."
    )
# --- End Google Geocoding API Configuration ---

GEOLOCATION_API_URL = "https://www.googleapis.com/geolocation/v1/geolocate"


class SingletonMeta(type):
    """
    A thread-safe implementation of Singleton with per-class locks.
    """

    _instances = {}

    def __init__(cls, name, bases, dict):
        cls._lock = threading.Lock()  # Each class gets its own lock
        super().__init__(name, bases, dict)

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in SingletonMeta._instances:
                instance = super().__call__(*args, **kwargs)
                SingletonMeta._instances[cls] = instance
        return SingletonMeta._instances[cls]


class GpsNmeaPositions(metaclass=SingletonMeta):
    """
    Converts array of NMEA sentences into array
    of (easting, northing) positions.
    """

    def __init__(self, debug=False):
        self.debug = debug

    def run(self, lines):
        positions = []
        if lines:
            for ts, nmea in lines:
                position = parse_gps_position(nmea, self.debug)
                if position:
                    positions.append((ts, *position))
        return positions


class GpsPosition(metaclass=SingletonMeta):
    """
    Reads NMEA lines from serial port and converts them into positions.
    """

    def __init__(self, serial_port, debug=False):
        from mower.hardware.serial_port import SerialLineReader

        self.line_reader = SerialLineReader(serial_port)
        self.debug = debug
        self.position_reader = GpsNmeaPositions(debug=self.debug)
        self.position = None
        self.metadata = None  # Store GPS metadata (satellites, HDOP, etc.)
        self.running = True
        self.lock = threading.Lock()

    def start(self):
        self.thread = threading.Thread(target=self._read_gps, daemon=True)
        self.thread.start()

    def _read_gps(self):
        while self.running:
            try:
                # Get both position and metadata
                positions = self.run()
                metadata = self.run_metadata()
                
                if positions:
                    with self.lock:
                        self.position = positions
                
                if metadata:
                    with self.lock:
                        self.metadata = metadata
                        
                if not positions:
                    logger.debug("No valid GPS position received.")
                time.sleep(1)  # Adjust as needed
            except IOError as e:
                logger.error("IO error reading GPS data: %s", e)
                time.sleep(5)  # Wait before retrying
            except ValueError as e:
                logger.error("Value error in GPS data processing: %s", e)
                time.sleep(5)  # Wait before retrying
            except RuntimeError as e:
                logger.error("Runtime error in GPS module: %s", e)
                time.sleep(5)  # Wait before retrying

    def run(self):
        lines = self.line_reader.run()
        return self.run_once(lines)

    def run_once(self, lines):
        positions = self.position_reader.run(lines)
        return positions[-1] if positions else None

    def run_metadata(self):
        """Parse GPS metadata from current NMEA lines."""
        lines = self.line_reader.run()
        return self.run_metadata_once(lines)

    def run_metadata_once(self, lines):
        """Parse GPS metadata from given NMEA lines."""
        if not lines:
            return None
            
        # Try to get metadata from the most recent NMEA sentences
        for ts, nmea in reversed(lines):
            metadata = parse_gps_metadata(nmea, self.debug)
            if metadata:
                return metadata
        return None

    def get_latest_position(self):
        with self.lock:
            return self.position

    def get_latest_metadata(self):
        """Get the latest GPS metadata (satellites, HDOP, etc.)."""
        with self.lock:
            return self.metadata

    def shutdown(self):
        self.running = False
        self.line_reader.shutdown()
        self.thread.join()
        logger.info("GPS Position shut down successfully.")


class GpsLatestPosition(metaclass=SingletonMeta):
    """
    Provides the most recent valid GPS position and status.
    """

    def __init__(self, gps_position_instance, debug=False):
        self.debug = debug
        self.gps_position = gps_position_instance
        self.position = None
        # self.status = "Initializing GPS..."
        self.lock = threading.Lock()

    def run(self):
        with self.lock:
            self.position = self.gps_position.get_latest_position()
            if self.position:
                # self.status = "GPS fix acquired."
                # else:
                # self.status = "Waiting for GPS fix..."
                return self.position

    def get_status(self):
        with self.lock:
            return self.status


class GpsPlayer(metaclass=SingletonMeta):
    """
    Plays back recorded NMEA sentences.
    """

    def __init__(self, nmea_logger: CsvLogger):
        self.nmea = nmea_logger
        self.index = -1
        self.starttime = None
        self.running = False

    def start(self):
        self.running = True
        self.starttime = None
        self.index = -1

    def stop(self):
        self.running = False

    def run(self, playing, nmea_sentences):
        if self.running and playing:
            nmea = self.run_once(time.time())
            return True, nmea
        return False, nmea_sentences

    def run_once(self, now):
        nmea_sentences = []
        if self.running:
            if self.starttime is None:
                logger.info("Resetting GPS player start time.")
                self.starttime = now

            start_nmea = self.nmea.get(0)
            if start_nmea:
                start_nmea_time = float(start_nmea[0])
                offset_nmea_time = 0
                within_time = True
                while within_time:
                    next_nmea = None
                    if self.index >= self.nmea.length():
                        self.index = 0
                        self.starttime += offset_nmea_time
                        next_nmea = self.nmea.get(0)
                    else:
                        next_nmea = self.nmea.get(self.index + 1)

                    if next_nmea is None:
                        self.index += 1
                    else:
                        next_nmea_time = float(next_nmea[0])
                        offset_nmea_time = next_nmea_time - start_nmea_time
                        next_nmea_time = self.starttime + offset_nmea_time
                        within_time = next_nmea_time <= now
                        if within_time:
                            nmea_sentences.append((next_nmea_time, next_nmea[1]))
                            self.index += 1
        return nmea_sentences


# Parsing and Utility Functions
def parse_gps_position(line, debug=False):
    """
    Parse a GPS NMEA sentence (GPRMC or GPGGA) and convert to UTM coordinates.
    Uses the pynmea2 library for robust parsing.
    """
    if not line:
        return None
    line = line.strip()
    if not line or not line.startswith("$") or "*" not in line:
        # Basic validation failed, ignore line
        return None

    # Verify checksum before full parsing
    try:
        # Recalculate and check checksum
        line_no_checksum = line[1:].split("*")[0]
        expected_checksum = reduce(operator.xor, map(ord, line_no_checksum), 0)
        provided_checksum = int(line.split("*")[1], 16)
        if expected_checksum != provided_checksum:
            logger.info("NMEA checksum does not match: %s != %s for line %s",
                        expected_checksum, provided_checksum, line)
            return None
    except (IndexError, ValueError) as e:
        logger.info("Could not validate checksum for line: %s, Error: %s", line, e)
        return None

    # Use pynmea2 to parse the verified line
    try:
        msg = pynmea2.parse(line)
    except pynmea2.ParseError as e:
        if debug:
            logger.error("NMEA parse error detected: %s", e)
        return None

    # Handle GPGGA sentences (often have the best fix data)
    if isinstance(msg, pynmea2.types.talker.GGA):
        # gps_qual: 0=invalid, 1=GPS fix, 2=DGPS, etc. We need at least 1.
        if msg.gps_qual < 1:
            if debug:
                logger.debug("GPGGA sentence received, but GPS fix is not valid (quality: %s).", msg.gps_qual)
            return None
        if not msg.latitude or not msg.longitude:
            if debug:
                logger.debug("GPGGA sentence received, but lat/lon is empty.")
            return None

        utm_position = utm.from_latlon(msg.latitude, msg.longitude)
        return (
            float(utm_position[0]),
            float(utm_position[1]),
            utm_position[2],
            utm_position[3],
        )

    # Handle GPRMC sentences as a fallback
    elif isinstance(msg, pynmea2.types.talker.RMC):
        if msg.status == 'V': # 'V' means Void/Warning
            if debug:
                logger.debug("GPRMC sentence received, but status is Void. Ignoring invalid position.")
            return None
        if not msg.latitude or not msg.longitude:
            if debug:
                logger.debug("GPRMC sentence received, but lat/lon is empty.")
            return None

        utm_position = utm.from_latlon(msg.latitude, msg.longitude)
        return (
            float(utm_position[0]),
            float(utm_position[1]),
            utm_position[2],
            utm_position[3],
        )

    # Return None if it's a different, unhandled NMEA sentence type
    return None


def parse_gps_metadata(line, debug=False):
    """
    Parse GPS metadata (satellites, HDOP, fix quality) from NMEA sentences.
    Extracts additional GPS information beyond just position.
    
    Args:
        line: NMEA sentence string
        debug: Enable debug logging
        
    Returns:
        dict: GPS metadata or None if parsing fails
            {
                'satellites': int,      # Number of satellites in use
                'hdop': float,         # Horizontal dilution of precision  
                'fix_quality': int,    # GPS fix quality indicator
                'altitude': float,     # Altitude above sea level (meters)
            }
    """
    if not line:
        return None
    line = line.strip()
    if not line or not line.startswith("$") or "*" not in line:
        return None

    # Verify checksum before parsing
    try:
        line_no_checksum = line[1:].split("*")[0]
        expected_checksum = reduce(operator.xor, map(ord, line_no_checksum), 0)
        provided_checksum = int(line.split("*")[1], 16)
        if expected_checksum != provided_checksum:
            if debug:
                logger.debug("NMEA checksum mismatch in metadata parsing: %s", line)
            return None
    except (IndexError, ValueError):
        if debug:
            logger.debug("Could not validate checksum for metadata: %s", line)
        return None

    # Use pynmea2 to parse the line
    try:
        msg = pynmea2.parse(line)
    except pynmea2.ParseError as e:
        if debug:
            logger.debug("NMEA parse error in metadata parsing: %s", e)
        return None

    # Extract metadata from GPGGA/GNGGA sentences (most complete GPS info)
    if isinstance(msg, pynmea2.types.talker.GGA):
        if msg.gps_qual < 1:
            if debug:
                logger.debug("GPGGA metadata: GPS fix quality insufficient (%s)", msg.gps_qual)
            return None
            
        metadata = {
            'satellites': int(msg.num_sats) if msg.num_sats else 0,
            'hdop': float(msg.horizontal_dil) if msg.horizontal_dil else 99.9,
            'fix_quality': int(msg.gps_qual) if msg.gps_qual else 0,
            'altitude': float(msg.altitude) if msg.altitude is not None else 0.0,
        }
        
        if debug:
            logger.debug("GPS metadata extracted: %s", metadata)
        return metadata

    # GSA sentences also have satellite info (fallback)
    elif isinstance(msg, pynmea2.types.talker.GSA):
        # Count active satellites
        active_sats = [sat for sat in [msg.sv_id01, msg.sv_id02, msg.sv_id03, msg.sv_id04,
                                      msg.sv_id05, msg.sv_id06, msg.sv_id07, msg.sv_id08,
                                      msg.sv_id09, msg.sv_id10, msg.sv_id11, msg.sv_id12] if sat]
        
        metadata = {
            'satellites': len(active_sats),
            'hdop': float(msg.hdop) if msg.hdop else 99.9,
            'fix_quality': 1 if msg.mode_fix_type == '3' else (1 if msg.mode_fix_type == '2' else 0),
            'altitude': 0.0,  # GSA doesn't have altitude
        }
        
        if debug:
            logger.debug("GPS metadata from GSA: %s", metadata)
        return metadata

    return None


def parse_nmea_checksum(nmea_line):
    try:
        return int(nmea_line[-2:], 16)
    except ValueError:
        logger.error("Failed to parse NMEA checksum.")
        return None


def calculate_nmea_checksum(nmea_line):
    return reduce(operator.xor, map(ord, nmea_line[1:-3]), 0)


def nmea_to_degrees(gps_str, direction):
    if not gps_str or gps_str == "0":
        return 0

    parts = gps_str.split(".")
    degrees_str = parts[0][:-2]
    minutes_str = parts[0][-2:]
    if len(parts) == 2:
        minutes_str += "." + parts[1]

    degrees = float(degrees_str) if degrees_str else 0.0
    minutes = float(minutes_str) / 60 if minutes_str else 0.0

    return (degrees + minutes) * (-1 if direction in ["W", "S"] else 1)


# --- Google Geocoding API Function ---
def address_to_coordinates(address_string: str) -> Optional[Tuple[float, float]]:
    """
    Converts a human-readable address string to latitude and longitude coordinates
    using the Google Geocoding API.

    Args:
        address_string: The address to geocode.

    Returns:
        A tuple of (latitude, longitude) if successful, or None otherwise.
    """
    if not GOOGLE_MAPS_API_KEY:
        logger.error("Cannot perform geocoding: GOOGLE_MAPS_API_KEY is not set.")
        return None

    if not address_string:
        logger.warning("Address string is empty, cannot geocode.")
        return None

    params = {"address": address_string, "key": GOOGLE_MAPS_API_KEY}
    url = f"{GEOCODING_API_URL}?{urllib.parse.urlencode(params)}"

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            response_body = response.read().decode("utf-8")
            data = json.loads(response_body)
    except urllib.error.URLError as e:
        logger.error(f"Network error during geocoding: {e.reason}")
        return None
    except json.JSONDecodeError:
        logger.error("Failed to decode JSON response from Geocoding API.")
        return None
    except Exception as e:  # Catch any other unexpected errors during request/parsing
        logger.error(f"Unexpected error during geocoding API call: {e}")
        return None

    status = data.get("status")
    if status == "OK":
        results = data.get("results")
        if results and len(results) > 0:
            location = results[0].get("geometry", {}).get("location")
            if location and "lat" in location and "lng" in location:
                return location["lat"], location["lng"]
            else:
                logger.error("Geocoding API 'OK' status but location data is malformed.")
                return None
        else:
            logger.error("Geocoding API 'OK' status but no results found.")
            return None
    elif status == "ZERO_RESULTS":
        logger.warning(f"Address '{address_string}' not found by Geocoding API (ZERO_RESULTS).")
        return None
    elif status == "OVER_QUERY_LIMIT":
        logger.error("Geocoding API query limit exceeded. Check usage and billing.")
        return None
    elif status == "REQUEST_DENIED":
        logger.error("Geocoding API request denied. Verify API key and permissions.")
        return None
    elif status == "INVALID_REQUEST":
        logger.error(f"Geocoding API invalid request. Sent params: {params}, Error: {data.get('error_message', 'N/A')}")
        return None
    else:  # UNKNOWN_ERROR or other statuses
        logger.error(f"Geocoding API returned an unhandled status: {status}. Error: {data.get('error_message', 'N/A')}")
        return None


# --- End Google Geocoding API Function ---


# --- Google Geolocation API Function ---
def get_location_from_wifi_cell(
    wifi_access_points: Optional[List[Dict[str, Any]]] = None,
    cell_towers: Optional[List[Dict[str, Any]]] = None,
    consider_ip: bool = True,
    ) -> Optional[Dict[str, Any]]:
    """
    Determines location based on WiFi access points, cell towers, and IP address
    using the Google Geolocation API.

    Args:
        wifi_access_points: A list of WiFi access point objects.
        cell_towers: A list of cell tower objects.
        consider_ip: Whether to use IP address for geolocation if other signals are absent.

    Returns:
        A dictionary containing 'location' (lat, lng) and 'accuracy' on success,
        or a dictionary with 'error' and 'details' on failure, or None for critical issues.
    """
    if not GOOGLE_MAPS_API_KEY:
        logger.error("Cannot perform geolocation: GOOGLE_MAPS_API_KEY is not set.")
        return {"error": "API key not configured", "details": "GOOGLE_MAPS_API_KEY is missing."}

    if not wifi_access_points and not cell_towers and not consider_ip:
        logger.warning("Geolocation requires WiFi, cell tower data, or IP consideration.")
        return {"error": "Insufficient input", "details": "No WiFi, cell, or IP data provided."}

    request_body_dict = {}
    if wifi_access_points:
        request_body_dict["wifiAccessPoints"] = wifi_access_points
    if cell_towers:
        request_body_dict["cellTowers"] = cell_towers
    if not wifi_access_points and not cell_towers:  # Only include considerIp if no other signals
        request_body_dict["considerIp"] = consider_ip

    # If only consider_ip is true, and others are empty, the dict might be just {"considerIp": True}
    # The API expects at least one signal or considerIp.
    # If all are false/empty, we already returned above.

    request_body_json = json.dumps(request_body_dict).encode("utf-8")
    url = f"{GEOLOCATION_API_URL}?key={GOOGLE_MAPS_API_KEY}"

    try:
        req = urllib.request.Request(
            url, data=request_body_json, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            response_body = response.read().decode("utf-8")
            data = json.loads(response_body)

            # Successful response: {"location": {"lat": ..., "lng": ...}, "accuracy": ...}
            if "location" in data and "accuracy" in data:
                return data
            # API can return 200 OK with an error object for "notFound"
            elif "error" in data and isinstance(data["error"], dict):
                logger.warning(f"Geolocation API returned an error object: {data['error']}")
                return {"error": "APIError", "details": data["error"]}
            else:  # Unexpected success response structure
                logger.error(f"Geolocation API success response malformed: {data}")
                return {"error": "Malformed success response", "details": str(data)}

    except urllib.error.HTTPError as e:
        error_details = f"HTTP {e.code}: {e.reason}"
        try:
            if e.fp:  # Try to read error body from API
                error_response_body = e.read().decode("utf-8")
                error_data = json.loads(error_response_body)
                if "error" in error_data and isinstance(error_data["error"], dict):
                    logger.error(f"HTTP error from Geolocation API: {e.code} - {error_data['error']}")
                    return {"error": "APIHTTPError", "details": error_data["error"]}
                else:
                    error_details = f"HTTP {e.code}: {e.reason} - Body: {error_response_body}"
            else:  # No body from HTTPError
                logger.error(f"HTTP error from Geolocation API: {e.code} {e.reason} (no body)")

        except json.JSONDecodeError:
            logger.error(
                f"HTTP error from Geolocation API (could not parse error body): {e.code} {e.reason} - Body: {error_response_body if 'error_response_body' in locals() else 'N/A'}"
            )
            error_details = f"HTTP {e.code}: {e.reason} (unparseable error body)"
        except Exception as inner_e:  # Catch other errors during error handling
            logger.error(f"Further error processing HTTPError for Geolocation API: {inner_e}")

        return {"error": "APIHTTPError", "details": error_details}

    except urllib.error.URLError as e:
        logger.error(f"Network error during Geolocation API call: {e.reason}")
        return {"error": "NetworkURLError", "details": str(e.reason)}
    except json.JSONDecodeError:
        logger.error("Failed to decode JSON response from Geolocation API.")
        return {"error": "JSONDecodeError", "details": "Malformed JSON response from server."}
    except Exception as e:
        logger.error(f"Unexpected error during Geolocation API call: {e}", exc_info=True)
        return {"error": "UnexpectedError", "details": str(e)}


# --- End Google Geolocation API Function ---

""" The __main__ self test can log position
or optionally record a set of waypoints"""

if __name__ == "__main__":
    import math
    import sys

    import numpy as np
    import readchar

    from mower.hardware.serial_port import SerialPort

    def stats(data):
        """
        Calculate (min, max, mean, std_deviation) of a list of floats
        """
        if not data:
            return None
        count = len(data)
        min = None
        max = None
        sum = 0
        for x in data:
            if min is None or x < min:
                min = x
            if max is None or x > max:
                max = x
            sum += x
        mean = sum / count
        sum_errors_squared = 0
        for x in data:
            error = x - mean
            sum_errors_squared += error * error
        std_deviation = math.sqrt(sum_errors_squared / count)
        return Stats(count, sum, min, max, mean, std_deviation)

    class Stats:
        """
        Statistics for a set of data
        """

        def __init__(self, count, sum, min, max, mean, std_deviation):
            self.count = count
            self.sum = sum
            self.min = min
            self.max = max
            self.mean = mean
            self.std_deviation = std_deviation

    class Waypoint:
        """
        A waypoint created from multiple samples,
        modelled as a non-axis-aligned (rotated) ellipsoid.
        This models a waypoint based on a jittery source,
        like GPS, where x and y values may not be completely
        independent values.
        """

        def __init__(self, samples, nstd=1.0):
            """
            Fit an ellipsoid to the given samples at the
            given multiple of the standard deviation of the samples.
            """

            # separate out the points by axis
            self.x = [w[1] for w in samples]
            self.y = [w[2] for w in samples]

            # calculate the stats for each axis
            self.x_stats = stats(self.x)
            self.y_stats = stats(self.y)

            # calculate a rotated ellipse that best fits the samples.
            # We use a rotated ellipse because the x and y values
            # of each point are not independent.

            def eigsorted(cov):
                """
                Calculate eigenvalues and eigenvectors
                and return them sorted by eigenvalue.
                """
                eigenvalues, eigenvectors = np.linalg.eigh(cov)
                order = eigenvalues.argsort()[::-1]
                return eigenvalues[order], eigenvectors[:, order]

            # calculate covariance matrix between x and y values
            self.cov = np.cov(self.x, self.y)

            # get eigenvalues and vectors from covariance matrix
            self.eigenvalues, self.eigenvectors = eigsorted(self.cov)

            # calculate the ellipsoid at the
            # given multiple of the standard deviation.
            self.theta = np.degrees(np.arctan2(*self.eigenvectors[:, 0][::-1]))
            self.width, self.height = 2 * nstd * np.sqrt(self.eigenvalues)

        def is_inside(self, x, y):
            """
            Determine if the given (x,y) point is within the waypoint's
            fitted ellipsoid
            """
            # if (x >= self.x_stats.min) and (x <= self.x_stats.max):
            #     if (y >= self.y_stats.min) and (y <= self.y_stats.max):
            #         return True
            # return False
            # if (x >= (self.x_stats.mean - self.x_stats.std_deviation))
            # and (x <= (self.x_stats.mean + self.x_stats.std_deviation)):
            #     if (y >= (self.y_stats.mean - self.y_stats.std_deviation))
            # and (y <= (self.y_stats.mean + self.y_stats.std_deviation)):
            #         return True
            # return False
            cos_theta = math.cos(self.theta)
            sin_theta = math.sin(self.theta)
            x_translated = x - self.x_stats.mean
            y_translated = y - self.y_stats.mean
            #
            # basically translate the test point into the
            # coordinate system of the ellipse (it's center)
            # and then rotate the point and do a normal ellipse test
            #
            part1 = ((cos_theta * x_translated + sin_theta * y_translated) / self.width) ** 2
            part2 = ((sin_theta * x_translated - cos_theta * y_translated) / self.height) ** 2
            return (part1 + part2) <= 1

        def is_in_range(self, x, y):
            """
            Determine if the given (x,y) point is within the
            range of the collected waypoint samples
            """
            return (
                (x >= self.x_stats.min)
                and (x <= self.x_stats.max)
                and (y >= self.y_stats.min)
                and (y <= self.y_stats.max)
            )

        def is_in_std(self, x, y, std_multiple=1.0):
            """
            Determine if the given (x, y) point is within a given
            multiple of the standard deviation of the samples
            on each axis.
            """
            x_std = self.x_stats.std_deviation * std_multiple
            y_std = self.y_stats.std_deviation * std_multiple
            return (
                (x >= (self.x_stats.mean - x_std))
                and (x <= (self.x_stats.mean + x_std))
                and (y >= (self.y_stats.mean - y_std))
                and (y <= (self.y_stats.mean + y_std))
            )

        def show(self):
            """
            Draw the waypoint ellipsoid
            """
            import matplotlib.pyplot as plt

            self.plot()
            plt.show()

        def plot(self):
            """
            Draw the waypoint ellipsoid
            """
            import matplotlib.pyplot as plt
            from matplotlib.patches import Ellipse, Rectangle

            # define Matplotlib figure and axis
            ax = plt.subplot(111, aspect="equal")

            # plot the collected readings
            plt.scatter(self.x, self.y)

            # plot the centroid
            plt.plot(
                self.x_stats.mean,
                self.y_stats.mean,
                marker="+",
                markeredgecolor="green",
                markerfacecolor="green",
            )

            # plot the range
            bounds = Rectangle(
                (self.x_stats.min, self.y_stats.min),
                self.x_stats.max - self.x_stats.min,
                self.y_stats.max - self.y_stats.min,
                alpha=0.5,
                edgecolor="red",
                fill=False,
                visible=True,
            )
            ax.add_artist(bounds)

            # plot the ellipsoid
            ellipse = Ellipse(
                xy=(self.x_stats.mean, self.y_stats.mean),
                width=self.width,
                height=self.height,
                angle=self.theta,
            )
            ellipse.set_alpha(0.25)
            ellipse.set_facecolor("green")
            ax.add_artist(ellipse)

    def is_in_waypoint_range(waypoints, x, y):
        i = 0
        for waypoint in waypoints:
            if waypoint.is_in_range(x, y):
                return True, i
            i += 1
        return False, -1

    def is_in_waypoint_std(waypoints, x, y, std):
        i = 0
        for waypoint in waypoints:
            if waypoint.is_in_std(x, y, std):
                return True, i
            i += 1
        return False, -1

    def is_in_waypoint(waypoints, x, y):
        i = 0
        for waypoint in waypoints:
            if waypoint.is_inside(x, y):
                return True, i
            i += 1
        return False, -1

    def plot(waypoints):
        """
        Draw the waypoint ellipsoid
        """
        import matplotlib.pyplot as plt

        for waypoint in waypoints:
            waypoint.plot()
        plt.show()

    import os
    import argparse
    from dotenv import load_dotenv

    # Load environment variables from .env if present
    load_dotenv()

    # Get defaults from environment variables
    DEFAULT_SERIAL_PORT = os.environ.get("GPS_SERIAL_PORT", "/dev/ttyACM1")
    DEFAULT_BAUD_RATE = int(os.environ.get("GPS_BAUD_RATE", "115200"))
    DEFAULT_TIMEOUT = float(os.environ.get("GPS_TIMEOUT", "1"))

    parser = argparse.ArgumentParser(description="GPS diagnostics and accuracy test.")
    parser.add_argument(
        "-s",
        "--serial",
        type=str,
        default=DEFAULT_SERIAL_PORT,
        help=f"Serial port address (default: {DEFAULT_SERIAL_PORT})",
    )
    parser.add_argument(
        "-b",
        "--baudrate",
        type=int,
        default=DEFAULT_BAUD_RATE,
        help=f"Serial port baud rate (default: {DEFAULT_BAUD_RATE})",
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help=f"Serial port timeout in seconds (default: {DEFAULT_TIMEOUT})",
    )
    parser.add_argument(
        "-sp",
        "--samples",
        type=int,
        default=5,
        help="Number of samples per waypoint.",
    )
    parser.add_argument(
        "-wp",
        "--waypoints",
        type=int,
        default=0,
        help="Number of waypoints to collect; > 0 to collect" "waypoints, 0 to just log position",
    )
    parser.add_argument(
        "-nstd",
        "--nstd",
        type=float,
        default=1.0,
        help="multiple of standard deviation for ellipse.",
    )
    parser.add_argument("-th", "--threaded", action="store_true", help="run in threaded mode.")
    parser.add_argument("-db", "--debug", action="store_true", help="Enable extra logging")
    args = parser.parse_args()

    if args.waypoints < 0:
        print("Use waypoints > 0 to collect waypoints" "use 0 waypoints to just log position")
        parser.print_help()
        sys.exit(0)

    if args.samples <= 0:
        print("Samples per waypoint must be greater than zero")
        parser.print_help()
        sys.exit(0)

    if args.nstd <= 0:
        print("Waypoint multiplier must be greater than zero")
        parser.print_help()
        sys.exit(0)

    if args.timeout <= 0:
        print("Timeout must be greater than zero")
        parser.print_help()
        sys.exit(0)

    update_thread = None
    line_reader = None

    waypoint_count = args.waypoints  # number of paypoints in the path
    samples_per_waypoint = args.samples  # number of readings per waypoint
    waypoints = []
    waypoint_samples = []

    from mower.hardware.serial_port import SerialLineReader

    try:
        serial_port = SerialPort(args.serial, baudrate=args.baudrate, timeout=args.timeout)
        line_reader = SerialLineReader(serial_port, max_lines=args.samples, debug=args.debug)
        position_reader = GpsNmeaPositions(args.debug)

        # start the threaded part
        # and a threaded window to show plot

        if args.threaded:

            def start_thread():
                update_thread = threading.Thread(target=line_reader.update, args=())
                update_thread.start()

            start_thread()

        def read_gps():
            lines = line_reader.run_threaded() if args.threaded else line_reader.run()
            positions = position_reader.run(lines)
            return positions

        ts = time.time()
        state = "prompt" if waypoint_count > 0 else ""
        last_valid_position_time = None
        valid_position_count = 0
        max_no_data_seconds = 30  # Warn if no valid NMEA for this many seconds
        try:
            while line_reader.running:
                readings = read_gps()
                if readings:
                    print("")
                    parsed_positions = []
                    for reading in readings:
                        # Reading is already a parsed position: (timestamp, easting, northing, zone_number, zone_letter)
                        if isinstance(reading, (tuple, list)) and len(reading) >= 5:
                            ts_val, easting, northing, zone_number, zone_letter = reading[:5]
                            parsed_positions.append((ts_val, easting, northing))
                            last_valid_position_time = time.time()
                            valid_position_count += 1
                            if args.debug:
                                print(f"[DEBUG] Parsed position: {easting:.2f}E, {northing:.2f}N (Zone {zone_number}{zone_letter})")
                        else:
                            if args.debug:
                                print(f"[DEBUG] Unexpected position format: {reading}")
                            continue

                    if state == "prompt":
                        print(
                            f"Move to waypoint #{len(waypoints) + 1} and "
                            f"press the space bar and enter to start sampling "
                            f"or any other key to just start logging."
                        )
                        state = "move"
                    elif state == "move":
                        key_press = readchar.readchar()  # sys.stdin.read(1)
                        if key_press == " ":
                            waypoint_samples = []
                            line_reader.clear()  # throw away buffered readings
                            state = "sampling"
                        else:
                            state = ""  # just start logging
                    elif state == "sampling":
                        waypoint_samples += parsed_positions
                        count = len(waypoint_samples)
                        print(f"Collected {count} so far...")
                        if count >= samples_per_waypoint:
                            print(f"...done.  Collected {count} samples for waypoint #{len(waypoints) + 1}")
                            waypoint = Waypoint(waypoint_samples, nstd=args.nstd)
                            waypoints.append(waypoint)
                            if len(waypoints) < waypoint_count:
                                state = "prompt"
                            else:
                                state = "test_prompt"
                                if args.debug:
                                    plot(waypoints)
                    elif state == "test_prompt":
                        print("Waypoints are recorded. Now walk around and see when in a waypoint.")
                        state = "test"
                    elif state == "test":
                        for ts_val, x, y in parsed_positions:
                            print(f"Your position is ({x}, {y})")
                            hit, index = is_in_waypoint_range(waypoints, x, y)
                            if hit:
                                print(f"You are within the sample range of waypoint #{index + 1}")
                            std_deviation = 1.0
                            hit, index = is_in_waypoint_std(waypoints, x, y, std_deviation)
                            if hit:
                                print(f"You are within {std_deviation} std devs of the center of waypoint #{index + 1}")
                            hit, index = is_in_waypoint(waypoints, x, y)
                            if hit:
                                print(f"You are at waypoint ellipse #{index + 1}")
                    else:
                        # just log the readings
                        for ts_val, x, y in parsed_positions:
                            print(f"You are at ({x}, {y})")
                else:
                    # No readings, print dot and check for timeout
                    if time.time() > (ts + 0.5):
                        print(".", end="")
                        ts = time.time()
                    # Warn if no valid NMEA for too long
                    if (last_valid_position_time is None or (time.time() - last_valid_position_time) > max_no_data_seconds):
                        print("[WARNING] No valid GPS positions parsed in the last 30 seconds. Check GPS wiring and baud rate.")
                        last_valid_position_time = time.time()  # Avoid spamming warning
        except KeyboardInterrupt:
            print("\n[INFO] Script interrupted by user.")
        finally:
            if valid_position_count == 0:
                print("[SUMMARY] No valid GPS positions were parsed during this session.")
    finally:
        if line_reader:
            line_reader.shutdown()
        if update_thread is not None:
            update_thread.join()  # wait for thread to end
