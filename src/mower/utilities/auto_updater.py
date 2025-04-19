#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Automatic update utility for the autonomous mower.

This module provides functionality to automatically check for updates to the
mower software, download them, and apply them. It can be run as a standalone
script or integrated into the mower's main controller to periodically check
for updates.

Key features:
- Check for updates from the Git repository
- Download and apply updates automatically
- Restart services after updates
- Configurable update frequency and sources
- Rollback capability if updates fail
- Notification of update status

Example usage:
    # Check for updates and apply them if available
    python -m mower.utilities.auto_updater

    # Check for updates but don't apply them (dry run)
    python -m mower.utilities.auto_updater --dry-run

    # Check for updates from a specific branch
    python -m mower.utilities.auto_updater --branch improvements
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any

# Import logger
from mower.utilities.logger_config import LoggerConfigInfo as LoggerConfig

# Configure logging
logger = LoggerConfig.get_logger(__name__)

# Constants
DEFAULT_REPO_URL = "https://github.com/yourusername/autonomous_mower.git"
DEFAULT_BRANCH = "main"
UPDATE_LOCK_FILE = "/tmp/mower_update.lock"
BACKUP_DIR = "/var/backups/autonomous-mower"
CONFIG_BACKUP_DIR = "/var/backups/autonomous-mower/config"


