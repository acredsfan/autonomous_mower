"""
Simulated GPS sensor.

This module provides a simulated version of the GPS sensor classes that interact
with the virtual world model to provide realistic GPS position data without
requiring physical hardware.
"""

import math
import random
import threading
import time
from typing import Any, Dict, List, Optional, Tuple, Type, Union

from mower.simulation.hardware_sim import SimulatedSensor
from mower.simulation.world_model import Vector2D, get_world_instance
from mower.utilities.logger_config import LoggerConfigInfo

# Configure logging
logger = LoggerConfigInfo.get_logger(__name__)


class SimulatedGpsPosition(SimulatedSensor):
    """
    Simulated GPS position sensor.

    This class provides a simulated version of the GpsPosition class that interacts
    with the virtual world model to provide realistic GPS position data without
    requiring physical hardware.
    """

    def __init__(self):
        """Initialize the simulated GPS sensor."""
        super().__init__("GPS Position")

        # Initialize sensor data
        self.state = {
            # (timestamp, easting, northing, zone_number, zone_letter)
            "position": None,
            "nmea_sentences": [],  # List of NMEA sentences
            "status": "Initializing GPS...",
            "fix_quality": 0,  # 0 = no fix, 1 = GPS fix, 2 = DGPS fix
            "satellites": 0,  # Number of satellites in view
            "hdop": 99.9,  # Horizontal dilution of precision
        }

        # Initialize sensor parameters
        self.noise_level = 0.0001  # Noise level in degrees (about 10m)
        self.reading_interval = 1.0  # 1Hz update rate (typical for GPS)
        self.fix_probability = 0.95  # Probability of having a GPS fix
        self.dgps_probability = 0.5  # Probability of having a DGPS fix if we have a fix

        # Initialize GPS parameters
        self.origin_lat = 37.7749  # San Francisco latitude
        self.origin_lng = -122.4194  # San Francisco longitude
        self.utm_zone = 10  # UTM zone for San Francisco
        self.utm_letter = "S"  # UTM letter for San Francisco

        # Get the virtual world instance
        self.world = get_world_instance()

        # Initialize thread for generating NMEA sentences
        self.running = False
        self.thread = None

    def _initialize_sim(self, *args, **kwargs) -> None:
        """Initialize the simulated GPS sensor."""
        # Start the NMEA generation thread
        self.running = True
        self.thread = threading.Thread(target=self._generate_nmea_sentences, daemon=True)
        self.thread.start()

    def _cleanup_sim(self) -> None:
        """Clean up the simulated GPS sensor."""
        # Stop the NMEA generation thread
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)

    def _update_sensor_data(self) -> None:
        """Update the simulated GPS sensor data from the virtual world."""
        # Get the robot state from the virtual world
        robot_state = self.world.get_robot_state()

        # Extract position
        position = robot_state["position"]

        # Convert position to lat/lng
        # In a real system, this would be more complex
        # For simulation, we'll use a simple approximation
        # 1 degree of latitude is approximately 111km
        # 1 degree of longitude is approximately 111km * cos(latitude)
        lat = self.origin_lat + position[1] / 111000.0
        lng = self.origin_lng + position[0] / (111000.0 * math.cos(math.radians(self.origin_lat)))

        # Add noise to lat/lng
        lat = self.add_noise(lat, self.noise_level)
        lng = self.add_noise(lng, self.noise_level)

        # Convert lat/lng to UTM
        # In a real system, this would use a proper UTM conversion
        # For simulation, we'll use a simple approximation
        easting = (lng - self.origin_lng) * 111000.0 * math.cos(math.radians(self.origin_lat))
        northing = (lat - self.origin_lat) * 111000.0

        # Determine fix quality
        if random.random() < self.fix_probability:
            if random.random() < self.dgps_probability:
                fix_quality = 2  # DGPS fix
                satellites = random.randint(8, 12)
                hdop = random.uniform(0.8, 1.5)
                status = "GPS fix acquired (DGPS)."
            else:
                fix_quality = 1  # GPS fix
                satellites = random.randint(4, 8)
                hdop = random.uniform(1.5, 3.0)
                status = "GPS fix acquired."
        else:
            fix_quality = 0  # No fix
            satellites = random.randint(0, 3)
            hdop = random.uniform(10.0, 99.9)
            status = "Waiting for GPS fix..."
            # Return early without updating position
            self.state.update(
                {
                    "fix_quality": fix_quality,
                    "satellites": satellites,
                    "hdop": hdop,
                    "status": status,
                }
            )
            return

        # Update state
        timestamp = time.time()
        self.state.update(
            {
                "position": (
                    timestamp,
                    easting,
                    northing,
                    self.utm_zone,
                    self.utm_letter,
                ),
                "fix_quality": fix_quality,
                "satellites": satellites,
                "hdop": hdop,
                "status": status,
            }
        )

    def _get_sensor_data(self) -> Dict[str, Any]:
        """Get the current simulated GPS sensor data."""
        return self.state

    def _generate_nmea_sentences(self) -> None:
        """Generate NMEA sentences in a background thread."""
        while self.running:
            try:
                # Get the current position
                position = self.state.get("position")
                if position:
                    timestamp, easting, northing, zone_number, zone_letter = position

                    # Convert UTM to lat/lng
                    # In a real system, this would use a proper UTM conversion
                    # For simulation, we'll use a simple approximation
                    lat = self.origin_lat + northing / 111000.0
                    lng = self.origin_lng + easting / (111000.0 * math.cos(math.radians(self.origin_lat)))

                    # Generate NMEA sentences
                    nmea_sentences = self._generate_nmea_for_position(lat, lng)

                    # Update state
                    with self._lock:
                        self.state["nmea_sentences"] = nmea_sentences

                # Sleep for a while
                time.sleep(1.0)

            except Exception as e:
                logger.error(f"Error generating NMEA sentences: {e}")
                time.sleep(1.0)

    def _generate_nmea_for_position(self, lat: float, lng: float) -> List[Tuple[float, str]]:
        """
        Generate NMEA sentences for the given position.

        Args:
            lat: Latitude in degrees
            lng: Longitude in degrees

        Returns:
            List[Tuple[float, str]]: List of (timestamp, nmea_sentence) tuples
        """
        timestamp = time.time()

        # Convert lat/lng to NMEA format
        lat_deg = int(lat)
        lat_min = (lat - lat_deg) * 60
        lat_nmea = f"{lat_deg:02d}{lat_min:06.3f}"
        lat_dir = "N" if lat >= 0 else "S"

        lng_deg = int(lng)
        lng_min = (lng - lng_deg) * 60
        lng_nmea = f"{lng_deg:03d}{lng_min:06.3f}"
        lng_dir = "E" if lng >= 0 else "W"

        # Generate time string
        gps_time = time.gmtime(timestamp)
        time_str = f"{gps_time.tm_hour:02d}{gps_time.tm_min:02d}{gps_time.tm_sec:02d}"
        date_str = f"{gps_time.tm_year % 100:02d}{gps_time.tm_mon:02d}{gps_time.tm_mday:02d}"
        time_str = f"{time_str}.{int(timestamp % 1 * 1e3):03d}"  # Add milliseconds

        # Generate a simple GPRMC sentence
        rmc = f"$GPRMC,{time_str},A,{lat_nmea},{lat_dir},{lng_nmea},{lng_dir}," f"0.0,0.0,{date_str},,,A"
        rmc_checksum = self._calculate_nmea_checksum(rmc)
        rmc = f"{rmc}*{rmc_checksum:02X}"

        # Generate GPGGA sentence
        # $GPGGA,time,lat,lat_dir,lng,lng_dir,quality,satellites,hdop,altitude,alt_unit,geoid_height,geoid_unit,age,ref_id*checksum
        quality = self.state["fix_quality"]
        satellites = self.state["satellites"]
        hdop = self.state["hdop"]
        altitude = 0.0  # Altitude in meters
        alt_unit = "M"  # Meters
        geoid_height = 0.0  # Geoid height
        geoid_unit = "M"  # Meters
        age = ""  # Age of DGPS data
        ref_id = ""  # Reference station ID

        gga = (
            f"$GPGGA,{time_str},{lat_nmea},{lat_dir},{lng_nmea},{lng_dir},"
            f"{quality},{satellites},{hdop:.1f},{altitude:.1f},{alt_unit},"
            f"{geoid_height:.1f},{geoid_unit},{age},{ref_id}"
        )
        gga_checksum = self._calculate_nmea_checksum(gga)
        gga = f"{gga}*{gga_checksum:02X}"

        return [(timestamp, rmc), (timestamp, gga)]

    def _calculate_nmea_checksum(self, nmea_str: str) -> int:
        """
        Calculate the checksum for an NMEA sentence.

        Args:
            nmea_str: NMEA sentence without the checksum

        Returns:
            int: Checksum value
        """
        # Remove the $ at the beginning
        nmea_str = nmea_str[1:]

        # Calculate XOR of all characters
        checksum = 0
        for char in nmea_str:
            checksum ^= ord(char)

        return checksum

    # GpsPosition interface methods

    def _initialize(self) -> bool:
        """Initialize the simulated GPS sensor."""
        return super()._initialize()

    def get_data(self) -> Dict[str, Any]:
        """Get all sensor data from the simulated GPS sensor."""
        return super().get_data()

    def get_position(self) -> Optional[Tuple[float, float, float, int, str]]:
        """
        Get the current GPS position.

        Returns:
            Optional[Tuple[float, float, float, int, str]]: (timestamp, easting, northing, zone_number, zone_letter)
            or None if no position is available
        """
        self.get_data()  # Ensure data is up to date
        return self.state["position"]

    def get_status(self) -> str:
        """
        Get the current GPS status.

        Returns:
            str: Status message
        """
        self.get_data()  # Ensure data is up to date
        return self.state["status"]

    def get_nmea_sentences(self) -> List[Tuple[float, str]]:
        """
        Get the current NMEA sentences.

        Returns:
            List[Tuple[float, str]]: List of (timestamp, nmea_sentence) tuples
        """
        self.get_data()  # Ensure data is up to date
        return self.state["nmea_sentences"]

    def run(self) -> Optional[Tuple[float, float, float, int, str]]:
        """
        Get the current GPS position (alias for get_position).

        Returns:
            Optional[Tuple[float, float, float, int, str]]: (timestamp, easting, northing, zone_number, zone_letter)
            or None if no position is available
        """
        return self.get_position()

    def cleanup(self) -> bool:
        """Clean up the simulated GPS sensor."""
        return super().cleanup()


