#!/usr/bin/env python3
"""
Test script for Map UI functionality.

This script tests the basic map functionality by:
1. Setting boundary points
2. Setting home location
3. Generating a test pattern

Usage:
    python test_map_ui.py
"""

import json
import os
import sys
import requests
from pathlib import Path

# Add src to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.mower.main_controller import ResourceManager
from src.mower.navigation.path_planner import PatternType


def test_map_functionality():
    """Test map functionality with resource manager."""
    print("Testing Map UI functionality...")

    # Initialize ResourceManager
    resource_manager = ResourceManager()

    # Test setting boundary points
    boundary_points = [
        [47.6062, -122.3321],  # Example coordinates
        [47.6064, -122.3311],
        [47.6052, -122.3301],
        [47.6050, -122.3318],
    ]

    print("\nTesting boundary points...")
    success = resource_manager.get_path_planner().set_boundary_points(boundary_points)
    print(f"Set boundary points: {'Success' if success else 'Failed'}")

    # Test setting home location
    home_location = [47.6058, -122.3315]

    print("\nTesting home location...")
    success = resource_manager.set_home_location(home_location)
    print(f"Set home location: {'Success' if success else 'Failed'}")

    # Test generating pattern
    print("\nTesting pattern generation...")
    pattern_type = "PARALLEL"
    settings = {"spacing": 0.5, "angle": 45, "overlap": 0.1}

    pattern = resource_manager.get_path_planner().generate_pattern(
        pattern_type, settings
    )
    print(f"Generated pattern with {len(pattern)} points")

    # Verify results by loading the saved file
    print("\nVerifying saved data...")
    config_path = resource_manager.user_polygon_path

    try:
        with open(config_path, "r") as f:
            data = json.load(f)
            print(f"Loaded config data: {json.dumps(data, indent=2)}")
    except Exception as e:
        print(f"Error loading config: {e}")

    print("\nMap UI functionality test completed.")


def test_api_endpoints():
    """Test the API endpoints using HTTP requests."""
    print("Testing API endpoints...")
    base_url = "http://localhost:5000/api"

    # Test save area endpoint
    boundary_points = [
        {"lat": 47.6062, "lng": -122.3321},
        {"lat": 47.6064, "lng": -122.3311},
        {"lat": 47.6052, "lng": -122.3301},
        {"lat": 47.6050, "lng": -122.3318},
    ]

    try:
        # Save area
        print("\nTesting save_area endpoint...")
        response = requests.post(
            f"{base_url}/save_area", json={"coordinates": boundary_points}
        )
        print(f"Save area response: {response.status_code} - {response.text}")

        # Set home
        print("\nTesting set_home endpoint...")
        response = requests.post(
            f"{base_url}/set_home",
            json={"location": {"lat": 47.6058, "lng": -122.3315}},
        )
        print(f"Set home response: {response.status_code} - {response.text}")

        # Generate pattern
        print("\nTesting generate_pattern endpoint...")
        response = requests.post(
            f"{base_url}/generate_pattern",
            json={
                "pattern_type": "PARALLEL",
                "settings": {"spacing": 0.5, "angle": 45, "overlap": 0.1},
            },
        )
        print(f"Generate pattern response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Generated path with {len(data.get('path', []))} points")
        else:
            print(f"Failed: {response.text}")

    except Exception as e:
        print(f"Error testing API: {e}")

    print("\nAPI endpoint test completed.")


if __name__ == "__main__":
    print("=== Map UI Functionality Tests ===")

    # Run tests
    test_map_functionality()

    # Optionally test API endpoints if the server is running
    if "--api" in sys.argv:
        test_api_endpoints()
    else:
        print("\nSkipping API tests. Run with --api flag to test endpoints.")

    print("\nAll tests completed.")
