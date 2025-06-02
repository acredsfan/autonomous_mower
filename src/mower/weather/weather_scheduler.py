"""
Weather-aware operation scheduling for the autonomous mower.

This module provides classes and utilities for implementing weather-aware
operation scheduling, allowing the mower to adjust its mowing schedule
based on weather forecasts and current conditions.
"""

import time
import threading
from typing import Dict, Any, Optional, List, Tuple, Callable
from datetime import datetime, timedelta
import logging
from enum import Enum

from mower.interfaces.weather import WeatherServiceInterface
from mower.utilities.logger_config import LoggerConfigInfo

logger = LoggerConfigInfo.get_logger(__name__)


class WeatherCondition(Enum):
    """Enum for different weather conditions."""

    SUNNY = "sunny"
    CLOUDY = "cloudy"
    PARTLY_CLOUDY = "partly_cloudy"
    RAINY = "rainy"
    HEAVY_RAIN = "heavy_rain"
    STORMY = "stormy"
    SNOWY = "snowy"
    FOGGY = "foggy"
    WINDY = "windy"
    UNKNOWN = "unknown"


class MowingRecommendation(Enum):
    """Enum for mowing recommendations based on weather."""

    OPTIMAL = "optimal"  # Ideal conditions for mowing
    GOOD = "good"  # Good conditions for mowing
    FAIR = "fair"  # Fair conditions, mowing is possible
    POOR = "poor"  # Poor conditions, mowing not recommended
    UNSAFE = "unsafe"  # Unsafe conditions, mowing should be avoided


