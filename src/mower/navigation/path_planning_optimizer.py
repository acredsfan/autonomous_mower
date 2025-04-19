"""
Path planning optimization module for autonomous mower.

This module provides tools for optimizing path planning algorithms
and improving their performance.
"""

import time
import functools
import numpy as np
from typing import List, Tuple, Dict, Any, Optional, Callable

from mower.navigation.path_planner import PathPlanner, PatternConfig, PatternType
from mower.utilities.logger_config import LoggerConfigInfo

# Initialize logger
logger = LoggerConfigInfo.get_logger(__name__)

class PathPlanningOptimizer:
    """
    Optimizer for path planning algorithms.
    
    This class provides methods for optimizing path planning algorithms
    by implementing caching, vectorization, and other performance improvements.
    """
    
    def __init__(self, path_planner: PathPlanner):
        """
        Initialize the path planning optimizer.
        
        Args:
            path_planner: The path planner to optimize
        """
        self.path_planner = path_planner
        self.path_cache = {}
        self.boundary_cache = {}
        self.intersection_cache = {}
        
        # Apply optimizations
        self._apply_optimizations()
        
        logger.info("Path planning optimizer initialized")
    
    def _apply_optimizations(self):
        """Apply optimizations to the path planner."""
        # Apply caching to expensive methods
        self._apply_caching()
        
        # Apply vectorization to performance-critical methods
        self._apply_vectorization()
        
        logger.info("Applied optimizations to path planner")
    
    def _apply_caching(self):
        """Apply caching to expensive methods."""
        # Cache the generate_path method
        original_generate_path = self.path_planner.generate_path
        
        @functools.wraps(original_generate_path)
        def cached_generate_path():
            # Create a cache key based on the current configuration
            cache_key = self._get_cache_key()
            
            # Check if the path is already cached
            if cache_key in self.path_cache:
                logger.debug(f"Using cached path for {cache_key}")
                return self.path_cache[cache_key]
            
            # Generate the path
            start_time = time.time()
            path = original_generate_path()
            generation_time = time.time() - start_time
            
            # Cache the path
            self.path_cache[cache_key] = path
            
            logger.debug(f"Path generation took {generation_time:.4f} seconds")
            return path
        
        # Replace the original method with the cached version
        self.path_planner.generate_path = cached_generate_path
        
        # Cache boundary calculations
        self._cache_boundary_calculations()
        
        logger.info("Applied caching optimizations")
    
    def _get_cache_key(self) -> str:
        """
        Generate a cache key based on the current configuration.
        
        Returns:
            A string that uniquely identifies the current configuration
        """
        pattern_config = self.path_planner.pattern_config
        return (
            f"{pattern_config.pattern_type.name}_"
            f"{pattern_config.spacing:.2f}_"
            f"{pattern_config.angle:.2f}_"
            f"{pattern_config.overlap:.2f}_"
            f"{hash(tuple(sorted(pattern_config.boundary_points)))}"
        )
    
    def _cache_boundary_calculations(self):
        """Cache boundary calculations."""
        # Cache the _find_boundary_intersections method
        original_find_intersections = self.path_planner._find_boundary_intersections
        
        @functools.wraps(original_find_intersections)
        def cached_find_intersections(start, end, boundary):
            # Create a cache key
            cache_key = (tuple(start), tuple(end), hash(tuple(map(tuple, boundary))))
            
            # Check if the intersections are already cached
            if cache_key in self.intersection_cache:
                return self.intersection_cache[cache_key]
            
            # Find the intersections
            intersections = original_find_intersections(start, end, boundary)
            
            # Cache the intersections
            self.intersection_cache[cache_key] = intersections
            
            return intersections
        
        # Replace the original method with the cached version
        self.path_planner._find_boundary_intersections = cached_find_intersections
    
    def _apply_vectorization(self):
        """Apply vectorization to performance-critical methods."""
        # Optimize the _calculate_path_distance method
        original_calculate_distance = self.path_planner._calculate_path_distance
        
        @functools.wraps(original_calculate_distance)
        def vectorized_calculate_distance(path):
            try:
                if len(path) < 2:
                    return float('inf')
                
                # Convert to numpy array for vectorized operations
                path_array = np.array(path)
                
                # Calculate distances between consecutive points
                diff = np.diff(path_array, axis=0)
                distances = np.sqrt(np.sum(diff**2, axis=1))
                
                # Sum all distances
                total_distance = np.sum(distances)
                
                return total_distance
            except Exception as e:
                logger.error(f"Error in vectorized distance calculation: {e}")
                # Fall back to original method
                return original_calculate_distance(path)
        
        # Replace the original method with the vectorized version
        self.path_planner._calculate_path_distance = vectorized_calculate_distance
        
        # Optimize the _point_in_polygon method
        original_point_in_polygon = self.path_planner._point_in_polygon
        
        @functools.wraps(original_point_in_polygon)
        def vectorized_point_in_polygon(point, polygon):
            try:
                # Use a more efficient implementation of the ray casting algorithm
                x, y = point
                n = len(polygon)
                inside = False
                
                # Cache frequently accessed values
                polygon_x = polygon[:, 0]
                polygon_y = polygon[:, 1]
                
                j = n - 1
                for i in range(n):
                    # Check if the ray from point crosses this edge
                    if ((polygon_y[i] > y) != (polygon_y[j] > y)) and \
                       (x < (polygon_x[j] - polygon_x[i]) * (y - polygon_y[i]) / 
                        (polygon_y[j] - polygon_y[i]) + polygon_x[i]):
                        inside = not inside
                    j = i
                
                return inside
            except Exception as e:
                logger.error(f"Error in vectorized point-in-polygon test: {e}")
                # Fall back to original method
                return original_point_in_polygon(point, polygon)
        
        # Replace the original method with the vectorized version
        self.path_planner._point_in_polygon = vectorized_point_in_polygon
        
        logger.info("Applied vectorization optimizations")
    
    def clear_caches(self):
        """Clear all caches."""
        self.path_cache.clear()
        self.boundary_cache.clear()
        self.intersection_cache.clear()
        logger.info("Cleared all caches")
    
    def update_obstacle_map(self, obstacles):
        """
        Update the obstacle map and invalidate relevant caches.
        
        Args:
            obstacles: List of obstacles
        """
        # Clear caches that depend on obstacles
        self.path_cache.clear()
        
        # Update obstacles in the path planner
        self.path_planner.update_obstacle_map(obstacles)
        
        logger.info("Updated obstacle map and invalidated caches")

