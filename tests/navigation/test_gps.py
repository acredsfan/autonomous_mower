import importlib  # For reloading the module to test API key loading
import json
import os

# Add src to path for imports
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

project_root = Path(__file__).resolve().parent.parent.parent
src_root = project_root / "src"
if str(src_root) not in sys.path:
    sys.path.insert(0, str(src_root))

# Module to test
from mower.navigation import gps  # Import the module itself for reloading
from mower.navigation.gps import address_to_coordinates  # The function to test

# Import the logger from the gps module to assert log calls
logger_under_test = gps.logger


class TestAddressToCoordinates(unittest.TestCase):

    def tearDown(self):
        # Clean up environment variable mocks if any test sets them directly
        if "GOOGLE_MAPS_API_KEY" in os.environ:
            del os.environ["GOOGLE_MAPS_API_KEY"]
        # Reload module to reset its global GOOGLE_MAPS_API_KEY state based on os.environ
        importlib.reload(gps)

    def _mock_urlopen(self, mock_urlopen_patch, status_code=200, response_json=None, side_effect=None):
        mock_response = MagicMock()
        mock_response.getcode.return_value = status_code
        if response_json is not None:
            mock_response.read.return_value = json.dumps(response_json).encode("utf-8")

        cm = MagicMock()  # Context manager mock
        cm.__enter__.return_value = mock_response
        cm.__exit__.return_value = None

        if side_effect:
            mock_urlopen_patch.side_effect = side_effect
        else:
            mock_urlopen_patch.return_value = cm
        return mock_response  # although cm is returned by urlopen, mock_response is useful for read()

    @patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_api_key"}, clear=True)
    @patch("mower.navigation.gps.urllib.request.urlopen")
    def test_valid_address_returns_coordinates(self, mock_urlopen):
        importlib.reload(gps)  # Ensure API key is loaded from mocked os.environ
        response_data = {"results": [{"geometry": {"location": {"lat": 34.0522, "lng": -118.2437}}}], "status": "OK"}
        self._mock_urlopen(mock_urlopen, response_json=response_data)

        lat, lng = address_to_coordinates("1600 Amphitheatre Parkway, Mountain View, CA")
        self.assertAlmostEqual(lat, 34.0522)
        self.assertAlmostEqual(lng, -118.2437)
        mock_urlopen.assert_called_once()
        called_url = mock_urlopen.call_args[0][0]
        self.assertIn("address=1600+Amphitheatre+Parkway%2C+Mountain+View%2C+CA", called_url)
        self.assertIn("key=fake_api_key", called_url)

    @patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_api_key"}, clear=True)
    @patch("mower.navigation.gps.urllib.request.urlopen")
    @patch.object(logger_under_test, "warning")
    def test_zero_results_returns_none(self, mock_logger_warning, mock_urlopen):
        importlib.reload(gps)
        response_data = {"results": [], "status": "ZERO_RESULTS"}
        self._mock_urlopen(mock_urlopen, response_json=response_data)

        result = address_to_coordinates("Invalid Address unlikely to exist anywhere")
        self.assertIsNone(result)
        mock_logger_warning.assert_called_with(
            "Address 'Invalid Address unlikely to exist anywhere' not found by Geocoding API (ZERO_RESULTS)."
        )

    @patch.dict(os.environ, {}, clear=True)  # No API key in environment
    @patch.object(logger_under_test, "error")
    def test_api_key_missing_returns_none_logs_error(self, mock_logger_error):
        importlib.reload(gps)  # Reload gps to make it see the empty os.environ
        self.assertIsNone(gps.GOOGLE_MAPS_API_KEY, "Module's API key should be None after reload with no env var")

        result = address_to_coordinates("Some Address")
        self.assertIsNone(result)
        mock_logger_error.assert_called_with("Cannot perform geocoding: GOOGLE_MAPS_API_KEY is not set.")

    @patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_api_key"}, clear=True)
    @patch("mower.navigation.gps.urllib.request.urlopen")
    @patch.object(logger_under_test, "error")
    def test_request_denied_returns_none_logs_error(self, mock_logger_error, mock_urlopen):
        importlib.reload(gps)
        response_data = {"status": "REQUEST_DENIED"}
        self._mock_urlopen(mock_urlopen, response_json=response_data)

        result = address_to_coordinates("Some Address")
        self.assertIsNone(result)
        mock_logger_error.assert_called_with("Geocoding API request denied. Verify API key and permissions.")

    @patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_api_key"}, clear=True)
    @patch("mower.navigation.gps.urllib.request.urlopen")
    @patch.object(logger_under_test, "error")
    def test_over_query_limit_returns_none_logs_error(self, mock_logger_error, mock_urlopen):
        importlib.reload(gps)
        response_data = {"status": "OVER_QUERY_LIMIT"}
        self._mock_urlopen(mock_urlopen, response_json=response_data)

        result = address_to_coordinates("Some Address")
        self.assertIsNone(result)
        mock_logger_error.assert_called_with("Geocoding API query limit exceeded. Check usage and billing.")

    @patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_api_key"}, clear=True)
    @patch("mower.navigation.gps.urllib.request.urlopen")
    @patch.object(logger_under_test, "error")
    def test_invalid_request_returns_none_logs_error(self, mock_logger_error, mock_urlopen):
        importlib.reload(gps)
        response_data = {"status": "INVALID_REQUEST", "error_message": "Malformed request"}
        self._mock_urlopen(mock_urlopen, response_json=response_data)

        result = address_to_coordinates("Some Address")
        self.assertIsNone(result)
        self.assertTrue(mock_logger_error.call_args[0][0].startswith("Geocoding API invalid request."))

    @patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_api_key"}, clear=True)
    @patch("mower.navigation.gps.urllib.request.urlopen")
    @patch.object(logger_under_test, "error")
    def test_unknown_api_status_returns_none_logs_error(self, mock_logger_error, mock_urlopen):
        importlib.reload(gps)
        response_data = {"status": "MYSTERIOUS_STATUS", "error_message": "Unknown issue"}
        self._mock_urlopen(mock_urlopen, response_json=response_data)

        result = address_to_coordinates("Some Address")
        self.assertIsNone(result)
        mock_logger_error.assert_called_with(
            "Geocoding API returned an unhandled status: MYSTERIOUS_STATUS. Error: Unknown issue"
        )

    @patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_api_key"}, clear=True)
    @patch("mower.navigation.gps.urllib.request.urlopen")
    @patch.object(logger_under_test, "error")
    def test_network_error_returns_none_logs_error(self, mock_logger_error, mock_urlopen):
        importlib.reload(gps)
        self._mock_urlopen(mock_urlopen, side_effect=urllib.error.URLError("Simulated network error"))

        result = address_to_coordinates("Some Address")
        self.assertIsNone(result)
        mock_logger_error.assert_called_with("Network error during geocoding: Simulated network error")

    @patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_api_key"}, clear=True)
    @patch("mower.navigation.gps.urllib.request.urlopen")
    @patch.object(logger_under_test, "error")
    def test_json_decode_error_returns_none_logs_error(self, mock_logger_error, mock_urlopen):
        importlib.reload(gps)
        mock_response = MagicMock()
        mock_response.read.return_value = b"This is not valid JSON"
        cm = MagicMock()
        cm.__enter__.return_value = mock_response
        mock_urlopen.return_value = cm

        result = address_to_coordinates("Some Address")
        self.assertIsNone(result)
        mock_logger_error.assert_called_with("Failed to decode JSON response from Geocoding API.")

    @patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_api_key"}, clear=True)  # Key needed for early check
    @patch.object(logger_under_test, "warning")
    def test_empty_address_string_returns_none_logs_warning(self, mock_logger_warning):
        importlib.reload(gps)
        result = address_to_coordinates("")
        self.assertIsNone(result)
        mock_logger_warning.assert_called_with("Address string is empty, cannot geocode.")

    @patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_api_key"}, clear=True)
    @patch("mower.navigation.gps.urllib.request.urlopen")
    @patch.object(logger_under_test, "error")
    def test_malformed_ok_response_no_results(self, mock_logger_error, mock_urlopen):
        importlib.reload(gps)
        response_data = {"status": "OK", "results": []}  # OK, but no results array
        self._mock_urlopen(mock_urlopen, response_json=response_data)

        result = address_to_coordinates("Some Address")
        self.assertIsNone(result)
        mock_logger_error.assert_called_with("Geocoding API 'OK' status but no results found.")

    @patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_api_key"}, clear=True)
    @patch("mower.navigation.gps.urllib.request.urlopen")
    @patch.object(logger_under_test, "error")
    def test_malformed_ok_response_no_geometry(self, mock_logger_error, mock_urlopen):
        importlib.reload(gps)
        response_data = {"status": "OK", "results": [{"some_other_key": "value"}]}  # No geometry
        self._mock_urlopen(mock_urlopen, response_json=response_data)

        result = address_to_coordinates("Some Address")
        self.assertIsNone(result)
        mock_logger_error.assert_called_with("Geocoding API 'OK' status but location data is malformed.")

    @patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_api_key"}, clear=True)
    @patch("mower.navigation.gps.urllib.request.urlopen")
    @patch.object(logger_under_test, "error")
    def test_malformed_ok_response_no_location(self, mock_logger_error, mock_urlopen):
        importlib.reload(gps)
        response_data = {"status": "OK", "results": [{"geometry": {"other_key": "value"}}]}  # No location
        self._mock_urlopen(mock_urlopen, response_json=response_data)

        result = address_to_coordinates("Some Address")
        self.assertIsNone(result)
        mock_logger_error.assert_called_with("Geocoding API 'OK' status but location data is malformed.")