class WeatherAwareScheduler:
    """
    Scheduler for weather-aware mowing operations.

    This class provides functionality for scheduling mowing operations
    based on weather forecasts and current conditions.
    """

    def __init__(self, weather_service: WeatherServiceInterface):
        """
        Initialize the WeatherAwareScheduler.

        Args:
            weather_service: Weather service instance for getting weather data
        """
        self._weather_service = weather_service
        self._schedule = {}  # Dict of day_of_week -> list of scheduled times
        self._weather_thresholds = {
            "max_rain_probability": 50.0,  # Percentage
            "max_wind_speed": 20.0,  # mph
            "min_temperature": 40.0,  # Fahrenheit
            "max_temperature": 95.0,  # Fahrenheit
            "unsafe_conditions": ["heavy_rain", "stormy", "snowy"],
        }
        self._forecast_cache = {}  # Dict of date -> forecast data
        self._forecast_cache_expiry = {}  # Dict of date -> expiry time
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._update_thread = None

    def set_schedule(
        self, schedule: Dict[int, List[Tuple[int, int]]]
    ) -> None:
        """
        Set the mowing schedule.

        Args:
            schedule: Dictionary mapping day of week (0-6, where 0 is Monday)
                     to list of (hour, minute) tuples for scheduled mowing times
        """
        with self._lock:
            self._schedule = schedule

        logger.info(f"Set mowing schedule: {schedule}")

    def get_schedule(self) -> Dict[int, List[Tuple[int, int]]]:
        """
        Get the current mowing schedule.

        Returns:
            Dict[int, List[Tuple[int, int]]]: Current schedule
        """
        with self._lock:
            return self._schedule.copy()

    def set_weather_thresholds(self, thresholds: Dict[str, Any]) -> None:
        """
        Set weather thresholds for mowing decisions.

        Args:
            thresholds: Dictionary of threshold values
        """
        with self._lock:
            self._weather_thresholds.update(thresholds)

        logger.info(f"Set weather thresholds: {thresholds}")

    def get_weather_thresholds(self) -> Dict[str, Any]:
        """
        Get the current weather thresholds.

        Returns:
            Dict[str, Any]: Current thresholds
        """
        with self._lock:
            return self._weather_thresholds.copy()

    def start_scheduler(self) -> None:
        """Start the weather forecast update thread."""
        if self._update_thread is not None and self._update_thread.is_alive():
            logger.warning("Weather update thread already running")
            return

        self._stop_event.clear()
        self._update_thread = threading.Thread(
            target=self._update_forecasts, daemon=True
        )
        self._update_thread.start()
        logger.info("Started weather forecast update thread")

    def stop_scheduler(self) -> None:
        """Stop the weather forecast update thread."""
        self._stop_event.set()
        if self._update_thread is not None:
            self._update_thread.join(timeout=5.0)
            if self._update_thread.is_alive():
                logger.warning(
                    "Weather update thread did not terminate within timeout"
                )
        logger.info("Stopped weather forecast update thread")

    def _update_forecasts(self) -> None:
        """Update weather forecasts periodically."""
        while not self._stop_event.is_set():
            try:
                self._fetch_forecasts()
                # Update every 3 hours (weather forecasts don't change that
                # frequently)
                time.sleep(3 * 60 * 60)
            except Exception as e:
                logger.error(f"Error updating weather forecasts: {e}")
                # Retry after 15 minutes on error
                time.sleep(15 * 60)

    def _fetch_forecasts(self) -> None:
        """Fetch weather forecasts for the next few days."""
        try:
            # Get forecast for the next 3 days
            forecast = self._weather_service.get_forecast(hours=72)

            # Process and cache the forecast data
            with self._lock:
                for day_forecast in forecast.get("hourly", []):
                    date = day_forecast.get("time")
                    if date:
                        self._forecast_cache[date] = day_forecast
                        # Set expiry time to 6 hours from now
                        self._forecast_cache_expiry[date] = (
                            datetime.now() + timedelta(hours=6)
                        )

            logger.info("Updated weather forecasts successfully")
        except Exception as e:
            logger.error(f"Failed to fetch weather forecasts: {e}")

    def _get_forecast_for_time(
        self, target_time: datetime
    ) -> Optional[Dict[str, Any]]:
        """
        Get the forecast for a specific time.

        Args:
            target_time: Target time for forecast

        Returns:
            Optional[Dict[str, Any]]: Forecast data, or None if not available
        """
        with self._lock:
            # Clean up expired cache entries
            now = datetime.now()
            expired_keys = [
                k for k, v in self._forecast_cache_expiry.items() if v < now
            ]
            for key in expired_keys:
                self._forecast_cache.pop(key, None)
                self._forecast_cache_expiry.pop(key, None)

            # Find the closest forecast time
            closest_time = None
            min_diff = timedelta(hours=24)

            for forecast_time_str in self._forecast_cache:
                try:
                    forecast_time = datetime.fromisoformat(forecast_time_str)
                    diff = abs(forecast_time - target_time)
                    if diff < min_diff:
                        min_diff = diff
                        closest_time = forecast_time_str
                except (ValueError, TypeError):
                    continue

            if closest_time and min_diff <= timedelta(hours=3):
                return self._forecast_cache.get(closest_time)

            return None

    def get_mowing_recommendation(
        self, time: Optional[datetime] = None
    ) -> Tuple[MowingRecommendation, str]:
        """
        Get a mowing recommendation for a specific time.

        Args:
            time: Target time for recommendation, or None for current time

        Returns:
            Tuple[MowingRecommendation, str]: Recommendation and reason
        """
        if time is None:
            time = datetime.now()

        # First check if mowing is scheduled for this time
        day_of_week = time.weekday()
        hour, minute = time.hour, time.minute

        with self._lock:
            scheduled_times = self._schedule.get(day_of_week, [])
            is_scheduled = any(
                abs(h - hour) <= 1 and abs(m - minute) <= 30
                for h, m in scheduled_times
            )

            if not is_scheduled:
                return (
                    MowingRecommendation.POOR,
                    "Not scheduled for mowing at this time",
                )

        # Check current weather conditions using the new detailed method
        try:
            with self._lock: # Access thresholds within lock
                thresholds = self._weather_thresholds.copy()

            weather_data = self._weather_service.get_detailed_weather_for_scheduler()

            if not weather_data or weather_data.get("error"):
                logger.warning(f"Could not retrieve valid weather data for recommendation: {weather_data.get('error', 'Unknown error') if weather_data else 'No data'}")
                return MowingRecommendation.POOR, "Weather data unavailable"

            current_temp_celsius = weather_data.get("current_temperature")
            is_currently_raining = weather_data.get("is_currently_raining")
            precipitation_probability_next_hours = weather_data.get("hourly_precipitation_probability", [])
            
            # Rule 1: Currently raining
            if is_currently_raining:
                logger.info(f"Mowing decision for {time}: Postponed - Currently raining. Details: {weather_data}")
                return MowingRecommendation.UNSAFE, "Currently raining"

            # Rule 2: High chance of rain soon (checking first forecast interval, e.g., next 1-3 hours)
            # The threshold for "max_rain_probability" is expected to be in percentage (e.g., 50.0 for 50%)
            # The precipitation_probability_next_hours from service is already in percentage.
            if precipitation_probability_next_hours and \
               precipitation_probability_next_hours[0] > thresholds.get("max_rain_probability", 50.0):
                reason_msg = f"High chance of rain soon ({precipitation_probability_next_hours[0]}%)"
                logger.info(f"Mowing decision for {time}: Postponed - {reason_msg}. Details: {weather_data}")
                return MowingRecommendation.POOR, reason_msg
            
            # Rule 3: Temperature too low (using Celsius)
            min_temp_celsius_threshold = 5.0 # Define this threshold directly or get from a new Celsius config
            # The existing self._weather_thresholds["min_temperature"] is in Fahrenheit.
            # For simplicity in this fix, using a hardcoded Celsius threshold.
            # TODO: Consider making thresholds unit-aware or consistently Celsius.
            if current_temp_celsius is not None and current_temp_celsius < min_temp_celsius_threshold:
                reason_msg = f"Temperature too low ({current_temp_celsius}°C)"
                logger.info(f"Mowing decision for {time}: Postponed - {reason_msg}. Details: {weather_data}")
                return MowingRecommendation.POOR, reason_msg
            
            # Add other checks if necessary (e.g., max temperature, wind speed)
            # Example: Wind speed check (assuming m/s from service, threshold in mph needs conversion or new m/s threshold)
            # current_wind_speed_ms = weather_data.get("current_wind_speed") # m/s
            # max_wind_speed_mph = thresholds.get("max_wind_speed", 20.0) # mph
            # max_wind_speed_ms = max_wind_speed_mph * 0.44704 # Convert mph to m/s
            # if current_wind_speed_ms is not None and current_wind_speed_ms > max_wind_speed_ms:
            #     logger.info(f"Mowing postponed: Too windy ({current_wind_speed_ms} m/s).")
            #     return MowingRecommendation.POOR, f"Too windy ({current_wind_speed_ms} m/s)"

            logger.info(f"Mowing decision for {time}: Weather conditions suitable. Details: {weather_data}")
            return MowingRecommendation.GOOD, "Weather conditions suitable"

        except Exception as e:
            logger.error(f"Error getting mowing recommendation for {time}: {e}")
            return (
                MowingRecommendation.POOR,
                f"Error evaluating weather: {str(e)}",
            )

    # _evaluate_forecast, _evaluate_current_conditions, _get_forecast_for_time, _fetch_forecasts, _update_forecasts
    # are now effectively bypassed by the new logic in get_mowing_recommendation using get_detailed_weather_for_scheduler.
    # They can be marked as deprecated or removed if no other part of the system uses them.
    # The WeatherService's own caching (_update_forecast) is still used by get_detailed_weather_for_scheduler.

    def get_next_mowing_time(self) -> Optional[datetime]:
        """
        Get the next scheduled mowing time with favorable weather.

        Returns:
            Optional[datetime]: Next mowing time, or None if no suitable time found
        """
        now = datetime.now()

        # Look ahead 7 days
        for days_ahead in range(7):
            target_date = now.date() + timedelta(days=days_ahead)
            day_of_week = target_date.weekday()

            with self._lock:
                scheduled_times = self._schedule.get(day_of_week, [])

            for hour, minute in scheduled_times:
                target_time_dt = datetime.combine( # Renamed to avoid conflict
                    target_date,
                    datetime.min.time().replace(hour=hour, minute=minute),
                )

                # Skip times in the past
                if target_time_dt <= now:
                    continue

                # Check if weather is suitable
                # Pass target_time_dt to get_mowing_recommendation
                recommendation, _ = self.get_mowing_recommendation( 
                    target_time_dt 
                )
                if recommendation in [
                    MowingRecommendation.OPTIMAL,
                    MowingRecommendation.GOOD,
                    # MowingRecommendation.FAIR, # FAIR might be too risky if we are proactive
                ]:
                    return target_time_dt

        return None

    def get_mowing_schedule_with_weather(
        self,
    ) -> Dict[datetime, Tuple[MowingRecommendation, str]]:
        """
        Get the mowing schedule for the next 7 days with weather recommendations.        Returns:
            Dict[datetime, Tuple[MowingRecommendation, str]]: Dictionary
                mapping scheduled times to (recommendation, reason) tuples
        """
        now = datetime.now()
        result_schedule = {} # Renamed to avoid conflict

        # Look ahead 7 days
        for days_ahead in range(7):
            target_date = now.date() + timedelta(days=days_ahead)
            day_of_week = target_date.weekday()

            with self._lock:
                scheduled_times = self._schedule.get(day_of_week, [])

            for hour, minute in scheduled_times:
                target_time_dt = datetime.combine( # Renamed
                    target_date,
                    datetime.min.time().replace(hour=hour, minute=minute),
                )

                # Skip times in the past
                if target_time_dt <= now:
                    continue

                # Get weather recommendation
                recommendation, reason = self.get_mowing_recommendation(
                    target_time_dt
                )
                result_schedule[target_time_dt] = (recommendation, reason)

        return result_schedule

    def cleanup(self) -> None:
        """Clean up resources used by the WeatherAwareScheduler."""
        self.stop_scheduler()
