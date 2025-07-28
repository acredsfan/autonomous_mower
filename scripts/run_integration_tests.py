#!/usr/bin/env python3
"""
Integration test runner for the autonomous mower project.

This script runs comprehensive integration tests including system startup/shutdown,
component interactions, and hardware simulation tests.
"""

import argparse
import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class IntegrationTestRunner:
    """Runs comprehensive integration tests."""
    
    def __init__(self, test_dir: str = "tests", verbose: bool = False):
        """Initialize the test runner.
        
        Args:
            test_dir: Directory containing tests.
            verbose: Enable verbose output.
        """
        self.test_dir = Path(test_dir)
        self.verbose = verbose
        self.results: Dict[str, Dict] = {}
        
    def run_command(self, cmd: List[str], timeout: int = 300) -> Tuple[bool, str, str]:
        """Run a command and capture output.
        
        Args:
            cmd: Command to run.
            timeout: Timeout in seconds.
            
        Returns:
            Tuple of (success, stdout, stderr).
        """
        try:
            if self.verbose:
                print(f"Running: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.test_dir.parent
            )
            
            return result.returncode == 0, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            return False, "", f"Command timed out after {timeout} seconds"
        except Exception as e:
            return False, "", f"Error running command: {e}"
    
    def run_pytest_suite(self, test_path: str, markers: Optional[List[str]] = None, 
                        extra_args: Optional[List[str]] = None) -> Dict:
        """Run a pytest test suite.
        
        Args:
            test_path: Path to test file or directory.
            markers: Pytest markers to filter tests.
            extra_args: Additional pytest arguments.
            
        Returns:
            Test results dictionary.
        """
        cmd = ["python", "-m", "pytest", test_path, "-v"]
        
        if markers:
            for marker in markers:
                cmd.extend(["-m", marker])
        
        if extra_args:
            cmd.extend(extra_args)
        
        # Add coverage if not already specified
        if "--cov" not in cmd:
            cmd.extend(["--cov=src/mower", "--cov-report=term-missing"])
        
        start_time = time.time()
        success, stdout, stderr = self.run_command(cmd)
        end_time = time.time()
        
        # Parse pytest output for test counts
        test_count = 0
        passed_count = 0
        failed_count = 0
        skipped_count = 0
        
        for line in stdout.split('\n'):
            if " passed" in line or " failed" in line or " skipped" in line:
                if " passed" in line:
                    try:
                        passed_count = int(line.split()[0])
                    except (ValueError, IndexError):
                        pass
                if " failed" in line:
                    try:
                        failed_count = int(line.split()[0])
                    except (ValueError, IndexError):
                        pass
                if " skipped" in line:
                    try:
                        skipped_count = int(line.split()[0])
                    except (ValueError, IndexError):
                        pass
        
        test_count = passed_count + failed_count + skipped_count
        
        return {
            "success": success,
            "test_count": test_count,
            "passed": passed_count,
            "failed": failed_count,
            "skipped": skipped_count,
            "duration": end_time - start_time,
            "stdout": stdout,
            "stderr": stderr
        }
    
    def run_system_startup_tests(self) -> Dict:
        """Run system startup and shutdown tests."""
        print("\\n" + "="*60)
        print("RUNNING SYSTEM STARTUP/SHUTDOWN TESTS")
        print("="*60)
        
        test_file = "tests/integration/test_system_startup_shutdown.py"
        return self.run_pytest_suite(
            test_file,
            markers=["integration"],
            extra_args=["--tb=short"]
        )
    
    def run_component_interaction_tests(self) -> Dict:
        """Run component interaction tests."""
        print("\\n" + "="*60)
        print("RUNNING COMPONENT INTERACTION TESTS")
        print("="*60)
        
        test_file = "tests/integration/test_component_interactions.py"
        return self.run_pytest_suite(
            test_file,
            markers=["integration"],
            extra_args=["--tb=short"]
        )
    
    def run_hardware_simulation_tests(self) -> Dict:
        """Run hardware simulation tests."""
        print("\\n" + "="*60)
        print("RUNNING HARDWARE SIMULATION TESTS")
        print("="*60)
        
        # Set simulation mode
        env = os.environ.copy()
        env["SIMULATION_MODE"] = "true"
        
        test_file = "tests/simulation/test_hardware_simulation.py"
        return self.run_pytest_suite(
            test_file,
            markers=["simulation"],
            extra_args=["--tb=short"]
        )
    
    def run_safety_integration_tests(self) -> Dict:
        """Run safety system integration tests."""
        print("\\n" + "="*60)
        print("RUNNING SAFETY SYSTEM INTEGRATION TESTS")
        print("="*60)
        
        test_files = [
            "tests/safety/test_autonomous_safety.py",
            "tests/safety/test_safety_error_handling.py",
            "tests/safety/test_safety_system_integration.py"
        ]
        
        all_results = {"success": True, "test_count": 0, "passed": 0, "failed": 0, "skipped": 0, "duration": 0}
        
        for test_file in test_files:
            if Path(test_file).exists():
                result = self.run_pytest_suite(
                    test_file,
                    markers=["safety"],
                    extra_args=["--tb=short"]
                )
                
                # Aggregate results
                all_results["success"] = all_results["success"] and result["success"]
                all_results["test_count"] += result["test_count"]
                all_results["passed"] += result["passed"]
                all_results["failed"] += result["failed"]
                all_results["skipped"] += result["skipped"]
                all_results["duration"] += result["duration"]
        
        return all_results
    
    def run_performance_tests(self) -> Dict:
        """Run performance and benchmark tests."""
        print("\\n" + "="*60)
        print("RUNNING PERFORMANCE TESTS")
        print("="*60)
        
        test_dirs = [
            "tests/performance",
            "tests/benchmarks"
        ]
        
        all_results = {"success": True, "test_count": 0, "passed": 0, "failed": 0, "skipped": 0, "duration": 0}
        
        for test_dir in test_dirs:
            if Path(test_dir).exists():
                result = self.run_pytest_suite(
                    test_dir,
                    markers=["performance"],
                    extra_args=["--tb=short", "--durations=10"]
                )
                
                # Aggregate results
                all_results["success"] = all_results["success"] and result["success"]
                all_results["test_count"] += result["test_count"]
                all_results["passed"] += result["passed"]
                all_results["failed"] += result["failed"]
                all_results["skipped"] += result["skipped"]
                all_results["duration"] += result["duration"]
        
        return all_results
    
    def run_all_integration_tests(self) -> None:
        """Run all integration tests."""
        print("="*80)
        print("COMPREHENSIVE INTEGRATION TEST SUITE")
        print("="*80)
        print(f"Test directory: {self.test_dir.absolute()}")
        print(f"Verbose mode: {self.verbose}")
        print()
        
        # Run test suites
        test_suites = [
            ("System Startup/Shutdown", self.run_system_startup_tests),
            ("Component Interactions", self.run_component_interaction_tests),
            ("Hardware Simulation", self.run_hardware_simulation_tests),
            ("Safety Integration", self.run_safety_integration_tests),
            ("Performance Tests", self.run_performance_tests)
        ]
        
        total_tests = 0
        total_passed = 0
        total_failed = 0
        total_skipped = 0
        total_duration = 0
        failed_suites = []
        
        for suite_name, test_function in test_suites:
            try:
                result = test_function()
                self.results[suite_name] = result
                
                # Aggregate totals
                total_tests += result["test_count"]
                total_passed += result["passed"]
                total_failed += result["failed"]
                total_skipped += result["skipped"]
                total_duration += result["duration"]
                
                if not result["success"]:
                    failed_suites.append(suite_name)
                
                # Print suite summary
                status = "✅ PASS" if result["success"] else "❌ FAIL"
                print(f"\\n{suite_name}: {status}")
                print(f"  Tests: {result['test_count']}, Passed: {result['passed']}, "
                      f"Failed: {result['failed']}, Skipped: {result['skipped']}")
                print(f"  Duration: {result['duration']:.2f}s")
                
                if self.verbose and not result["success"]:
                    print(f"  Error output:\\n{result['stderr']}")
                
            except Exception as e:
                print(f"\\n{suite_name}: ❌ ERROR - {e}")
                failed_suites.append(suite_name)
        
        # Print final summary
        self.print_final_summary(total_tests, total_passed, total_failed, 
                               total_skipped, total_duration, failed_suites)
    
    def print_final_summary(self, total_tests: int, total_passed: int, total_failed: int,
                          total_skipped: int, total_duration: float, failed_suites: List[str]) -> None:
        """Print final test summary."""
        print("\\n" + "="*80)
        print("INTEGRATION TEST SUMMARY")
        print("="*80)
        
        print(f"Total tests run: {total_tests}")
        print(f"Passed: {total_passed}")
        print(f"Failed: {total_failed}")
        print(f"Skipped: {total_skipped}")
        print(f"Total duration: {total_duration:.2f}s")
        
        if failed_suites:
            print(f"\\n❌ Failed test suites: {', '.join(failed_suites)}")
            print("\\nPlease check the detailed output above for specific failures.")
            sys.exit(1)
        else:
            print("\\n✅ All integration tests passed!")
            
            # Calculate coverage if available
            coverage_file = Path("htmlcov/index.html")
            if coverage_file.exists():
                print(f"\\n📊 Coverage report available at: {coverage_file.absolute()}")
    
    def run_specific_test(self, test_path: str, markers: Optional[List[str]] = None) -> None:
        """Run a specific test file or directory."""
        print(f"Running specific test: {test_path}")
        
        if markers:
            print(f"With markers: {', '.join(markers)}")
        
        result = self.run_pytest_suite(test_path, markers)
        
        if result["success"]:
            print(f"\\n✅ Test passed: {result['passed']}/{result['test_count']} tests")
        else:
            print(f"\\n❌ Test failed: {result['failed']}/{result['test_count']} tests failed")
            if self.verbose:
                print(f"Error output:\\n{result['stderr']}")
            sys.exit(1)
    
    def list_available_tests(self) -> None:
        """List all available integration tests."""
        print("Available integration tests:")
        print("="*40)
        
        test_files = [
            "tests/integration/test_system_startup_shutdown.py",
            "tests/integration/test_component_interactions.py", 
            "tests/simulation/test_hardware_simulation.py",
            "tests/safety/test_autonomous_safety.py",
            "tests/safety/test_safety_error_handling.py",
            "tests/safety/test_safety_system_integration.py",
            "tests/performance/",
            "tests/benchmarks/"
        ]
        
        for test_file in test_files:
            path = Path(test_file)
            if path.exists():
                print(f"✅ {test_file}")
            else:
                print(f"❌ {test_file} (not found)")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Run integration tests")
    parser.add_argument(
        "--test-dir",
        default="tests",
        help="Test directory (default: tests)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--specific",
        help="Run specific test file or directory"
    )
    parser.add_argument(
        "--markers", "-m",
        nargs="+",
        help="Pytest markers to filter tests"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available tests"
    )
    parser.add_argument(
        "--suite",
        choices=["startup", "interactions", "simulation", "safety", "performance"],
        help="Run specific test suite"
    )
    
    args = parser.parse_args()
    
    # Verify test directory exists
    if not Path(args.test_dir).exists():
        print(f"Error: Test directory '{args.test_dir}' does not exist.")
        sys.exit(1)
    
    runner = IntegrationTestRunner(args.test_dir, args.verbose)
    
    if args.list:
        runner.list_available_tests()
        return
    
    if args.specific:
        runner.run_specific_test(args.specific, args.markers)
        return
    
    if args.suite:
        suite_functions = {
            "startup": runner.run_system_startup_tests,
            "interactions": runner.run_component_interaction_tests,
            "simulation": runner.run_hardware_simulation_tests,
            "safety": runner.run_safety_integration_tests,
            "performance": runner.run_performance_tests
        }
        
        result = suite_functions[args.suite]()
        if result["success"]:
            print(f"\\n✅ {args.suite} tests passed!")
        else:
            print(f"\\n❌ {args.suite} tests failed!")
            sys.exit(1)
        return
    
    # Run all integration tests
    runner.run_all_integration_tests()


if __name__ == "__main__":
    main()