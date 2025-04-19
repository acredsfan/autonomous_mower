#!/usr/bin/env python3
"""
Setup script for pre-commit hooks.

This script installs pre-commit and sets up the hooks for the autonomous_mower project.
It checks if pre-commit is installed, installs it if needed, and then installs the hooks.
"""

import os
import subprocess
import sys
from pathlib import Path


def check_pre_commit_installed():
    """Check if pre-commit is installed."""
    try:
        subprocess.run(
            ["pre-commit", "--version"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def install_pre_commit():
    """Install pre-commit using pip."""
    print("Installing pre-commit...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "pre-commit"],
            check=True,
        )
        print("pre-commit installed successfully.")
        return True
    except subprocess.SubprocessError as e:
        print(f"Error installing pre-commit: {e}")
        return False


def install_hooks():
    """Install pre-commit hooks."""
    print("Installing pre-commit hooks...")
    try:
        subprocess.run(
            ["pre-commit", "install"],
            check=True,
        )
        print("pre-commit hooks installed successfully.")
        return True
    except subprocess.SubprocessError as e:
        print(f"Error installing pre-commit hooks: {e}")
        return False


def install_dev_dependencies():
    """Install development dependencies."""
    print("Installing development dependencies...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", ".[dev]"],
            check=True,
        )
        print("Development dependencies installed successfully.")
        return True
    except subprocess.SubprocessError as e:
        print(f"Error installing development dependencies: {e}")
        return False


def main():
    """Main function to set up pre-commit hooks."""
    # Change to the repository root directory
    repo_root = Path(__file__).parent.parent
    os.chdir(repo_root)

    print("Setting up pre-commit hooks for autonomous_mower...")

    # Check if pre-commit is installed
    if not check_pre_commit_installed():
        print("pre-commit is not installed.")
        if not install_pre_commit():
            print("Failed to install pre-commit. Please install it manually:")
            print("    pip install pre-commit")
            return 1

    # Install development dependencies
    if not install_dev_dependencies():
        print("Failed to install development dependencies.")
        print("You can install them manually with:")
        print("    pip install -e .[dev]")

    # Install hooks
    if not install_hooks():
        print("Failed to install pre-commit hooks.")
        print("You can install them manually with:")
        print("    pre-commit install")
        return 1

    print("\nPre-commit hooks setup completed successfully!")
    print("\nThe following hooks are now installed:")
    print("  - trailing-whitespace: Removes trailing whitespace")
    print("  - end-of-file-fixer: Ensures files end with a newline")
    print("  - check-yaml/json/toml: Validates YAML/JSON/TOML files")
    print("  - black: Formats Python code")
    print("  - isort: Sorts imports")
    print("  - flake8: Lints Python code")
    print("  - mypy: Type checks Python code")
    print("  - bandit: Checks for security issues")
    print("\nYou can run the hooks manually with:")
    print("    pre-commit run --all-files")
    print("\nThe hooks will also run automatically on each commit.")
    return 0


if __name__ == "__main__":
    sys.exit(main())