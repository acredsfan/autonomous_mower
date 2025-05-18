"""
Unit tests for network_diagnostics utility.

These tests mock network requests to verify connectivity and endpoint checks.
"""

import pytest
from unittest.mock import patch, MagicMock

from mower.utilities import network_diagnostics


@pytest.fixture
def endpoints():
    return [
        "https://example.com/resource1",
        "https://example.com/resource2"
    ]


@patch("requests.get")
def test_check_internet_connectivity_success(mock_get):
    mock_get.return_value.status_code = 200
    assert network_diagnostics.check_internet_connectivity() is True


@patch("requests.get")
def test_check_internet_connectivity_failure(mock_get):
    mock_get.side_effect = Exception("No connection")
    assert network_diagnostics.check_internet_connectivity() is False


@patch("requests.head")
def test_check_required_endpoints_all_ok(mock_head, endpoints):
    mock_head.return_value.status_code = 200
    with patch.object(network_diagnostics, "REQUIRED_ENDPOINTS", endpoints):
        assert network_diagnostics.check_required_endpoints() is True


@patch("requests.head")
def test_check_required_endpoints_some_fail(mock_head, endpoints):
    # First endpoint OK, second fails
    def side_effect(url, *args, **kwargs):
        mock_resp = MagicMock()
        mock_resp.status_code = 200 if "resource1" in url else 404
        return mock_resp
    mock_head.side_effect = side_effect
    with patch.object(network_diagnostics, "REQUIRED_ENDPOINTS", endpoints):
        assert network_diagnostics.check_required_endpoints() is False


@patch("mower.utilities.network_diagnostics.check_internet_connectivity")
@patch("mower.utilities.network_diagnostics.check_required_endpoints")
def test_run_preflight_check_all_ok(mock_endpoints, mock_internet):
    mock_internet.return_value = True
    mock_endpoints.return_value = True
    assert network_diagnostics.run_preflight_check() is True


@patch("mower.utilities.network_diagnostics.check_internet_connectivity")
@patch("mower.utilities.network_diagnostics.check_required_endpoints")
def test_run_preflight_check_fail(mock_endpoints, mock_internet):
    mock_internet.return_value = False
    mock_endpoints.return_value = True
    assert network_diagnostics.run_preflight_check() is False
