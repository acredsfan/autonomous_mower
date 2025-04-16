"""
Weather service module for autonomous mower.

This module provides weather prediction and monitoring capabilities using
OpenWeatherMap API and local sensor data.
"""

import os
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from dotenv import load_dotenv  # type:ignore

from mower.utilities.logger_config import LoggerConfigInfo

# Ensure logger initialization uses LoggerConfigInfo for consistency.
logger = LoggerConfigInfo.get_logger(__name__)

# Load environment variables
load_dotenv()


@dataclass
class WeatherConditions:
    """Data class for weather conditions."""
    temperature: float
    humidity: float
    rain_probability: float
    wind_speed: float
    cloud_cover: float
    timestamp: datetime
    source: str  # 'api' or 'sensor'


class WeatherService:
    """Service for weather monitoring and prediction."""

    def __init__(self):
        self.api_key = os.getenv('OPENWEATHERMAP_API_KEY')
        self.latitude = float(os.getenv('LATITUDE', 0))
        self.longitude = float(os.getenv('LONGITUDE', 0))
        self.cache_duration = 1800  # 30 minutes in seconds
        self.last_api_update = 0
        self.cached_forecast = None
        self.ideal_mowing_conditions = {
            'min_temperature': 10,  # °C
            'max_temperature': 35,  # °C
            'max_humidity': 80,    # %
            'max_rain_probability': 30,  # %
            'max_wind_speed': 20,  # km/h
            'max_cloud_cover': 70  # %
        }

    def get_current_conditions(self) -> WeatherConditions:
        """Get current weather conditions from API and sensors."""
        try:
            # Get API data if cache is expired
            if time.time() - self.last_api_update > self.cache_duration:
                self._update_forecast()

            # Get sensor data
            sensor_data = self._get_sensor_data()

            # Combine API and sensor data
            conditions = self._combine_weather_data(sensor_data)

            return conditions
        except Exception as e:
            logger.error(f"Error getting weather conditions: {e}")
            return self._get_fallback_conditions()

    def is_mowing_weather(self) -> Tuple[bool, str]:
        """Check if current weather is suitable for mowing."""
        conditions = self.get_current_conditions()
        reasons = []
        # Check temperature
        if conditions.temperature < self.ideal_mowing_conditions[
                'min_temperature']:
            reasons.append("too cold")
        elif conditions.temperature > self.ideal_mowing_conditions[
                'max_temperature']:
            reasons.append("too hot")

        # Check humidity
        if conditions.humidity > self.ideal_mowing_conditions['max_humidity']:
            reasons.append("too humid")

        # Check rain probability
        if (conditions.rain_probability >
                self.ideal_mowing_conditions['max_rain_probability']):
            reasons.append("high chance of rain")
        # Check wind speed
        if conditions.wind_speed > self.ideal_mowing_conditions[
                'max_wind_speed']:
            reasons.append("too windy")

        # Check cloud cover
        if conditions.cloud_cover > self.ideal_mowing_conditions[
                'max_cloud_cover']:
            reasons.append("too cloudy")

        is_suitable = len(reasons) == 0
        reason = " and ".join(reasons) if reasons else "suitable for mowing"

        return is_suitable, reason

    def get_forecast(self, hours: int = 24) -> Dict:
        """Get weather forecast for specified number of hours."""
        try:
            if time.time() - self.last_api_update > self.cache_duration:
                self._update_forecast()

            if not self.cached_forecast:
                return {}

            forecast = []
            for hour in range(hours):
                timestamp = datetime.now() + timedelta(hours=hour)
                conditions = self._get_forecast_for_time(timestamp)
                if conditions:
                    forecast.append({
                        'timestamp': timestamp.isoformat(),
                        'temperature': conditions.temperature,
                        'humidity': conditions.humidity,
                        'rain_probability': conditions.rain_probability,
                        'wind_speed': conditions.wind_speed,
                        'cloud_cover': conditions.cloud_cover
                    })

            return {'forecast': forecast}
        except Exception as e:
            logger.error(f"Error getting forecast: {e}")
            return {}

    def _update_forecast(self) -> None:
        """Update forecast data from OpenWeatherMap API."""
        try:
            url = (
                f"https://api.openweathermap.org/data/2.5/forecast?"
                f"lat={self.latitude}&lon={self.longitude}&"
                f"appid={self.api_key}&units=metric"
            )
            response = requests.get(url)
            response.raise_for_status()
            self.cached_forecast = response.json()
            self.last_api_update = time.time()
        except Exception as e:
            logger.error(f"Error updating forecast: {e}")

    def _get_sensor_data(self) -> Dict:
        """Get weather data from local sensors."""
        try:
            from mower.hardware.sensor_interface import SensorInterface
            sensors = SensorInterface()
            return {
                'temperature': sensors.get_temperature(),
                'humidity': sensors.get_humidity(),
                'pressure': sensors.get_pressure()
            }
        except Exception as e:
            logger.error(f"Error getting sensor data: {e}")
            return {}

    def _combine_weather_data(self, sensor_data: Dict) -> WeatherConditions:
        """Combine API and sensor data for best accuracy."""
        try:
            # Get API data for current time
            api_data = self._get_forecast_for_time(datetime.now())

            if not api_data:
                return self._get_fallback_conditions()

            # Use sensor data if available, otherwise use API data
            temperature = (
                sensor_data.get('temperature', api_data.temperature)
                if sensor_data else api_data.temperature
            )
            humidity = (
                sensor_data.get('humidity', api_data.humidity)
                if sensor_data else api_data.humidity
            )

            return WeatherConditions(
                temperature=temperature,
                humidity=humidity,
                rain_probability=api_data.rain_probability,
                wind_speed=api_data.wind_speed,
                cloud_cover=api_data.cloud_cover,
                timestamp=datetime.now(),
                source='sensor' if sensor_data else 'api'
            )
        except Exception as e:
            logger.error(f"Error combining weather data: {e}")
            return self._get_fallback_conditions()

    def _get_forecast_for_time(
            self,
            timestamp: datetime) -> Optional[WeatherConditions]:
        """Get forecast data for specific timestamp."""
        if not self.cached_forecast:
            return None

        try:
            # Find closest forecast time
            closest_forecast = None
            min_time_diff = float('inf')

            for forecast in self.cached_forecast['list']:
                forecast_time = datetime.fromtimestamp(forecast['dt'])
                time_diff = abs((timestamp - forecast_time).total_seconds())

                if time_diff < min_time_diff:
                    min_time_diff = time_diff
                    closest_forecast = forecast

            if closest_forecast:
                return WeatherConditions(
                    temperature=closest_forecast['main']['temp'],
                    humidity=closest_forecast['main']['humidity'],
                    rain_probability=closest_forecast.get('pop', 0) * 100,
                    wind_speed=closest_forecast['wind']['speed'],
                    cloud_cover=closest_forecast['clouds']['all'],
                    timestamp=datetime.fromtimestamp(closest_forecast['dt']),
                    source='api'
                )
        except Exception as e:
            logger.error(f"Error getting forecast for time: {e}")

        return None

    def _get_fallback_conditions(self) -> WeatherConditions:
        """Get fallback weather conditions when API/sensors fail."""
        return WeatherConditions(
            temperature=20.0,
            humidity=50.0,
            rain_probability=0.0,
            wind_speed=0.0,
            cloud_cover=0.0,
            timestamp=datetime.now(),
            source='fallback'
        )
