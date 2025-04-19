# Performance Benchmarks

This directory contains performance benchmarks for critical operations in the autonomous mower codebase. These benchmarks help identify performance bottlenecks and track performance improvements over time.

## Overview

The benchmarks are implemented using `pytest-benchmark`, which provides a framework for measuring the performance of Python code. The benchmarks are organized by component:

- `test_path_planner_benchmarks.py`: Benchmarks for path planning algorithms
- `test_avoidance_algorithm_benchmarks.py`: Benchmarks for obstacle detection and avoidance algorithms

## Running the Benchmarks

### Using pytest-benchmark

To run all benchmarks:

```bash
pytest tests/benchmarks
```

To run benchmarks for a specific component:

```bash
pytest tests/benchmarks/test_path_planner_benchmarks.py
```

To run a specific benchmark:

```bash
pytest tests/benchmarks/test_path_planner_benchmarks.py::test_generate_path_benchmark
```

### Command-line Options

`pytest-benchmark` provides several command-line options for controlling the benchmark execution:

- `--benchmark-min-rounds=N`: Minimum number of rounds to perform (default: 5)
- `--benchmark-max-time=N`: Maximum time to spend on each benchmark (default: 1 second)
- `--benchmark-warmup`: Perform a warmup round before measuring
- `--benchmark-disable`: Disable benchmarking, useful for debugging
- `--benchmark-skip`: Skip benchmarks, useful for debugging
- `--benchmark-only`: Only run benchmarks, skip regular tests
- `--benchmark-save=NAME`: Save the benchmark results to a file
- `--benchmark-compare=NAME`: Compare the benchmark results with a previous run
- `--benchmark-histogram=PATH`: Plot a histogram of the benchmark results

For example:

```bash
pytest tests/benchmarks --benchmark-min-rounds=10 --benchmark-max-time=2
```

### Running Directly

The benchmark files can also be run directly as Python scripts:

```bash
python tests/benchmarks/test_path_planner_benchmarks.py
```

This will run the benchmarks using the custom benchmarking utilities in `utils.py` rather than `pytest-benchmark`.

## Interpreting Results

When running with `pytest-benchmark`, the results will be displayed in a table format:

```
--------------------------------------------------------------------------------------- benchmark: 4 tests ---------------------------------------------------------------------------------------
Name (time in ms)                                Min                Max               Mean            StdDev             Median               IQR            Outliers       OPS            Rounds  Iterations
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
test_generate_path_benchmark                  1.3249 (1.0)       1.4112 (1.0)       1.3530 (1.0)     0.0242 (1.0)       1.3469 (1.0)      0.0312 (1.0)           2;0  739.0989 (1.0)          8           1
test_calculate_reward_benchmark               2.6498 (2.0)       2.8224 (2.0)       2.7060 (2.0)     0.0484 (2.0)       2.6938 (2.0)      0.0625 (2.0)           2;0  369.5494 (0.5)          8           1
test_calculate_path_distance_benchmark        5.2996 (4.0)       5.6448 (4.0)       5.4120 (4.0)     0.0968 (4.0)       5.3876 (4.0)      0.1249 (4.0)           2;0  184.7747 (0.25)         8           1
test_calculate_coverage_benchmark            10.5992 (8.0)      11.2896 (8.0)      10.8240 (8.0)     0.1936 (8.0)      10.7752 (8.0)      0.2498 (8.0)           2;0   92.3874 (0.13)         8           1
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
```

The key metrics to look at are:

- **Mean**: The average execution time
- **Min/Max**: The minimum and maximum execution times
- **StdDev**: The standard deviation of execution times
- **OPS**: Operations per second (higher is better)

When running directly, the results will be logged to the console:

```
INFO:tests.benchmarks.utils:Benchmark: generate_path
INFO:tests.benchmarks.utils:  Mean time: 0.001353 seconds
INFO:tests.benchmarks.utils:  Median time: 0.001347 seconds
INFO:tests.benchmarks.utils:  Min time: 0.001325 seconds
INFO:tests.benchmarks.utils:  Max time: 0.001411 seconds
INFO:tests.benchmarks.utils:  Std dev: 0.000024 seconds
```

## Adding New Benchmarks

To add a new benchmark:

1. Identify a critical operation that needs benchmarking
2. Add a new test function to the appropriate benchmark file
3. Use the `benchmark` fixture to measure the performance of the operation
4. Add assertions to verify that the operation produces the expected results

Example:

```python
def test_my_operation_benchmark(benchmark, my_component):
    """Benchmark the my_operation method."""
    # Set up test data
    test_data = ...
    
    # Use pytest-benchmark to measure performance
    result = benchmark(my_component.my_operation, test_data)
    
    # Verify that the operation produces the expected results
    assert result is not None
    assert result.some_property == expected_value
```

## Best Practices

- **Isolate the operation**: Benchmark only the specific operation you want to measure, not the setup or verification code.
- **Use realistic data**: Use data that is representative of real-world usage.
- **Verify results**: Always verify that the operation produces the expected results to ensure that optimizations don't break functionality.
- **Compare before and after**: When optimizing, always compare the performance before and after the optimization.
- **Focus on critical operations**: Focus on operations that are executed frequently or are known to be performance bottlenecks.
- **Consider edge cases**: Benchmark with different input sizes and edge cases to understand how performance scales.