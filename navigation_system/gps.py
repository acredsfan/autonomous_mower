import argparse
import threading
import time
import requests
import base64
import os
import pynmea2
import utm
from dotenv import load_dotenv
from functools import reduce
import operator

from hardware_interface import SerialPort, SerialLineReader
from donkeycar.parts.text_writer import CsvLogger

from utils import LoggerConfig

# Initialize logger
logger = LoggerConfig.get_logger(__name__)

dotenv_path = '/home/pi/autonomous_mower/.env'
load_dotenv(dotenv_path)
NTRIP_user = os.getenv("NTRIP_USER")
NTRIP_pass = os.getenv("NTRIP_PASS")
NTRIP_url = os.getenv("NTRIP_URL")
NTRIP_mountpoint = os.getenv("NTRIP_MOUNTPOINT")
NTRIP_port = os.getenv("NTRIP_PORT")


class GpsNmeaPositions:
    def __init__(self, debug=False):
        self.debug = debug

    def get_lines(self):
        lines = []
        for _ in range(5):
            line = self.serial_port.readline().decode(
                'ascii', errors='replace')
            lines.append((time.time(), line))
        return lines

    def run(self, lines):
        positions = []
        if lines:
            for ts, nmea in lines:
                position = parseGpsPosition(nmea, self.debug)
                if position:
                    positions.append((ts, position[0], position[1]))
        return positions

    def update(self):
        pass

    def run_threaded(self, lines):
        return self.run(lines)


class GpsLatestPosition:
    def __init__(self, debug=False):
        self.debug = debug
        self.position = None
        self.gps_nmea_positions = GpsNmeaPositions()

    def run(self):
        lines = self.gps_nmea_positions.get_lines()
        positions = self.gps_nmea_positions.run(lines)
        if positions is not None and len(positions) > 0:
            self.position = positions[-1]
        return self.position

    def get_latest_position(self):
        return self.position


class GpsPosition:
    def __init__(
            self,
            serial: SerialPort,
            NTRIP_user,
            NTRIP_pass,
            NTRIP_url,
            NTRIP_mountpoint,
            NTRIP_port,
            debug=False) -> None:
        self.line_reader = SerialLineReader(serial)
        self.debug = debug
        self.position_reader = GpsNmeaPositions()
        self.position = None
        self.NTRIP_user = NTRIP_user
        self.NTRIP_pass = NTRIP_pass
        self.NTRIP_url = NTRIP_url
        self.NTRIP_mountpoint = NTRIP_mountpoint
        self.NTRIP_port = NTRIP_port
        self.correction_thread = threading.Thread(
            target=self.get_correction_data, daemon=True)
        self.correction_thread.start()
        self._start()

    def _start(self):
        while self.position is None:
            logger.info("Waiting for GPS fix")
            self.position = self.run()

    def run_once(self, lines):
        positions = self.position_reader.run(lines)
        if positions is not None and len(positions) > 0:
            self.position = positions[-1]
            if self.debug:
                logger.info(
                    f"UTM long = {
                        self.position[0]}, UTM lat = {
                        self.position[1]}")
        return self.position

    def run(self):
        lines = self.line_reader.run()
        return self.run_once(lines)

    def run_threaded(self):
        lines = self.line_reader.run_threaded()
        return self.run_once(lines)

    def update(self):
        self.line_reader.update()

    def shutdown(self):
        return self.line_reader.shutdown()

    def connect_to_NTRIP(self):
        auth = base64.b64encode(
            f"{self.NTRIP_user}:{self.NTRIP_pass}".encode()).decode()
        headers = {'Authorization': f'Basic {auth}'}
        url = (
            f"http://{self.NTRIP_url}:{self.NTRIP_port}/"
            f"{self.NTRIP_mountpoint}"
        )
        response = requests.get(url, headers=headers, stream=True)
        if response.status_code == 200:
            print("Connected to NTRIP")
            return response
        else:
            print(f"Failed to connect to NTRIP: {response.status_code}")
            return None

    def get_correction_data(self):
        response = self.connect_to_NTRIP()
        if response:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    self.line_reader.serial.write(chunk)


