# Add src to path for imports
import sys
import unittest
from datetime import datetime
from datetime import time as dt_time
from datetime import timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

project_root = Path(__file__).resolve().parent.parent.parent
src_root = project_root / "src"
if str(src_root) not in sys.path:
    sys.path.insert(0, str(src_root))

from mower.weather.weather_scheduler import MowingRecommendation, WeatherAwareScheduler
from mower.weather.weather_service import WeatherService  # For type hinting, can be MagicMock

# from mower.weather.weather_scheduler import logger as weather_scheduler_logger


class TestWeatherAwareScheduler(unittest.TestCase):

    def setUp(self):
        # Create a mock WeatherService instance
        self.mock_weather_service = MagicMock(spec=WeatherService)
        self.scheduler = WeatherAwareScheduler(weather_service=self.mock_weather_service)

        # Default schedule: Monday, Wednesday, Friday at 10:00 AM
        # Day of week: Monday is 0, Sunday is 6
        self.default_schedule = {
            0: [(10, 0)],  # Monday 10:00
            2: [(10, 0)],  # Wednesday 10:00
            4: [(10, 0)],  # Friday 10:00
        }
        self.scheduler.set_schedule(self.default_schedule)

        # Default thresholds (can be overridden in tests)
        # Note: The scheduler's internal logic now uses specific thresholds (5°C, 50% precip)
        # directly in get_mowing_recommendation, rather than fully relying on these.
        # These might be used by other parts or if the logic is expanded.
        self.scheduler.set_weather_thresholds(
            {
                "max_rain_probability": 50.0,  # %
                "min_temperature": 5.0,  # Celsius (overriding Fahrenheit default for consistency with new logic)
            }
        )

    def _get_fixed_time_in_schedule(self, day_offset=0, hour=10, minute=0):
        """Helper to get a datetime object that falls within a scheduled mowing time."""
        today = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
        # Find next Monday (day 0)
        monday = today - timedelta(days=today.weekday()) + timedelta(days=day_offset)
        return monday

    def test_recommendation_optimal_weather_scheduled_time(self):
        # Mock weather data for optimal conditions
        good_weather_data = {
            "current_temperature": 20.0,  # Celsius
            "is_currently_raining": False,
            "hourly_precipitation_probability": [10.0, 15.0],  # %
            "error": None,
        }
        self.mock_weather_service.get_detailed_weather_for_scheduler.return_value = good_weather_data

        # Pick a time that is in the schedule (e.g., next Monday 10:00 AM)
        scheduled_time = self._get_fixed_time_in_schedule(day_offset=0)  # Monday

        recommendation, reason = self.scheduler.get_mowing_recommendation(time=scheduled_time)

        self.assertEqual(recommendation, MowingRecommendation.GOOD)  # Current logic returns GOOD
        self.assertEqual(reason, "Weather conditions suitable")

    def test_recommendation_not_scheduled_time(self):
        # Time not in schedule (e.g., Tuesday 10:00 AM)
        not_scheduled_time = self._get_fixed_time_in_schedule(day_offset=1)  # Tuesday

        recommendation, reason = self.scheduler.get_mowing_recommendation(time=not_scheduled_time)

        self.assertEqual(recommendation, MowingRecommendation.POOR)
        self.assertEqual(reason, "Not scheduled for mowing at this time")

    def test_recommendation_currently_raining(self):
        raining_weather_data = {
            "current_temperature": 15.0,
            "is_currently_raining": True,
            "hourly_precipitation_probability": [30.0, 40.0],
            "error": None,
        }
        self.mock_weather_service.get_detailed_weather_for_scheduler.return_value = raining_weather_data
        scheduled_time = self._get_fixed_time_in_schedule()

        recommendation, reason = self.scheduler.get_mowing_recommendation(time=scheduled_time)
        self.assertEqual(recommendation, MowingRecommendation.UNSAFE)
        self.assertEqual(reason, "Currently raining")

    def test_recommendation_high_precipitation_probability(self):
        high_precip_data = {
            "current_temperature": 18.0,
            "is_currently_raining": False,
            "hourly_precipitation_probability": [60.0, 70.0],  # > 50%
            "error": None,
        }
        self.mock_weather_service.get_detailed_weather_for_scheduler.return_value = high_precip_data
        scheduled_time = self._get_fixed_time_in_schedule()

        recommendation, reason = self.scheduler.get_mowing_recommendation(time=scheduled_time)
        self.assertEqual(recommendation, MowingRecommendation.POOR)
        self.assertEqual(reason, "High chance of rain soon (60.0%)")

    def test_recommendation_low_temperature(self):
        low_temp_data = {
            "current_temperature": 3.0,  # Below 5°C
            "is_currently_raining": False,
            "hourly_precipitation_probability": [10.0, 10.0],
            "error": None,
        }
        self.mock_weather_service.get_detailed_weather_for_scheduler.return_value = low_temp_data
        scheduled_time = self._get_fixed_time_in_schedule()

        recommendation, reason = self.scheduler.get_mowing_recommendation(time=scheduled_time)
        self.assertEqual(recommendation, MowingRecommendation.POOR)
        self.assertEqual(reason, "Temperature too low (3.0°C)")

    def test_recommendation_weather_data_unavailable(self):
        self.mock_weather_service.get_detailed_weather_for_scheduler.return_value = {"error": "API Unreachable"}
        scheduled_time = self._get_fixed_time_in_schedule()

        recommendation, reason = self.scheduler.get_mowing_recommendation(time=scheduled_time)
        self.assertEqual(recommendation, MowingRecommendation.POOR)
        self.assertEqual(reason, "Weather data unavailable")

    def test_get_next_mowing_time_good_weather_today(self):
        good_weather = {
            "current_temperature": 20.0,
            "is_currently_raining": False,
            "hourly_precipitation_probability": [10.0, 10.0],
            "error": None,
        }
        self.mock_weather_service.get_detailed_weather_for_scheduler.return_value = good_weather

        # Assume today is Monday, and it's before 10 AM
        now = datetime.now().replace(second=0, microsecond=0)
        monday_10am = now.replace(hour=10, minute=0)
        if now.weekday() != 0 or now.time() >= dt_time(10, 0):  # If not Monday before 10am
            # Find next Monday
            monday_10am = (now + timedelta(days=(0 - now.weekday() + 7) % 7)).replace(hour=10, minute=0)
            if monday_10am <= now:  # if next Monday 10am is still past
                monday_10am += timedelta(days=7)

        with patch("mower.weather.weather_scheduler.datetime") as mock_dt:
            # Mock datetime.now() to control "current time" for the test
            # Ensure the "current time" is before the scheduled Monday 10 AM
            mock_dt.now.return_value = monday_10am - timedelta(hours=1)
            mock_dt.combine.side_effect = datetime.combine  # Use real combine
            # Ensure that datetime.min.time() in the code under test works as expected
            mock_dt.min = datetime.min  # mock_dt.min will now be the real datetime.min

            next_time = self.scheduler.get_next_mowing_time()
            self.assertIsNotNone(next_time)
            self.assertEqual(next_time.weekday(), 0)  # Monday
            self.assertEqual(next_time.hour, 10)

    def test_get_next_mowing_time_bad_weather_today_good_later(self):
        # Scenario: Today (Monday 10 AM) is raining, Wednesday 10 AM is good.
        raining_weather = {
            "current_temperature": 15.0,
            "is_currently_raining": True,
            "hourly_precipitation_probability": [100.0, 100.0],
            "error": None,
        }
        good_weather = {
            "current_temperature": 20.0,
            "is_currently_raining": False,
            "hourly_precipitation_probability": [10.0, 10.0],
            "error": None,
        }

        # This mock will be called multiple times by get_next_mowing_time
        # It needs to return bad weather for today, good for Wednesday
        def weather_side_effect(*args, **kwargs):
            # get_mowing_recommendation calls get_detailed_weather_for_scheduler
            # get_next_mowing_time calls get_mowing_recommendation(target_time)
            # We need to check the 'target_time' that get_mowing_recommendation would use.
            # This is tricky because the mock is on get_detailed_weather_for_scheduler,
            # not get_mowing_recommendation itself.
            # For simplicity, assume the test checks days sequentially.
            # First call (today, Monday) -> raining
            # Second call (Wednesday) -> good
            if self.mock_weather_service.get_detailed_weather_for_scheduler.call_count == 1:  # Monday
                return raining_weather
            return good_weather  # Wednesday onwards

        self.mock_weather_service.get_detailed_weather_for_scheduler.side_effect = weather_side_effect

        now = datetime.now().replace(second=0, microsecond=0)
        # Set "now" to be just before Monday 10 AM
        current_monday_9am = (now - timedelta(days=now.weekday())).replace(hour=9, minute=0)

        with patch("mower.weather.weather_scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = current_monday_9am
            mock_dt.combine.side_effect = datetime.combine
            # Ensure that datetime.min.time() in the code under test works as expected
            mock_dt.min = datetime.min  # mock_dt.min will now be the real datetime.min

            next_time = self.scheduler.get_next_mowing_time()

            self.assertIsNotNone(next_time)
            self.assertEqual(next_time.weekday(), 2)  # Wednesday
            self.assertEqual(next_time.hour, 10)
            # Ensure it was called for Monday (rain) and then Wednesday (good)
            self.assertEqual(self.mock_weather_service.get_detailed_weather_for_scheduler.call_count, 2)


if __name__ == "__main__":
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
