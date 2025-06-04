# flake8: noqa

import os
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests  # weather_service.py uses requests

# flake8: noqa: E402  # allow path manipulation before imports
# ruff: noqa: E402


project_root = Path(__file__).resolve().parent.parent.parent
src_root = project_root / "src"
if str(src_root) not in sys.path:
    sys.path.insert(0, str(src_root))

from mower.weather.weather_service import WeatherService

# Import the logger from the service to check log messages if needed
# from mower.weather.weather_service import logger as weather_service_logger


# Sample valid Google Weather API response for /forecast/hours:lookup (simplified)
# Note: datetime.now() is used for dynamic timestamps. In real tests, fixed datetimes might be better.
def generate_google_weather_response():
    now = datetime.now()
    return {
        "forecastHours": [
            {  # Current hour
                "interval": {
                    "startTime": now.isoformat() + "Z",
                    "endTime": (now + timedelta(hours=1)).isoformat() + "Z",
                },
                "temperature": {"degrees": 15.0, "unit": "CELSIUS"},
                "relativeHumidity": 60,
                "precipitation": {"probability": {"percent": 10}, "qpf": {"quantity": 0.0, "unit": "MILLIMETERS"}},
                "wind": {"speed": {"value": 10.8, "unit": "KILOMETERS_PER_HOUR"}},  # 3 m/s
                "cloudCover": 5,
                "weatherCondition": {"type": "CLEAR", "description": {"text": "Clear sky"}},
            },
            {  # Next hour
                "interval": {
                    "startTime": (now + timedelta(hours=1)).isoformat() + "Z",
                    "endTime": (now + timedelta(hours=2)).isoformat() + "Z",
                },
                "temperature": {"degrees": 16.0, "unit": "CELSIUS"},
                "relativeHumidity": 65,
                "precipitation": {"probability": {"percent": 65}, "qpf": {"quantity": 0.5, "unit": "MILLIMETERS"}},
                "wind": {"speed": {"value": 12.6, "unit": "KILOMETERS_PER_HOUR"}},  # 3.5 m/s
                "cloudCover": 40,
                "weatherCondition": {"type": "PARTLY_CLOUDY", "description": {"text": "Partly cloudy"}},
            },
            {  # Next + 1 hour
                "interval": {
                    "startTime": (now + timedelta(hours=2)).isoformat() + "Z",
                    "endTime": (now + timedelta(hours=3)).isoformat() + "Z",
                },
                "temperature": {"degrees": 14.0, "unit": "CELSIUS"},
                "relativeHumidity": 70,
                "precipitation": {"probability": {"percent": 80}, "qpf": {"quantity": 2.5, "unit": "MILLIMETERS"}},
                "wind": {"speed": {"value": 14.4, "unit": "KILOMETERS_PER_HOUR"}},  # 4 m/s
                "cloudCover": 75,
                "weatherCondition": {"type": "RAIN", "description": {"text": "Light rain"}},
            },
            {  # Next + 2 hour (for summing up 3 hours of QPF)
                "interval": {
                    "startTime": (now + timedelta(hours=3)).isoformat() + "Z",
                    "endTime": (now + timedelta(hours=4)).isoformat() + "Z",
                },
                "temperature": {"degrees": 13.0, "unit": "CELSIUS"},
                "relativeHumidity": 75,
                "precipitation": {"probability": {"percent": 70}, "qpf": {"quantity": 1.0, "unit": "MILLIMETERS"}},
                "wind": {"speed": {"value": 10.0, "unit": "KILOMETERS_PER_HOUR"}},
                "cloudCover": 80,
                "weatherCondition": {"type": "RAIN_SHOWERS", "description": {"text": "Rain showers"}},
            },
        ]
    }


SAMPLE_API_FORECAST_RESPONSE = generate_google_weather_response()


