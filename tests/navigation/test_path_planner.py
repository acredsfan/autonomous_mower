import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import json
import numpy as np # numpy is used by the module under test indirectly
import requests # For requests.exceptions

import sys
from pathlib import Path

# Add the project's 'src' directory to the Python path
project_root = Path(__file__).resolve().parent.parent.parent # /app
src_root = project_root / "src"
if str(src_root) not in sys.path:
    sys.path.insert(0, str(src_root))

# Now imports should work as 'from mower.module...'
from mower.navigation.path_planner import (
    PathPlanner,
    PatternConfig,
    PatternType,
    LearningConfig,
    get_elevation_for_path,
    GOOGLE_MAPS_API_KEY as MODULE_API_KEY_FROM_MODULE, 
    ELEVATION_API_URL,
    logger as path_planner_logger 
)
from mower.utilities.logger_config import LoggerConfigInfo


# Configure a specific logger for tests
test_logger = LoggerConfigInfo.get_logger("test_path_planner_logger")

DEFAULT_BOUNDARY = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
DEFAULT_START_POINT = (0.0, 0.0)

def create_default_pattern_config():
    return PatternConfig(
        pattern_type=PatternType.PARALLEL,
        spacing=1.0,
        angle=0.0,
        overlap=0.1,
        start_point=DEFAULT_START_POINT,
        boundary_points=DEFAULT_BOUNDARY,
    )

