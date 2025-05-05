#!/usr/bin/env python3
"""
Test script for Map API endpoints.

This script tests the area.html API endpoints by:
1. Testing boundary_points endpoint
2. Testing home_location endpoint
3. Testing pattern generation

Usage:
    python test_map_api.py
"""

import json
import requests
import sys
from pathlib import Path

# Adjust these settings for your environment
API_BASE_URL = "http://localhost:5000/api"


def test_boundary_points_api():
    """Test the boundary_points API endpoint."""
    print("\nTesting boundary_points API...")

    try:
        response = requests.post(f"{API_BASE_URL}/boundary_points")
        print(f"Status code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data.get('success', False)}")
            coordinates = data.get("coordinates", [])
            print(f"Received {len(coordinates)} boundary points")

            if coordinates:
                print(f"Sample point: {coordinates[0]}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")


def test_home_location_api():
    """Test the home_location API endpoint."""
    print("\nTesting home_location API...")

    try:
        response = requests.post(f"{API_BASE_URL}/home_location")
        print(f"Status code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data.get('success', False)}")
            location = data.get("location", [])
            print(f"Home location: {location}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")


def test_set_home_api():
    """Test setting home location through API."""
    print("\nTesting set_home API...")

    # Example home location
    home_location = {"lat": 47.6062, "lng": -122.3321}

    try:
        response = requests.post(
            f"{API_BASE_URL}/set_home", json={"location": home_location}
        )
        print(f"Status code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data.get('success', False)}")
            print(f"Message: {data.get('message', '')}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")


def test_generate_pattern_api():
    """Test the pattern generation API."""
    print("\nTesting generate_pattern API...")

    pattern_config = {
        "pattern_type": "PARALLEL",
        "settings": {"spacing": 0.5, "angle": 45, "overlap": 0.1},
    }

    try:
        response = requests.post(
            f"{API_BASE_URL}/generate_pattern", json=pattern_config
        )
        print(f"Status code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data.get('success', False)}")
            path = data.get("path", [])
            print(f"Generated path with {len(path)} points")
            if path:
                print(f"First few points: {path[:3]}")
                print(f"Last few points: {path[-3:] if len(path) >= 3 else path}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")


if __name__ == "__main__":
    print("=== Testing Map API Endpoints ===")

    # Run tests
    test_boundary_points_api()
    test_home_location_api()
    test_set_home_api()
    test_generate_pattern_api()

    print("\nAll tests completed.")
