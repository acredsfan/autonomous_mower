#!/usr/bin/env python3
"""
Script to run comprehensive system validation tests.

This script executes the complete system validation test suite and generates
a detailed report of the results. It covers all requirements for task 12.1:
- System startup in both hardware and simulation modes
- Major functionality verification
- Error handling and recovery mechanisms
- Performance metrics validation

Usage:
    python scripts/run_comprehensive_system_tests.py [--verbose] [--output-file FILENAME]
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import the validation suite
sys.path.insert(0, str(Path(__file__).parent.parent))
from tests.system_validation.test_comprehensive_system import SystemValidationSuite


def generate_detailed_report(results: Dict[str, Any], output_file: str = None) -> str:
    """Generate a detailed test report."""
    
    report_lines = []
    
    # Header
    report_lines.append("=" * 100)
    report_lines.append("AUTONOMOUS MOWER SYSTEM - COMPREHENSIVE VALIDATION REPORT")
    report_lines.append("=" * 100)
    report_lines.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"Total Validation Time: {results['validation_time']:.2f} seconds")
    report_lines.append("")
    
    # Executive Summary
    report_lines.append("EXECUTIVE SUMMARY")
    report_lines.append("-" * 50)
    overall_status = "PASS" if results['overall_success'] else "FAIL"
    report_lines.append(f"Overall Status: {overall_status}")
    report_lines.append(f"Success Rate: {results['summary']['success_rate']:.1%}")
    report_lines.append(f"Test Suites Passed: {results['summary']['passed_suites']}/{results['summary']['total_suites']}")
    report_lines.append("")
    
    # Requirements Coverage
    report_lines.append("REQUIREMENTS COVERAGE")
    report_lines.append("-" * 50)
    requirements_coverage = {
        "1.3 - System startup without crashes": "Simulation Mode Startup" in results['suite_results'] and results['suite_results']["Simulation Mode Startup"]["success"],
        "4.4 - Simulation mode functionality": "Major Functionality" in results['suite_results'] and results['suite_results']["Major Functionality"]["success"],
        "7.3 - Hardware abstraction layer": "Hardware Mode Startup" in results['suite_results'] and results['suite_results']["Hardware Mode Startup"]["success"]
    }
    
    for req, status in requirements_coverage.items():
        status_text = "PASS" if status else "FAIL"
        report_lines.append(f"  {req}: {status_text}")
    report_lines.append("")
    
    # Detailed Test Results
    report_lines.append("DETAILED TEST RESULTS")
    report_lines.append("-" * 50)
    
    for suite_name, suite_result in results['suite_results'].items():
        status = "PASS" if suite_result['success'] else "FAIL"
        report_lines.append(f"\n{suite_name}: {status}")
        report_lines.append("-" * len(f"{suite_name}: {status}"))
        
        # Show errors if any
        if suite_result.get('errors'):
            report_lines.append("  Errors:")
            for error in suite_result['errors']:
                report_lines.append(f"    - {error}")
        
        # Show details
        if suite_result.get('details'):
            details = suite_result['details']
            
            # Common details
            if 'initialization_time' in details:
                report_lines.append(f"  Initialization Time: {details['initialization_time']:.2f}s")
            if 'total_time' in details:
                report_lines.append(f"  Total Time: {details['total_time']:.2f}s")
            if 'success_rate' in details:
                report_lines.append(f"  Success Rate: {details['success_rate']:.1%}")
            
            # Suite-specific details
            if suite_name == "Simulation Mode Startup":
                if 'critical_components' in details:
                    report_lines.append("  Critical Components:")
                    for comp, available in details['critical_components'].items():
                        status_text = "Available" if available else "Missing"
                        report_lines.append(f"    - {comp}: {status_text}")
                
                if 'sensor_data_types' in details:
                    report_lines.append(f"  Sensor Data Types: {', '.join(details['sensor_data_types'])}")
            
            elif suite_name == "Hardware Mode Startup":
                if 'hardware_components' in details:
                    report_lines.append("  Hardware Components:")
                    for comp, available in details['hardware_components'].items():
                        status_text = "Available" if available else "Missing"
                        report_lines.append(f"    - {comp}: {status_text}")
            
            elif suite_name == "Major Functionality":
                if 'functionality_tests' in details:
                    report_lines.append("  Functionality Tests:")
                    for test_name, test_result in details['functionality_tests'].items():
                        test_status = "PASS" if test_result.get('success', False) else "FAIL"
                        report_lines.append(f"    - {test_name}: {test_status}")
                        if 'error' in test_result:
                            report_lines.append(f"      Error: {test_result['error']}")
            
            elif suite_name == "Error Handling & Recovery":
                if 'error_tests' in details:
                    report_lines.append("  Error Handling Tests:")
                    for test_name, test_result in details['error_tests'].items():
                        test_status = "PASS" if test_result.get('success', False) else "FAIL"
                        report_lines.append(f"    - {test_name}: {test_status}")
                        if 'error' in test_result:
                            report_lines.append(f"      Error: {test_result['error']}")
            
            elif suite_name == "Performance Metrics":
                if 'performance_metrics' in details:
                    report_lines.append("  Performance Metrics:")
                    metrics = details['performance_metrics']
                    report_lines.append(f"    - Initialization Time: {metrics.get('initialization_time', 0):.2f}s")
                    report_lines.append(f"    - Memory Usage: {metrics.get('memory_usage_mb', 0):.1f} MB")
                    report_lines.append(f"    - Avg Sensor Collection: {metrics.get('avg_sensor_collection_time', 0):.3f}s")
                    report_lines.append(f"    - Max Sensor Collection: {metrics.get('max_sensor_collection_time', 0):.3f}s")
                
                if 'performance_checks' in details:
                    report_lines.append("  Performance Checks:")
                    for check_name, passed in details['performance_checks'].items():
                        check_status = "PASS" if passed else "FAIL"
                        report_lines.append(f"    - {check_name}: {check_status}")
    
    # Recommendations
    report_lines.append("\n\nRECOMMENDATIONS")
    report_lines.append("-" * 50)
    
    if results['overall_success']:
        report_lines.append("✓ System validation completed successfully")
        report_lines.append("✓ All critical requirements are met")
        report_lines.append("✓ System is ready for deployment")
    else:
        report_lines.append("⚠ System validation failed - review errors above")
        report_lines.append("⚠ Address failing test suites before deployment")
        
        # Specific recommendations based on failures
        failed_suites = [name for name, result in results['suite_results'].items() if not result['success']]
        if "Simulation Mode Startup" in failed_suites:
            report_lines.append("⚠ Fix simulation mode startup issues")
        if "Hardware Mode Startup" in failed_suites:
            report_lines.append("⚠ Review hardware abstraction layer")
        if "Major Functionality" in failed_suites:
            report_lines.append("⚠ Address core functionality failures")
        if "Error Handling & Recovery" in failed_suites:
            report_lines.append("⚠ Improve error handling mechanisms")
        if "Performance Metrics" in failed_suites:
            report_lines.append("⚠ Optimize system performance")
    
    report_lines.append("")
    report_lines.append("=" * 100)
    
    report_text = "\n".join(report_lines)
    
    # Save to file if requested
    if output_file:
        try:
            with open(output_file, 'w') as f:
                f.write(report_text)
            print(f"Detailed report saved to: {output_file}")
        except Exception as e:
            print(f"Failed to save report to {output_file}: {e}")
    
    return report_text


def main():
    """Main function to run comprehensive system tests."""
    parser = argparse.ArgumentParser(description="Run comprehensive system validation tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--output-file", "-o", help="Save detailed report to file")
    parser.add_argument("--json-output", help="Save results as JSON to file")
    
    args = parser.parse_args()
    
    print("Starting Autonomous Mower System Comprehensive Validation...")
    print("=" * 80)
    
    # Create and run validation suite
    validator = SystemValidationSuite()
    
    try:
        # Run comprehensive validation
        results = validator.run_comprehensive_validation()
        
        # Generate and display report
        if args.verbose:
            detailed_report = generate_detailed_report(results, args.output_file)
            print(detailed_report)
        else:
            # Show summary
            print(f"\nValidation Results:")
            print(f"Overall Success: {'PASS' if results['overall_success'] else 'FAIL'}")
            print(f"Success Rate: {results['summary']['success_rate']:.1%}")
            print(f"Validation Time: {results['validation_time']:.2f} seconds")
            
            print(f"\nSuite Results:")
            for suite_name, suite_result in results['suite_results'].items():
                status = "PASS" if suite_result['success'] else "FAIL"
                print(f"  {suite_name}: {status}")
                if not suite_result['success'] and suite_result.get('errors'):
                    for error in suite_result['errors'][:2]:  # Show first 2 errors
                        print(f"    Error: {error}")
                    if len(suite_result['errors']) > 2:
                        print(f"    ... and {len(suite_result['errors']) - 2} more errors")
            
            if args.output_file:
                generate_detailed_report(results, args.output_file)
        
        # Save JSON results if requested
        if args.json_output:
            try:
                with open(args.json_output, 'w') as f:
                    json.dump(results, f, indent=2, default=str)
                print(f"JSON results saved to: {args.json_output}")
            except Exception as e:
                print(f"Failed to save JSON results: {e}")
        
        # Return appropriate exit code
        return 0 if results['overall_success'] else 1
        
    except Exception as e:
        print(f"System validation failed with error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())