class GpsPlayer:
    def __init__(self, nmea_logger: CsvLogger):
        self.nmea = nmea_logger
        self.index = -1
        self.starttime = None
        self.running = False

    def start(self):
        self.running = True
        self.starttime = None
        self.index = -1
        return self

    def stop(self):
        self.running = False
        return self

    def run(self, playing, nmea_sentences):
        if self.running and playing:
            nmea = self.run_once(time.time())
            return True, nmea
        return False, nmea_sentences

    def run_once(self, now):
        nmea_sentences = []
        if self.running:
            if self.starttime is None:
                print("Resetting GPS player start time.")
                self.starttime = now

            start_nmea = self.nmea.get(0)
            if start_nmea is not None:
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
                        offset_nmea_time = (next_nmea_time - start_nmea_time)
                        next_nmea_time = self.starttime + offset_nmea_time
                        within_time = next_nmea_time <= now
                        if within_time:
                            nmea_sentences.append(
                                (next_nmea_time, next_nmea[1]))
                            self.index += 1
        return nmea_sentences


def parseGpsPosition(line, debug=False):
    if not line:
        return None
    line = line.strip()
    if not line:
        return None
    
    if '$' != line[0]:
        logger.info("NMEA Missing line start")
        return None

    if '*' != line[-3]:
        logger.info("NMEA Missing checksum")
        return None

    nmea_checksum = parse_nmea_checksum(line)
    nmea_msg = line[1:-3]
    nmea_parts = nmea_msg.split(",")
    message = nmea_parts[0]
    if (message == "GPRMC") or (message == "GNRMC"):
        calculated_checksum = calculate_nmea_checksum(line)
        if nmea_checksum != calculated_checksum:
            logger.info(
                "NMEA checksum does not match: "
                f"{nmea_checksum} != {calculated_checksum}")
            return None

        if debug:
            try:
                msg = pynmea2.parse(line)
            except pynmea2.ParseError as e:
                logger.error('NMEA parse error detected: {}'.format(e))
                return None

        if nmea_parts[2] == 'V':
            logger.info(
                "GPS receiver warning; position not valid."
                "Ignore invalid position.")
        else:
            longitude = nmea_to_degrees(nmea_parts[5], nmea_parts[6])
            latitude = nmea_to_degrees(nmea_parts[3], nmea_parts[4])

            if debug:
                if msg.longitude != longitude:
                    print(f"Longitude mismatch {msg.longitude} != {longitude}")
                if msg.latitude != latitude:
                    print(f"Latitude mismatch {msg.latitude} != {latitude}")

            utm_position = utm.from_latlon(latitude, longitude)
            # utm_position returns (Easting, Northing, Zone Num, Zone Letter)
            return (
                float(utm_position[0]),
                float(utm_position[1]),
                utm_position[2],
                utm_position[3]
            )
    return None


def parse_nmea_checksum(nmea_line):
    return int(nmea_line[-2:], 16)


def calculate_nmea_checksum(nmea_line):
    return reduce(operator.xor, map(ord, nmea_line[1:-3]), 0)


def nmea_to_degrees(gps_str, direction):
    if not gps_str or gps_str == "0":
        return 0

    parts = gps_str.split(".")
    degrees_str = parts[0][:-2]
    minutes_str = parts[0][-2:]
    if 2 == len(parts):
        minutes_str += "." + parts[1]

    degrees = 0.0
    if len(degrees_str) > 0:
        degrees = float(degrees_str)

    minutes = 0.0
    if len(minutes_str) > 0:
        minutes = float(minutes_str) / 60

    return (degrees + minutes) * (-1 if direction in ['W', 'S'] else 1)


