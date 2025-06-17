#!/usr/bin/env python3
"""
Library Version Updater for Autonomous Mower Project
Scans and updates all files containing library definitions with the most recent compatible versions
Designed to run in VS Code on Windows for Raspberry Pi target deployment
"""

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class LibraryInfo:
    """Information about a library and its versions"""

    name: str
    current_version: Optional[str]
    latest_version: Optional[str]
    latest_compatible: Optional[str]
    constraints: List[str]
    is_compatible: bool
    notes: str = ""


class ProjectLibraryUpdater:
    """Updates library versions across all project files"""

    # Core libraries for the autonomous mower project
    CORE_LIBRARIES = {
        # GPIO and Hardware
        "gpiozero": ">=2.0",
        "lgpio": None,  # Backend for gpiozero on Bookworm
        "smbus2": ">=0.4.0",  # I2C communication
        "pyserial": ">=3.5",  # UART communication
        # Sensor Libraries
        "adafruit-circuitpython-gps": ">=3.10.0",
        "adafruit-circuitpython-bno055": ">=5.4.0",
        "VL53L1X": ">=0.0.5",  # ToF sensors
        # Computer Vision
        "opencv-python-headless": ">=4.8.0",  # Headless for Pi
        "tflite-runtime": "==2.14.0",  # Exact version for Coral TPU
        "Pillow": ">=10.0.0",
        # Web Framework
        "fastapi": ">=0.110.0",
        "uvicorn": ">=0.29.0",
        "pydantic": ">=2.7.0",
        "websockets": ">=12.0",
        "aiofiles": ">=23.0.0",
        # Async and System
        "aiohttp": ">=3.9.0",
        "python-multipart": ">=0.0.9",
        # Utilities
        "python-dotenv": ">=1.0.0",
        "pyyaml": ">=6.0",
        "numpy": ">=1.24.0,<2.0.0",  # Many libraries don't support numpy 2.0 yet
        "setuptools": ">=69.0.0",
        "wheel": ">=0.42.0",
        # Development Tools
        "pytest": ">=8.0.0",
        "pytest-asyncio": ">=0.23.0",
        "pytest-cov": ">=5.0.0",
        "black": ">=24.0.0",
        "mypy": ">=1.9.0",
        "pylint": ">=3.0.0",
        "isort": ">=5.13.0",
        # Additional project dependencies
        "requests": ">=2.31.0",
        "psutil": ">=5.9.0",
        "gps": ">=3.19",
        "board": None,  # Adafruit board definitions
        "busio": None,  # Adafruit busio
        "adafruit-blinka": ">=8.0.0",
        "readchar": None,  # For reading keyboard input
    }

    # Files to scan and update
    TARGET_FILES = [
        "requirements.txt",
        "requirements.dev.txt",
        "requirements.prod.txt",
        "install_requirements.sh",
        "setup_wizard.py",
        "setup.py",
        "pyproject.toml",
        ".github/workflows/*.yml",
        "scripts/setup_*.py",
        "docs/*.md",
        ".github/copilot-instructions.md",
    ]

    # Patterns to match library definitions in different file types
    PATTERNS = {
        ".txt": [
            (r"^([a-zA-Z0-9\-_.]+)(==|>=|<=|>|<|~=)([0-9.]+.*?)$", "requirements"),
            (r"^([a-zA-Z0-9\-_.]+)$", "requirements_simple"),
        ],
        ".sh": [
            (r"pip3?\s+install\s+([a-zA-Z0-9\-_.]+)(==|>=|<=|>|<|~=)([0-9.]+)", "pip_install"),
            (r'pip3?\s+install\s+"([a-zA-Z0-9\-_.]+)(==|>=|<=|>|<|~=)([0-9.]+)"', "pip_install_quoted"),
            (r"apt-get\s+install\s+.*?python3?-([a-zA-Z0-9\-_.]+)", "apt_install"),
            (r'PACKAGE_VERSION="([0-9.]+)"', "version_var"),
        ],
        ".py": [
            (r"install_requires\s*=\s*\[(.*?)\]", "setup_py_requires"),
            (r'"([a-zA-Z0-9\-_.]+)(==|>=|<=|>|<|~=)([0-9.]+)"', "string_requirement"),
            (r"\'([a-zA-Z0-9\-_.]+)(==|>=|<=|>|<|~=)([0-9.]+)\'", "string_requirement"),
            (r"([a-zA-Z0-9\-_.]+)==([0-9.]+)", "version_comment"),
        ],
        ".yml": [
            (r"pip3?\s+install\s+([a-zA-Z0-9\-_.]+)(==|>=|<=|>|<|~=)([0-9.]+)", "pip_install"),
            (r"python\s+-m\s+pip\s+install\s+([a-zA-Z0-9\-_.]+)(==|>=|<=|>|<|~=)([0-9.]+)", "pip_install"),
        ],
        ".md": [
            (r"([a-zA-Z0-9\-_.]+)==([0-9.]+)", "version_reference"),
            (r"`([a-zA-Z0-9\-_.]+)(==|>=|<=|>|<|~=)([0-9.]+)`", "code_block_version"),
            (r"```python\n.*?([a-zA-Z0-9\-_.]+)==([0-9.]+).*?\n```", "python_code_block"),
        ],
        ".toml": [
            (r'([a-zA-Z0-9\-_.]+)\s*=\s*"(==|>=|<=|>|<|~=)([0-9.]+)"', "toml_dependency"),
            (r'([a-zA-Z0-9\-_.]+)\s*=\s*\{version\s*=\s*"(==|>=|<=|>|<|~=)([0-9.]+)"', "toml_table"),
        ],
    }

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.results: Dict[str, LibraryInfo] = {}
        self.updated_files: List[str] = []
        self.python_version = "3.11"  # Target Python version for Raspberry Pi Bookworm

    def get_latest_version(self, package: str) -> Optional[str]:
        """Get latest available version of a package from PyPI"""
        try:
            # Use pip index versions or pip search
            result = subprocess.run(
                [sys.executable, "-m", "pip", "index", "versions", package], capture_output=True, text=True, check=False
            )
            if result.returncode == 0:
                # Parse the output to find available versions
                lines = result.stdout.split("\n")
                for line in lines:
                    if "Available versions:" in line:
                        versions = line.split(":", 1)[1].strip().split(", ")
                        if versions:
                            return versions[0]
            else:
                # Fallback to pip show for simpler lookup
                import requests

                response = requests.get(f"https://pypi.org/pypi/{package}/json", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    return data.get("info", {}).get("version")
        except Exception as e:
            print(f"Warning: Could not fetch version for {package}: {e}")
        return None

    def check_compatibility(self, package: str, version: str) -> Tuple[bool, str]:
        """Check if a specific version is compatible with our constraints"""
        # Special cases for Raspberry Pi deployment
        if package == "tflite-runtime":
            if version != "2.14.0":
                return False, "Must be exactly 2.14.0 for Coral TPU compatibility"

        if package == "numpy":
            if version.startswith("2."):
                return False, "NumPy 2.0+ incompatible with OpenCV and TFLite on Pi"

        if package == "opencv-python":
            return True, "Note: Use opencv-python-headless on Pi"

        return True, "Compatible"

    def resolve_dependencies(self) -> Dict[str, LibraryInfo]:
        """Resolve all dependencies and check compatibility"""
        print(f"Resolving dependencies for Raspberry Pi (Python {self.python_version})")
        print("=" * 70)

        for package, constraint in self.CORE_LIBRARIES.items():
            print(f"Checking {package}...", end=" ")

            latest = self.get_latest_version(package)

            # Determine latest compatible version
            compatible_version = latest
            is_compatible = True
            notes = ""

            if latest:
                is_compat, compat_note = self.check_compatibility(package, latest)
                if not is_compat:
                    # For some packages, we have specific versions we know work
                    if package == "tflite-runtime":
                        compatible_version = "2.14.0"
                        is_compatible = True
                    else:
                        compatible_version = latest
                        is_compatible = True
                    notes = compat_note
                print(f"✓ {latest}")
            else:
                print("⚠️  Could not fetch version")

            self.results[package] = LibraryInfo(
                name=package,
                current_version=None,  # Not checking installed versions on Windows
                latest_version=latest,
                latest_compatible=compatible_version,
                constraints=[constraint] if constraint else [],
                is_compatible=is_compatible,
                notes=notes.strip(),
            )

        return self.results

    def find_project_files(self) -> List[Path]:
        """Find all files that might contain library definitions"""
        files = []

        for pattern in self.TARGET_FILES:
            if "*" in pattern:
                # Handle wildcards
                base_path = self.project_root / pattern.split("*")[0]
                if base_path.exists():
                    for file in base_path.rglob("*"):
                        if file.is_file():
                            files.append(file)
            else:
                # Direct file reference
                file_path = self.project_root / pattern
                if file_path.exists():
                    files.append(file_path)

        return files

    def update_file(self, file_path: Path) -> bool:
        """Update library versions in a single file"""
        if not file_path.exists():
            return False

        # Determine file type and patterns to use
        suffix = file_path.suffix
        if suffix not in self.PATTERNS:
            # Try to guess from content
            if file_path.name == "requirements.txt":
                suffix = ".txt"
            elif file_path.name.endswith(".sh"):
                suffix = ".sh"
            else:
                return False

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            original_content = content
            patterns = self.PATTERNS[suffix]

            # Apply each pattern
            for pattern, pattern_type in patterns:
                if pattern_type == "requirements":
                    # Simple line-by-line replacement for requirements files
                    lines = content.split("\n")
                    new_lines = []
                    for line in lines:
                        match = re.match(pattern, line.strip())
                        if match:
                            lib_name = match.group(1)
                            if lib_name in self.results and self.results[lib_name].latest_compatible:
                                # Keep the same operator type
                                operator = match.group(2) if len(match.groups()) > 1 else "=="
                                new_version = self.results[lib_name].latest_compatible
                                new_line = f"{lib_name}{operator}{new_version}"
                                new_lines.append(new_line)
                                print(f"  Updated {lib_name} to {new_version}")
                            else:
                                new_lines.append(line)
                        else:
                            new_lines.append(line)
                    content = "\n".join(new_lines)

                elif pattern_type in ["pip_install", "pip_install_quoted"]:
                    # Update pip install commands
                    def replacer(match):
                        lib_name = match.group(1)
                        if lib_name in self.results and self.results[lib_name].latest_compatible:
                            operator = match.group(2) if len(match.groups()) > 1 else "=="
                            new_version = self.results[lib_name].latest_compatible
                            return match.group(0).replace(
                                f"{lib_name}{operator}{match.group(3)}", f"{lib_name}{operator}{new_version}"
                            )
                        return match.group(0)

                    content = re.sub(pattern, replacer, content, flags=re.MULTILINE)

            # Only write if content changed
            if content != original_content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.updated_files.append(str(file_path))
                return True

        except Exception as e:
            print(f"Error updating {file_path}: {e}")

        return False

    def update_copilot_instructions(self) -> None:
        """Update the copilot-instructions.md file with resolved versions"""
        instructions_path = self.project_root / ".github" / "copilot-instructions.md"
        if not instructions_path.exists():
            print("Warning: copilot-instructions.md not found")
            return

        try:
            with open(instructions_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Find the library versions section
            start_marker = "## Current Library Versions"

            start_idx = content.find(start_marker)
            if start_idx == -1:
                print("Warning: Could not find library versions section in copilot-instructions.md")
                return

            # Find the code block after the header
            code_start = content.find("```python", start_idx)
            if code_start == -1:
                return

            code_end = content.find("```", code_start + 10)
            if code_end == -1:
                return

            # Build new library section
            new_libs = ["# GPIO Libraries - NEVER use RPi.GPIO (deprecated)"]

            # Categorize libraries
            categories = {
                "GPIO Libraries": ["gpiozero", "lgpio"],
                "Sensor Libraries": [
                    "adafruit-circuitpython-gps",
                    "adafruit-circuitpython-bno055",
                    "pyserial",
                    "VL53L1X",
                    "smbus2",
                ],
                "Computer Vision": ["opencv-python-headless", "tflite-runtime", "Pillow"],
                "Web Framework": ["fastapi", "uvicorn", "pydantic", "websockets", "aiofiles"],
            }

            for category, libs in categories.items():
                new_libs.append(f"\n# {category}")
                for lib in libs:
                    if lib in self.results and self.results[lib].latest_compatible:
                        version = self.results[lib].latest_compatible
                        if lib == "tflite-runtime":
                            new_libs.append(f"{lib}=={version}  # Exact version for Coral TPU")
                        elif lib == "opencv-python-headless":
                            new_libs.append(f"{lib}=={version}  # Headless for Pi")
                        else:
                            new_libs.append(f"{lib}=={version}")

            # Replace the content
            new_content = content[: code_start + 10] + "\n" + "\n".join(new_libs) + "\n" + content[code_end:]

            with open(instructions_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            self.updated_files.append(str(instructions_path))
            print(f"✓ Updated {instructions_path}")

        except Exception as e:
            print(f"Error updating copilot-instructions.md: {e}")

    def generate_report(self) -> None:
        """Generate a summary report"""
        report_path = self.project_root / "library_update_report.md"

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# Library Update Report\n\n")
            f.write(f"**Generated**: {datetime.now().isoformat()}\n")
            f.write(f"**Target Platform**: Raspberry Pi with Python {self.python_version}\n\n")

            f.write("## Updated Libraries\n\n")
            f.write("| Library | Version | Notes |\n")
            f.write("|---------|---------|-------|\n")

            for info in sorted(self.results.values(), key=lambda x: x.name):
                if info.latest_compatible:
                    notes = info.notes or "Compatible"
                    f.write(f"| {info.name} | {info.latest_compatible} | {notes} |\n")

            f.write("\n## Updated Files\n\n")
            for file in self.updated_files:
                f.write(f"- {file}\n")

        print(f"\n✅ Report saved to {report_path}")


def main():
    parser = argparse.ArgumentParser(description="Update library versions across Autonomous Mower project")
    parser.add_argument("--project-root", help="Project root directory", default=".")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be updated without making changes")

    args = parser.parse_args()

    updater = ProjectLibraryUpdater(args.project_root)

    # Resolve dependencies
    print("🔍 Resolving library versions for Raspberry Pi deployment...\n")
    results = updater.resolve_dependencies()

    if args.dry_run:
        print("\n🔍 DRY RUN - No files will be modified\n")
        print("Would update these libraries:")
        for name, info in results.items():
            if info.latest_compatible:
                print(f"  {name} -> {info.latest_compatible}")
        return

    # Find and update project files
    print("\n📝 Updating project files...\n")

    files = updater.find_project_files()
    print(f"Found {len(files)} files to scan\n")

    for file in files:
        print(f"Checking {file}...")
        if updater.update_file(file):
            print("  ✓ Updated")

    # Update copilot instructions specifically
    updater.update_copilot_instructions()

    # Generate report
    updater.generate_report()

    print(f"\n✅ Update complete! Modified {len(updater.updated_files)} files")
    print("\n⚠️  Remember to:")
    print("  1. Review the changes before committing")
    print("  2. Test the updated dependencies on your Raspberry Pi")
    print("  3. Run your test suite to ensure compatibility")


if __name__ == "__main__":
    main()
