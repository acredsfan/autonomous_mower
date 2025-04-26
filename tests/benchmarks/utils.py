"""
Utility functions for benchmarking.

This module provides utility functions for benchmarking critical operations
in the autonomous mower codebase.
"""

import os
import sys
import time
import logging
import numpy as np
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_test_data_path() -> Path:
    """
    Get the path to the test data directory.

    Returns:
        Path: Path to the test data directory
    """
    # Get the path to the tests directory
    tests_dir = Path(__file__).parent.parent

    # Create the test data directory if it doesn't exist
    test_data_dir = tests_dir / "data"
    test_data_dir.mkdir(exist_ok=True)

    return test_data_dir


def generate_random_boundary(
    num_points: int = 8, radius: float = 50.0
) -> List[Tuple[float, float]]:
    """
    Generate a random boundary for testing.

    Args:
        num_points: Number of points in the boundary
        radius: Radius of the boundary

    Returns:
        List[Tuple[float, float]]: List of boundary points
    """
    # Generate points on a circle for a convex polygon
    angles = sorted(
        [np.random.uniform(0, 2 * np.pi) for _ in range(num_points)]
    )
    center_x = np.random.uniform(-50.0, 50.0)
    center_y = np.random.uniform(-50.0, 50.0)

    boundary_points = [
        (center_x + radius * np.cos(angle), center_y + radius * np.sin(angle))
        for angle in angles
    ]

    return boundary_points


def generate_random_obstacles(
    num_obstacles: int = 5,
    boundary: Optional[List[Tuple[float, float]]] = None,
    min_size: float = 0.5,
    max_size: float = 2.0,
) -> List[Tuple[Tuple[float, float], float]]:
    """
    Generate random obstacles for testing.

    Args:
        num_obstacles: Number of obstacles to generate
        boundary: Optional boundary to place obstacles within
        min_size: Minimum obstacle size
        max_size: Maximum obstacle size

    Returns:
        List[Tuple[Tuple[float, float], float]]: List of obstacles as (position, size) tuples
    """
    obstacles = []

    if boundary:
        # Calculate the bounding box of the boundary
        x_coords = [p[0] for p in boundary]
        y_coords = [p[1] for p in boundary]
        min_x, max_x = min(x_coords), max(x_coords)
        min_y, max_y = min(y_coords), max(y_coords)
    else:
        # Use a default bounding box
        min_x, max_x = -100.0, 100.0
        min_y, max_y = -100.0, 100.0

    # Generate random obstacles
    for _ in range(num_obstacles):
        x = np.random.uniform(min_x, max_x)
        y = np.random.uniform(min_y, max_y)
        size = np.random.uniform(min_size, max_size)

        obstacles.append(((x, y), size))

    return obstacles


def time_function(func: Callable, *args, **kwargs) -> Tuple[Any, float]:
    """
    Time the execution of a function.

    Args:
        func: Function to time
        *args: Arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function

    Returns:
        Tuple[Any, float]: Tuple of (function result, execution time in seconds)
    """
    start_time = time.time()
    result = func(*args, **kwargs)
    end_time = time.time()

    return result, end_time - start_time


def log_benchmark_results(
    name: str, times: List[float], results: Optional[List[Any]] = None
) -> Dict[str, float]:
    """
    Log benchmark results.

    Args:
        name: Name of the benchmark
        times: List of execution times
        results: Optional list of function results

    Returns:
        Dict[str, float]: Dictionary of benchmark statistics
    """
    # Calculate statistics
    mean_time = np.mean(times)
    median_time = np.median(times)
    min_time = np.min(times)
    max_time = np.max(times)
    std_dev = np.std(times)

    # Log results
    logger.info(f"Benchmark: {name}")
    logger.info(f"  Mean time: {mean_time:.6f} seconds")
    logger.info(f"  Median time: {median_time:.6f} seconds")
    logger.info(f"  Min time: {min_time:.6f} seconds")
    logger.info(f"  Max time: {max_time:.6f} seconds")
    logger.info(f"  Std dev: {std_dev:.6f} seconds")

    # Return statistics
    return {
        "mean": mean_time,
        "median": median_time,
        "min": min_time,
        "max": max_time,
        "std_dev": std_dev,
    }