if __name__ == "__main__":
    import math
    import numpy as np
    import sys
    import readchar
    from hardware_interface import SerialPort

    def stats(data):
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
            sum_errors_squared += (error * error)
        std_deviation = math.sqrt(sum_errors_squared / count)
        return Stats(count, sum, min, max, mean, std_deviation)

    class Stats:
        def __init__(self, count, sum, min, max, mean, std_deviation):
            self.count = count
            self.sum = sum
            self.min = min
            self.max = max
            self.mean = mean
            self.std_deviation = std_deviation

    class Waypoint:
        def __init__(self, samples, nstd=1.0):
            self.x = [w[1] for w in samples]
            self.y = [w[2] for w in samples]

            self.x_stats = stats(self.x)
            self.y_stats = stats(self.y)

            def eigsorted(cov):
                eigenvalues, eigenvectors = np.linalg.eigh(cov)
                order = eigenvalues.argsort()[::-1]
                return eigenvalues[order], eigenvectors[:, order]

            self.cov = np.cov(self.x, self.y)

            self.eigenvalues, self.eigenvectors = eigsorted(self.cov)

            self.theta = np.degrees(np.arctan2(*self.eigenvectors[:, 0][::-1]))
            self.width, self.height = 2 * nstd * np.sqrt(self.eigenvalues)

        def is_inside(self, x, y):
            cos_theta = math.cos(self.theta)
            sin_theta = math.sin(self.theta)
            x_translated = x - self.x_stats.mean
            y_translated = y - self.y_stats.mean

            part1 = (
                (cos_theta *
                 x_translated +
                 sin_theta *
                 y_translated) /
                self.width)**2
            part2 = (
                (sin_theta *
                 x_translated -
                 cos_theta *
                 y_translated) /
                self.height)**2
            return (part1 + part2) <= 1

        def is_in_range(self, x, y):
            return (x >= self.x_stats.min) and \
                   (x <= self.x_stats.max) and \
                   (y >= self.y_stats.min) and \
                   (y <= self.y_stats.max)

        def is_in_std(self, x, y, std_multiple=1.0):
            x_std = self.x_stats.std_deviation * std_multiple
            y_std = self.y_stats.std_deviation * std_multiple
            return (x >= (self.x_stats.mean - x_std)) and \
                   (x <= (self.x_stats.mean + x_std)) and \
                   (y >= (self.y_stats.mean - y_std)) and \
                   (y <= (self.y_stats.mean + y_std))

        def show(self):
            import matplotlib.pyplot as plt
            self.plot()
            plt.show()

        def plot(self):
            from matplotlib.patches import Ellipse, Rectangle
            import matplotlib.pyplot as plt
            ax = plt.subplot(111, aspect='equal')
            plt.scatter(self.x, self.y)
            plt.plot(
                self.x_stats.mean,
                self.y_stats.mean,
                marker="+",
                markeredgecolor="green",
                markerfacecolor="green")
            bounds = Rectangle(
                (self.x_stats.min, self.y_stats.min),
                self.x_stats.max - self.x_stats.min,
                self.y_stats.max - self.y_stats.min,
                alpha=0.5,
                edgecolor='red',
                fill=False,
                visible=True)
            ax.add_artist(bounds)
            ellipse = Ellipse(xy=(self.x_stats.mean, self.y_stats.mean),
                              width=self.width, height=self.height,
                              angle=self.theta)
            ellipse.set_alpha(0.25)
            ellipse.set_facecolor('green')
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
        import matplotlib.pyplot as plt
        for waypoint in waypoints:
            waypoint.plot()
        plt.show()

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-s",
        "--serial",
        type=str,
        required=True,
        help="Serial port address, like '/dev/ttyUSB0'")
    parser.add_argument(
        "-b",
        "--baudrate",
        type=int,
        default=115200,
        help="Serial port baud rate.")
    parser.add_argument(
        "-t",
        "--timeout",
        type=float,
        default=0.5,
        help="Serial port timeout in seconds.")
    parser.add_argument(
        "-sp",
        '--samples',
        type=int,
        default=5,
        help="Number of samples per waypoint.")
    parser.add_argument(
        "-wp",
        "--waypoints",
        type=int,
        default=0,
        help="Number of waypoints to collect;"
        "> 0 to collect waypoints, 0 to just log position")
    parser.add_argument(
        "-nstd",
        "--nstd",
        type=float,
        default=1.0,
        help="multiple of standard deviation for ellipse.")
    parser.add_argument(
        "-th",
        "--threaded",
        action='store_true',
        help="run in threaded mode.")
    parser.add_argument(
        "-db",
        "--debug",
        action='store_true',
        help="Enable extra logging")
    parser.add_argument(
        "-u",
        "--user",
        type=str,
        required=True,
        help="NTRIP username")
    parser.add_argument(
        "-p",
        "--password",
        type=str,
        required=True,
        help="NTRIP password")
    parser.add_argument(
        "-url",
        "--url",
        type=str,
        required=True,
        help="NTRIP URL")
    parser.add_argument(
        "-mp",
        "--mountpoint",
        type=str,
        required=True,
        help="NTRIP mountpoint")
    args = parser.parse_args()

    if args.waypoints < 0:
        print(
            "Use waypoints > 0 to collect waypoints,"
            "use 0 waypoints to just log position")
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

    waypoint_count = args.waypoints
    samples_per_waypoint = args.samples
    waypoints = []
    waypoint_samples = []

    try:
        serial_port = SerialPort(
            args.serial,
            baudrate=args.baudrate,
            timeout=args.timeout)
        line_reader = SerialLineReader(
            serial_port,
            max_lines=args.samples,
            debug=args.debug)
        position_reader = GpsNmeaPositions(args.debug)

        gps_position = GpsPosition(
            serial_port,
            args.user,
            args.password,
            args.url,
            args.mountpoint,
            debug=args.debug)

        if args.threaded:
            update_thread = threading.Thread(
                target=line_reader.update, args=(), daemon=True)
            update_thread.start()

        def read_gps():
            lines = (line_reader.run_threaded()
                     if args.threaded
                     else line_reader.run())
            positions = position_reader.run(lines)
            return positions

        ts = time.time()
        state = "prompt" if waypoint_count > 0 else ""
        while line_reader.running:
            readings = read_gps()
            if readings:
                print("")
                if state == "prompt":
                    print(
                        f"Move to waypoint #{len(waypoints) + 1} "
                        "and press the space bar and enter to start"
                        "sampling or any other key to just start logging.")

                    state = "move"
                elif state == "move":
                    key_press = readchar.readchar()
                    if key_press == ' ':
                        waypoint_samples = []
                        line_reader.clear()
                        state = "sampling"
                    else:
                        state = ""
                elif state == "sampling":
                    waypoint_samples += readings
                    count = len(waypoint_samples)
                    print(f"Collected {count} so far...")
                    if count > samples_per_waypoint:
                        print(
                            f"...done. Collected {count} samples "
                            f"for waypoint "
                            f"{len(waypoints) + 1}"
                        )
                        waypoint = Waypoint(waypoint_samples, nstd=args.nstd)
                        waypoints.append(waypoint)
                        if len(waypoints) < waypoint_count:
                            state = "prompt"
                        else:
                            state = "test_prompt"
                            if args.debug:
                                plot(waypoints)
                elif state == "test_prompt":
                    print(
                        "Waypoints are recorded.  Now walk around and "
                        "see when you are in a waypoint.")
                    state = "test"
                elif state == "test":
                    for ts, x, y in readings:
                        print(f"Your position is ({x}, {y})")
                        hit, index = is_in_waypoint_range(waypoints, x, y)
                        if hit:
                            print(
                                f"You are within the sample range "
                                f"of waypoint #{
                                    index + 1}")
                        std_deviation = 1.0
                        hit, index = is_in_waypoint_std(
                            waypoints, x, y, std_deviation)
                        if hit:
                            print(
                                f"You are within {std_deviation} std devs "
                                f"of the center of waypoint #{
                                    index + 1}")
                        hit, index = is_in_waypoint(waypoints, x, y)
                        if hit:
                            print(
                                f"You are at waypoint's ellipse #{
                                    index + 1}")
                else:
                    for position in readings:
                        ts, x, y = position
                        print(f"You are at ({x}, {y})")
            else:
                if time.time() > (ts + 0.5):
                    print(".", end="")
                    ts = time.time()
    finally:
        if line_reader:
            line_reader.shutdown()
        if update_thread is not None:
            update_thread.join()
