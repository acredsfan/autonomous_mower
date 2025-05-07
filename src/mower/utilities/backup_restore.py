#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backup and restore utility for the autonomous mower.

This module provides functionality to create backups of the mower's configuration,
data, and logs, and restore from those backups if needed. It helps users recover
from system failures or configuration errors.

Key features:
- Create full or selective backups (config, data, logs)
- Restore from backups
- List available backups
- Scheduled automatic backups
- Backup rotation and cleanup
- Backup verification

Example usage:
    # Create a full backup
    python -m mower.utilities.backup_restore --backup full

    # Restore from a specific backup
    python -m mower.utilities.backup_restore --restore <backup_id>

    # List available backups
    python -m mower.utilities.backup_restore --list
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tarfile
import time
from datetime import datetime
import tempfile
# from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Import logger
from mower.utilities.logger_config import LoggerConfigInfo as LoggerConfig

# Configure logging
logger = LoggerConfig.get_logger(__name__)

# Constants
BACKUP_DIR = "/var/backups/autonomous-mower"
CONFIG_DIR = "/home/pi/autonomous_mower/config"
DATA_DIR = "/home/pi/autonomous_mower/data"
LOG_DIR = "/var/log/autonomous-mower"
BACKUP_MANIFEST_FILE = "backup_manifest.json"
MAX_BACKUPS = 10  # Maximum number of backups to keep


