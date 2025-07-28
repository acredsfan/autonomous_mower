#!/usr/bin/env python3
"""
Script to remove unused imports from Python files.
Uses autoflake to safely remove unused imports.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def find_python_files(path):
    """Find all Python files in the given path (directory or file)."""
    python_files = []
    
    # If path is a file and ends with .py, return it
    if os.path.isfile(path) and path.endswith('.py'):
        return [path]
    
    # If path is a directory, walk through it
    if os.path.isdir(path):
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))
    
    return python_files


def remove_unused_imports(file_path, dry_run=True):
    """Remove unused imports from a Python file using autoflake."""
    cmd = [
        'autoflake',
        '--remove-all-unused-imports',
        '--remove-unused-variables',
    ]
    
    if dry_run:
        cmd.append('--stdout')
    else:
        cmd.append('--in-place')
    
    cmd.append(file_path)
    
    try:
        if dry_run:
            result = subprocess.run(cmd, capture_output=True, text=True)
            original_content = Path(file_path).read_text()
            if original_content != result.stdout:
                # Find the imports that would be removed
                original_imports = set()
                for line in original_content.splitlines():
                    if line.strip().startswith('import ') or line.strip().startswith('from '):
                        original_imports.add(line.strip())
                
                new_imports = set()
                for line in result.stdout.splitlines():
                    if line.strip().startswith('import ') or line.strip().startswith('from '):
                        new_imports.add(line.strip())
                
                removed_imports = original_imports - new_imports
                print(f"Found {len(removed_imports)} unused imports in {file_path}")
                for imp in removed_imports:
                    print(f"  - {imp}")
                return True
            return False
        else:
            subprocess.run(cmd)
            return True
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Remove unused imports from Python files.')
    parser.add_argument('path', help='File or directory to process')
    parser.add_argument('--apply', action='store_true', help='Apply changes (default is dry run)')
    args = parser.parse_args()
    
    try:
        # Check if autoflake is installed
        subprocess.run(['autoflake', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: autoflake is not installed. Please install it with 'pip install autoflake'.")
        sys.exit(1)
    
    python_files = find_python_files(args.path)
    print(f"Found {len(python_files)} Python files in {args.path}")
    
    modified_count = 0
    for file_path in python_files:
        if remove_unused_imports(file_path, dry_run=not args.apply):
            modified_count += 1
    
    print()
    if args.apply:
        print(f"Modified {modified_count} files to remove unused imports.")
    else:
        print(f"Found {modified_count} files with unused imports.")
        print("To remove these imports, run with --apply flag.")


if __name__ == "__main__":
    main()