#!/usr/bin/env python3
"""
Comprehensive code quality checker for the autonomous mower project.

This script runs all code quality tools (mypy, flake8, bandit, black, isort)
and provides a unified report of code quality issues.
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional


class CheckResult(NamedTuple):
    """Result of a code quality check."""
    tool: str
    success: bool
    output: str
    error_count: int


class CodeQualityChecker:
    """Runs comprehensive code quality checks."""
    
    def __init__(self, source_dirs: List[str] = None, fix_issues: bool = False):
        """Initialize the code quality checker.
        
        Args:
            source_dirs: List of directories to check. Defaults to ['src', 'tests'].
            fix_issues: Whether to automatically fix issues where possible.
        """
        self.source_dirs = source_dirs or ['src', 'tests']
        self.fix_issues = fix_issues
        self.results: List[CheckResult] = []
        
    def run_command(self, cmd: List[str], tool_name: str) -> CheckResult:
        """Run a command and capture its output.
        
        Args:
            cmd: Command to run as list of strings.
            tool_name: Name of the tool being run.
            
        Returns:
            CheckResult with the outcome of the command.
        """
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            success = result.returncode == 0
            output = result.stdout + result.stderr
            
            # Count errors/warnings in output
            error_count = self._count_issues(output, tool_name)
            
            return CheckResult(
                tool=tool_name,
                success=success,
                output=output,
                error_count=error_count
            )
            
        except subprocess.TimeoutExpired:
            return CheckResult(
                tool=tool_name,
                success=False,
                output=f"Timeout: {tool_name} took longer than 5 minutes",
                error_count=1
            )
        except Exception as e:
            return CheckResult(
                tool=tool_name,
                success=False,
                output=f"Error running {tool_name}: {e}",
                error_count=1
            )
    
    def _count_issues(self, output: str, tool_name: str) -> int:
        """Count issues in tool output.
        
        Args:
            output: Tool output to analyze.
            tool_name: Name of the tool.
            
        Returns:
            Number of issues found.
        """
        if tool_name == "mypy":
            return output.count("error:")
        elif tool_name == "flake8":
            return len([line for line in output.split('\n') if ':' in line and line.strip()])
        elif tool_name == "bandit":
            return output.count(">> Issue:")
        elif tool_name in ["black", "isort"]:
            return output.count("would reformat") + output.count("Fixing")
        else:
            return 0
    
    def run_mypy(self) -> CheckResult:
        """Run mypy type checking."""
        print("Running mypy type checking...")
        cmd = ["python", "-m", "mypy"] + self.source_dirs
        return self.run_command(cmd, "mypy")
    
    def run_flake8(self) -> CheckResult:
        """Run flake8 linting."""
        print("Running flake8 linting...")
        cmd = [
            "python", "-m", "flake8",
            "--max-line-length=120",
            "--extend-ignore=E203,W503,D100,D104"
        ] + self.source_dirs
        return self.run_command(cmd, "flake8")
    
    def run_bandit(self) -> CheckResult:
        """Run bandit security analysis."""
        print("Running bandit security analysis...")
        cmd = [
            "python", "-m", "bandit",
            "-r", "-c", "pyproject.toml"
        ] + self.source_dirs
        return self.run_command(cmd, "bandit")
    
    def run_black(self) -> CheckResult:
        """Run black code formatting."""
        print("Running black code formatting...")
        cmd = [
            "python", "-m", "black",
            "--line-length=120",
            "--check" if not self.fix_issues else "",
            "--diff"
        ] + self.source_dirs
        
        # Remove empty strings from cmd
        cmd = [arg for arg in cmd if arg]
        
        return self.run_command(cmd, "black")
    
    def run_isort(self) -> CheckResult:
        """Run isort import sorting."""
        print("Running isort import sorting...")
        cmd = [
            "python", "-m", "isort",
            "--profile=black",
            "--line-length=120",
            "--check-only" if not self.fix_issues else "",
            "--diff"
        ] + self.source_dirs
        
        # Remove empty strings from cmd
        cmd = [arg for arg in cmd if arg]
        
        return self.run_command(cmd, "isort")
    
    def run_import_analysis(self) -> CheckResult:
        """Run custom import analysis."""
        print("Running import dependency analysis...")
        
        # Check if our custom import analyzer exists
        analyzer_path = Path("scripts/enhanced_import_analyzer.py")
        if analyzer_path.exists():
            cmd = ["python", str(analyzer_path)]
            return self.run_command(cmd, "import_analysis")
        else:
            return CheckResult(
                tool="import_analysis",
                success=True,
                output="Import analyzer not found, skipping...",
                error_count=0
            )
    
    def run_all_checks(self) -> None:
        """Run all code quality checks."""
        print("=" * 80)
        print("RUNNING COMPREHENSIVE CODE QUALITY CHECKS")
        print("=" * 80)
        print(f"Checking directories: {', '.join(self.source_dirs)}")
        print(f"Auto-fix mode: {'ON' if self.fix_issues else 'OFF'}")
        print()
        
        # Run all checks
        self.results = [
            self.run_mypy(),
            self.run_flake8(),
            self.run_bandit(),
            self.run_black(),
            self.run_isort(),
            self.run_import_analysis()
        ]
        
        self.print_summary()
    
    def print_summary(self) -> None:
        """Print a summary of all check results."""
        print("\n" + "=" * 80)
        print("CODE QUALITY SUMMARY")
        print("=" * 80)
        
        total_issues = 0
        failed_tools = []
        
        for result in self.results:
            status = "✓ PASS" if result.success else "✗ FAIL"
            issue_text = f"({result.error_count} issues)" if result.error_count > 0 else ""
            
            print(f"{result.tool:20} {status:10} {issue_text}")
            
            total_issues += result.error_count
            if not result.success:
                failed_tools.append(result.tool)
        
        print("-" * 80)
        print(f"Total issues found: {total_issues}")
        
        if failed_tools:
            print(f"Failed tools: {', '.join(failed_tools)}")
        
        print("\n" + "=" * 80)
        print("DETAILED RESULTS")
        print("=" * 80)
        
        for result in self.results:
            if not result.success or result.error_count > 0:
                print(f"\n{result.tool.upper()} OUTPUT:")
                print("-" * 40)
                print(result.output)
        
        # Exit with error code if any checks failed
        if failed_tools or total_issues > 0:
            print(f"\n❌ Code quality checks failed. Please fix the issues above.")
            if not self.fix_issues:
                print("💡 Run with --fix to automatically fix formatting issues.")
            sys.exit(1)
        else:
            print("\n✅ All code quality checks passed!")


def main() -> None:
    """Main function to run code quality checks."""
    parser = argparse.ArgumentParser(description="Run comprehensive code quality checks")
    parser.add_argument(
        "--dirs",
        nargs="+",
        default=["src", "tests"],
        help="Directories to check (default: src tests)"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Automatically fix issues where possible"
    )
    parser.add_argument(
        "--tools",
        nargs="+",
        choices=["mypy", "flake8", "bandit", "black", "isort", "imports"],
        help="Specific tools to run (default: all)"
    )
    
    args = parser.parse_args()
    
    # Verify directories exist
    for directory in args.dirs:
        if not Path(directory).exists():
            print(f"Error: Directory '{directory}' does not exist.")
            sys.exit(1)
    
    checker = CodeQualityChecker(args.dirs, args.fix)
    
    if args.tools:
        # Run specific tools
        print(f"Running specific tools: {', '.join(args.tools)}")
        results = []
        
        if "mypy" in args.tools:
            results.append(checker.run_mypy())
        if "flake8" in args.tools:
            results.append(checker.run_flake8())
        if "bandit" in args.tools:
            results.append(checker.run_bandit())
        if "black" in args.tools:
            results.append(checker.run_black())
        if "isort" in args.tools:
            results.append(checker.run_isort())
        if "imports" in args.tools:
            results.append(checker.run_import_analysis())
        
        checker.results = results
        checker.print_summary()
    else:
        # Run all checks
        checker.run_all_checks()


if __name__ == "__main__":
    main()