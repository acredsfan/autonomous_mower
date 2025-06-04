"""Input validation and sanitization for the web interface.

This module provides functions for validating and sanitizing user inputs
to protect against injection attacks and other security vulnerabilities.
It also includes address validation using Google's Address Validation API.
"""

import json
import os
import re
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple, Union

from flask import Request
from werkzeug.datastructures import ImmutableMultiDict

from mower.utilities.logger_config import LoggerConfigInfo

# Initialize logger
logger = LoggerConfigInfo.get_logger(__name__)


# --- Google Address Validation API Configuration ---
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")
ADDRESS_VALIDATION_API_URL_BASE = "https://addressvalidation.googleapis.com/v1:validateAddress"

if not GOOGLE_MAPS_API_KEY:
    logger.warning(
        "GOOGLE_MAPS_API_KEY environment variable not found. "
        "Address validation functionality will be severely limited or unavailable."
    )
# --- End Google Address Validation API Configuration ---


def sanitize_string(value: str) -> str:
    """Sanitize a string input to prevent XSS attacks.

    Args:
        value: The string to sanitize.

    Returns:
        The sanitized string.
    """
    if not isinstance(value, str):
        return ""

    # Replace potentially dangerous characters
    sanitized = value.replace("<", "&lt;").replace(">", "&gt;")
    sanitized = sanitized.replace('"', "&quot;").replace("'", "&#x27;")
    sanitized = sanitized.replace("(", "&#40;").replace(")", "&#41;")
    sanitized = sanitized.replace("/", "&#x2F;")

    return sanitized


def validate_coordinates(coordinates: List[Dict[str, float]]) -> Tuple[bool, str]:
    """Validate a list of GPS coordinates.

    Args:
        coordinates: A list of coordinate dictionaries with lat and lng keys.

    Returns:
        A tuple of (is_valid, error_message).
    """
    if not isinstance(coordinates, list):
        return False, "Coordinates must be a list"

    if len(coordinates) < 3:
        return False, "At least 3 coordinates are required to define an area"

    for point in coordinates:
        if not isinstance(point, dict):
            return False, "Each coordinate must be a dictionary"

        if "lat" not in point or "lng" not in point:
            return False, "Each coordinate must have 'lat' and 'lng' keys"

        if not isinstance(point.get("lat"), (int, float)) or not isinstance(point.get("lng"), (int, float)):
            return False, "Latitude and longitude must be numbers"

        if point.get("lat") < -90 or point.get("lat") > 90:
            return False, "Latitude must be between -90 and 90"

        if point.get("lng") < -180 or point.get("lng") > 180:
            return False, "Longitude must be between -180 and 180"

    return True, ""


def validate_pattern_type(pattern_type: str) -> Tuple[bool, str]:
    """Validate a mowing pattern type.

    Args:
        pattern_type: The pattern type to validate.

    Returns:
        A tuple of (is_valid, error_message).
    """
    valid_patterns = ["PARALLEL", "SPIRAL", "ZIGZAG", "PERIMETER"]

    if not isinstance(pattern_type, str):
        return False, "Pattern type must be a string"

    if pattern_type not in valid_patterns:
        return (
            False,
            f"Invalid pattern type. Must be one of: {', '.join(valid_patterns)}",
        )

    return True, ""


def validate_numeric_range(
    value: Union[int, float],
    min_value: Union[int, float],
    max_value: Union[int, float],
    name: str,
) -> Tuple[bool, str]:
    """Validate that a numeric value is within a specified range.

    Args:
        value: The value to validate.
        min_value: The minimum allowed value.
        max_value: The maximum allowed value.
        name: The name of the value for error messages.

    Returns:
        A tuple of (is_valid, error_message).
    """
    if not isinstance(value, (int, float)):
        return False, f"{name} must be a number"

    if value < min_value or value > max_value:
        return False, f"{name} must be between {min_value} and {max_value}"

    return True, ""


