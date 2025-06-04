"""
Weather service module for autonomous mower.

This module provides weather prediction and monitoring capabilities using
OpenWeatherMap API and local sensor data.
"""

import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple  # Added Any, List

import requests
from dotenv import load_dotenv

from mower.utilities.logger_config import LoggerConfigInfo

# Initialize logger
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
        self.api_key = os.getenv("GOOGLE_WEATHER_API_KEY")
        self.latitude = float(os.getenv("LATITUDE", 0))
        self.longitude = float(os.getenv("LONGITUDE", 0))
        self.cache_duration = 1800  # 30 minutes in seconds
        self.last_api_update = 0
        self.cached_forecast = None
        self.ideal_mowing_conditions = {
            "min_temperature": 10,  # °C
            "max_temperature": 35,  # °C
            "max_humidity": 80,  # %
            "max_rain_probability": 30,  # %
            "max_wind_speed": 20,  # km/h
            "max_cloud_cover": 70,  # %
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
        if conditions.temperature < self.ideal_mowing_conditions["min_temperature"]:
            reasons.append("too cold")
        elif conditions.temperature > self.ideal_mowing_conditions["max_temperature"]:
            reasons.append("too hot")

        # Check humidity
        if conditions.humidity > self.ideal_mowing_conditions["max_humidity"]:
            reasons.append("too humid")

        # Check rain probability
        if conditions.rain_probability > self.ideal_mowing_conditions["max_rain_probability"]:
            reasons.append("high chance of rain")
        # Check wind speed
        if conditions.wind_speed > self.ideal_mowing_conditions["max_wind_speed"]:
            reasons.append("too windy")

        # Check cloud cover
        if conditions.cloud_cover > self.ideal_mowing_conditions["max_cloud_cover"]:
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
                    forecast.append(
                        {
                            "timestamp": timestamp.isoformat(),
                            "temperature": conditions.temperature,
                            "humidity": conditions.humidity,
                            "rain_probability": conditions.rain_probability,
                            "wind_speed": conditions.wind_speed,
                            "cloud_cover": conditions.cloud_cover,
                        }
                    )

            return {"forecast": forecast}
        except Exception as e:
            logger.error(f"Error getting forecast: {e}")
            return {}

    def _update_forecast(self) -> None:
        """Update forecast data from OpenWeatherMap API."""
        if not self.api_key:
            logger.error("Google Weather API key is missing. Cannot update forecast.")
            self.cached_forecast = None
            self.last_api_update = time.time()  # Treat as an update attempt to prevent rapid retries
            return

        try:
            url = "https://weather.googleapis.com/v1/forecast/hours:lookup"
            params = {
                "key": self.api_key,
                "location.latitude": self.latitude,
                "location.longitude": self.longitude,
                "unitsSystem": "METRIC",
            }
            response = requests.get(url, params=params)
            response.raise_for_status()
            self.cached_forecast = response.json()  # Google API returns data in 'forecastHours'
            self.last_api_update = time.time()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error updating forecast from Google Weather API: {e}")
            self.cached_forecast = None  # Ensure cache is cleared on API error
        except Exception as e:  # Catch any other unexpected errors
            logger.error(f"Unexpected error updating forecast: {e}")
            self.cached_forecast = None

    def _get_sensor_data(self) -> Dict:
        """Get weather data from local sensors."""
        try:
            from mower.hardware.sensor_interface import SensorInterface

            sensors = SensorInterface()
            return {
                "temperature": sensors.get_temperature(),
                "humidity": sensors.get_humidity(),
                "pressure": sensors.get_pressure(),
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
            temperature = sensor_data.get("temperature", api_data.temperature) if sensor_data else api_data.temperature
            humidity = sensor_data.get("humidity", api_data.humidity) if sensor_data else api_data.humidity

            return WeatherConditions(
                temperature=temperature,
                humidity=humidity,
                rain_probability=api_data.rain_probability,
                wind_speed=api_data.wind_speed,
                cloud_cover=api_data.cloud_cover,
                timestamp=datetime.now(),
                source="sensor" if sensor_data else "api",
            )
        except Exception as e:
            logger.error(f"Error combining weather data: {e}")
            return self._get_fallback_conditions()

    def _get_forecast_for_time(self, timestamp: datetime) -> Optional[WeatherConditions]:
        """Get forecast data for specific timestamp."""
        if not self.cached_forecast or not self.cached_forecast.get("forecastHours"):
            logger.warning("No forecast data available in _get_forecast_for_time.")
            return None

        try:
            closest_forecast_item = None
            min_time_diff = float("inf")

            for forecast_item in self.cached_forecast.get("forecastHours", []):
                # Parse timestamp from 'interval.startTime'
                # Example: "2025-02-05T23:00:00Z"
                try:
                    item_start_time_str = forecast_item.get("interval", {}).get("startTime")
                    if not item_start_time_str:
                        logger.warning("Missing interval.startTime in forecast item.")
                        continue

                    # Handle 'Z' for UTC timezone aware datetime object
                    forecast_time = datetime.fromisoformat(item_start_time_str.replace("Z", "+00:00"))
                except (ValueError, TypeError) as e:
                    logger.error(f"Error parsing forecast item timestamp: {item_start_time_str}. Error: {e}")
                    continue

                time_diff = abs((timestamp.replace(tzinfo=None) - forecast_time.replace(tzinfo=None)).total_seconds())

                if time_diff < min_time_diff:
                    min_time_diff = time_diff
                    closest_forecast_item = forecast_item

            if closest_forecast_item:
                # Map Google API response fields to WeatherConditions
                # Ensure to handle potential missing keys gracefully with .get() and defaults
                temp = closest_forecast_item.get("temperature", {}).get("degrees")
                humidity = closest_forecast_item.get("relativeHumidity")
                rain_prob = closest_forecast_item.get("precipitation", {}).get("probability", {}).get("percent")
                wind_speed_kmh = closest_forecast_item.get("wind", {}).get("speed", {}).get("value")  # km/h
                cloud_cover_percent = closest_forecast_item.get("cloudCover")

                # Parse timestamp again for the selected forecast
                forecast_dt_str = closest_forecast_item.get("interval", {}).get("startTime")
                if not forecast_dt_str:  # Should not happen if selected
                    logger.error("Selected forecast item missing startTime.")
                    return None

                parsed_timestamp = datetime.fromisoformat(forecast_dt_str.replace("Z", "+00:00"))

                # Check if all essential values were found
                if any(v is None for v in [temp, humidity, rain_prob, wind_speed_kmh, cloud_cover_percent]):
                    logger.warning(f"Missing one or more weather values in forecast item: {closest_forecast_item}")
                    # Fallback to safer defaults for missing numeric values if needed, or return None
                    # For now, we proceed, but WeatherConditions might get None if not handled by caller

                return WeatherConditions(
                    temperature=float(temp) if temp is not None else 0.0,  # Default to 0.0 if None
                    humidity=float(humidity) if humidity is not None else 0.0,
                    rain_probability=float(rain_prob) if rain_prob is not None else 0.0,
                    wind_speed=float(wind_speed_kmh) if wind_speed_kmh is not None else 0.0,  # Already in km/h
                    cloud_cover=float(cloud_cover_percent) if cloud_cover_percent is not None else 0.0,
                    timestamp=parsed_timestamp,
                    source="api",
                )
        except Exception as e:
            logger.error(f"Error processing forecast for time: {timestamp}. Error: {e}")

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
            source="fallback",
        )

    def get_detailed_weather_for_scheduler(self) -> Optional[Dict[str, Any]]:
        """
        Provides current weather and short-term precipitation forecast,
        tailored for the WeatherScheduler's decision-making.

        Returns:
            A dictionary containing:
            - 'current_temperature': float
            - 'current_wind_speed': float
            - 'current_rain_volume_3h': float (rain volume in last 3h, can indicate current rain)
            - 'is_currently_raining': bool (derived from current_rain_volume_3h or specific weather codes)
            - 'hourly_precipitation_probability': List[float] (e.g., for next 3, 6 hours)
            - 'error': Optional[str] if data fetching failed.
        Or None if a significant error occurred.
        """
        try:
            if time.time() - self.last_api_update > self.cache_duration:
                self._update_forecast()

            if not self.cached_forecast or not self.cached_forecast.get("forecastHours"):
                logger.warning("No forecast data available to provide details for scheduler (Google API).")
                return {"error": "No forecast data available."}

            forecast_hours = self.cached_forecast.get("forecastHours", [])
            if not forecast_hours:
                logger.warning("ForecastHours list is empty.")
                return {"error": "No forecast data available."}

            # The first item in forecastHours is the most current hourly forecast
            current_hour_data = forecast_hours[0]

            current_temp = current_hour_data.get("temperature", {}).get("degrees")
            # Google API returns wind speed in km/h with unitsSystem=METRIC. Convert to m/s.
            current_wind_kmh = current_hour_data.get("wind", {}).get("speed", {}).get("value")
            current_wind_mps = (float(current_wind_kmh) / 3.6) if current_wind_kmh is not None else None

            # Sum QPF for the first 3 hours (or fewer if not available)
            current_rain_volume_3h = 0.0
            for i in range(min(3, len(forecast_hours))):
                qpf = forecast_hours[i].get("precipitation", {}).get("qpf", {}).get("quantity")
                if qpf is not None:
                    current_rain_volume_3h += float(qpf)

            # Determine if it's "currently raining"
            is_raining = False
            first_hour_qpf = forecast_hours[0].get("precipitation", {}).get("qpf", {}).get("quantity")
            if first_hour_qpf is not None and float(first_hour_qpf) > 0:
                is_raining = True
            else:
                # Check weatherCondition.type for rain
                # Example rain types: 'RAIN', 'LIGHT_RAIN', 'HEAVY_RAIN', 'THUNDERSTORM', 'RAIN_SHOWERS', 'DRIZZLE'
                # (This list might need adjustment based on Google Weather API documentation for condition types)
                rain_condition_types = ["RAIN", "LIGHT_RAIN", "HEAVY_RAIN", "THUNDERSTORM", "RAIN_SHOWERS", "DRIZZLE"]
                current_condition_type = current_hour_data.get("weatherCondition", {}).get("type", "").upper()
                if current_condition_type in rain_condition_types:
                    is_raining = True

            # Hourly precipitation probability for the next few hours (e.g., first 3)
            hourly_precip_prob = []
            for i in range(min(3, len(forecast_hours))):  # Get for first 3 hours
                prob = forecast_hours[i].get("precipitation", {}).get("probability", {}).get("percent")
                if prob is not None:
                    hourly_precip_prob.append(float(prob))
                else:
                    hourly_precip_prob.append(0.0)  # Default if missing

            # Handle cases where essential data might be missing
            if current_temp is None or current_wind_mps is None:
                logger.warning("Missing temperature or wind speed in current hour data for scheduler.")
                return {"error": "Critical weather data missing for current hour."}

            return {
                "current_temperature": float(current_temp),
                "current_wind_speed": current_wind_mps,  # m/s
                "current_rain_volume_3h": current_rain_volume_3h,  # mm
                "is_currently_raining": is_raining,
                "hourly_precipitation_probability": hourly_precip_prob,  # List of %
                "error": None,
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"API request error in get_detailed_weather_for_scheduler (Google): {e}")
            return {"error": f"API request error: {e}"}
        except (KeyError, IndexError, TypeError, ValueError) as e:  # Added ValueError for float conversions
            logger.error(f"Error parsing Google weather data in get_detailed_weather_for_scheduler: {e}")
            return {"error": f"Error parsing weather data: {e}"}
        except Exception as e:
            logger.error(f"Unexpected error in get_detailed_weather_for_scheduler: {e}")
            return {"error": f"Unexpected error: {e}"}
