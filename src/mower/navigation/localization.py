import math
import os
import sys
import time
from typing import Tuple, Dict
from dataclasses import dataclass

import numpy as np
from shapely.geometry import Point, Polygon

from mower.navigation.gps import (
    GpsLatestPosition,
    GpsNmeaPositions
)
from mower.utilities.logger_config import (
    LoggerConfigInfo as LoggerConfig
)
from mower.constants import (
    max_lat,
    max_lng,
    min_lat,
    min_lng,
    polygon_coordinates
)


LoggerConfig.configure_logging()
logging = LoggerConfig.get_logger(__name__)

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@dataclass
class Position:
    """Data class to store position information."""

    latitude: float
    longitude: float
    altitude: float
    heading: float
    accuracy: float
    last_update: float


class Localization:
    """Enhanced localization system with sensor fusion and error handling."""

    _instance = None

    def __new__(cls):
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super(Localization, cls).__new__(cls)
            cls.__init__(cls._instance)
        return cls._instance

    def __init__(self):
        """Initialize the localization system."""
        if hasattr(self, '_initialized'):
            return
        self._initialized = True

        # Initialize GPS components
        self.position_reader = GpsNmeaPositions(debug=False)
        self.latest_position = GpsLatestPosition(debug=False)

        # Initialize position tracking
        self.position = Position(
            latitude=0.0,
            longitude=0.0,
            altitude=0.0,
            heading=0.0,
            accuracy=0.0,
            last_update=time.time()
        )

        # Initialize sensor interface and position tracking
        self.sensor_interface = None
        self.fused_position = None
        self.time_since_last_update = 0

        # Initialize boundaries
        self.yard_boundary = polygon_coordinates
        self.boundaries = {
            'min_lat': min_lat,
            'max_lat': max_lat,
            'min_lng': min_lng,
            'max_lng': max_lng
        }

        # Kalman filter parameters
        self.kalman_state = None
        self.kalman_covariance = None
        self.process_noise = 0.1
        self.measurement_noise = 0.5

    def get_sensor_interface(self):
        """Get or initialize the enhanced sensor interface."""
        if self.sensor_interface is None:
            from mower.hardware.sensor_interface import (
                EnhancedSensorInterface
            )
            self.sensor_interface = EnhancedSensorInterface()
        return self.sensor_interface

    def estimate_position(self) -> Tuple[float, float]:
        """
        Estimate current position using sensor fusion of GPS and IMU data.

        Returns:
            Tuple[float, float]: Estimated latitude and longitude
        """
        try:
            # Get sensor data
            sensor_interface = self.get_sensor_interface()
            sensor_data = sensor_interface.get_sensor_data()

            # Get GPS data
            gps_data = self.latest_position.run()

            if gps_data and 'heading' in sensor_data:
                return self._process_sensor_data(gps_data, sensor_data)
            else:
                return self._handle_limited_data(sensor_data)

        except Exception as e:
            logging.error(f"Position estimation error: {str(e)}")
            return (self.position.latitude, self.position.longitude)

    def _process_sensor_data(
        self,
        gps_data: Dict,
        sensor_data: Dict
    ) -> Tuple[float, float]:
        """
        Process GPS and sensor data for position estimation.

        Args:
            gps_data: Dictionary containing GPS data
            sensor_data: Dictionary containing sensor readings

        Returns:
            Tuple[float, float]: Processed latitude and longitude
        """
        gps_lat = gps_data['latitude']
        gps_lon = gps_data['longitude']
        imu_heading = sensor_data['heading']

        # Initialize Kalman filter if needed
        if self.kalman_state is None:
            self.kalman_state = np.array([gps_lat, gps_lon])
            self.kalman_covariance = np.eye(2) * 0.1

        # Predict step
        predicted_pos = self._predict_position(
            self.kalman_state,
            imu_heading,
            sensor_data.get('speed', 0),
            time.time() - self.position.last_update
        )

        # Update Kalman filter
        kalman_gain = self._calculate_kalman_gain()
        self.kalman_state = self._update_kalman_state(
            predicted_pos,
            kalman_gain,
            gps_lat,
            gps_lon
        )

        # Update position data
        self._update_position_data(imu_heading)

        return (self.position.latitude, self.position.longitude)

    def _handle_limited_data(self, sensor_data: Dict) -> Tuple[float, float]:
        """
        Handle position estimation with limited sensor data.

        Args:
            sensor_data: Dictionary containing sensor readings

        Returns:
            Tuple[float, float]: Best estimate of position
        """
        if self.kalman_state is not None and 'heading' in sensor_data:
            predicted_pos = self._predict_position(
                self.kalman_state,
                sensor_data['heading'],
                sensor_data.get('speed', 0),
                time.time() - self.position.last_update
            )
            self.kalman_state = predicted_pos
            self.kalman_covariance += self.process_noise

            self._update_position_from_kalman()

            return (self.position.latitude, self.position.longitude)

        logging.warning("Insufficient data for position estimation")
        return (self.position.latitude, self.position.longitude)

    def _predict_position(
        self,
        current_pos: np.ndarray,
        heading: float,
        speed: float,
        time_delta: float
    ) -> np.ndarray:
        """
        Predict next position based on current motion.

        Args:
            current_pos: Current position as numpy array
            heading: Current heading in degrees
            speed: Current speed
            time_delta: Time since last update

        Returns:
            np.ndarray: Predicted position
        """
        heading_rad = math.radians(heading)
        distance = speed * time_delta

        lat_change = distance * math.cos(heading_rad)
        lon_change = distance * math.sin(heading_rad)

        return current_pos + np.array([lat_change, lon_change])

    def _calculate_kalman_gain(self) -> float:
        """Calculate Kalman gain for position updating."""
        return (self.kalman_covariance /
                (self.kalman_covariance + self.measurement_noise))

    def _update_kalman_state(
        self,
        predicted_pos: np.ndarray,
        kalman_gain: float,
        gps_lat: float,
        gps_lon: float
    ) -> np.ndarray:
        """
        Update Kalman filter state with new measurements.

        Args:
            predicted_pos: Predicted position
            kalman_gain: Calculated Kalman gain
            gps_lat: GPS latitude
            gps_lon: GPS longitude

        Returns:
            np.ndarray: Updated Kalman state
        """
        measurement = np.array([gps_lat, gps_lon])
        self.kalman_covariance = (
            (1 - kalman_gain) * self.kalman_covariance + self.process_noise
        )
        return predicted_pos + kalman_gain * (measurement - predicted_pos)

    def _update_position_data(self, heading: float):
        """
        Update position object with new data.

        Args:
            heading: Current heading in degrees
        """
        self.position.latitude = float(self.kalman_state[0])
        self.position.longitude = float(self.kalman_state[1])
        self.position.heading = heading
        self.position.last_update = time.time()
        self.position.accuracy = float(
            np.sqrt(self.kalman_covariance.diagonal().mean())
        )

    def _update_position_from_kalman(self):
        """Update position object from Kalman state."""
        self.position.latitude = float(self.kalman_state[0])
        self.position.longitude = float(self.kalman_state[1])
        self.position.last_update = time.time()

    def update(self) -> Dict:
        """
        Update position and orientation, returning current state.

        Returns:
            Dict: Current position and status information
        """
        try:
            new_lat, new_lon = self.estimate_position()

            # Update orientation from IMU
            sensor_data = self.get_sensor_interface().get_sensor_data()
            if 'heading' in sensor_data:
                self.position.heading = sensor_data['heading']

            # Check boundary
            in_bounds = self.is_within_yard(new_lat, new_lon)
            if not in_bounds:
                logging.warning("Position outside"
                                "yard boundary!")

            return {
                'latitude': new_lat,
                'longitude': new_lon,
                'heading': self.position.heading,
                'accuracy': self.position.accuracy,
                'last_update': self.position.last_update,
                'in_bounds': in_bounds
            }

        except Exception as e:
            logging.error(f"Update error: {str(e)}")
            return self._generate_error_status(str(e))

    def _generate_error_status(self, error_msg: str) -> Dict:
        """
        Generate status dictionary for error conditions.

        Args:
            error_msg: Error message to include

        Returns:
            Dict: Status dictionary with error information
        """
        return {
            'latitude': self.position.latitude,
            'longitude': self.position.longitude,
            'heading': self.position.heading,
            'accuracy': self.position.accuracy,
            'last_update': self.position.last_update,
            'in_bounds': False,
            'error': error_msg
        }

    def is_within_yard(self, lat: float, lon: float) -> bool:
        """
        Check if position is within yard boundary.

        Args:
            lat: Latitude to check
            lon: Longitude to check

        Returns:
            bool: True if position is within yard boundary
        """
        try:
            # First check simple rectangular bounds
            in_rectangle = (
                self.boundaries['min_lat'] <= lat <= self.boundaries['max_lat']
                and
                self.boundaries['min_lng'] <= lon <= self.boundaries['max_lng']
            )

            if not in_rectangle:
                return False

            # Then check against detailed polygon if available
            if self.yard_boundary:
                point = Point(lon, lat)
                polygon = Polygon(self.yard_boundary)
                return polygon.contains(point)

            return True

        except Exception as e:
            logging.error(f"Boundary check error: {str(e)}")
            return False

    def get_position_accuracy(self) -> float:
        """
        Get estimated accuracy of current position.

        Returns:
            float: Estimated accuracy in meters
        """
        return self.position.accuracy

    def get_last_update_age(self) -> float:
        """
        Get age of last position update in seconds.

        Returns:
            float: Time since last update in seconds
        """
        return time.time() - self.position.last_update


def main():
    """Test the localization system."""
    localization = Localization()
    try:
        while True:
            status = localization.update()
            print(
                f"Position: ({status['latitude']:.6f}, "
                f"{status['longitude']:.6f})\n"
                f"Heading: {status['heading']:.1f}°\n"
                f"Accuracy: {status['accuracy']:.2f}m\n"
                f"In Bounds: {status['in_bounds']}\n"
                f"Update Age: {localization.get_last_update_age():.1f}s"
            )
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nProgram terminated by user.")


if __name__ == "__main__":
    main()
