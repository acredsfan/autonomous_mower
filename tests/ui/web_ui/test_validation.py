import importlib  # For reloading the module
import json
import os

# Add src to path for imports
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

project_root = Path(__file__).resolve().parent.parent.parent.parent  # Adjust if test file location changes
src_root = project_root / "src"
if str(src_root) not in sys.path:
    sys.path.insert(0, str(src_root))

# Module to test
from mower.ui.web_ui import validation  # Import the module itself for reloading
from mower.ui.web_ui.validation import validate_address  # The function to test

# Import the logger from the validation module to assert log calls
logger_under_test = validation.logger


class TestValidateAddress(unittest.TestCase):

    def tearDown(self):
        # Clean up environment variable mocks
        if "GOOGLE_MAPS_API_KEY" in os.environ:
            del os.environ["GOOGLE_MAPS_API_KEY"]
        importlib.reload(validation)  # Reset module's global API key state

    def _mock_urlopen_response(
        self,
        status_code=200,
        response_dict=None,
        read_raises_error=None,
        is_http_error=False,
        http_error_code=None,
        http_error_reason=None,
    ):
        mock_response = MagicMock()
        if is_http_error:  # For urllib.error.HTTPError, urlopen returns the error itself
            mock_http_error = urllib.error.HTTPError(
                url="http://fakeurl.com",
                code=http_error_code,
                msg=http_error_reason,
                hdrs={},
                fp=MagicMock(),  # Mock the fp attribute for e.read()
            )
            if response_dict:
                mock_http_error.fp.read.return_value = json.dumps(response_dict).encode("utf-8")
            else:
                mock_http_error.fp.read.return_value = b""
            return mock_http_error

        # For successful calls or non-HTTP URLErrors, urlopen returns a response-like object
        mock_response.getcode.return_value = status_code  # Not directly used by urllib, but good for consistency
        if response_dict is not None:
            mock_response.read.return_value = json.dumps(response_dict).encode("utf-8")
        if read_raises_error:
            mock_response.read.side_effect = read_raises_error

        # The context manager part
        cm = MagicMock()
        cm.__enter__.return_value = mock_response
        cm.__exit__.return_value = None
        return cm

    @patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_api_key"}, clear=True)
    @patch("mower.ui.web_ui.validation.urllib.request.urlopen")
    def test_valid_address_premise_granularity(self, mock_urlopen):
        importlib.reload(validation)
        api_response = {"result": {"verdict": {"validationGranularity": "PREMISE"}}}
        mock_urlopen.return_value = self._mock_urlopen_response(response_dict=api_response)

        address_data = {"address": {"regionCode": "US", "addressLines": ["1600 Amphitheatre Parkway"]}}
        result = validate_address(address_data)

        self.assertTrue(result["isValid"])
        self.assertEqual(result["validationResult"], api_response["result"])
        self.assertIsNone(result["error"])
        mock_urlopen.assert_called_once()
        request_arg = mock_urlopen.call_args[0][0]
        self.assertIsInstance(request_arg, urllib.request.Request)
        self.assertIn("key=fake_api_key", request_arg.full_url)
        self.assertEqual(json.loads(request_arg.data), address_data)

    @patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_api_key"}, clear=True)
    @patch("mower.ui.web_ui.validation.urllib.request.urlopen")
    def test_valid_address_subpremise_granularity(self, mock_urlopen):
        importlib.reload(validation)
        api_response = {"result": {"verdict": {"validationGranularity": "SUB_PREMISE"}}}
        mock_urlopen.return_value = self._mock_urlopen_response(response_dict=api_response)

        result = validate_address({"address": {"addressLines": ["Apt 1"]}})
        self.assertTrue(result["isValid"])
        self.assertEqual(result["validationResult"], api_response["result"])

    @patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_api_key"}, clear=True)
    @patch("mower.ui.web_ui.validation.urllib.request.urlopen")
    def test_address_other_granularity_is_invalid(self, mock_urlopen):
        importlib.reload(validation)
        api_response = {"result": {"verdict": {"validationGranularity": "ROUTE"}}}
        mock_urlopen.return_value = self._mock_urlopen_response(response_dict=api_response)

        result = validate_address({"address": {"addressLines": ["Some street"]}})
        self.assertFalse(result["isValid"])
        self.assertEqual(result["validationResult"], api_response["result"])

    @patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_api_key"}, clear=True)
    @patch("mower.ui.web_ui.validation.urllib.request.urlopen")
    def test_address_with_missing_components_is_invalid(self, mock_urlopen):
        importlib.reload(validation)
        api_response = {"result": {"verdict": {"validationGranularity": "PREMISE", "hasMissingComponents": True}}}
        mock_urlopen.return_value = self._mock_urlopen_response(response_dict=api_response)

        result = validate_address({"address": {"addressLines": ["123 Main"]}})  # Missing locality/postal code
        self.assertFalse(result["isValid"])
        self.assertEqual(result["validationResult"], api_response["result"])

    @patch.dict(os.environ, {}, clear=True)  # No API key
    @patch.object(logger_under_test, "error")
    def test_api_key_missing(self, mock_logger_error):
        importlib.reload(validation)  # Reload to pick up missing key
        self.assertIsNone(validation.GOOGLE_MAPS_API_KEY)

        result = validate_address({"address": {}})
        self.assertFalse(result["isValid"])
        self.assertEqual(result["error"], "API key for address validation is not configured.")
        mock_logger_error.assert_called_with("Address Validation API key is missing.")

    @patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_api_key"}, clear=True)
    @patch.object(logger_under_test, "warning")
    def test_invalid_input_format_no_address_key(self, mock_logger_warning):
        importlib.reload(validation)
        result = validate_address({"wrong_key": {}})  # Missing 'address' key
        self.assertFalse(result["isValid"])
        self.assertEqual(result["error"], "Invalid input format for address validation.")
        mock_logger_warning.assert_called_with("Invalid address_input format for validation.")

    @patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_api_key"}, clear=True)
    @patch("mower.ui.web_ui.validation.urllib.request.urlopen")
    @patch.object(logger_under_test, "error")
    def test_http_error_from_api(self, mock_logger_error, mock_urlopen):
        importlib.reload(validation)
        # urlopen itself raises HTTPError
        mock_urlopen.side_effect = self._mock_urlopen_response(
            is_http_error=True, http_error_code=403, http_error_reason="Forbidden"
        )

        result = validate_address({"address": {}})
        self.assertFalse(result["isValid"])
        self.assertEqual(result["error"], "Address Validation API request failed with HTTP 403.")
        mock_logger_error.assert_called_with("HTTP error from Address Validation API: 403 Forbidden - ")

    @patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_api_key"}, clear=True)
    @patch("mower.ui.web_ui.validation.urllib.request.urlopen")
    @patch.object(logger_under_test, "error")
    def test_url_error_network(self, mock_logger_error, mock_urlopen):
        importlib.reload(validation)
        mock_urlopen.side_effect = urllib.error.URLError("Simulated network problem")

        result = validate_address({"address": {}})
        self.assertFalse(result["isValid"])
        self.assertEqual(result["error"], "Network error connecting to Address Validation API.")
        mock_logger_error.assert_called_with(
            "Network error during Address Validation API call: Simulated network problem"
        )

    @patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_api_key"}, clear=True)
    @patch("mower.ui.web_ui.validation.urllib.request.urlopen")
    @patch.object(logger_under_test, "error")
    def test_json_decode_error_response(self, mock_logger_error, mock_urlopen):
        importlib.reload(validation)
        mock_response_cm = MagicMock()  # Context manager for urlopen
        mock_response_content = MagicMock()  # The response object itself
        mock_response_content.read.return_value = b"This is not JSON"
        mock_response_cm.__enter__.return_value = mock_response_content
        mock_urlopen.return_value = mock_response_cm

        result = validate_address({"address": {}})
        self.assertFalse(result["isValid"])
        self.assertEqual(result["error"], "Invalid JSON response from Address Validation API.")
        mock_logger_error.assert_called_with("Failed to decode JSON response from Address Validation API.")

    @patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_api_key"}, clear=True)
    @patch("mower.ui.web_ui.validation.urllib.request.urlopen")
    def test_api_returns_empty_result_object(self, mock_urlopen):
        importlib.reload(validation)
        api_response = {"result": {}}  # Empty result
        mock_urlopen.return_value = self._mock_urlopen_response(response_dict=api_response)

        result = validate_address({"address": {}})
        self.assertFalse(result["isValid"])  # No granularity, so invalid
        self.assertEqual(result["validationResult"], {})
        self.assertIsNone(result["error"])

    @patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_api_key"}, clear=True)
    @patch("mower.ui.web_ui.validation.urllib.request.urlopen")
    def test_api_returns_no_result_object(self, mock_urlopen):
        importlib.reload(validation)
        api_response = {}  # No result object at all
        mock_urlopen.return_value = self._mock_urlopen_response(response_dict=api_response)

        result = validate_address({"address": {}})
        self.assertFalse(result["isValid"])
        self.assertEqual(result["validationResult"], {})
        self.assertIsNone(result["error"])

    @patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_api_key"}, clear=True)
    @patch("mower.ui.web_ui.validation.urllib.request.urlopen")
    @patch.object(logger_under_test, "error")
    def test_unexpected_error_during_api_call(self, mock_logger_error, mock_urlopen):
        importlib.reload(validation)
        mock_urlopen.side_effect = Exception("Highly unexpected error")

        result = validate_address({"address": {}})
        self.assertFalse(result["isValid"])
        self.assertEqual(result["error"], "An unexpected error occurred.")
        mock_logger_error.assert_called_with(
            "Unexpected error during Address Validation API call: Highly unexpected error"
        )


if __name__ == "__main__":
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