class TestPathPlannerElevation(unittest.TestCase):
    def setUp(self):
        self.pattern_config = create_default_pattern_config()
        self.learning_config = LearningConfig(model_path="test_model.json", update_frequency=10000, memory_size=10, batch_size=2) 
        self.planner = PathPlanner(self.pattern_config, self.learning_config)
        
        model_file = Path(self.learning_config.model_path)
        if model_file.exists():
            model_file.unlink()

    def tearDown(self):
        model_file = Path(self.learning_config.model_path)
        if model_file.exists():
            model_file.unlink()
        if "GOOGLE_MAPS_API_KEY" in os.environ:
            del os.environ["GOOGLE_MAPS_API_KEY"]
        
        # Reload module to reset its global state for GOOGLE_MAPS_API_KEY
        import importlib
        from mower.navigation import path_planner 
        importlib.reload(path_planner)

    @patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "test_key_123"}, clear=True)
    def test_api_key_loaded_on_module_import(self):
        import importlib
        from mower.navigation import path_planner 
        importlib.reload(path_planner)
        self.assertEqual(path_planner.GOOGLE_MAPS_API_KEY, "test_key_123")

    @patch.dict(os.environ, {}, clear=True) 
    @patch("mower.navigation.path_planner.logger.warning") 
    def test_api_key_missing_logs_warning_on_import_and_usage(self, mock_logger_warning):
        import importlib
        from mower.navigation import path_planner 
        importlib.reload(path_planner) 

        self.assertIsNone(path_planner.GOOGLE_MAPS_API_KEY)
        mock_logger_warning.assert_any_call(
            "GOOGLE_MAPS_API_KEY environment variable not found. "
            "Elevation data will not be fetched. Path planning may be suboptimal."
        )
        
        mock_logger_warning.reset_mock()
        path_planner.get_elevation_for_path([(0,0)])
        mock_logger_warning.assert_any_call(
            "Cannot fetch elevation data: GOOGLE_MAPS_API_KEY is not set."
        )

    @patch("mower.navigation.path_planner.requests.get")
    def test_get_elevation_success(self, mock_requests_get):
        with patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_key"}, clear=True):
            import importlib
            from mower.navigation import path_planner
            importlib.reload(path_planner)

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "results": [{"elevation": 10.0}, {"elevation": 20.0}], "status": "OK",
            }
            mock_requests_get.return_value = mock_response
            
            path = [(39.7, -105.2), (40.7, -105.3)]
            elevations = path_planner.get_elevation_for_path(path)
            
            self.assertEqual(elevations, [10.0, 20.0])
            mock_requests_get.assert_called_once()
            args, kwargs = mock_requests_get.call_args
            self.assertEqual(kwargs['params']['key'], "fake_key")
            self.assertEqual(kwargs['params']['locations'], "39.7,-105.2|40.7,-105.3")

    def _run_get_elevation_test_with_mocked_api(self, api_response_json, expected_log_message, mock_logger_error, mock_requests_get):
        with patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_key"}, clear=True):
            import importlib
            from mower.navigation import path_planner
            importlib.reload(path_planner)

            mock_response = MagicMock()
            mock_response.status_code = 200 
            mock_response.json.return_value = api_response_json
            mock_requests_get.return_value = mock_response
            
            elevations = path_planner.get_elevation_for_path([(0,0)]) # Pass a non-empty path
            self.assertIsNone(elevations)
            if expected_log_message:
                # For INVALID_REQUEST, the log includes the locations string.
                if "INVALID_REQUEST" in api_response_json.get("status", ""):
                     mock_logger_error.assert_any_call(expected_log_message) # Use any_call due to dynamic part
                else:
                    mock_logger_error.assert_called_with(expected_log_message)


    @patch("mower.navigation.path_planner.logger.error")
    @patch("mower.navigation.path_planner.requests.get")
    def test_get_elevation_api_error_over_query_limit(self, mock_requests_get, mock_logger_error):
        self._run_get_elevation_test_with_mocked_api(
            {"results": [], "status": "OVER_QUERY_LIMIT"},
            "Google Maps Elevation API: Query limit exceeded. Consider reducing request frequency or upgrading your plan.",
            mock_logger_error, mock_requests_get
        )

    @patch("mower.navigation.path_planner.logger.error")
    @patch("mower.navigation.path_planner.requests.get")
    def test_get_elevation_api_error_request_denied(self, mock_requests_get, mock_logger_error):
        self._run_get_elevation_test_with_mocked_api(
            {"results": [], "status": "REQUEST_DENIED"},
            "Google Maps Elevation API: Request denied. Check your API key and ensure the Elevation API is enabled.",
            mock_logger_error, mock_requests_get
        )

    @patch("mower.navigation.path_planner.logger.error")
    @patch("mower.navigation.path_planner.requests.get")
    def test_get_elevation_api_error_invalid_request(self, mock_requests_get, mock_logger_error):
         # The expected log message contains the locations string, which is dynamic.
         # So we check if the expected prefix is present in any of the calls.
        self._run_get_elevation_test_with_mocked_api(
            {"results": [], "status": "INVALID_REQUEST", "error_message": "Test error"},
            "Google Maps Elevation API: Invalid request. Locations: 0,0, Error: Test error",
            mock_logger_error, mock_requests_get
        )

    @patch("mower.navigation.path_planner.logger.error")
    @patch("mower.navigation.path_planner.requests.get")
    def test_get_elevation_api_error_unknown(self, mock_requests_get, mock_logger_error):
        self._run_get_elevation_test_with_mocked_api(
            {"results": [], "status": "SOME_OTHER_ERROR", "error_message": "Unknown issue"},
            "Google Maps Elevation API: Error - SOME_OTHER_ERROR. Error message: Unknown issue",
            mock_logger_error, mock_requests_get
        )

    def _run_get_elevation_test_with_request_exception(self, exception_to_raise, expected_log_message, mock_logger_error, mock_requests_get):
        with patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_key"}, clear=True):
            import importlib
            from mower.navigation import path_planner
            importlib.reload(path_planner)

            mock_requests_get.side_effect = exception_to_raise
            
            elevations = path_planner.get_elevation_for_path([(0,0)])
            self.assertIsNone(elevations)
            if expected_log_message:
                mock_logger_error.assert_called_with(expected_log_message)

    @patch("mower.navigation.path_planner.logger.error")
    @patch("mower.navigation.path_planner.requests.get")
    def test_get_elevation_network_error_timeout(self, mock_requests_get, mock_logger_error):
        self._run_get_elevation_test_with_request_exception(
            requests.exceptions.Timeout("Test timeout"),
            "Google Maps Elevation API: Request timed out.",
            mock_logger_error, mock_requests_get
        )

    @patch("mower.navigation.path_planner.logger.error")
    @patch("mower.navigation.path_planner.requests.get")
    def test_get_elevation_network_error_httperror(self, mock_requests_get, mock_logger_error):
        mock_response = MagicMock()
        mock_response.text = "Server Error Text"
        self._run_get_elevation_test_with_request_exception(
            requests.exceptions.HTTPError("Test HTTP Error", response=mock_response),
            "Google Maps Elevation API: HTTP error occurred: Test HTTP Error - Server Error Text",
            mock_logger_error, mock_requests_get
        )

    @patch("mower.navigation.path_planner.logger.error")
    @patch("mower.navigation.path_planner.requests.get")
    def test_get_elevation_network_error_requestexception(self, mock_requests_get, mock_logger_error):
        self._run_get_elevation_test_with_request_exception(
            requests.exceptions.RequestException("Test RequestException"),
            "Google Maps Elevation API: Request failed: Test RequestException",
            mock_logger_error, mock_requests_get
        )

    @patch("mower.navigation.path_planner.logger.error")
    @patch("mower.navigation.path_planner.requests.get")
    def test_get_elevation_key_error(self, mock_requests_get, mock_logger_error): # Malformed JSON
        self._run_get_elevation_test_with_mocked_api(
            {"status": "OK", "unexpected_field": []}, 
            "Google Maps Elevation API: Invalid response format from API.",
            mock_logger_error, mock_requests_get
        )

    @patch("mower.navigation.path_planner.logger.error")
    @patch("mower.navigation.path_planner.requests.get")
    def test_get_elevation_json_decode_error(self, mock_requests_get, mock_logger_error):
        with patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_key"}, clear=True):
            import importlib
            from mower.navigation import path_planner
            importlib.reload(path_planner)

            mock_response = MagicMock()
            mock_response.json.side_effect = json.JSONDecodeError("Error decoding", "doc", 0)
            mock_requests_get.return_value = mock_response
            
            elevations = path_planner.get_elevation_for_path([(0,0)])
            self.assertIsNone(elevations)
            mock_logger_error.assert_called_with("Google Maps Elevation API: Could not decode JSON response.")

    @patch("mower.navigation.path_planner.logger.warning")
    def test_get_elevation_no_api_key(self, mock_logger_warning):
        with patch.dict(os.environ, {}, clear=True): 
            import importlib
            from mower.navigation import path_planner
            importlib.reload(path_planner)

            elevations = path_planner.get_elevation_for_path([(0,0)])
            self.assertIsNone(elevations)
            mock_logger_warning.assert_any_call(
                "GOOGLE_MAPS_API_KEY environment variable not found. "
                "Elevation data will not be fetched. Path planning may be suboptimal."
            )
            mock_logger_warning.assert_any_call(
                "Cannot fetch elevation data: GOOGLE_MAPS_API_KEY is not set."
            )
    
    def test_get_elevation_empty_path(self):
        with patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_key"}, clear=True):
            import importlib
            from mower.navigation import path_planner
            importlib.reload(path_planner)
            elevations = path_planner.get_elevation_for_path([])
            self.assertEqual(elevations, [])

    @patch("mower.navigation.path_planner.logger.error")
    @patch("mower.navigation.path_planner.requests.get")
    def test_get_elevation_mismatch_results(self, mock_requests_get, mock_logger_error):
        # Path has 2 points, API returns 1 elevation
        path_coords = [(39.7, -105.2), (40.7, -105.3)] 
        with patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_key"}, clear=True):
            import importlib
            from mower.navigation import path_planner
            importlib.reload(path_planner)

            mock_response = MagicMock()
            mock_response.json.return_value = {
                "results": [{"elevation": 10.0}], "status": "OK",
            }
            mock_requests_get.return_value = mock_response
            
            elevations = path_planner.get_elevation_for_path(path_coords)
            self.assertIsNone(elevations)
            mock_logger_error.assert_called_with(
                "Mismatch between number of requested coordinates and received elevations."
            )
    
    @patch("mower.navigation.path_planner.requests.get")
    def test_get_elevation_batched_requests(self, mock_requests_get):
        with patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_key"}, clear=True):
            import importlib
            from mower.navigation import path_planner
            importlib.reload(path_planner)

            num_points = 600 
            path_coords = [(float(i), float(i)) for i in range(num_points)]
            
            mock_response_1 = MagicMock()
            mock_response_1.json.return_value = {
                "results": [{"elevation": float(i)} for i in range(512)], "status": "OK",
            }
            mock_response_2 = MagicMock()
            mock_response_2.json.return_value = {
                "results": [{"elevation": float(i)} for i in range(512, num_points)], "status": "OK",
            }
            mock_requests_get.side_effect = [mock_response_1, mock_response_2]
            
            elevations = path_planner.get_elevation_for_path(path_coords)
            
            self.assertIsNotNone(elevations)
            self.assertEqual(len(elevations), num_points)
            self.assertEqual(elevations[512], 512.0)
            self.assertEqual(mock_requests_get.call_count, 2)

    @patch("mower.navigation.path_planner.get_elevation_for_path")
    # Removed class-level patch for _generate_pattern_path from decorators
    def test_generate_path_with_elevation_data(self, mock_get_elevation):
        fixed_path_coords = [(0.0,0.0), (1.0,1.0), (2.0,0.0)]
        mock_elevations = [10.0 + i * 0.5 for i in range(len(fixed_path_coords))]
        mock_get_elevation.return_value = mock_elevations

        # Mock the instance method directly using 'with patch.object'
        with patch.object(self.planner, '_generate_pattern_path', return_value=fixed_path_coords) as mock_instance_generate_pattern, \
             patch.object(self.planner, '_calculate_reward', wraps=self.planner._calculate_reward) as mock_calc_reward:
            
            with patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_key"}, clear=True):
                import importlib
                from mower.navigation import path_planner 
                importlib.reload(path_planner)
                
                generated_path = self.planner.generate_path() 
            
            self.assertEqual(generated_path, fixed_path_coords) 
            mock_instance_generate_pattern.assert_called_once() 
            mock_get_elevation.assert_called_once_with(fixed_path_coords)
            mock_calc_reward.assert_called()
            args, kwargs = mock_calc_reward.call_args
            self.assertEqual(args[0], fixed_path_coords) 
            self.assertEqual(args[1], mock_elevations) 


    @patch("mower.navigation.path_planner.get_elevation_for_path")
    # Removed class-level patch for _generate_pattern_path from decorators
    @patch("mower.navigation.path_planner.logger.debug") 
    def test_generate_path_api_failure_graceful(self, mock_logger_debug, mock_get_elevation):
        fixed_path_coords = [(0.0,0.0), (1.0,1.0), (2.0,0.0)]
        mock_get_elevation.return_value = None # Simulate API failure
        
        # Mock the instance method directly using 'with patch.object'
        with patch.object(self.planner, '_generate_pattern_path', return_value=fixed_path_coords) as mock_instance_generate_pattern, \
             patch.object(self.planner, '_calculate_reward', wraps=self.planner._calculate_reward) as mock_calc_reward:

            with patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "fake_key"}, clear=True):
                import importlib
                from mower.navigation import path_planner
                importlib.reload(path_planner)
                generated_path = self.planner.generate_path()
            
            self.assertEqual(generated_path, fixed_path_coords)
            mock_instance_generate_pattern.assert_called_once()
            mock_get_elevation.assert_called_once_with(fixed_path_coords)
            mock_calc_reward.assert_called()
            args, kwargs = mock_calc_reward.call_args
            self.assertEqual(args[0], fixed_path_coords) # path
            self.assertIsNone(args[1]) # elevation_data should be None
            
            log_messages = [call[0][0] for call in mock_logger_debug.call_args_list]
            self.assertFalse(any("Elevation penalty applied" in msg for msg in log_messages))

    def test_reward_calculation_with_elevation(self):
        path = [(0,0), (10,0), (20,0)] 
        elevations = [10.0, 12.0, 11.0] 
        
        with patch.object(self.planner, '_calculate_path_distance', return_value=20.0), \
             patch.object(self.planner, '_calculate_coverage', return_value=0.8), \
             patch.object(self.planner, '_calculate_smoothness', return_value=0.9):
            reward = self.planner._calculate_reward(path, elevations)
            self.assertAlmostEqual(reward, 0.50, places=3)

    def test_reward_calculation_with_steep_slope_penalty(self):
        path = [(0,0), (10,0)] 
        elevations = [10.0, 13.0] 
        
        with patch.object(self.planner, '_calculate_path_distance', return_value=10.0), \
             patch.object(self.planner, '_calculate_coverage', return_value=0.8), \
             patch.object(self.planner, '_calculate_smoothness', return_value=1.0):
            reward = self.planner._calculate_reward(path, elevations)
            self.assertAlmostEqual(reward, 0.52, places=3)

    def test_reward_calculation_without_elevation(self):
        path = [(0,0), (10,0), (20,0)]
        with patch.object(self.planner, '_calculate_path_distance', return_value=20.0), \
             patch.object(self.planner, '_calculate_coverage', return_value=0.8), \
             patch.object(self.planner, '_calculate_smoothness', return_value=0.9):
            reward = self.planner._calculate_reward(path, None) 
            self.assertAlmostEqual(reward, 0.52, places=3)

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