if __name__ == "__main__":
    unittest.main(argv=["first-arg-is-ignored"], exit=False)


class TestGetLocationFromWifiCell(unittest.TestCase):

    def tearDown(self):
        if "GOOGLE_MAPS_API_KEY" in os.environ:
            del os.environ["GOOGLE_MAPS_API_KEY"]
        # Corrected: 'utils' was indeed a typo from a copy-paste, should be 'gps'
        # However, gps module is already reloaded below. If 'utils' was meant for
        # another module's state reset, it's not relevant here.
        # For clarity, only reloading 'gps' as it's the module under test for API key.
        importlib.reload(gps)

    def _mock_urlopen_post_response(
        self,
        mock_urlopen_patch,
        status_code=200,
        response_dict=None,
        http_error_code=None,
        http_error_reason=None,
        read_side_effect=None,
    ):
        mock_response = MagicMock()

        if http_error_code:  # For urllib.error.HTTPError
            mock_http_error = urllib.error.HTTPError(
                url="http://fakeurl.com", code=http_error_code, msg=http_error_reason, hdrs={}, fp=MagicMock()
            )
            if response_dict:  # Error body might be JSON
                mock_http_error.fp.read.return_value = json.dumps(response_dict).encode("utf-8")
            else:
                mock_http_error.fp.read.return_value = b""
            mock_urlopen_patch.side_effect = mock_http_error
            return mock_http_error

        if response_dict is not None:
            mock_response.read.return_value = json.dumps(response_dict).encode("utf-8")

        if read_side_effect:  # For non-HTTP errors like JSONDecodeError during read
            mock_response.read.side_effect = read_side_effect

        cm = MagicMock()  # Context manager mock
        cm.__enter__.return_value = mock_response
        cm.__exit__.return_value = None

        if not http_error_code and not (read_side_effect and isinstance(read_side_effect, Exception)):
            mock_urlopen_patch.return_value = cm
        elif read_side_effect and isinstance(read_side_effect, Exception):  # for urlopen's side_effect like URLError
            mock_urlopen_patch.side_effect = read_side_effect

        return mock_response

    SAMPLE_WIFI = [{"macAddress": "00:25:9c:cf:1c:ac", "signalStrength": -65, "signalToNoiseRatio": 40}]
    SAMPLE_CELL = [
        {
            "cellId": 42,
            "locationAreaCode": 415,
            "mobileCountryCode": 310,
            "mobileNetworkCode": 410,
            "age": 0,
            "signalStrength": -60,
            "timingAdvance": 15,
        }
    ]
    SUCCESS_RESPONSE = {"location": {"lat": 51.0, "lng": -0.1}, "accuracy": 1200.0}
    NOT_FOUND_ERROR_RESPONSE_BODY = {
        "error": {
            "errors": [{"domain": "geolocation", "reason": "notFound", "message": "Not Found"}],
            "code": 404,
            "message": "Not Found",
        }
    }

    @patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_geo_key"}, clear=True)
    @patch("mower.navigation.gps.urllib.request.urlopen")
    def test_success_with_wifi(self, mock_urlopen):
        importlib.reload(gps)
        self._mock_urlopen_post_response(mock_urlopen, response_dict=self.SUCCESS_RESPONSE)

        result = gps.get_location_from_wifi_cell(wifi_access_points=self.SAMPLE_WIFI)
        self.assertEqual(result, self.SUCCESS_RESPONSE)

        mock_urlopen.assert_called_once()
        request_obj = mock_urlopen.call_args[0][0]
        self.assertIsInstance(request_obj, urllib.request.Request)
        self.assertEqual(request_obj.method, "POST")
        self.assertIn("key=fake_geo_key", request_obj.full_url)
        self.assertEqual(json.loads(request_obj.data), {"wifiAccessPoints": self.SAMPLE_WIFI})

    @patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_geo_key"}, clear=True)
    @patch("mower.navigation.gps.urllib.request.urlopen")
    def test_success_with_cell(self, mock_urlopen):
        importlib.reload(gps)
        self._mock_urlopen_post_response(mock_urlopen, response_dict=self.SUCCESS_RESPONSE)

        result = gps.get_location_from_wifi_cell(cell_towers=self.SAMPLE_CELL)
        self.assertEqual(result, self.SUCCESS_RESPONSE)
        self.assertEqual(json.loads(mock_urlopen.call_args[0][0].data), {"cellTowers": self.SAMPLE_CELL})

    @patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_geo_key"}, clear=True)
    @patch("mower.navigation.gps.urllib.request.urlopen")
    def test_success_with_wifi_and_cell(self, mock_urlopen):
        importlib.reload(gps)
        self._mock_urlopen_post_response(mock_urlopen, response_dict=self.SUCCESS_RESPONSE)

        result = gps.get_location_from_wifi_cell(wifi_access_points=self.SAMPLE_WIFI, cell_towers=self.SAMPLE_CELL)
        self.assertEqual(result, self.SUCCESS_RESPONSE)
        self.assertEqual(
            json.loads(mock_urlopen.call_args[0][0].data),
            {"wifiAccessPoints": self.SAMPLE_WIFI, "cellTowers": self.SAMPLE_CELL},
        )

    @patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_geo_key"}, clear=True)
    @patch("mower.navigation.gps.urllib.request.urlopen")
    def test_success_with_consider_ip_only(self, mock_urlopen):
        importlib.reload(gps)
        self._mock_urlopen_post_response(mock_urlopen, response_dict=self.SUCCESS_RESPONSE)

        result = gps.get_location_from_wifi_cell(consider_ip=True)
        self.assertEqual(result, self.SUCCESS_RESPONSE)
        self.assertEqual(json.loads(mock_urlopen.call_args[0][0].data), {"considerIp": True})

    @patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_geo_key"}, clear=True)
    @patch("mower.navigation.gps.urllib.request.urlopen")
    @patch.object(logger_under_test, "warning")
    def test_api_returns_not_found_error_in_body(
        self, mock_logger, mock_urlopen
    ):  # API returns 200 OK, but error in body
        importlib.reload(gps)
        self._mock_urlopen_post_response(mock_urlopen, response_dict=self.NOT_FOUND_ERROR_RESPONSE_BODY)

        result = gps.get_location_from_wifi_cell(consider_ip=True)  # Using consider_ip to trigger a call
        self.assertIsNotNone(result)
        self.assertEqual(result.get("error"), "APIError")
        self.assertEqual(result.get("details"), self.NOT_FOUND_ERROR_RESPONSE_BODY["error"])
        mock_logger.assert_called_once()
        self.assertIn("Geolocation API returned an error object", mock_logger.call_args[0][0])

    @patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_geo_key"}, clear=True)
    @patch("mower.navigation.gps.urllib.request.urlopen")
    @patch.object(logger_under_test, "error")
    def test_api_returns_http_403_key_error(self, mock_logger, mock_urlopen):
        importlib.reload(gps)
        error_response_body = {
            "error": {"code": 403, "message": "API key invalid", "errors": [{"reason": "keyInvalid"}]}
        }
        self._mock_urlopen_post_response(
            mock_urlopen, http_error_code=403, http_error_reason="Forbidden", response_dict=error_response_body
        )

        result = gps.get_location_from_wifi_cell(consider_ip=True)
        self.assertIsNotNone(result)
        self.assertEqual(result.get("error"), "APIHTTPError")
        self.assertEqual(result.get("details"), error_response_body["error"])
        mock_logger.assert_called_once()
        self.assertIn("HTTP error from Geolocation API: 403", mock_logger.call_args[0][0])

    @patch.dict(os.environ, {}, clear=True)  # No API key
    @patch.object(logger_under_test, "error")
    def test_local_api_key_missing(self, mock_logger_error):
        importlib.reload(gps)
        self.assertIsNone(gps.GOOGLE_MAPS_API_KEY)

        result = gps.get_location_from_wifi_cell(consider_ip=True)
        self.assertIsNotNone(result)
        self.assertEqual(result.get("error"), "API key not configured")
        mock_logger_error.assert_called_with("Cannot perform geolocation: GOOGLE_MAPS_API_KEY is not set.")

    @patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_geo_key"}, clear=True)
    @patch("mower.navigation.gps.urllib.request.urlopen")
    @patch.object(logger_under_test, "error")
    def test_network_url_error(self, mock_logger_error, mock_urlopen):
        importlib.reload(gps)
        mock_urlopen.side_effect = urllib.error.URLError("Simulated network problem")

        result = gps.get_location_from_wifi_cell(consider_ip=True)
        self.assertIsNotNone(result)
        self.assertEqual(result.get("error"), "NetworkURLError")
        self.assertEqual(result.get("details"), "Simulated network problem")
        mock_logger_error.assert_called_with("Network error during Geolocation API call: Simulated network problem")

    @patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_geo_key"}, clear=True)
    @patch.object(logger_under_test, "warning")
    def test_no_input_data_provided(self, mock_logger_warning):
        importlib.reload(gps)
        # Call with all None/False inputs
        result = gps.get_location_from_wifi_cell(wifi_access_points=None, cell_towers=None, consider_ip=False)
        self.assertIsNotNone(result)
        self.assertEqual(result.get("error"), "Insufficient input")
        mock_logger_warning.assert_called_with("Geolocation requires WiFi, cell tower data, or IP consideration.")

    @patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_geo_key"}, clear=True)
    @patch("mower.navigation.gps.urllib.request.urlopen")
    @patch.object(logger_under_test, "error")
    def test_api_returns_malformed_success_response(self, mock_logger_error, mock_urlopen):
        importlib.reload(gps)
        # API returns 200 OK, but content is not the expected success structure
        malformed_data = {"message": "Request processed but data is odd"}
        self._mock_urlopen_post_response(mock_urlopen, response_dict=malformed_data)

        result = gps.get_location_from_wifi_cell(consider_ip=True)
        self.assertIsNotNone(result)
        self.assertEqual(result.get("error"), "Malformed success response")
        self.assertTrue(mock_logger_error.call_args[0][0].startswith("Geolocation API success response malformed"))

    @patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_geo_key"}, clear=True)
    @patch("mower.navigation.gps.urllib.request.urlopen")
    @patch.object(logger_under_test, "error")
    def test_json_decode_error(self, mock_logger_error, mock_urlopen):
        importlib.reload(gps)
        # Simulate urlopen's response.read() returning non-JSON bytes
        mock_response = MagicMock()
        mock_response.read.return_value = b"This is not JSON"
        cm = MagicMock()  # Context manager mock
        cm.__enter__.return_value = mock_response
        mock_urlopen.return_value = cm

        result = gps.get_location_from_wifi_cell(consider_ip=True)
        self.assertIsNotNone(result)
        self.assertEqual(result.get("error"), "JSONDecodeError")
        self.assertEqual(result.get("details"), "Malformed JSON response from server.")
        mock_logger_error.assert_called_with("Failed to decode JSON response from Geolocation API.")

    @patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_geo_key"}, clear=True)
    @patch("mower.navigation.gps.urllib.request.urlopen")
    @patch.object(logger_under_test, "error")
    def test_unexpected_error(self, mock_logger_error, mock_urlopen):
        importlib.reload(gps)
        mock_urlopen.side_effect = Exception("Completely unexpected error")  # Generic exception

        result = gps.get_location_from_wifi_cell(consider_ip=True)
        self.assertIsNotNone(result)
        self.assertEqual(result.get("error"), "UnexpectedError")
        self.assertEqual(result.get("details"), "Completely unexpected error")
        mock_logger_error.assert_called_with(
            "Unexpected error during Geolocation API call: Completely unexpected error", exc_info=True
        )
