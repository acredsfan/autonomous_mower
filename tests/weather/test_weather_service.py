import unittest
from unittest.mock import patch, MagicMock
import os
import time
from datetime import datetime, timedelta
import requests # weather_service.py uses requests
import json # Added to resolve NameError

# Add src to path for imports
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent.parent
src_root = project_root / "src"
if str(src_root) not in sys.path:
    sys.path.insert(0, str(src_root))

from mower.weather.weather_service import WeatherService, WeatherConditions
# Import the logger from the service to check log messages if needed
# from mower.weather.weather_service import logger as weather_service_logger

# Sample valid OpenWeatherMap API response for /forecast (simplified)
SAMPLE_API_FORECAST_RESPONSE = {
    "list": [
        { # Current or very recent block
            "dt": int(datetime.now().timestamp()),
            "main": {"temp": 15.0, "humidity": 60.0},
            "weather": [{"id": 800, "main": "Clear", "description": "clear sky"}],
            "clouds": {"all": 5},
            "wind": {"speed": 3.0}, # m/s
            "pop": 0.1, # Probability of precipitation
            "rain": {"3h": 0.0} # Optional: rain volume for last 3h
        },
        { # Next 3-hour block
            "dt": int((datetime.now() + timedelta(hours=3)).timestamp()),
            "main": {"temp": 16.0, "humidity": 65.0},
            "weather": [{"id": 802, "main": "Clouds", "description": "scattered clouds"}],
            "clouds": {"all": 40},
            "wind": {"speed": 3.5},
            "pop": 0.65, # 65%
            "rain": {"3h": 0.5}
        },
        { # Next 6-hour block
            "dt": int((datetime.now() + timedelta(hours=6)).timestamp()),
            "main": {"temp": 14.0, "humidity": 70.0},
            "weather": [{"id": 500, "main": "Rain", "description": "light rain"}],
            "clouds": {"all": 75},
            "wind": {"speed": 4.0},
            "pop": 0.80, # 80%
            "rain": {"3h": 2.5}
        }
    ],
    "city": {"name": "Test City"} # Other metadata
}