class BackupRestore:
    """
    Backup and restore utility for the autonomous mower.

    This class provides methods to create backups of the mower's configuration,
    data, and logs, and restore from those backups if needed.
    """

    def __init__(self, backup_dir: str = BACKUP_DIR):
        """
        Initialize the backup and restore utility.

        Args:
            backup_dir: Directory where backups will be stored.
        """
        self.backup_dir = backup_dir
        os.makedirs(self.backup_dir, exist_ok=True)
        self.manifest_file = os.path.join(
            self.backup_dir, BACKUP_MANIFEST_FILE
        )
        self._load_manifest()

    def _load_manifest(self) -> None:
        """Load the backup manifest file."""
        if os.path.exists(self.manifest_file):
            try:
                with open(self.manifest_file, "r") as f:
                    self.manifest = json.load(f)
            except json.JSONDecodeError:
                logger.error(
                    f"Error parsing manifest file: {self.manifest_file}"
                )
                self.manifest = {"backups": []}
        else:
            self.manifest = {"backups": []}

    def _save_manifest(self) -> None:
        """Save the backup manifest file."""
        try:
            with open(self.manifest_file, "w") as f:
                json.dump(self.manifest, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving manifest file: {e}")

    def _generate_backup_id(self) -> str:
        """
        Generate a unique backup ID.

        Returns:
            str: Unique backup ID based on timestamp.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"backup_{timestamp}"

    def _create_backup_dir(self, backup_id: str) -> str:
        """
        Create a directory for the backup.

        Args:
            backup_id: Unique backup ID.

        Returns:
            str: Path to the backup directory.
        """
        backup_path = os.path.join(self.backup_dir, backup_id)
        os.makedirs(backup_path, exist_ok=True)
        return backup_path

    def _create_tarball(
        self, source_dir: str, target_file: str, compress: bool = True
    ) -> bool:
        """
        Create a tarball of a directory.

        Args:
            source_dir: Directory to archive.
            target_file: Path to the output tarball.
            compress: Whether to compress the tarball.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            mode = "w:gz" if compress else "w"
            with tarfile.open(target_file, mode) as tar:
                tar.add(source_dir, arcname=os.path.basename(source_dir))
            return True
        except Exception as e:
            logger.error(f"Error creating tarball: {e}")
            return False

    def _extract_tarball(self, source_file: str, target_dir: str) -> bool:
        """
        Extract a tarball to a directory.

        Args:
            source_file: Path to the tarball.
            target_dir: Directory to extract to.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            with tarfile.open(source_file, "r:*") as tar:
                tar.extractall(path=target_dir)
            return True
        except Exception as e:
            logger.error(f"Error extracting tarball: {e}")
            return False

    def _verify_backup(self, backup_id: str) -> bool:
        """
        Verify the integrity of a backup.

        Args:
            backup_id: ID of the backup to verify.

        Returns:
            bool: True if the backup is valid, False otherwise.
        """
        # Check if the backup exists in the manifest
        backup_info = None
        for backup in self.manifest["backups"]:
            if backup["id"] == backup_id:
                backup_info = backup
                break

        if backup_info is None:
            logger.error(f"Backup {backup_id} not found in manifest")
            return False

        # Check if the backup directory exists
        backup_path = os.path.join(self.backup_dir, backup_id)
        if not os.path.exists(backup_path):
            logger.error(f"Backup directory {backup_path} not found")
            return False

        # Check if all the expected files exist
        for component in backup_info["components"]:
            file_path = os.path.join(backup_path, f"{component}.tar.gz")
            if not os.path.exists(file_path):
                logger.error(f"Backup file {file_path} not found")
                return False

        return True

    def _rotate_backups(self) -> None:
        """
        Remove old backups to stay within the maximum number of backups.
        """
        if len(self.manifest["backups"]) <= MAX_BACKUPS:
            return

        # Sort backups by creation time (oldest first)
        sorted_backups = sorted(
            self.manifest["backups"], key=lambda x: x["created_at"]
        )

        # Remove oldest backups
        backups_to_remove = sorted_backups[
            : len(sorted_backups) - MAX_BACKUPS
        ]
        for backup in backups_to_remove:
            self.delete_backup(backup["id"])

    def create_backup(
        self, components: List[str] = None, description: str = None
    ) -> Tuple[bool, str]:
        """
        Create a backup of the specified components.

        Args:
            components: List of components to backup (config, data, logs).
                If None, all components will be backed up.
            description: Optional description of the backup.

        Returns:
            Tuple[bool, str]: (success, message)
                success: True if the backup was successful, False otherwise.
                message: Information about the backup process or error message.
        """
        if components is None:
            components = ["config", "data", "logs"]

        # Validate components
        valid_components = ["config", "data", "logs"]
        for component in components:
            if component not in valid_components:
                return (
                    False,
                    (
                        f"Invalid component: {component}. "
                        f"Valid components: {valid_components}"
                    ),
                )

        # Generate backup ID and create directory
        backup_id = self._generate_backup_id()
        backup_path = self._create_backup_dir(backup_id)

        # Create backup for each component
        successful_components = []
        for component in components:
            if component == "config":
                source_dir = CONFIG_DIR
            elif component == "data":
                source_dir = DATA_DIR
            elif component == "logs":
                source_dir = LOG_DIR
            else:
                continue

            # Skip if source directory doesn't exist
            if not os.path.exists(source_dir):
                logger.warning(
                    f"Source directory {source_dir} not found, skipping"
                )
                continue

            # Create tarball
            target_file = os.path.join(backup_path, f"{component}.tar.gz")
            if self._create_tarball(source_dir, target_file):
                successful_components.append(component)
            else:
                logger.error(f"Failed to backup {component}")

        # If no components were backed up successfully, return error
        if not successful_components:
            shutil.rmtree(backup_path)
            return False, "No components were backed up successfully"

        # Add backup to manifest
        backup_info = {
            "id": backup_id,
            "created_at": datetime.now().isoformat(),
            "components": successful_components,
            "description": description
            or "Backup created by backup_restore.py",
        }
        self.manifest["backups"].append(backup_info)
        self._save_manifest()

        # Rotate backups
        self._rotate_backups()

        return (
            True,
            (
                f"Backup {backup_id} created successfully with components: "
                f"{successful_components}"
            ),
        )

    def restore_backup(
        self, backup_id: str, components: List[str] = None
    ) -> Tuple[bool, str]:
        """
        Restore from a backup.

        Args:
            backup_id: ID of the backup to restore from.
            components: List of components to restore (config, data, logs).
                If None, all components in the backup will be restored.

        Returns:
            Tuple[bool, str]: (success, message)
                success: True if the restore was successful, False otherwise.
                message: Information about the restore process or error message.
        """
        # Verify the backup
        if not self._verify_backup(backup_id):
            return False, f"Backup {backup_id} is invalid or incomplete"

        # Get backup info from manifest
        backup_info = None
        for backup in self.manifest["backups"]:
            if backup["id"] == backup_id:
                backup_info = backup
                break

        if backup_info is None:
            return False, f"Backup {backup_id} not found in manifest"

        # If components is None, restore all components in the backup
        if components is None:
            components = backup_info["components"]
        else:
            # Validate components
            for component in components:
                if component not in backup_info["components"]:
                    return (
                        False, f"Component {component} not found "
                        f"in backup {backup_id}", )

        # Stop services before restoring
        logger.info("Stopping autonomous-mower service")
        try:
            subprocess.run(
                ["sudo", "systemctl", "stop", "autonomous-mower.service"],
                check=True,
                capture_output=True,
                text=True,
            )
            time.sleep(2)  # Wait for the service to stop
        except subprocess.CalledProcessError as e:
            logger.warning(f"Error stopping service: {e.stderr}")
            # Continue anyway, the service might not be running

        # Restore each component
        backup_path = os.path.join(self.backup_dir, backup_id)
        successful_components = []
        for component in components:
            source_file = os.path.join(backup_path, f"{component}.tar.gz")
            if component == "config":
                target_dir = os.path.dirname(CONFIG_DIR)
            elif component == "data":
                target_dir = os.path.dirname(DATA_DIR)
            elif component == "logs":
                target_dir = os.path.dirname(LOG_DIR)
            else:
                continue

            # Extract tarball
            if self._extract_tarball(source_file, target_dir):
                successful_components.append(component)
            else:
                logger.error(f"Failed to restore {component}")

        # Start services after restoring
        logger.info("Starting autonomous-mower service")
        try:
            subprocess.run(
                ["sudo", "systemctl", "start", "autonomous-mower.service"],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Error starting service: {e.stderr}")
            return (
                False,
                f"Restore partially successful, but failed to start service: {
                    e.stderr}",
            )

        if not successful_components:
            return False, "No components were restored successfully"

        return (
            True,
            (
                f"Restore from backup {backup_id} completed successfully "
                f"with components: {successful_components}"
            ),
        )

    def list_backups(self) -> List[Dict[str, Any]]:
        """
        List all available backups.

        Returns:
            List[Dict[str, Any]]: List of backup information.
        """
        return self.manifest["backups"]

    def get_backup_info(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific backup.

        Args:
            backup_id: ID of the backup.

        Returns:
            Optional[Dict[str, Any]]: Backup information, or None if not found.
        """
        for backup in self.manifest["backups"]:
            if backup["id"] == backup_id:
                return backup
        return None

    def delete_backup(self, backup_id: str) -> Tuple[bool, str]:
        """
        Delete a backup.

        Args:
            backup_id: ID of the backup to delete.

        Returns:
            Tuple[bool, str]: (success, message)
                success: True if the deletion was successful, False otherwise.
                message: Information about the deletion process or error message.
        """
        # Check if the backup exists in the manifest
        backup_info = None
        for i, backup in enumerate(self.manifest["backups"]):
            if backup["id"] == backup_id:
                backup_info = backup
                backup_index = i
                break

        if backup_info is None:
            return False, f"Backup {backup_id} not found in manifest"

        # Delete the backup directory
        backup_path = os.path.join(self.backup_dir, backup_id)
        if os.path.exists(backup_path):
            try:
                shutil.rmtree(backup_path)
            except Exception as e:
                logger.error(f"Error deleting backup directory: {e}")
                return False, f"Error deleting backup directory: {e}"

        # Remove the backup from the manifest
        self.manifest["backups"].pop(backup_index)
        self._save_manifest()

        return True, f"Backup {backup_id} deleted successfully"

    def create_scheduled_backup(
        self, components: List[str] = None, description: str = None
    ) -> Tuple[bool, str]:
        """
        Create a scheduled backup using cron.

        Args:
            components: List of components to backup (config, data, logs).
                If None, all components will be backed up.
            description: Optional description of the backup.

        Returns:
            Tuple[bool, str]: (success, message)
                success: True if the scheduled backup was set up successfully, F
                alse otherwise.
                message: Information about the process or error message.
        """
        # Create a cron job to run the backup script
        components_str = (
            ",".join(components) if components else "config,data,logs"
        )
        description_str = f'"{description}"' if description else '""'

        cron_command = (
            f"0 2 * * * python3 -m mower.utilities.backup_restore "
            f"--backup {components_str} --description {description_str} "
            f"> /dev/null 2>&1"
        )

        try:
            # Get existing crontab
            result = subprocess.run(
                ["crontab", "-l"],
                capture_output=True,
                text=True,
            )

            # If crontab doesn't exist, start with an empty one
            if result.returncode != 0:
                current_crontab = ""
            else:
                current_crontab = result.stdout

            # Check if the backup command already exists
            if "mower.utilities.backup_restore --backup" in current_crontab:
                return False, "Scheduled backup already exists in crontab"

            # Add the new cron job
            new_crontab = current_crontab + cron_command + "\n"

            # Write the new crontab
            with tempfile.NamedTemporaryFile(
                mode="w", delete=False
            ) as temp_file:
                temp_file.write(new_crontab)
                temp_file_path = temp_file.name

            subprocess.run(
                ["crontab", temp_file_path],
                check=True,
                capture_output=True,
                text=True,
            )

            os.unlink(temp_file_path)

            return (
                True,
                "Scheduled backup set up successfully (daily at 2:00 AM)",
            )
        except Exception as e:
            logger.error(f"Error setting up scheduled backup: {e}")
            return False, f"Error setting up scheduled backup: {e}"


def main():
    """
    Run the backup and restore utility from the command line.

    This function parses command-line arguments and runs the backup and restore
    utility accordingly.

    Command-line options:
        --backup: Create a backup (specify components or 'full')
        --restore: Restore from a backup
        --list: List available backups
        --info: Get information about a specific backup
        --delete: Delete a backup
        --schedule: Set up a scheduled backup
        --backup-dir: Directory where backups will be stored

    Returns:
        System exit code: 0 on success, non-zero on error
    """
    parser = argparse.ArgumentParser(
        description="Backup and restore utility for the autonomous mower"
    )

    # Create a mutually exclusive group for the main actions
    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument(
        "--backup",
        nargs="*",
        metavar="COMPONENT",
        help="Create a backup (specify components or 'full')",
    )
    action_group.add_argument(
        "--restore",
        metavar="BACKUP_ID",
        help="Restore from a backup",
    )
    action_group.add_argument(
        "--list",
        action="store_true",
        help="List available backups",
    )
    action_group.add_argument(
        "--info",
        metavar="BACKUP_ID",
        help="Get information about a specific backup",
    )
    action_group.add_argument(
        "--delete",
        metavar="BACKUP_ID",
        help="Delete a backup",
    )
    action_group.add_argument(
        "--schedule",
        nargs="*",
        metavar="COMPONENT",
        help="Set up a scheduled backup (specify components or 'full')",
    )

    # Additional options
    parser.add_argument(
        "--components",
        nargs="+",
        choices=["config", "data", "logs"],
        help="Components to backup or restore (used with --restore)",
    )
    parser.add_argument(
        "--description",
        help="Description of the backup (used with --backup)",
    )
    parser.add_argument(
        "--backup-dir",
        default=BACKUP_DIR,
        help=f"Directory where backups will be stored (default: {BACKUP_DIR})",
    )

    args = parser.parse_args()

    # Initialize the backup and restore utility
    backup_restore = BackupRestore(backup_dir=args.backup_dir)

    # Process the command
    try:
        if args.backup is not None:
            # Handle 'full' backup
            if len(args.backup) == 1 and args.backup[0] == "full":
                components = None
            else:
                components = args.backup

            success, message = backup_restore.create_backup(
                components=components,
                description=args.description,
            )
            print(message)
            return 0 if success else 1

        elif args.restore:
            success, message = backup_restore.restore_backup(
                backup_id=args.restore,
                components=args.components,
            )
            print(message)
            return 0 if success else 1

        elif args.list:
            backups = backup_restore.list_backups()
            if not backups:
                print("No backups found")
                return 0

            print(f"Found {len(backups)} backups:")
            for backup in backups:
                created_at = datetime.fromisoformat(
                    backup["created_at"]
                ).strftime("%Y-%m-%d %H:%M:%S")
                print(f"ID: {backup['id']}")
                print(f"  Created: {created_at}")
                print(f"  Components: {', '.join(backup['components'])}")
                print(f"  Description: {backup['description']}")
                print()
            return 0

        elif args.info:
            backup_info = backup_restore.get_backup_info(args.info)
            if backup_info is None:
                print(f"Backup {args.info} not found")
                return 1

            created_at = datetime.fromisoformat(
                backup_info["created_at"]
            ).strftime("%Y-%m-%d %H:%M:%S")
            print(f"Backup ID: {backup_info['id']}")
            print(f"Created: {created_at}")
            print(f"Components: {', '.join(backup_info['components'])}")
            print(f"Description: {backup_info['description']}")

            # Check if the backup is valid
            is_valid = backup_restore._verify_backup(args.info)
            print(
                f"Status: {'Valid' if is_valid else 'Invalid or incomplete'}"
            )

            return 0

        elif args.delete:
            success, message = backup_restore.delete_backup(args.delete)
            print(message)
            return 0 if success else 1

        elif args.schedule is not None:
            # Handle 'full' backup
            if len(args.schedule) == 1 and args.schedule[0] == "full":
                components = None
            else:
                components = args.schedule

            success, message = backup_restore.create_scheduled_backup(
                components=components,
                description=args.description,
            )
            print(message)
            return 0 if success else 1

    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
