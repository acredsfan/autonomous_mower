#!/usr/bin/env python3
"""
YOLOv8 TFLite Model Setup Script for Autonomous Mower

This script:
1. Downloads the appropriate YOLOv8 TFLite model
2. Sets up the environment variables
3. Updates configuration files
4. Ensures dependencies are installed

Usage:
  python3 setup_yolov8.py [--model yolov8n|yolov8s|yolov8m]
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Set up YOLOv8 TFLite model for obstacle detection"
    )
    parser.add_argument(
        "--model",
        choices=["yolov8n", "yolov8s", "yolov8m"],
        default="yolov8n",
        help="YOLOv8 model size (default: yolov8n)"
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output directory for model files (default: models/)"
    )
    return parser.parse_args()


def get_repo_root():
    """Get the root directory of the repository."""
    # Start from current directory and go up until we find .git
    current = Path.cwd().absolute()
    while current != current.parent:
        if (current / '.git').exists():
            return current
        current = current.parent

    # If we couldn't find .git, assume current directory is the root
    return Path.cwd().absolute()


def setup_path():
    """Add src directory to sys.path for imports."""
    # Get repository root
    repo_root = get_repo_root()

    # Add src to path if it exists
    src_path = repo_root / 'src'
    if src_path.exists():
        sys.path.insert(0, str(src_path))


def install_dependencies():
    """Install required Python packages."""
    print("Checking and installing dependencies...")

    # Define required packages
    required = [
        'tflite-runtime',
        'opencv-python',
        'pillow',
        'numpy',
        'requests',
        'tqdm'
    ]

    # Install packages
    for package in required:
        try:
            subprocess.check_call([
                sys.executable, '-m', 'pip', 'install', package, '--quiet'
            ])
            print(f"✓ {package}")
        except subprocess.CalledProcessError:
            print(f"× Failed to install {package}, please install manually")


def download_model(model_name, output_dir):
    """Download the YOLOv8 model."""
    try:
        # Set up paths
        setup_path()

        # Import the downloader
        from mower.obstacle_detection.yolov8_downloads import (
            download_yolov8_model
        )

        # Create models directory if specified output is None
        if output_dir is None:
            repo_root = get_repo_root()
            output_dir = repo_root / 'models'

        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

        print(f"Downloading YOLOv8 {model_name} model...")
        model_path, labelmap_path = download_yolov8_model(
            model_name, output_dir)

        if model_path and labelmap_path:
            print(f"Successfully downloaded model to {model_path}")
            print(f"Label map saved to {labelmap_path}")
            return model_path, labelmap_path
        else:
            print("Failed to download model")
            return None, None

    except ImportError:
        print("Failed to import YOLOv8 downloader. "
              "Ensure you're running from the repository root.")
        return None, None
    except Exception as e:
        print(f"Error downloading model: {e}")
        return None, None


def update_env_file(model_path, labelmap_path):
    """Update .env file with YOLOv8 paths."""
    # Get repository root
    repo_root = get_repo_root()
    env_file = repo_root / '.env'

    # Default env content if file doesn't exist
    env_content = ""
    if env_file.exists():
        with open(env_file, 'r') as f:
            env_content = f.read()

    # Update YOLOV8_MODEL_PATH if exists, otherwise add it
    if 'YOLOV8_MODEL_PATH' in env_content:
        lines = env_content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('YOLOV8_MODEL_PATH'):
                lines[i] = f"YOLOV8_MODEL_PATH={model_path}"
        env_content = '\n'.join(lines)
    else:
        env_content += "\n# YOLOv8 configuration"
        env_content += f"\nYOLOV8_MODEL_PATH={model_path}"

    # Update LABEL_MAP_PATH if exists, otherwise add it
    if 'LABEL_MAP_PATH' in env_content:
        lines = env_content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('LABEL_MAP_PATH'):
                lines[i] = f"LABEL_MAP_PATH={labelmap_path}"
        env_content = '\n'.join(lines)
    else:
        env_content += f"\nLABEL_MAP_PATH={labelmap_path}"

    # Add USE_YOLOV8 flag
    if 'USE_YOLOV8' not in env_content:
        env_content += "\nUSE_YOLOV8=True"

    # Write updated content back to file
    with open(env_file, 'w') as f:
        f.write(env_content)

    print(f"Updated environment variables in {env_file}")


def main():
    """Main entry point."""
    args = parse_args()

    print(f"Setting up YOLOv8 {args.model} for obstacle detection...")

    # Install dependencies
    install_dependencies()

    # Download model
    output_dir = args.output
    model_path, labelmap_path = download_model(args.model, output_dir)

    if model_path and labelmap_path:
        # Update environment variables
        update_env_file(model_path, labelmap_path)

        print("\n✓ YOLOv8 setup complete!")
        print("\nYou can now use YOLOv8 for obstacle detection in your "
              "autonomous mower.")
        print("The obstacle detector will automatically use YOLOv8 "
              "if available.")
        print("\nTo test the model, run:")
        print("  python -c \"from mower.obstacle_detection.obstacle_detector "
              "import get_obstacle_detector; "
              "detector = get_obstacle_detector(); "
              "print('YOLOv8 enabled:', "
              "detector.yolov8_detector is not None)\"")
    else:
        print("\n× YOLOv8 setup failed.")
        print("Please check the error messages above and try again.")


if __name__ == "__main__":
    main()
