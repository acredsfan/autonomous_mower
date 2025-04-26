"""
Sensor interfaces for the autonomous mower.

This module defines interfaces for various sensor types used in the
autonomous mower project, providing a flexible framework for adding
new sensor types and implementing sensor fusion.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime


class SensorInterface(ABC):
    """
    Base interface for all sensor implementations.

    This interface defines the common contract that all sensor
    implementations must adhere to.
    """

    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the sensor.

        Returns:
            bool: True if initialization was successful, False otherwise
        """
        pass

    @abstractmethod
    def read(self) -> Dict[str, Any]:
        """
        Read data from the sensor.

        Returns:
            Dict[str, Any]: Sensor readings
        """
        pass

    @abstractmethod
    def calibrate(self) -> bool:
        """
        Calibrate the sensor.

        Returns:
            bool: True if calibration was successful, False otherwise
        """
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the sensor.

        Returns:
            Dict[str, Any]: Sensor status information
        """
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources used by the sensor."""
        pass


class EnvironmentalSensorInterface(SensorInterface):
    """Interface for environmental sensors (temperature, humidity, pressure, etc.)."""

    @abstractmethod
    def get_temperature(self) -> float:
        """
        Get the current temperature.

        Returns:
            float: Temperature in degrees Celsius
        """
        pass

    @abstractmethod
    def get_humidity(self) -> float:
        """
        Get the current humidity.

        Returns:
            float: Relative humidity as a percentage
        """
        pass

    @abstractmethod
    def get_pressure(self) -> float:
        """
        Get the current atmospheric pressure.

        Returns:
            float: Pressure in hPa
        """
        pass


class IMUSensorInterface(SensorInterface):
    """Interface for Inertial Measurement Unit sensors."""

    @abstractmethod
    def get_acceleration(self) -> Tuple[float, float, float]:
        """
        Get the current acceleration.

        Returns:
            Tuple[float, float, float]: Acceleration in m/s² (x, y, z)
        """
        pass

    @abstractmethod
    def get_gyroscope(self) -> Tuple[float, float, float]:
        """
        Get the current gyroscope readings.

        Returns:
            Tuple[float, float, float]: Angular velocity in rad/s (x, y, z)
        """
        pass

    @abstractmethod
    def get_magnetometer(self) -> Tuple[float, float, float]:
        """
        Get the current magnetometer readings.

        Returns:
            Tuple[float, float, float]: Magnetic field in μT (x, y, z)
        """
        pass

    @abstractmethod
    def get_orientation(self) -> Tuple[float, float, float]:
        """
        Get the current orientation.

        Returns:
            Tuple[float, float, float]: Orientation in degrees (roll, pitch, yaw)
        """
        pass


class DistanceSensorInterface(SensorInterface):
    """Interface for distance/proximity sensors."""

    @abstractmethod
    def get_distance(self) -> float:
        """
        Get the current distance measurement.

        Returns:
            float: Distance in centimeters
        """
        pass

    @abstractmethod
    def set_range(self, min_range: float, max_range: float) -> None:
        """
        Set the valid measurement range for the sensor.

        Args:
            min_range: Minimum valid range in centimeters
            max_range: Maximum valid range in centimeters
        """
        pass


class GPSSensorInterface(SensorInterface):
    """Interface for GPS/GNSS sensors."""

    @abstractmethod
    def get_position(self) -> Tuple[float, float]:
        """
        Get the current GPS position.

        Returns:
            Tuple[float, float]: Latitude and longitude
        """
        pass

    @abstractmethod
    def get_altitude(self) -> float:
        """
        Get the current altitude.

        Returns:
            float: Altitude in meters
        """
        pass

    @abstractmethod
    def get_speed(self) -> float:
        """
        Get the current ground speed.

        Returns:
            float: Speed in meters per second
        """
        pass

    @abstractmethod
    def get_heading(self) -> float:
        """
        Get the current heading.

        Returns:
            float: Heading in degrees (0-359)
        """
        pass

    @abstractmethod
    def get_satellites(self) -> int:
        """
        Get the number of satellites in view.

        Returns:
            int: Number of satellites
        """
        pass

    @abstractmethod
    def get_fix_quality(self) -> int:
        """
        Get the GPS fix quality.

        Returns:
            int: Fix quality (0=no fix, 1=GPS fix, 2=DGPS fix)
        """
        pass


class PowerSensorInterface(SensorInterface):
    """Interface for power monitoring sensors."""

    @abstractmethod
    def get_voltage(self, channel: Optional[int] = None) -> float:
        """
        Get the current voltage.

        Args:
            channel: Optional channel number for multi-channel sensors

        Returns:
            float: Voltage in volts
        """
        pass

    @abstractmethod
    def get_current(self, channel: Optional[int] = None) -> float:
        """
        Get the current current draw.

        Args:
            channel: Optional channel number for multi-channel sensors

        Returns:
            float: Current in amperes
        """
        pass

    @abstractmethod
    def get_power(self, channel: Optional[int] = None) -> float:
        """
        Get the current power consumption.

        Args:
            channel: Optional channel number for multi-channel sensors

        Returns:
            float: Power in watts
        """
        pass

    @abstractmethod
    def get_battery_level(self) -> float:
        """
        Get the current battery level.

        Returns:
            float: Battery level as a percentage
        """
        pass


class RainSensorInterface(SensorInterface):
    """Interface for rain sensors."""

    @abstractmethod
    def is_raining(self) -> bool:
        """
        Check if it's currently raining.

        Returns:
            bool: True if raining, False otherwise
        """
        pass

    @abstractmethod
    def get_rain_intensity(self) -> float:
        """
        Get the current rain intensity.

        Returns:
            float: Rain intensity (0.0-1.0)
        """
        pass


class SensorFusionInterface(ABC):
    """
    Interface for sensor fusion implementations.

    This interface defines methods for combining data from multiple sensors
    to improve accuracy and reliability.
    """

    @abstractmethod
    def register_sensor(
        self, sensor_type: str, sensor: SensorInterface
    ) -> None:
        """
        Register a sensor with the fusion system.

        Args:
            sensor_type: Type of sensor being registered
            sensor: Sensor instance
        """
        pass

    @abstractmethod
    def unregister_sensor(
        self, sensor_type: str, sensor: SensorInterface
    ) -> None:
        """
        Unregister a sensor from the fusion system.

        Args:
            sensor_type: Type of sensor being unregistered
            sensor: Sensor instance
        """
        pass

    @abstractmethod
    def get_fused_position(self) -> Tuple[float, float]:
        """
        Get the fused position estimate from multiple sensors.

        Returns:
            Tuple[float, float]: Latitude and longitude
        """
        pass

    @abstractmethod
    def get_fused_orientation(self) -> Tuple[float, float, float]:
        """
        Get the fused orientation estimate from multiple sensors.

        Returns:
            Tuple[float, float, float]: Orientation in degrees (roll, pitch, yaw)
        """
        pass

    @abstractmethod
    def get_fused_obstacle_map(self) -> Dict[str, Any]:
        """
        Get the fused obstacle map from multiple sensors.

        Returns:
            Dict[str, Any]: Obstacle map data
        """
        pass

    @abstractmethod
    def get_confidence_levels(self) -> Dict[str, float]:
        """
        Get confidence levels for various fused measurements.

        Returns:
            Dict[str, float]: Confidence levels (0.0-1.0) for different measurements
        """
        pass