class TestWeatherService(unittest.TestCase):

    def setUp(self):
        # Mock environment variables for API key, lat, lon
        self.mock_env = {
            "OPENWEATHERMAP_API_KEY": "fake_api_key",
            "LATITUDE": "50.0",
            "LONGITUDE": "10.0"
        }
        self.env_patcher = patch.dict(os.environ, self.mock_env)
        self.env_patcher.start()
        self.weather_service = WeatherService()

    def tearDown(self):
        self.env_patcher.stop()

    @patch('mower.weather.weather_service.requests.get')
    def test_get_detailed_weather_for_scheduler_success(self, mock_requests_get):
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_API_FORECAST_RESPONSE
        mock_response.raise_for_status.return_value = None # Simulate successful HTTP status
        mock_requests_get.return_value = mock_response

        # Force update and fill cache
        self.weather_service._update_forecast() 
        
        detailed_weather = self.weather_service.get_detailed_weather_for_scheduler()

        self.assertIsNotNone(detailed_weather)
        self.assertIsNone(detailed_weather.get("error"))
        self.assertEqual(detailed_weather["current_temperature"], 15.0)
        self.assertEqual(detailed_weather["current_wind_speed"], 3.0)
        self.assertEqual(detailed_weather["current_rain_volume_3h"], 0.0)
        self.assertFalse(detailed_weather["is_currently_raining"]) # Based on 0.0 rain and code 800
        
        # Precipitation probabilities: current block (10%), next block (65%)
        # The function takes the current block and the next one for its "hourly_precipitation_probability"
        # if they are distinct enough in time.
        # Given the sample data, it should pick the dt for "now" and dt for "now + 3 hours"
        # Pop values are 0.1 (10%) and 0.65 (65%)
        self.assertListEqual(detailed_weather["hourly_precipitation_probability"], [10.0, 65.0])

    @patch('mower.weather.weather_service.requests.get')
    def test_get_detailed_weather_currently_raining_by_volume(self, mock_requests_get):
        raining_response = json.loads(json.dumps(SAMPLE_API_FORECAST_RESPONSE)) # Deep copy
        raining_response["list"][0]["rain"] = {"3h": 1.5} # Current block has rain volume
        raining_response["list"][0]["weather"] = [{"id": 500}] # Rain weather code

        mock_response = MagicMock()
        mock_response.json.return_value = raining_response
        mock_response.raise_for_status.return_value = None
        mock_requests_get.return_value = mock_response
        
        self.weather_service._update_forecast()
        detailed_weather = self.weather_service.get_detailed_weather_for_scheduler()

        self.assertTrue(detailed_weather["is_currently_raining"])
        self.assertEqual(detailed_weather["current_rain_volume_3h"], 1.5)

    @patch('mower.weather.weather_service.requests.get')
    def test_get_detailed_weather_currently_raining_by_code(self, mock_requests_get):
        raining_response = json.loads(json.dumps(SAMPLE_API_FORECAST_RESPONSE))
        raining_response["list"][0]["rain"] = {} # No "3h" key, or 0.0
        raining_response["list"][0]["weather"] = [{"id": 501, "main": "Rain", "description": "moderate rain"}]

        mock_response = MagicMock()
        mock_response.json.return_value = raining_response
        mock_response.raise_for_status.return_value = None
        mock_requests_get.return_value = mock_response

        self.weather_service._update_forecast()
        detailed_weather = self.weather_service.get_detailed_weather_for_scheduler()
        
        self.assertTrue(detailed_weather["is_currently_raining"])

    @patch('mower.weather.weather_service.requests.get')
    def test_get_detailed_weather_api_request_error(self, mock_requests_get):
        mock_requests_get.side_effect = requests.exceptions.RequestException("API down")

        # Clear cache to force API call attempt
        self.weather_service.cached_forecast = None
        self.weather_service.last_api_update = 0
        
        detailed_weather = self.weather_service.get_detailed_weather_for_scheduler()
        
        self.assertIsNotNone(detailed_weather)
        # If _update_forecast fails due to RequestException, it logs and returns, cached_forecast remains None.
        # Then get_detailed_weather_for_scheduler finds no data.
        self.assertEqual("No forecast data available.", detailed_weather.get("error", ""))

    @patch('mower.weather.weather_service.requests.get')
    def test_get_detailed_weather_parsing_error(self, mock_requests_get):
        malformed_response_data = {"list": [{"dt": "not_a_timestamp"}]} # Missing main, wind etc.
        mock_response = MagicMock()
        mock_response.json.return_value = malformed_response_data
        mock_response.raise_for_status.return_value = None
        mock_requests_get.return_value = mock_response

        self.weather_service._update_forecast() # Fill cache with malformed data
        detailed_weather = self.weather_service.get_detailed_weather_for_scheduler()

        self.assertIsNotNone(detailed_weather)
        self.assertIn("Error parsing weather data", detailed_weather.get("error", ""))

    def test_get_detailed_weather_no_cached_data(self):
        # Ensure no API call is made if _update_forecast fails and leaves cache empty
        with patch.object(self.weather_service, '_update_forecast', side_effect=Exception("Simulated _update_forecast failure")):
            self.weather_service.cached_forecast = None
            self.weather_service.last_api_update = 0 # Ensure it tries to update
            
            detailed_weather = self.weather_service.get_detailed_weather_for_scheduler()
            self.assertIsNotNone(detailed_weather)
            # If _update_forecast itself raises an Exception (other than RequestException),
            # get_detailed_weather_for_scheduler catches it in its own try-except.
            self.assertEqual(detailed_weather.get("error"), "Unexpected error: Simulated _update_forecast failure")

    @patch.dict(os.environ, {"OPENWEATHERMAP_API_KEY": ""}, clear=True) # Simulate missing API key
    @patch('mower.weather.weather_service.requests.get') # Still mock requests.get to see what happens
    def test_get_detailed_weather_missing_api_key(self, mock_requests_get):
        # Re-initialize WeatherService to pick up the changed environment variable
        # Or, more directly, patch self.weather_service.api_key
        with patch.object(self.weather_service, 'api_key', None):
            # Clear cache to force API call attempt which should fail due to no key
            self.weather_service.cached_forecast = None
            self.weather_service.last_api_update = 0
            
            # _update_forecast should log an error and not set cached_forecast
            # Then get_detailed_weather_for_scheduler should return its "no data" error
            detailed_weather = self.weather_service.get_detailed_weather_for_scheduler()
            
            self.assertIsNotNone(detailed_weather)
            self.assertEqual(detailed_weather.get("error"), "No forecast data available.")
            # We expect _update_forecast to have failed silently or logged,
            # and requests.get should not have been called if api_key was None.
            mock_requests_get.assert_not_called()


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