def validate_json_request(
    request: Request,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Validate that a request contains valid JSON data.

    Args:
        request: The Flask request object.

    Returns:
        A tuple of (is_valid, error_message, data).
    """
    if not request.is_json:
        return False, "Request must be JSON", None

    try:
        data = request.get_json()
        if data is None:
            return False, "Empty JSON data", None

        if not isinstance(data, dict):
            return False, "JSON data must be an object", None

        return True, "", data
    except Exception as e:
        logger.error(f"Error parsing JSON data: {e}")
        return False, f"Invalid JSON data: {str(e)}", None


def sanitize_form_data(form_data: ImmutableMultiDict) -> Dict[str, str]:
    """Sanitize form data to prevent XSS attacks.

    Args:
        form_data: The form data to sanitize.

    Returns:
        A dictionary of sanitized form data.
    """
    sanitized = {}

    for key in form_data:
        sanitized[key] = sanitize_string(form_data[key])

    return sanitized


def validate_schedule(schedule: Dict[str, Any]) -> Tuple[bool, str]:
    """Validate a mowing schedule.

    Args:
        schedule: The schedule to validate.

    Returns:
        A tuple of (is_valid, error_message).
    """
    if not isinstance(schedule, dict):
        return False, "Schedule must be a dictionary"

    days = [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]

    for day in days:
        if day not in schedule:
            return False, f"Schedule must include {day}"

        day_schedule = schedule[day]
        if not isinstance(day_schedule, list):
            return False, f"Schedule for {day} must be a list"

        for time_slot in day_schedule:
            if not isinstance(time_slot, dict):
                return False, f"Time slot for {day} must be a dictionary"

            if "start" not in time_slot or "end" not in time_slot:
                return (
                    False,
                    f"Time slot for {day} must have 'start' and 'end' keys",
                )

            # Validate time format (HH:MM)
            time_pattern = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")

            if not time_pattern.match(time_slot["start"]):
                return (
                    False,
                    f"Invalid start time format for {day}. Use HH:MM (24-hour format)",
                )

            if not time_pattern.match(time_slot["end"]):
                return (
                    False,
                    f"Invalid end time format for {day}. Use HH:MM (24-hour format)",
                )

    return True, ""


def validate_ip_address(ip: str) -> bool:
    """Validate an IP address.

    Args:
        ip: The IP address to validate.

    Returns:
        True if the IP address is valid, False otherwise.
    """
    ip_pattern = re.compile(
        r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}" r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
    )

    return bool(ip_pattern.match(ip))


def validate_allowed_ips(ip_list: str) -> Tuple[bool, str]:
    """Validate a comma-separated list of IP addresses or CIDR ranges.

    Args:
        ip_list: A comma-separated list of IP addresses or CIDR ranges.

    Returns:
        A tuple of (is_valid, error_message).
    """
    if not ip_list:
        return True, ""  # Empty list is valid (no restrictions)

    ip_entries = [entry.strip() for entry in ip_list.split(",")]

    for entry in ip_entries:
        # Check if it's a CIDR range
        if "/" in entry:
            ip, prefix = entry.split("/")

            if not validate_ip_address(ip):
                return False, f"Invalid IP address in CIDR range: {ip}"

            try:
                prefix_num = int(prefix)
                if prefix_num < 0 or prefix_num > 32:
                    return False, f"Invalid prefix in CIDR range: {prefix}"
            except ValueError:
                return False, f"Invalid prefix in CIDR range: {prefix}"
        else:
            # It's a single IP address
            if not validate_ip_address(entry):
                return False, f"Invalid IP address: {entry}"

    return True, ""


# --- Google Address Validation API Function ---
def validate_address(address_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates a given address using the Google Address Validation API.

    Args:
        address_input: A dictionary representing the address to validate.
                       Expected format: {"address": {"regionCode": "US", ...}}

    Returns:
        A dictionary containing:
        - isValid: bool (True if validationGranularity is PREMISE/SUB_PREMISE and no major issues)
        - validationResult: dict (the 'result' object from the API response)
        - error: Optional[str] (error message if API call failed or key was missing)
    """
    default_error_response = {
        "isValid": False,
        "validationResult": {},
        "error": "An unexpected error occurred.",
    }

    if not GOOGLE_MAPS_API_KEY:
        logger.error("Address Validation API key is missing.")
        return {
            "isValid": False,
            "validationResult": {},
            "error": "API key for address validation is not configured.",
        }

    if not isinstance(address_input, dict) or "address" not in address_input:
        logger.warning("Invalid address_input format for validation.")
        return {
            "isValid": False,
            "validationResult": {},
            "error": "Invalid input format for address validation.",
        }

    api_url = f"{ADDRESS_VALIDATION_API_URL_BASE}?key={GOOGLE_MAPS_API_KEY}"
    request_body = json.dumps(address_input).encode("utf-8")

    try:
        req = urllib.request.Request(api_url, data=request_body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as response:
            response_body = response.read().decode("utf-8")
            data = json.loads(response_body)
    except urllib.error.HTTPError as e:
        error_content = e.read().decode("utf-8") if e.fp else "No additional error content"
        logger.error(f"HTTP error from Address Validation API: {e.code} {e.reason} - {error_content}")
        return {
            "isValid": False,
            "validationResult": {},
            "error": f"Address Validation API request failed with HTTP {e.code}.",
        }
    except urllib.error.URLError as e:
        logger.error(f"Network error during Address Validation API call: {e.reason}")
        return {
            "isValid": False,
            "validationResult": {},
            "error": "Network error connecting to Address Validation API.",
        }
    except json.JSONDecodeError:
        logger.error("Failed to decode JSON response from Address Validation API.")
        return {
            "isValid": False,
            "validationResult": {},
            "error": "Invalid JSON response from Address Validation API.",
        }
    except Exception as e:
        logger.error(f"Unexpected error during Address Validation API call: {e}")
        return default_error_response  # Use a generic error for truly unexpected issues

    # Process the API response
    validation_result = data.get("result", {})
    verdict = validation_result.get("verdict", {})

    # Determine 'isValid' based on verdict
    # High precision is desired: PREMISE or SUB_PREMISE granularity.
    # No critical issues like missing required fields.
    is_valid = False
    validation_granularity = verdict.get("validationGranularity")

    if validation_granularity in ["PREMISE", "SUB_PREMISE"]:
        # Check for problematic flags.
        # Depending on strictness, hasUnconfirmedComponents or hasInferredComponents might be acceptable.
        # For this implementation, we'll be relatively strict.
        if not verdict.get("hasMissingComponents", False):
            is_valid = True
            # Optionally, be stricter:
            # if not verdict.get("hasUnconfirmedComponents", False) and \
            #    not verdict.get("hasInferredComponents", False):
            #     is_valid = True

    return {
        "isValid": is_valid,
        "validationResult": validation_result,
        "error": None,  # No error if API call was successful
    }


# --- End Google Address Validation API Function ---