class TestWeatherService(unittest.TestCase):

    def setUp(self):
        # Mock environment variables for API key, lat, lon
        self.mock_env = {
            "GOOGLE_WEATHER_API_KEY": "fake_api_key",  # Updated key name
            "LATITUDE": "50.0",
            "LONGITUDE": "10.0",
        }
        self.env_patcher = patch.dict(os.environ, self.mock_env)
        self.env_patcher.start()
        self.weather_service = WeatherService()

    def tearDown(self):
        self.env_patcher.stop()

    @patch("mower.weather.weather_service.requests.get")
    def test_get_detailed_weather_for_scheduler_success(self, mock_requests_get):
        current_sample_response = generate_google_weather_response()  # Ensure fresh timestamps
        mock_response = MagicMock()
        mock_response.json.return_value = current_sample_response
        mock_response.raise_for_status.return_value = None
        mock_requests_get.return_value = mock_response

        self.weather_service._update_forecast()

        detailed_weather = self.weather_service.get_detailed_weather_for_scheduler()

        self.assertIsNotNone(detailed_weather)
        self.assertIsNone(detailed_weather.get("error"), f"Unexpected error: {detailed_weather.get('error')}")

        first_hour_data = current_sample_response["forecastHours"][0]
        self.assertEqual(detailed_weather["current_temperature"], first_hour_data["temperature"]["degrees"])
        self.assertAlmostEqual(
            detailed_weather["current_wind_speed"], first_hour_data["wind"]["speed"]["value"] / 3.6, places=2
        )

        # Expected rain volume is sum of QPF for first 3 hours from sample
        expected_rain_vol = sum(
            h["precipitation"]["qpf"]["quantity"] for h in current_sample_response["forecastHours"][:3]
        )
        self.assertEqual(detailed_weather["current_rain_volume_3h"], expected_rain_vol)

        # is_currently_raining check: first hour QPF is 0.0 and type is CLEAR
        self.assertFalse(detailed_weather["is_currently_raining"])

        # Expected precipitation probabilities for the first 3 hours
        expected_precip_probs = [
            h["precipitation"]["probability"]["percent"] for h in current_sample_response["forecastHours"][:3]
        ]
        self.assertListEqual(detailed_weather["hourly_precipitation_probability"], expected_precip_probs)

    @patch("mower.weather.weather_service.requests.get")
    def test_get_detailed_weather_currently_raining_by_volume(self, mock_requests_get):
        raining_response = generate_google_weather_response()
        # Modify first hour to have rain volume
        raining_response["forecastHours"][0]["precipitation"]["qpf"]["quantity"] = 1.5
        # Optional: also set condition type to RAIN for consistency
        raining_response["forecastHours"][0]["weatherCondition"]["type"] = "RAIN"

        mock_response = MagicMock()
        mock_response.json.return_value = raining_response
        mock_response.raise_for_status.return_value = None
        mock_requests_get.return_value = mock_response

        self.weather_service._update_forecast()
        detailed_weather = self.weather_service.get_detailed_weather_for_scheduler()

        self.assertTrue(detailed_weather["is_currently_raining"])
        # Rain volume for 3h will be 1.5 (first hour) + 0.5 (second hour) + 2.5 (third hour)
        expected_rain_vol = (
            1.5
            + raining_response["forecastHours"][1]["precipitation"]["qpf"]["quantity"]
            + raining_response["forecastHours"][2]["precipitation"]["qpf"]["quantity"]
        )
        self.assertEqual(detailed_weather["current_rain_volume_3h"], expected_rain_vol)

    @patch("mower.weather.weather_service.requests.get")
    def test_get_detailed_weather_currently_raining_by_code(self, mock_requests_get):
        raining_response_by_code = generate_google_weather_response()
        # Ensure QPF is 0 for the first hour
        raining_response_by_code["forecastHours"][0]["precipitation"]["qpf"]["quantity"] = 0.0
        # Set weather condition type to indicate rain
        raining_response_by_code["forecastHours"][0]["weatherCondition"]["type"] = "RAIN"

        mock_response = MagicMock()
        mock_response.json.return_value = raining_response_by_code
        mock_response.raise_for_status.return_value = None
        mock_requests_get.return_value = mock_response

        self.weather_service._update_forecast()
        detailed_weather = self.weather_service.get_detailed_weather_for_scheduler()

        self.assertTrue(detailed_weather["is_currently_raining"])

    @patch("mower.weather.weather_service.requests.get")
    def test_get_detailed_weather_api_request_error(self, mock_requests_get):
        mock_requests_get.side_effect = requests.exceptions.RequestException("API down")

        # Clear cache to force API call attempt
        self.weather_service.cached_forecast = None
        self.weather_service.last_api_update = 0

        detailed_weather = self.weather_service.get_detailed_weather_for_scheduler()

        self.assertIsNotNone(detailed_weather)
        # _update_forecast should set cached_forecast to None on RequestException
        # get_detailed_weather_for_scheduler then sees no data.
        self.assertEqual("No forecast data available.", detailed_weather.get("error", ""))

    @patch("mower.weather.weather_service.requests.get")
    def test_get_detailed_weather_parsing_error_malformed_response(self, mock_requests_get):
        # Malformed: 'forecastHours' is there, but content is not as expected (e.g. missing 'temperature')
        malformed_response_data = {"forecastHours": [{"interval": {"startTime": "sometime"}}]}
        mock_response = MagicMock()
        mock_response.json.return_value = malformed_response_data
        mock_response.raise_for_status.return_value = None
        mock_requests_get.return_value = mock_response

        self.weather_service._update_forecast()  # Fill cache with malformed data
        detailed_weather = self.weather_service.get_detailed_weather_for_scheduler()

        self.assertIsNotNone(detailed_weather)
        # The exact error message might vary based on what specific key is missing first.
        # It should indicate an issue with parsing.
        self.assertIn("Error parsing weather data", detailed_weather.get("error", ""))

    @patch("mower.weather.weather_service.requests.get")
    def test_get_detailed_weather_parsing_error_empty_forecast_hours(self, mock_requests_get):
        # Correct structure but empty list
        empty_forecast_response = {"forecastHours": []}
        mock_response = MagicMock()
        mock_response.json.return_value = empty_forecast_response
        mock_response.raise_for_status.return_value = None
        mock_requests_get.return_value = mock_response

        self.weather_service._update_forecast()
        detailed_weather = self.weather_service.get_detailed_weather_for_scheduler()
        self.assertIsNotNone(detailed_weather)
        self.assertEqual("No forecast data available.", detailed_weather.get("error"))

    def test_get_detailed_weather_no_cached_data_after_failed_update(self):
        # Simulate _update_forecast failing in a way that it doesn't set cached_forecast (e.g., API key missing)
        with patch.object(self.weather_service, "_update_forecast") as mock_update:
            mock_update.side_effect = lambda: setattr(self.weather_service, "cached_forecast", None)

            self.weather_service.cached_forecast = None  # Start with no cache
            self.weather_service.last_api_update = 0  # Ensure it tries to update

            detailed_weather = self.weather_service.get_detailed_weather_for_scheduler()
            self.assertIsNotNone(detailed_weather)
            self.assertEqual(detailed_weather.get("error"), "No forecast data available.")

    @patch("mower.weather.weather_service.requests.get")
    def test_get_detailed_weather_missing_api_key(self, mock_requests_get):
        # Patch self.weather_service.api_key directly to None
        with patch.object(self.weather_service, "api_key", None):
            # Clear cache to force API call attempt
            self.weather_service.cached_forecast = None
            self.weather_service.last_api_update = 0

            # _update_forecast should log an error and set cached_forecast to None.
            # Then get_detailed_weather_for_scheduler should return its "no data" error.
            detailed_weather = self.weather_service.get_detailed_weather_for_scheduler()

            self.assertIsNotNone(detailed_weather)
            self.assertEqual(detailed_weather.get("error"), "No forecast data available.")
            # requests.get should not have been called if api_key was None within _update_forecast
            mock_requests_get.assert_not_called()

    @patch("mower.weather.weather_service.requests.get")
    def test_get_forecast_for_time_handles_missing_values(self, mock_requests_get):
        # Test that _get_forecast_for_time can handle a forecast item with some missing fields
        response_with_missing_data = generate_google_weather_response()
        # Corrupt the first forecast item: remove temperature and wind speed
        del response_with_missing_data["forecastHours"][0]["temperature"]
        del response_with_missing_data["forecastHours"][0]["wind"]

        mock_response = MagicMock()
        mock_response.json.return_value = response_with_missing_data
        mock_response.raise_for_status.return_value = None
        mock_requests_get.return_value = mock_response

        self.weather_service._update_forecast()

        # Attempt to get conditions for a time that would match the first (corrupted) item
        # Need to parse the startTime from the (now modified) sample to pass to _get_forecast_for_time
        target_dt_str = response_with_missing_data["forecastHours"][0]["interval"]["startTime"]
        target_dt = datetime.fromisoformat(target_dt_str.replace("Z", "+00:00"))

        conditions = self.weather_service._get_forecast_for_time(target_dt)

        self.assertIsNotNone(conditions)
        # Check that defaults are applied (e.g., 0.0 for float types)
        self.assertEqual(conditions.temperature, 0.0)
        self.assertEqual(conditions.wind_speed, 0.0)
        # Check that other values are still present
        self.assertEqual(conditions.humidity, response_with_missing_data["forecastHours"][0]["relativeHumidity"])
        self.assertEqual(
            conditions.rain_probability,
            response_with_missing_data["forecastHours"][0]["precipitation"]["probability"]["percent"],
        )

    @patch("mower.weather.weather_service.requests.get")
    def test_get_detailed_weather_for_scheduler_critical_data_missing(self, mock_requests_get):
        # Simulate a response where the first hour (current) is missing temperature
        critical_missing_response = generate_google_weather_response()
        del critical_missing_response["forecastHours"][0]["temperature"]

        mock_response = MagicMock()
        mock_response.json.return_value = critical_missing_response
        mock_response.raise_for_status.return_value = None
        mock_requests_get.return_value = mock_response

        self.weather_service._update_forecast()
        detailed_weather = self.weather_service.get_detailed_weather_for_scheduler()

        self.assertIsNotNone(detailed_weather)
        self.assertEqual(detailed_weather.get("error"), "Critical weather data missing for current hour.")


if __name__ == "__main__":
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
