"""
Utility functions for benchmark tests.
"""

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


def get_test_data_dir() -> Path:
    """
    Get the path to the test data directory.

    Returns:
        Path: Path to the test data directory
    """
    # Assuming the test data directory is at the same level as the tests directory
    # and named 'test_data'. Adjust if your structure is different.
    return Path(__file__).parent.parent / "test_data"


def generate_random_boundary(num_points: int = 5, radius: float = 10.0) -> List[Tuple[float, float]]:
    """
    Generate a random boundary for testing.

    Args:
        num_points: Number of points in the boundary
        radius: Radius of the boundary

    Returns:
        List[Tuple[float, float]]: List of boundary points
    """
    pass


def generate_random_obstacles(
    num_obstacles: int = 3,
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
        List[Tuple[Tuple[float, float], float]]:
            List of obstacles as (position, size) tuples
    """
    pass


def time_execution(func: Callable, *args: Any, **kwargs: Any) -> Tuple[Any, float]:
    """
    Time the execution of a function.

    Args:
        func: Function to time
        *args: Arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function

    Returns:
        Tuple[Any, float]: Tuple of (function result, execution time in seconds)
    """
    pass


def log_benchmark_results(name: str, times: List[float], results: Optional[List[Any]] = None) -> Dict[str, float]:
    """
    Log benchmark results.

    Args:
        name: Name of the benchmark
        times: List of execution times
        results: Optional list of function results

    Returns:
        Dict[str, float]: Dictionary of benchmark statistics
    """
    pass
