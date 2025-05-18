#!/usr/bin/env python3
"""
Network diagnostics CLI for the autonomous mower project.

Checks internet connectivity and access to required endpoints.
Prints actionable results and exits with status code 0 (success) or 1 (failure).

Usage:
    python3 scripts/network_diagnostics.py
"""

import sys

from mower.utilities.network_diagnostics import run_preflight_check


def main():
    print("Running network diagnostics...")
    result = run_preflight_check()
    if result:
        print(
            "Network diagnostics PASSED: "
            "All required network resources are reachable."
        )
        sys.exit(0)
    else:
        print(
            "Network diagnostics FAILED: "
            "Please resolve network issues before setup or downloads."
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
