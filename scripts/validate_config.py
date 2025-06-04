#!/usr/bin/env python3
"""
CLI tool to validate mower configuration files using Pydantic schema.

Usage:
    python scripts/validate_config.py <config_file>
"""

import sys
from pathlib import Path

from mower.utilities.resource_utils import load_config


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/validate_config.py <config_file>")
        sys.exit(2)

    config_path = sys.argv[1]
    if not Path(config_path).exists():
        print(f"Error: Config file '{config_path}' does not exist.")
        sys.exit(2)

    config = load_config(config_path)
    if config is None:
        print((f"Validation failed: Configuration file '{config_path}'" f" is invalid or missing required fields."))
        sys.exit(1)

    print(f"Validation successful: '{config_path}' is a valid mower configuration.")


if __name__ == "__main__":
    main()
