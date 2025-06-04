"""
Performance profiling module for the autonomous mower.

This module provides tools for profiling the performance of various components
of the autonomous mower system, identifying bottlenecks, and suggesting
optimization strategies.
"""

import cProfile
import io
import os
import pstats
import time
from typing import Any, Callable, Dict, List

import matplotlib.pyplot as plt
import numpy as np

from mower.utilities.logger_config import LoggerConfigInfo

# from pathlib import Path


# Initialize logger
logger = LoggerConfigInfo.get_logger(__name__)


class PerformanceProfiler:
    """
    Performance profiler for the autonomous mower system.

    This class provides methods for profiling the performance of various
    components of the system, identifying bottlenecks, and suggesting
    optimization strategies.
    """

    def __init__(self, output_dir: str = "profiling_results"):
        """
        Initialize the performance profiler.

        Args:
            output_dir: Directory to store profiling results
        """
        self.output_dir = output_dir
        self.results = {}

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        logger.info(f"Performance profiler initialized with output directory: {output_dir}")

    def profile_function(self, func: Callable, *args, **kwargs) -> Dict[str, Any]:
        """
        Profile a function and return performance metrics.

        Args:
            func: Function to profile
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function

        Returns:
            Dictionary of performance metrics
        """
        # Create profiler
        profiler = cProfile.Profile()

        # Start timing
        start_time = time.time()

        # Start profiling
        profiler.enable()

        # Call function
        result = func(*args, **kwargs)

        # Stop profiling
        profiler.disable()

        # Calculate execution time
        execution_time = time.time() - start_time

        # Get profiling statistics
        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s).sort_stats("cumulative")
        ps.print_stats(20)  # Print top 20 functions

        # Parse statistics
        stats_str = s.getvalue()

        # Extract function calls
        total_calls = ps.total_calls

        # Create results dictionary
        metrics = {
            "execution_time": execution_time,
            "total_calls": total_calls,
            "stats": stats_str,
            "result": result,
        }

        logger.info((f"Profiled {func.__name__}: {execution_time:.4f} seconds" f", {total_calls} calls"))

        return metrics

    def profile_component(self, name: str, func: Callable, iterations: int = 10, *args, **kwargs) -> Dict[str, Any]:
        """
        Profile a component multiple times and calculate average performance.

        Args:
            name: Name of the component
            func: Function to profile
            iterations: Number of iterations to run
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function

        Returns:
            Dictionary of performance metrics
        """
        logger.info(f"Profiling component {name} for {iterations} iterations")

        execution_times = []
        total_calls_list = []

        for i in range(iterations):
            logger.debug(f"Iteration {i + 1}/{iterations}")
            metrics = self.profile_function(func, *args, **kwargs)
            execution_times.append(metrics["execution_time"])
            total_calls_list.append(metrics["total_calls"])

        # Calculate statistics
        avg_time = np.mean(execution_times)
        std_time = np.std(execution_times)
        min_time = np.min(execution_times)
        max_time = np.max(execution_times)
        avg_calls = np.mean(total_calls_list)

        # Create results dictionary
        results = {
            "name": name,
            "iterations": iterations,
            "avg_time": avg_time,
            "std_time": std_time,
            "min_time": min_time,
            "max_time": max_time,
            "avg_calls": avg_calls,
            "execution_times": execution_times,
            "total_calls_list": total_calls_list,
            "last_stats": metrics["stats"],
        }

        # Store results
        self.results[name] = results

        # Log results
        logger.info(f"Component {name} profiling results:")
        logger.info(f"  Average execution time: {avg_time:.4f} seconds")
        logger.info(f"  Standard deviation: {std_time:.4f} seconds")
        logger.info(f"  Min/Max time: {min_time:.4f}/{max_time:.4f} seconds")
        logger.info(f"  Average function calls: {avg_calls:.1f}")

        # Save results to file
        self._save_results(name, results)

        return results

    def _save_results(self, name: str, results: Dict[str, Any]) -> None:
        """
        Save profiling results to files.

        Args:
            name: Name of the component
            results: Dictionary of performance metrics
        """
        # Create component directory
        component_dir = os.path.join(self.output_dir, name.replace(" ", "_"))
        os.makedirs(component_dir, exist_ok=True)

        # Save statistics to text file
        stats_file = os.path.join(component_dir, "stats.txt")
        with open(stats_file, "w") as f:
            f.write(f"Component: {name}\n")
            f.write(f"Iterations: {results['iterations']}\n")
            f.write(f"Average execution time: {results['avg_time']:.4f} seconds\n")
            f.write(f"Standard deviation: {results['std_time']:.4f} seconds\n")
            f.write(f"Min/Max time: {results['min_time']:.4f}" f"/{results['max_time']:.4f} seconds\n")
            f.write(f"Average function calls: {results['avg_calls']:.1f}\n\n")
            f.write("Detailed statistics:\n")
            f.write(results["last_stats"])

        # Create performance graph
        plt.figure(figsize=(10, 6))
        plt.plot(
            range(1, results["iterations"] + 1),
            results["execution_times"],
            "o-",
        )
        plt.title(f"{name} Performance")
        plt.xlabel("Iteration")
        plt.ylabel("Execution Time (seconds)")
        plt.grid(True)
        plt.savefig(os.path.join(component_dir, "performance.png"))
        plt.close()

        logger.info(f"Saved profiling results to {component_dir}")

    def compare_components(self, names: List[str]) -> None:
        """
        Compare the performance of multiple components.

        Args:
            names: List of component names to compare
        """
        if not all(name in self.results for name in names):
            missing = [name for name in names if name not in self.results]
            logger.error(f"Components not found: {missing}")
            return

        # Create comparison graph
        plt.figure(figsize=(12, 8))

        for name in names:
            results = self.results[name]
            plt.plot(
                range(1, results["iterations"] + 1),
                results["execution_times"],
                "o-",
                label=name,
            )

        plt.title("Component Performance Comparison")
        plt.xlabel("Iteration")
        plt.ylabel("Execution Time (seconds)")
        plt.legend()
        plt.grid(True)

        # Save comparison graph
        comparison_file = os.path.join(self.output_dir, "comparison.png")
        plt.savefig(comparison_file)
        plt.close()

        # Create bar chart of average times
        plt.figure(figsize=(10, 6))
        avg_times = [self.results[name]["avg_time"] for name in names]
        plt.bar(names, avg_times)
        plt.title("Average Execution Time Comparison")
        plt.xlabel("Component")
        plt.ylabel("Average Execution Time (seconds)")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()

        # Save bar chart
        bar_chart_file = os.path.join(self.output_dir, "avg_times.png")
        plt.savefig(bar_chart_file)
        plt.close()

        logger.info(f"Saved component comparison to {self.output_dir}")

    def profile_path_planning(self, pattern_config, learning_config=None, iterations: int = 5) -> Dict[str, Any]:
        """
        Profile the path planning component.

        Args:
            pattern_config: Configuration for the path planner
            learning_config: Learning configuration (optional)
            iterations: Number of iterations to run

        Returns:
            Dictionary of performance metrics
        """
        from mower.navigation.path_planner import PathPlanner

        # Create path planner
        path_planner = PathPlanner(pattern_config, learning_config)

        # Profile different pattern types
        results = {}

        # Profile generate_path method
        results["generate_path"] = self.profile_component(
            "Path Planning - Generate Path",
            path_planner.generate_path,
            iterations,
        )

        return results

    def profile_obstacle_detection(self, iterations: int = 5) -> Dict[str, Any]:
        """
        Profile the obstacle detection component.

        Args:
            iterations: Number of iterations to run

        Returns:
            Dictionary of performance metrics
        """
        from mower.hardware.camera_instance import capture_frame
        from mower.obstacle_detection.obstacle_detector import get_obstacle_detector

        # Get obstacle detector
        detector = get_obstacle_detector()

        # Capture a frame for testing
        frame = capture_frame()

        if frame is None:
            logger.error("Failed to capture frame for profiling")
            return {}

        # Profile different detection methods
        results = {}

        # Profile ML-based detection
        results["ml_detection"] = self.profile_component(
            "Obstacle Detection - ML",
            detector._detect_obstacles_ml,
            iterations,
            frame,
        )

        # Profile OpenCV-based detection
        results["opencv_detection"] = self.profile_component(
            "Obstacle Detection - OpenCV",
            detector._detect_obstacles_opencv,
            iterations,
            frame,
        )

        # Profile drop detection
        results["drop_detection"] = self.profile_component(
            "Obstacle Detection - Drop",
            detector.detect_drops,
            iterations,
            frame,
        )

        # Profile full detection pipeline
        results["full_detection"] = self.profile_component(
            "Obstacle Detection - Full Pipeline",
            detector.detect_obstacles,
            iterations,
            frame,
        )

        # Compare all detection methods
        self.compare_components(
            [
                "Obstacle Detection - ML",
                "Obstacle Detection - OpenCV",
                "Obstacle Detection - Drop",
                "Obstacle Detection - Full Pipeline",
            ]
        )

        return results

    def profile_startup(self) -> Dict[str, Any]:
        """
        Profile the startup time of various components.

        Returns:
            Dictionary of performance metrics
        """
        results = {}

        # Profile obstacle detector initialization
        def init_obstacle_detector():
            from mower.obstacle_detection.obstacle_detector import ObstacleDetector

            detector = ObstacleDetector()
            return detector

        results["obstacle_detector_init"] = self.profile_component(
            "Startup - Obstacle Detector Initialization",
            init_obstacle_detector,
            1,  # Only need to run once
        )

        # Profile path planner initialization
        def init_path_planner():
            from mower.navigation.path_planner import PathPlanner, PatternConfig, PatternType

            config = PatternConfig(
                pattern_type=PatternType.PARALLEL,
                spacing=0.5,
                angle=0.0,
                overlap=0.1,
                start_point=(0.0, 0.0),
                boundary_points=[(0, 0), (10, 0), (10, 10), (0, 10)],
            )
            planner = PathPlanner(config)
            return planner

        results["path_planner_init"] = self.profile_component(
            "Startup - Path Planner Initialization",
            init_path_planner,
            1,  # Only need to run once
        )

        return results


def run_profiling():
    """Run comprehensive profiling of the system."""
    logger.info("Starting comprehensive performance profiling")

    # Create profiler
    profiler = PerformanceProfiler()

    # Profile startup time
    profiler.profile_startup()

    # Profile path planning
    from mower.navigation.path_planner import PatternConfig, PatternType

    config = PatternConfig(
        pattern_type=PatternType.PARALLEL,
        spacing=0.5,
        angle=0.0,
        overlap=0.1,
        start_point=(0.0, 0.0),
        boundary_points=[(0, 0), (10, 0), (10, 10), (0, 10)],
    )
    profiler.profile_path_planning(config)

    # Profile obstacle detection
    profiler.profile_obstacle_detection()

    logger.info("Comprehensive performance profiling completed")

    return profiler


if __name__ == "__main__":
    run_profiling()