class SimulatedGpsLatestPosition(SimulatedSensor):
    """
    Simulated GPS latest position sensor.

    This class provides a simulated version of the GpsLatestPosition class that
    interacts with the virtual world model to provide the latest GPS position data
    without requiring physical hardware.
    """

    def __init__(self, gps_position: SimulatedGpsPosition):
        """
        Initialize the simulated GPS latest position sensor.

        Args:
            gps_position: SimulatedGpsPosition instance to get position data from
        """
        super().__init__("GPS Latest Position")

        # Store the GPS position sensor
        self.gps_position = gps_position

        # Initialize sensor data
        self.state = {
            # (timestamp, easting, northing, zone_number, zone_letter)
            "position": None,
            "status": "Initializing GPS...",
        }

    def _initialize_sim(self, *args, **kwargs) -> None:
        """Initialize the simulated GPS latest position sensor."""
        # Nothing special to initialize
        pass

    def _cleanup_sim(self) -> None:
        """Clean up the simulated GPS latest position sensor."""
        # Nothing special to clean up
        pass

    def _update_sensor_data(self) -> None:
        """Update the simulated GPS latest position sensor data."""
        # Get the latest position from the GPS position sensor
        position = self.gps_position.get_position()
        status = self.gps_position.get_status()

        # Update state
        self.state.update({"position": position, "status": status})

    def _get_sensor_data(self) -> Dict[str, Any]:
        """Get the current simulated GPS latest position sensor data."""
        return self.state

    # GpsLatestPosition interface methods

    def _initialize(self) -> bool:
        """Initialize the simulated GPS latest position sensor."""
        return super()._initialize()

    def get_data(self) -> Dict[str, Any]:
        """Get all sensor data from the simulated GPS latest position sensor."""
        return super().get_data()

    def run(self) -> Optional[Tuple[float, float, float, int, str]]:
        """
        Get the latest GPS position.

        Returns:
            Optional[Tuple[float, float, float, int, str]]: (timestamp, easting, northing, zone_number, zone_letter)
            or None if no position is available
        """
        self.get_data()  # Ensure data is up to date
        return self.state["position"]

    def get_status(self) -> str:
        """
        Get the current GPS status.

        Returns:
            str: Status message
        """
        self.get_data()  # Ensure data is up to date
        return self.state["status"]

    def cleanup(self) -> bool:
        """Clean up the simulated GPS latest position sensor."""
        return super().cleanup()