class AutoUpdater:
    """
    Automatic updater for the autonomous mower software.

    This class provides methods to check for updates, download them, and apply
    them to the mower software. It includes safety checks and rollback
    capabilities to ensure the mower remains operational after updates.
    """

    def __init__(
        self,
        repo_url: str = DEFAULT_REPO_URL,
        branch: str = DEFAULT_BRANCH,
        repo_path: Optional[str] = None,
    ):
        """
        Initialize the auto updater.

        Args:
            repo_url: URL of the Git repository.
            branch: Branch to check for updates.
            repo_path: Path to the local repository. If None, the current
                directory is used.
        """
        self.repo_url = repo_url
        self.branch = branch
        self.repo_path = repo_path or os.getcwd()
        self.update_in_progress = False
        self.backup_created = False
        self.service_was_running = False

    def check_for_updates(self) -> Tuple[bool, str]:
        """
        Check if updates are available.

        Returns:
            Tuple[bool, str]: (updates_available, message)
                updates_available: True if updates are available, False otherwise.
                message: Information about the updates or error message.
        """
        try:
            # Ensure we're in the repository directory
            os.chdir(self.repo_path)

            # Fetch the latest changes
            logger.info(f"Fetching latest changes from {self.repo_url}, branch {self.branch}")
            subprocess.run(
                ["git", "fetch", "origin", self.branch],
                check=True,
                capture_output=True,
                text=True,
            )

            # Get the current commit hash
            current_commit = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()

            # Get the latest commit hash from the remote branch
            remote_commit = subprocess.run(
                ["git", "rev-parse", f"origin/{self.branch}"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()

            # Check if we're behind the remote
            if current_commit != remote_commit:
                # Get the number of commits behind
                commits_behind = subprocess.run(
                    ["git", "rev-list", "--count", f"HEAD..origin/{self.branch}"],
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.strip()

                # Get the commit messages
                commit_messages = subprocess.run(
                    ["git", "log", "--pretty=format:%h %s", f"HEAD..origin/{self.branch}"],
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.strip()

                message = (
                    f"Updates available: {commits_behind} commits behind origin/{self.branch}\n"
                    f"Commits:\n{commit_messages}"
                )
                return True, message
            else:
                return False, "No updates available. Already at the latest version."
        except subprocess.CalledProcessError as e:
            error_msg = f"Error checking for updates: {e.stderr}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Error checking for updates: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def create_backup(self) -> bool:
        """
        Create a backup of the current installation.

        Returns:
            bool: True if backup was successful, False otherwise.
        """
        try:
            # Create backup directories if they don't exist
            os.makedirs(BACKUP_DIR, exist_ok=True)
            os.makedirs(CONFIG_BACKUP_DIR, exist_ok=True)

            # Create a timestamp for the backup
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"mower_backup_{timestamp}"
            backup_path = os.path.join(BACKUP_DIR, backup_name)

            # Create a temporary directory for the backup
            os.makedirs(backup_path, exist_ok=True)

            # Backup the repository (excluding .git directory)
            logger.info(f"Creating backup of repository to {backup_path}")
            for item in os.listdir(self.repo_path):
                if item != ".git" and item != "venv" and item != "__pycache__":
                    src = os.path.join(self.repo_path, item)
                    dst = os.path.join(backup_path, item)
                    if os.path.isdir(src):
                        shutil.copytree(src, dst, symlinks=True)
                    else:
                        shutil.copy2(src, dst)

            # Backup configuration files
            config_files = [
                "/etc/systemd/system/autonomous-mower.service",
                os.path.join(self.repo_path, ".env"),
            ]
            for config_file in config_files:
                if os.path.exists(config_file):
                    dst = os.path.join(CONFIG_BACKUP_DIR, os.path.basename(config_file) + f".{timestamp}")
                    shutil.copy2(config_file, dst)
                    logger.info(f"Backed up {config_file} to {dst}")

            self.backup_created = True
            self.backup_path = backup_path
            self.backup_timestamp = timestamp
            return True
        except Exception as e:
            logger.error(f"Error creating backup: {str(e)}")
            return False

    def restore_from_backup(self) -> bool:
        """
        Restore the system from the most recent backup.

        Returns:
            bool: True if restore was successful, False otherwise.
        """
        if not self.backup_created:
            logger.error("No backup available to restore from")
            return False

        try:
            logger.info(f"Restoring from backup {self.backup_path}")

            # Restore the repository files
            for item in os.listdir(self.backup_path):
                src = os.path.join(self.backup_path, item)
                dst = os.path.join(self.repo_path, item)
                if os.path.isdir(src):
                    if os.path.exists(dst):
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst, symlinks=True)
                else:
                    if os.path.exists(dst):
                        os.remove(dst)
                    shutil.copy2(src, dst)

            # Restore configuration files
            config_files = [
                "/etc/systemd/system/autonomous-mower.service",
                os.path.join(self.repo_path, ".env"),
            ]
            for config_file in config_files:
                backup_file = os.path.join(
                    CONFIG_BACKUP_DIR,
                    os.path.basename(config_file) + f".{self.backup_timestamp}"
                )
                if os.path.exists(backup_file):
                    shutil.copy2(backup_file, config_file)
                    logger.info(f"Restored {config_file} from {backup_file}")

            logger.info("Restore from backup completed successfully")
            return True
        except Exception as e:
            logger.error(f"Error restoring from backup: {str(e)}")
            return False

    def stop_services(self) -> bool:
        """
        Stop the mower services before updating.

        Returns:
            bool: True if services were stopped successfully, False otherwise.
        """
        try:
            # Check if the service is running
            result = subprocess.run(
                ["systemctl", "is-active", "autonomous-mower.service"],
                capture_output=True,
                text=True,
            )
            self.service_was_running = result.stdout.strip() == "active"

            if self.service_was_running:
                logger.info("Stopping autonomous-mower service")
                subprocess.run(
                    ["sudo", "systemctl", "stop", "autonomous-mower.service"],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                # Wait for the service to stop
                time.sleep(2)
                return True
            else:
                logger.info("Service was not running, no need to stop")
                return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Error stopping services: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Error stopping services: {str(e)}")
            return False

    def start_services(self) -> bool:
        """
        Start the mower services after updating.

        Returns:
            bool: True if services were started successfully, False otherwise.
        """
        try:
            if self.service_was_running:
                logger.info("Starting autonomous-mower service")
                subprocess.run(
                    ["sudo", "systemctl", "daemon-reload"],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                subprocess.run(
                    ["sudo", "systemctl", "start", "autonomous-mower.service"],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                # Wait for the service to start
                time.sleep(2)
                # Check if the service started successfully
                result = subprocess.run(
                    ["systemctl", "is-active", "autonomous-mower.service"],
                    capture_output=True,
                    text=True,
                )
                if result.stdout.strip() != "active":
                    logger.error("Service failed to start after update")
                    return False
                return True
            else:
                logger.info("Service was not running before update, not starting")
                return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Error starting services: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Error starting services: {str(e)}")
            return False

    def apply_updates(self) -> Tuple[bool, str]:
        """
        Apply updates from the remote repository.

        Returns:
            Tuple[bool, str]: (success, message)
                success: True if updates were applied successfully, False otherwise.
                message: Information about the update process or error message.
        """
        if self.update_in_progress:
            return False, "Update already in progress"

        # Create a lock file to prevent multiple updates
        try:
            with open(UPDATE_LOCK_FILE, "x") as f:
                f.write(str(os.getpid()))
        except FileExistsError:
            # Check if the process that created the lock file is still running
            try:
                with open(UPDATE_LOCK_FILE, "r") as f:
                    pid = int(f.read().strip())
                try:
                    os.kill(pid, 0)  # This will raise an exception if the process is not running
                    return False, f"Update already in progress (PID: {pid})"
                except OSError:
                    # Process is not running, remove the lock file
                    os.remove(UPDATE_LOCK_FILE)
                    # Try to create the lock file again
                    with open(UPDATE_LOCK_FILE, "x") as f:
                        f.write(str(os.getpid()))
            except (ValueError, OSError):
                # Invalid PID or other error, remove the lock file
                os.remove(UPDATE_LOCK_FILE)
                # Try to create the lock file again
                with open(UPDATE_LOCK_FILE, "x") as f:
                    f.write(str(os.getpid()))

        self.update_in_progress = True
        try:
            # Check if updates are available
            updates_available, message = self.check_for_updates()
            if not updates_available:
                self.update_in_progress = False
                os.remove(UPDATE_LOCK_FILE)
                return False, message

            # Create a backup before updating
            if not self.create_backup():
                self.update_in_progress = False
                os.remove(UPDATE_LOCK_FILE)
                return False, "Failed to create backup, aborting update"

            # Stop services
            if not self.stop_services():
                self.update_in_progress = False
                os.remove(UPDATE_LOCK_FILE)
                return False, "Failed to stop services, aborting update"

            # Apply updates
            try:
                logger.info(f"Applying updates from origin/{self.branch}")
                # Ensure we're in the repository directory
                os.chdir(self.repo_path)

                # Pull the latest changes
                subprocess.run(
                    ["git", "pull", "origin", self.branch],
                    check=True,
                    capture_output=True,
                    text=True,
                )

                # Install any new dependencies
                logger.info("Installing dependencies")
                subprocess.run(
                    ["sudo", "python3", "-m", "pip", "install", "--break-system-packages", "--no-cache-dir", "-e", "."],
                    check=True,
                    capture_output=True,
                    text=True,
                )

                # Start services
                if not self.start_services():
                    logger.error("Failed to start services after update, rolling back")
                    self.restore_from_backup()
                    self.start_services()  # Try to start services from backup
                    self.update_in_progress = False
                    os.remove(UPDATE_LOCK_FILE)
                    return False, "Failed to start services after update, rolled back to previous version"

                # Update successful
                logger.info("Update completed successfully")
                self.update_in_progress = False
                os.remove(UPDATE_LOCK_FILE)
                return True, "Update completed successfully"
            except subprocess.CalledProcessError as e:
                logger.error(f"Error applying updates: {e.stderr}")
                # Roll back to the backup
                logger.info("Rolling back to previous version")
                self.restore_from_backup()
                self.start_services()  # Try to start services from backup
                self.update_in_progress = False
                os.remove(UPDATE_LOCK_FILE)
                return False, f"Error applying updates: {e.stderr}. Rolled back to previous version."
            except Exception as e:
                logger.error(f"Error applying updates: {str(e)}")
                # Roll back to the backup
                logger.info("Rolling back to previous version")
                self.restore_from_backup()
                self.start_services()  # Try to start services from backup
                self.update_in_progress = False
                os.remove(UPDATE_LOCK_FILE)
                return False, f"Error applying updates: {str(e)}. Rolled back to previous version."
        except Exception as e:
            logger.error(f"Error in update process: {str(e)}")
            self.update_in_progress = False
            if os.path.exists(UPDATE_LOCK_FILE):
                os.remove(UPDATE_LOCK_FILE)
            return False, f"Error in update process: {str(e)}"


def main():
    """
    Run the auto updater from the command line.

    This function parses command-line arguments and runs the auto updater
    accordingly.

    Command-line options:
        --repo-url: URL of the Git repository (default: DEFAULT_REPO_URL)
        --branch: Branch to check for updates (default: main)
        --repo-path: Path to the local repository (default: current directory)
        --dry-run: Check for updates but don't apply them
        --force: Force update even if no updates are available

    Returns:
        System exit code: 0 on success, non-zero on error
    """
    parser = argparse.ArgumentParser(
        description="Automatic updater for the autonomous mower"
    )
    parser.add_argument(
        "--repo-url",
        type=str,
        default=DEFAULT_REPO_URL,
        help=f"URL of the Git repository (default: {DEFAULT_REPO_URL})",
    )
    parser.add_argument(
        "--branch",
        type=str,
        default=DEFAULT_BRANCH,
        help=f"Branch to check for updates (default: {DEFAULT_BRANCH})",
    )
    parser.add_argument(
        "--repo-path",
        type=str,
        default=None,
        help="Path to the local repository (default: current directory)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check for updates but don't apply them",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force update even if no updates are available",
    )

    args = parser.parse_args()

    # Initialize the auto updater
    updater = AutoUpdater(
        repo_url=args.repo_url,
        branch=args.branch,
        repo_path=args.repo_path,
    )

    # Check for updates
    updates_available, message = updater.check_for_updates()
    print(message)

    # Apply updates if available and not in dry-run mode
    if (updates_available or args.force) and not args.dry_run:
        print("Applying updates...")
        success, message = updater.apply_updates()
        print(message)
        return 0 if success else 1
    else:
        return 0


if __name__ == "__main__":
    sys.exit(main())