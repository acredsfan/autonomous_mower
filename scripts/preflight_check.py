#!/usr/bin/env python3
import sys

from src.mower.utilities.permission_check import run_permission_checks

"""
Pre-flight permission check script for the autonomous mower project.

- Verifies access to critical directories and hardware groups before
  setup or deployment.
- Logs actionable errors and exits with nonzero status if any permission
  issues are found.

Usage:
    python scripts/preflight_check.py
"""


def main():
    """Run permission checks before installation."""
    print("Running pre-flight permission checks...")
    success = run_permission_checks()
    if not success:
        print(
            "\n[ERROR] Permission checks failed. "
            "Please resolve the above issues before continuing setup or deployment."
        )
        sys.exit(1)
    print("[OK] All permission checks passed.")


if __name__ == "__main__":
    main()
