#!/usr/bin/env python3
"""
Performance Profiler Demo Script

This script demonstrates the enhanced performance profiling capabilities
of the autonomous mower system. It runs a series of performance tests and
generates a comprehensive performance report.

Usage:
    python scripts/demo_performance_profiler.py [--output OUTPUT_FILE] [--compare BASELINE_FILE]

Options:
    --output OUTPUT_FILE    Save performance results to the specified file
    --compare BASELINE_FILE Compare results against a baseline file
    --threshold PERCENT     Alert threshold for performance regression (default: 10)
    --verbose               Show detailed performance information
"""

import os
import sys
import json
import time
import argparse
import datetime
import subprocess
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from src.mower.diagnostics.enhanced_performance_profiler import (
        PerformanceMonitor,
        PerformanceAnalysis,
        get_performance_monitor
    )
    from src.core.logger import get_logger
except ImportError:
    print("Error: Could not import required modules. Make sure you're running from the project root.")
    sys.exit(1)

# Initialize logger
logger = get_logger("performance_profiler")


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Performance Profiler Demo")
    parser.add_argument("--output", type=str, help="Output file for performance results")
    parser.add_argument("--compare", type=str, help="Baseline file to compare against")
    parser.add_argument("--threshold", type=float, default=10.0,
                        help="Alert threshold for performance regression (percent)")
    parser.add_argument("--verbose", action="store_true", help="Show detailed performance information")
    return parser.parse_args()


def run_benchmarks():
    """Run performance benchmarks using pytest-benchmark."""
    logger.info("Running performance benchmarks...")
    
    # Create output directory if it doesn't exist
    os.makedirs("benchmark_results", exist_ok=True)
    
    # Generate timestamp for benchmark results
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    json_output = f"benchmark_results/benchmark_{timestamp}.json"
    
    # Run benchmarks with pytest-benchmark
    cmd = [
        "pytest",
        "tests/benchmarks",
        "--benchmark-only",
        f"--benchmark-json={json_output}",
        "--benchmark-min-rounds=5",
        "--benchmark-warmup=true"
    ]
    
    try:
        subprocess.run(cmd, check=True)
        logger.info(f"Benchmarks completed successfully. Results saved to {json_output}")
        return json_output
    except subprocess.CalledProcessError as e:
        logger.error(f"Benchmark execution failed: {e}")
        return None


def profile_system_components():
    """Profile key system components using the PerformanceMonitor."""
    logger.info("Profiling system components...")
    
    # Get the performance monitor
    monitor = get_performance_monitor()
    
    # Start monitoring
    monitor.start()
    
    try:
        # Import components here to avoid circular imports
        from src.mower.navigation.path_planner import PathPlanner
        from src.mower.obstacle_detection.obstacle_detector import ObstacleDetector
        from src.mower.hardware.sensor_manager import SensorManager
        
        # Create test instances with mock dependencies
        from unittest.mock import MagicMock
        config_manager = MagicMock()
        hardware_manager = MagicMock()
        
        # Profile path planner
        logger.info("Profiling path planner...")
        path_planner = PathPlanner(config_manager, hardware_manager)
        for _ in range(10):
            with monitor.profile("path_planner.generate_path"):
                path_planner.generate_path([(0, 0), (1, 1), (2, 2)])
        
        # Profile obstacle detector
        logger.info("Profiling obstacle detector...")
        obstacle_detector = ObstacleDetector(config_manager, hardware_manager)
        for _ in range(10):
            with monitor.profile("obstacle_detector.detect_obstacles"):
                obstacle_detector.detect_obstacles()
        
        # Profile sensor manager
        logger.info("Profiling sensor manager...")
        sensor_manager = SensorManager(config_manager)
        for _ in range(10):
            with monitor.profile("sensor_manager.read_all_sensors"):
                sensor_manager.read_all_sensors()
        
        # Let the monitor collect data
        time.sleep(1)
        
        # Get performance analysis
        analysis = monitor.get_performance_analysis()
        return analysis
        
    finally:
        # Stop monitoring
        monitor.stop()


def compare_results(current_results, baseline_file, threshold):
    """Compare current results with baseline and detect regressions."""
    logger.info(f"Comparing results with baseline: {baseline_file}")
    
    try:
        with open(baseline_file, 'r') as f:
            baseline = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Error loading baseline file: {e}")
        return None
    
    # Compare benchmark results
    regressions = []
    improvements = []
    
    for bench_current in current_results.get("benchmarks", []):
        name = bench_current.get("name")
        
        # Find matching benchmark in baseline
        baseline_match = next(
            (b for b in baseline.get("benchmarks", []) if b.get("name") == name),
            None
        )
        
        if baseline_match:
            current_mean = bench_current.get("stats", {}).get("mean", 0)
            baseline_mean = baseline_match.get("stats", {}).get("mean", 0)
            
            if baseline_mean > 0:
                percent_change = ((current_mean - baseline_mean) / baseline_mean) * 100
                
                if percent_change > threshold:
                    regressions.append({
                        "name": name,
                        "baseline": baseline_mean,
                        "current": current_mean,
                        "change_percent": percent_change
                    })
                elif percent_change < -threshold:
                    improvements.append({
                        "name": name,
                        "baseline": baseline_mean,
                        "current": current_mean,
                        "change_percent": percent_change
                    })
    
    return {
        "regressions": regressions,
        "improvements": improvements
    }