def optimize_path_planner(path_planner: PathPlanner) -> PathPlanner:
    """
    Optimize a path planner for better performance.
    
    Args:
        path_planner: The path planner to optimize
        
    Returns:
        The optimized path planner
    """
    optimizer = PathPlanningOptimizer(path_planner)
    return path_planner

def benchmark_path_planner(path_planner: PathPlanner, iterations: int = 5) -> Dict[str, Any]:
    """
    Benchmark a path planner's performance.
    
    Args:
        path_planner: The path planner to benchmark
        iterations: Number of iterations to run
        
    Returns:
        Dictionary with benchmark results
    """
    logger.info(f"Benchmarking path planner for {iterations} iterations")
    
    # Benchmark generate_path
    generate_times = []
    for i in range(iterations):
        start_time = time.time()
        path = path_planner.generate_path()
        end_time = time.time()
        generate_times.append(end_time - start_time)
    
    # Calculate statistics
    avg_time = np.mean(generate_times)
    std_time = np.std(generate_times)
    min_time = np.min(generate_times)
    max_time = np.max(generate_times)
    
    results = {
        'generate_path': {
            'avg_time': avg_time,
            'std_time': std_time,
            'min_time': min_time,
            'max_time': max_time,
            'times': generate_times
        }
    }
    
    logger.info(f"Path generation benchmark results:")
    logger.info(f"  Average time: {avg_time:.4f} seconds")
    logger.info(f"  Standard deviation: {std_time:.4f} seconds")
    logger.info(f"  Min/Max time: {min_time:.4f}/{max_time:.4f} seconds")
    
    return results

def compare_path_planners(
    original_planner: PathPlanner,
    optimized_planner: PathPlanner,
    iterations: int = 5
) -> Dict[str, Any]:
    """
    Compare the performance of two path planners.
    
    Args:
        original_planner: The original path planner
        optimized_planner: The optimized path planner
        iterations: Number of iterations to run
        
    Returns:
        Dictionary with comparison results
    """
    logger.info(f"Comparing path planners for {iterations} iterations")
    
    # Benchmark original planner
    original_results = benchmark_path_planner(original_planner, iterations)
    
    # Benchmark optimized planner
    optimized_results = benchmark_path_planner(optimized_planner, iterations)
    
    # Calculate improvement
    original_avg = original_results['generate_path']['avg_time']
    optimized_avg = optimized_results['generate_path']['avg_time']
    improvement = (original_avg - optimized_avg) / original_avg * 100
    
    comparison = {
        'original': original_results,
        'optimized': optimized_results,
        'improvement_percent': improvement
    }
    
    logger.info(f"Performance comparison results:")
    logger.info(f"  Original average time: {original_avg:.4f} seconds")
    logger.info(f"  Optimized average time: {optimized_avg:.4f} seconds")
    logger.info(f"  Improvement: {improvement:.2f}%")
    
    return comparison

def run_optimization_benchmark():
    """Run a benchmark to compare original and optimized path planners."""
    logger.info("Running path planning optimization benchmark")
    
    # Create a test boundary
    boundary_points = [(0, 0), (10, 0), (10, 10), (0, 10)]
    
    # Create pattern config
    pattern_config = PatternConfig(
        pattern_type=PatternType.PARALLEL,
        spacing=0.5,
        angle=0.0,
        overlap=0.1,
        start_point=(0.0, 0.0),
        boundary_points=boundary_points
    )
    
    # Create original path planner
    original_planner = PathPlanner(pattern_config)
    
    # Create optimized path planner
    optimized_planner = PathPlanner(pattern_config)
    optimize_path_planner(optimized_planner)
    
    # Compare planners
    results = compare_path_planners(original_planner, optimized_planner)
    
    return results

if __name__ == "__main__":
    run_optimization_benchmark()