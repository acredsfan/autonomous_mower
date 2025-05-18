"""
Permission check utility for the autonomous mower project.

- Verifies access to critical directories (models/, logs/, config/)
- Checks for required hardware group memberships (gpio, i2c)
- Logs actionable error messages with suggestions for resolution

Author: Autonomous Mower Project
"""

import os
import grp
import getpass
from typing import List, Optional
import sys

from .logger_config import LoggerConfigInfo

CRITICAL_DIRS = [
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "../../../models")),
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "../../../logs")),
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "../../../config")),
]

REQUIRED_GROUPS = ["gpio", "i2c"]

logger = LoggerConfigInfo.get_logger("permission_check")


def check_directory_permissions(
        directories: Optional[List[str]] = None) -> List[str]:
    """
    Check read/write access to critical directories.
    Returns a list of error messages for directories with insufficient permissions.
    """
    if directories is None:
        directories = CRITICAL_DIRS

    errors = []
    for d in directories:
        if not os.path.exists(d):
            errors.append(
                f"Directory '{d}' does not exist. "
                f"Please create it with: mkdir -p '{d}'"
            )
            continue
        if not os.access(d, os.R_OK):
            errors.append(
                f"Read access denied for '{d}'. Try: sudo chmod a+r '{d}'"
            )
        if not os.access(d, os.W_OK):
            errors.append(
                f"Write access denied for '{d}'. Try: sudo chmod a+rw '{d}'"
            )
    return errors


def check_group_membership(groups: Optional[List[str]] = None) -> List[str]:
    """
    Check if the current user is a member of the required hardware groups.
    Returns a list of error messages for missing group memberships.
    """
    if groups is None:
        groups = REQUIRED_GROUPS

    errors = []
    user = getpass.getuser()
    if not sys.platform.startswith("linux"):
        logger.warning(
            "Group membership checks are only supported on Linux. "
            "Skipping hardware group checks."
        )
        return []
    try:
        user_groups = [g.gr_name for g in grp.getgrall() if user in g.gr_mem]
        # Also check primary group
        user_gid = os.getgid()
        user_groups.append(grp.getgrgid(user_gid).gr_name)
    except Exception as e:
        logger.error(f"Failed to get group membership: {e}")
        return [f"Could not determine group membership for user '{user}'."]

    for group in groups:
        if group not in user_groups:
            errors.append(
                f"User '{user}' is not in the '{group}' group. "
                f"Add with: sudo usermod -aG {group} {user} (then log out and back in)"
            )
    return errors


def run_permission_checks() -> bool:
    """
    Run all permission checks and log actionable errors.
    Returns True if all checks pass, False otherwise.
    """
    logger.info(
        "Running permission checks for critical directories and hardware groups...")
    dir_errors = check_directory_permissions()
    group_errors = check_group_membership()

    all_errors = dir_errors + group_errors

    if all_errors:
        for err in all_errors:
            logger.error(f"PERMISSION ERROR: {err}")
        logger.error(
            "Permission check failed. "
            "Please resolve the above issues before proceeding."
        )
        return False

    logger.info("All permission checks passed.")
    return True