def generate_report(benchmark_results, profile_results, comparison=None):
    """Generate a comprehensive performance report."""
    report = {
        "timestamp": datetime.datetime.now().isoformat(),
        "benchmark_results": benchmark_results,
        "profile_results": profile_results.to_dict() if profile_results else None,
        "comparison": comparison
    }
    
    return report


def save_report(report, output_file):
    """Save the performance report to a file."""
    if not output_file:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"performance_report_{timestamp}.json"
    
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"Performance report saved to {output_file}")
    return output_file


def print_report_summary(report, verbose=False):
    """Print a summary of the performance report."""
    print("\n" + "=" * 80)
    print("PERFORMANCE PROFILER SUMMARY")
    print("=" * 80)
    
    # Print benchmark summary
    if report.get("benchmark_results"):
        print("\nBenchmark Results:")
        print("-" * 40)
        
        benchmarks = report["benchmark_results"].get("benchmarks", [])
        for bench in benchmarks:
            name = bench.get("name")
            mean = bench.get("stats", {}).get("mean", 0) * 1000  # Convert to ms
            print(f"{name}: {mean:.2f} ms")
    
    # Print profile summary
    if report.get("profile_results"):
        print("\nComponent Profiling:")
        print("-" * 40)
        
        components = report["profile_results"].get("component_metrics", {})
        for component, metrics in components.items():
            mean_time = metrics.get("mean_time", 0) * 1000  # Convert to ms
            print(f"{component}: {mean_time:.2f} ms")
        
        # Print system metrics
        system_metrics = report["profile_results"].get("system_metrics", {})
        print("\nSystem Metrics:")
        print(f"CPU Usage: {system_metrics.get('cpu_usage', 0):.1f}%")
        print(f"Memory Usage: {system_metrics.get('memory_usage', 0):.1f} MB")
        
        # Print suggestions
        suggestions = report["profile_results"].get("suggestions", [])
        if suggestions:
            print("\nOptimization Suggestions:")
            for suggestion in suggestions:
                print(f"- {suggestion}")
    
    # Print comparison results
    if report.get("comparison"):
        print("\nPerformance Comparison:")
        print("-" * 40)
        
        regressions = report["comparison"].get("regressions", [])
        if regressions:
            print("\nPerformance Regressions:")
            for reg in regressions:
                name = reg.get("name")
                baseline = reg.get("baseline", 0) * 1000  # Convert to ms
                current = reg.get("current", 0) * 1000  # Convert to ms
                change = reg.get("change_percent", 0)
                print(f"{name}: {baseline:.2f} ms -> {current:.2f} ms ({change:.1f}% slower)")
        
        improvements = report["comparison"].get("improvements", [])
        if improvements:
            print("\nPerformance Improvements:")
            for imp in improvements:
                name = imp.get("name")
                baseline = imp.get("baseline", 0) * 1000  # Convert to ms
                current = imp.get("current", 0) * 1000  # Convert to ms
                change = imp.get("change_percent", 0)
                print(f"{name}: {baseline:.2f} ms -> {current:.2f} ms ({abs(change):.1f}% faster)")
    
    # Print detailed information if verbose
    if verbose and report.get("profile_results"):
        print("\nDetailed Performance Information:")
        print("-" * 40)
        
        bottlenecks = report["profile_results"].get("bottlenecks", [])
        if bottlenecks:
            print("\nIdentified Bottlenecks:")
            for bottleneck in bottlenecks:
                component = bottleneck.get("component")
                impact = bottleneck.get("impact", 0)
                print(f"{component}: Impact Score {impact:.1f}")
        
        # Print more detailed metrics if available
        if verbose > 1 and report.get("benchmark_results"):
            print("\nDetailed Benchmark Metrics:")
            benchmarks = report["benchmark_results"].get("benchmarks", [])
            for bench in benchmarks:
                name = bench.get("name")
                stats = bench.get("stats", {})
                print(f"\n{name}:")
                print(f"  Mean: {stats.get('mean', 0) * 1000:.2f} ms")
                print(f"  Min: {stats.get('min', 0) * 1000:.2f} ms")
                print(f"  Max: {stats.get('max', 0) * 1000:.2f} ms")
                print(f"  StdDev: {stats.get('stddev', 0) * 1000:.2f} ms")
                print(f"  Operations/sec: {1 / stats.get('mean', 1):.1f}")
    
    print("\n" + "=" * 80)


def main():
    """Main function."""
    args = parse_arguments()
    
    logger.info("Starting Performance Profiler Demo")
    
    # Run benchmarks
    benchmark_file = run_benchmarks()
    if benchmark_file:
        with open(benchmark_file, 'r') as f:
            benchmark_results = json.load(f)
    else:
        benchmark_results = None
    
    # Profile system components
    profile_results = profile_system_components()
    
    # Compare with baseline if provided
    comparison = None
    if args.compare and benchmark_results:
        comparison = compare_results(benchmark_results, args.compare, args.threshold)
    
    # Generate report
    report = generate_report(benchmark_results, profile_results, comparison)
    
    # Save report if output file specified
    if args.output:
        save_report(report, args.output)
    
    # Print report summary
    print_report_summary(report, args.verbose)
    
    # Exit with error code if regressions found
    if comparison and comparison.get("regressions"):
        logger.warning("Performance regressions detected!")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())