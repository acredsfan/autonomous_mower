"""
Utilities module for the autonomous mower project.

This module contains utility functions for various tasks
like mapping values between ranges and other general helpers.
It also includes functions to interact with Google Maps APIs like Time Zone API.
"""

import json
import logging
import os
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional  # Added Any for broader dict compatibility

# --- Module Level Configuration ---
logger = logging.getLogger(__name__)

GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")
TIMEZONE_API_URL = "https://maps.googleapis.com/maps/api/timezone/json"

if not GOOGLE_MAPS_API_KEY:
    logger.warning(
        "GOOGLE_MAPS_API_KEY environment variable not found. "
        "Functions requiring this key (e.g., get_timezone_for_coordinates) will not work."
    )
# --- End Module Level Configuration ---


class Utils:
    """
    Utility class containing static helper methods.

    This class provides various utility functions used throughout the project.
    """

    @staticmethod
    def map_range(x, x_min, x_max, y_min, y_max):
        """
        Linear mapping between two ranges of values.

        Args:
            x: Input value to be mapped
            x_min: Minimum value of input range
            x_max: Maximum value of input range
            y_min: Minimum value of output range
            y_max: Maximum value of output range

        Returns:
            int: Mapped value in the output range as an integer
        """
        x_range = x_max - x_min
        y_range = y_max - y_min
        xy_ratio = x_range / y_range

        y = ((x - x_min) / xy_ratio + y_min) // 1

        return int(y)

    @staticmethod
    def map_range_float(x, x_min, x_max, y_min, y_max):
        """
        Linear mapping between two ranges of values with float results.

        Args:
            x: Input value to be mapped
            x_min: Minimum value of input range
            x_max: Maximum value of input range
            y_min: Minimum value of output range
            y_max: Maximum value of output range

        Returns:
            float: Mapped value in the output range (rounded to 2 decimal places)
        """
        x_range = x_max - x_min
        y_range = y_max - y_min
        xy_ratio = x_range / y_range

        y = (x - x_min) / xy_ratio + y_min

        return round(y, 2)


# --- Google Time Zone API Function ---
def get_timezone_for_coordinates(
    latitude: float, longitude: float, timestamp: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    """
    Fetches timezone information for given coordinates and timestamp using Google Time Zone API.

    Args:
        latitude: Latitude of the location.
        longitude: Longitude of the location.
        timestamp: Seconds since epoch (UTC). Defaults to current time if None.

    Returns:
        A dictionary containing timezone information (dstOffset, rawOffset, timeZoneId,
        timeZoneName, status) or None if an error occurs.
    """
    if not GOOGLE_MAPS_API_KEY:
        logger.error("Cannot fetch timezone: GOOGLE_MAPS_API_KEY is not set.")
        return {"error": "API key not configured", "status": "API_KEY_MISSING"}

    if timestamp is None:
        timestamp = int(time.time())

    params = {
        "location": f"{latitude},{longitude}",
        "timestamp": str(timestamp),
        "key": GOOGLE_MAPS_API_KEY,
    }
    url = f"{TIMEZONE_API_URL}?{urllib.parse.urlencode(params)}"

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            response_body = response.read().decode("utf-8")
            data = json.loads(response_body)

            # Google Time Zone API includes the status within the main JSON body.
            # We should return the whole body if status is OK, or relevant parts.
            # For errors, the body itself often contains the status and error_message.
            if data.get("status") == "OK":
                return data
            else:
                logger.error(
                    f"Time Zone API returned status: {data.get('status')}. "
                    f"Error message: {data.get('errorMessage', 'N/A')}"
                )
                # Return the API's error structure if available, else a custom one
                return (
                    data
                    if "status" in data
                    else {"error": "API request failed", "status": data.get("status", "UNKNOWN_ERROR")}
                )

    except urllib.error.HTTPError as e:
        error_body = "No additional error content"
        try:
            if e.fp:  # fp is the file-like object for the response body
                error_body = e.read().decode("utf-8")
        except Exception:
            pass  # Keep default error_body
        logger.error(f"HTTP error from Time Zone API: {e.code} {e.reason} - {error_body}")
        return {"error": f"HTTP {e.code}: {e.reason}", "status": "NETWORK_HTTP_ERROR"}
    except urllib.error.URLError as e:
        logger.error(f"Network error during Time Zone API call: {e.reason}")
        return {"error": f"Network error: {e.reason}", "status": "NETWORK_URL_ERROR"}
    except json.JSONDecodeError:
        logger.error("Failed to decode JSON response from Time Zone API.")
        return {"error": "Invalid JSON response", "status": "JSON_DECODE_ERROR"}
    except Exception as e:
        logger.error(f"Unexpected error during Time Zone API call: {e}", exc_info=True)
        return {"error": f"Unexpected error: {str(e)}", "status": "UNEXPECTED_ERROR"}


# --- End Google Time Zone API Function ---
