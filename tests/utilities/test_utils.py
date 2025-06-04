import importlib  # For reloading the module
import json
import os

# Add src to path for imports
import sys
import time
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

project_root = Path(__file__).resolve().parent.parent.parent
src_root = project_root / "src"
if str(src_root) not in sys.path:
    sys.path.insert(0, str(src_root))

# Module to test
from mower.utilities import utils  # Import the module itself for reloading
from mower.utilities.utils import get_timezone_for_coordinates

# Import the logger from the utils module to assert log calls
logger_under_test = utils.logger


class TestGetTimezoneForCoordinates(unittest.TestCase):

    def tearDown(self):
        # Clean up environment variable mocks if any test sets them directly
        if "GOOGLE_MAPS_API_KEY" in os.environ:
            del os.environ["GOOGLE_MAPS_API_KEY"]
        # Reload module to reset its global GOOGLE_MAPS_API_KEY state based on os.environ
        importlib.reload(utils)

    def _mock_urlopen_response(
        self,
        mock_urlopen_patch,
        status_code=200,
        response_dict=None,
        read_side_effect=None,
        is_http_error=False,
        http_error_code=None,
        http_error_reason=None,
    ):
        mock_response = MagicMock()

        if is_http_error:  # For urllib.error.HTTPError, urlopen itself raises the error
            mock_http_error = urllib.error.HTTPError(
                url="http://fakeurl.com",
                code=http_error_code,
                msg=http_error_reason,
                hdrs={},
                fp=MagicMock(),  # Mock the fp attribute for e.read()
            )
            if response_dict:  # If HTTPError also has a JSON body with error details
                mock_http_error.fp.read.return_value = json.dumps(response_dict).encode("utf-8")
            else:
                mock_http_error.fp.read.return_value = b""  # No body or non-JSON body
            mock_urlopen_patch.side_effect = mock_http_error
            return mock_http_error  # The error itself is what's "returned" by urlopen via exception

        # For successful calls or non-HTTP URLErrors handled by the caller
        if response_dict is not None:
            mock_response.read.return_value = json.dumps(response_dict).encode("utf-8")
        if read_side_effect:
            mock_response.read.side_effect = read_side_effect

        # The context manager part for 'with urlopen(...) as response:'
        cm = MagicMock()
        cm.__enter__.return_value = mock_response
        cm.__exit__.return_value = None

        if read_side_effect and not is_http_error and not isinstance(read_side_effect, Exception):
            # if read_side_effect is just a value, not an exception
            mock_urlopen_patch.return_value = cm
        elif not is_http_error:  # Normal case, no side effect or side effect is an exception for read
            mock_urlopen_patch.return_value = cm
        # If side_effect is for urlopen itself (like URLError other than HTTPError), it's already set
        elif isinstance(read_side_effect, Exception) and not is_http_error:  # for urlopen's side_effect
            mock_urlopen_patch.side_effect = read_side_effect

        return mock_response

    @patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_api_key"}, clear=True)
    @patch("mower.utilities.utils.urllib.request.urlopen")
    def test_successful_call(self, mock_urlopen):
        importlib.reload(utils)  # Ensure API key is loaded
        expected_response_data = {
            "dstOffset": 3600,
            "rawOffset": -28800,
            "status": "OK",
            "timeZoneId": "America/Los_Angeles",
            "timeZoneName": "Pacific Daylight Time",
        }
        self._mock_urlopen_response(mock_urlopen, response_dict=expected_response_data)

        result = get_timezone_for_coordinates(34.0522, -118.2437)

        self.assertEqual(result, expected_response_data)
        mock_urlopen.assert_called_once()
        # The first argument to urlopen is the URL string or a Request object.
        # In get_timezone_for_coordinates, it's a URL string.
        called_url_or_request_obj = mock_urlopen.call_args[0][0]
        self.assertIsInstance(called_url_or_request_obj, str)  # It's a URL string
        self.assertIn("location=34.0522%2C-118.2437", called_url_or_request_obj)  # Comma is URL encoded
        self.assertIn("key=fake_api_key", called_url_or_request_obj)
        self.assertIn("timestamp=", called_url_or_request_obj)  # Check timestamp is present

    @patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_api_key"}, clear=True)
    @patch("mower.utilities.utils.urllib.request.urlopen")
    @patch.object(logger_under_test, "error")
    def test_api_error_status(self, mock_logger_error, mock_urlopen):
        importlib.reload(utils)
        error_statuses = ["ZERO_RESULTS", "INVALID_REQUEST", "REQUEST_DENIED", "OVER_DAILY_LIMIT", "UNKNOWN_ERROR"]
        for status in error_statuses:
            with self.subTest(status=status):
                mock_urlopen.reset_mock()
                mock_logger_error.reset_mock()
                api_response = {"status": status, "errorMessage": "Test error message for " + status}
                self._mock_urlopen_response(mock_urlopen, response_dict=api_response)

                result = get_timezone_for_coordinates(1.0, 1.0)
                self.assertEqual(result, api_response)
                mock_logger_error.assert_called_once()
                self.assertIn(status, mock_logger_error.call_args[0][0])
                if status not in ["ZERO_RESULTS"]:  # ZERO_RESULTS might not be an error log, but a warning or info
                    self.assertIn("Test error message", mock_logger_error.call_args[0][0])

    @patch.dict(os.environ, {}, clear=True)  # No API key in environment
    @patch.object(logger_under_test, "error")
    def test_api_key_missing(self, mock_logger_error):
        importlib.reload(utils)  # Reload to see empty os.environ
        self.assertIsNone(utils.GOOGLE_MAPS_API_KEY)  # Check module global is None

        result = get_timezone_for_coordinates(1.0, 1.0)
        self.assertIsNotNone(result)
        self.assertEqual(result.get("status"), "API_KEY_MISSING")
        self.assertEqual(result.get("error"), "API key not configured")
        mock_logger_error.assert_called_with("Cannot fetch timezone: GOOGLE_MAPS_API_KEY is not set.")

    @patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_api_key"}, clear=True)
    @patch("mower.utilities.utils.urllib.request.urlopen")
    @patch.object(logger_under_test, "error")
    def test_network_url_error(self, mock_logger_error, mock_urlopen):
        importlib.reload(utils)
        mock_urlopen.side_effect = urllib.error.URLError("Simulated network problem")

        result = get_timezone_for_coordinates(1.0, 1.0)
        self.assertIsNotNone(result)
        self.assertEqual(result.get("status"), "NETWORK_URL_ERROR")
        self.assertEqual(result.get("error"), "Network error: Simulated network problem")
        mock_logger_error.assert_called_with("Network error during Time Zone API call: Simulated network problem")

    @patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_api_key"}, clear=True)
    @patch("mower.utilities.utils.urllib.request.urlopen")
    @patch.object(logger_under_test, "error")
    def test_network_http_error(self, mock_logger_error, mock_urlopen):
        importlib.reload(utils)
        # Simulate HTTPError being raised by urlopen
        self._mock_urlopen_response(
            mock_urlopen, is_http_error=True, http_error_code=503, http_error_reason="Service Unavailable"
        )

        result = get_timezone_for_coordinates(1.0, 1.0)
        self.assertIsNotNone(result)
        self.assertEqual(result.get("status"), "NETWORK_HTTP_ERROR")
        self.assertEqual(result.get("error"), "HTTP 503: Service Unavailable")
        mock_logger_error.assert_called_with("HTTP error from Time Zone API: 503 Service Unavailable - ")

    @patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_api_key"}, clear=True)
    @patch("mower.utilities.utils.urllib.request.urlopen")
    @patch.object(logger_under_test, "error")
    def test_invalid_json_response(self, mock_logger_error, mock_urlopen):
        importlib.reload(utils)
        # Setup mock_urlopen to return a context manager whose response.read() returns invalid JSON
        mock_response = MagicMock()
        mock_response.read.return_value = b"This is not valid JSON"
        cm = MagicMock()
        cm.__enter__.return_value = mock_response
        mock_urlopen.return_value = cm

        result = get_timezone_for_coordinates(1.0, 1.0)
        self.assertIsNotNone(result)
        self.assertEqual(result.get("status"), "JSON_DECODE_ERROR")
        self.assertEqual(result.get("error"), "Invalid JSON response")
        mock_logger_error.assert_called_with("Failed to decode JSON response from Time Zone API.")

    @patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_api_key"}, clear=True)
    @patch("mower.utilities.utils.urllib.request.urlopen")
    def test_timestamp_defaulting_and_usage(self, mock_urlopen):
        importlib.reload(utils)
        expected_response_data = {"status": "OK", "timeZoneId": "America/Denver"}
        self._mock_urlopen_response(mock_urlopen, response_dict=expected_response_data)

        # Test with no timestamp (should default to now)
        current_ts_before_call = int(time.time())
        get_timezone_for_coordinates(39.7, -104.9)
        current_ts_after_call = int(time.time())

        mock_urlopen.assert_called_once()
        args, _ = mock_urlopen.call_args
        called_url_or_request_obj = args[0]  # This will be the URL string
        self.assertIsInstance(called_url_or_request_obj, str)

        # Check that the timestamp used is very close to time.time()
        # Parse the URL string
        parsed_url = urllib.parse.urlparse(called_url_or_request_obj)
        query_params = urllib.parse.parse_qs(parsed_url.query)

        self.assertIn("timestamp", query_params)
        api_timestamp = int(query_params["timestamp"][0])
        self.assertTrue(current_ts_before_call <= api_timestamp <= current_ts_after_call)

        # Test with a specific timestamp
        mock_urlopen.reset_mock()
        specific_timestamp = 1458000000  # Some specific time
        self._mock_urlopen_response(mock_urlopen, response_dict=expected_response_data)  # Re-prime mock
        get_timezone_for_coordinates(39.7, -104.9, timestamp=specific_timestamp)

        mock_urlopen.assert_called_once()
        args_specific, _ = mock_urlopen.call_args
        called_url_specific = args_specific[0]  # This will be the URL string
        parsed_url_specific = urllib.parse.urlparse(called_url_specific)
        query_params_specific = urllib.parse.parse_qs(parsed_url_specific.query)

        self.assertIn("timestamp", query_params_specific)
        self.assertEqual(int(query_params_specific["timestamp"][0]), specific_timestamp)


if __name__ == "__main__":
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
