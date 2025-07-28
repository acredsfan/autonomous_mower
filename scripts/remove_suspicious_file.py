#!/usr/bin/env python3
"""
Script to safely remove a suspicious file from the codebase.
Creates a backup before removal and runs tests to verify system integrity.
"""

import os
import sys
import shutil
import argparse
import subprocess
from pathlib import Path
from datetime import datetime


def backup_file(file_path):
    """Create a backup of the file before removal."""
    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = os.path.basename(file_path)
    backup_path = backup_dir / f"{file_name}.{timestamp}.bak"
    
    shutil.copy2(file_path, backup_path)
    print(f"Created backup at {backup_path}")
    return backup_path


def run_tests():
    """Run the test suite to verify system integrity."""
    print("Running tests to verify system integrity...")
    try:
        result = subprocess.run(["pytest", "-xvs", "tests/"], capture_output=True, text=True)
        if result.returncode == 0:
            print("All tests passed!")
            return True
        else:
            print("Tests failed! See output below:")
            print(result.stdout)
            print(result.stderr)
            return False
    except Exception as e:
        print(f"Error running tests: {e}")
        return False


def remove_file(file_path, dry_run=True, skip_tests=False):
    """Remove a file from the codebase with safety checks."""
    file_path = Path(file_path)
    
    if not file_path.exists():
        print(f"Error: File {file_path} does not exist.")
        return False
    
    print(f"Preparing to remove file: {file_path}")
    
    # Create backup
    backup_path = backup_file(file_path)
    
    if dry_run:
        print(f"Dry run: Would remove {file_path}")
        print(f"Backup created at {backup_path}")
        return True
    
    # Remove the file
    try:
        os.remove(file_path)
        print(f"Removed file: {file_path}")
        
        # Run tests if not skipped
        if not skip_tests:
            tests_passed = run_tests()
            if not tests_passed:
                print(f"Tests failed! Restoring file from backup: {backup_path}")
                shutil.copy2(backup_path, file_path)
                print(f"Restored {file_path} from backup")
                return False
        
        print(f"File successfully removed: {file_path}")
        print(f"Backup preserved at: {backup_path}")
        return True
    
    except Exception as e:
        print(f"Error removing file: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Safely remove a suspicious file from the codebase.')
    parser.add_argument('file_path', help='Path to the file to remove')
    parser.add_argument('--apply', action='store_true', help='Actually remove the file (default is dry run)')
    parser.add_argument('--skip-tests', action='store_true', help='Skip running tests after removal')
    args = parser.parse_args()
    
    remove_file(args.file_path, dry_run=not args.apply, skip_tests=args.skip_tests)


if __name__ == "__main__":
    main()