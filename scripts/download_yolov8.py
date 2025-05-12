#!/usr/bin/env python3
"""
YOLOv8 TFLite Model Download Script for Autonomous Mower

This script directly downloads pre-converted YOLOv8 TFLite models
instead of attempting conversion on the Pi, which can be problematic
due to library incompatibilities.

Usage:
  python3 download_yolov8.py [--model yolov8n|yolov8s|yolov8m]
"""

import sys
import argparse
import urllib.request
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# COCO Label Map Content
COCO_LABELS = """person
bicycle
car
motorcycle
airplane
bus
train
truck
boat
traffic light
fire hydrant
stop sign
parking meter
bench
bird
cat
dog
horse
sheep
cow
elephant
bear
zebra
giraffe
backpack
umbrella
handbag
tie
suitcase
frisbee
skis
snowboard
sports ball
kite
baseball bat
baseball glove
skateboard
surfboard
tennis racket
bottle
wine glass
cup
fork
knife
spoon
bowl
banana
apple
sandwich
orange
broccoli
carrot
hot dog
pizza
donut
cake
chair
couch
potted plant
bed
dining table
toilet
tv
laptop
mouse
remote
keyboard
cell phone
microwave
oven
toaster
sink
refrigerator
book
clock
vase
scissors
teddy bear
hair drier
toothbrush""".splitlines()


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Download pre-converted YOLOv8 TFLite models"
    )
    parser.add_argument(
        "--model",
        choices=["yolov8n", "yolov8s", "yolov8m"],
        default="yolov8n",
        help="YOLOv8 model size (default: yolov8n)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Output directory for model and label files "
            "(default: <repo_root>/src/mower/obstacle_detection/models/)"
        ),
    )
    return parser.parse_args()


def get_repo_root():
    """Get the root directory of the repository."""
    current = Path.cwd().absolute()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    # Fallback if not in a git repo
    logging.warning(
        "Could not find .git directory. Assuming current directory is root."
    )
    return Path.cwd().absolute()


def download_model(model_name: str, output_dir: Path):
    """Download pre-converted YOLOv8 TFLite model."""
    model_url = f"https://github.com/ultralytics/assets/raw/main/{model_name}.tflite"
    model_path = output_dir / f"{model_name}.tflite"

    try:
        logging.info(f"Creating output directory: {output_dir}")
        output_dir.mkdir(parents=True, exist_ok=True)

        logging.info(f"Downloading {model_name} from {model_url}")
        urllib.request.urlretrieve(model_url, model_path)
        logging.info(f"Successfully downloaded model to {model_path}")
        return model_path
    except Exception as e:
        logging.error(f"Error downloading model {model_name}: {e}")
        return None


def save_label_map(output_dir: Path):
    """Saves the COCO label map to the specified directory."""
    labelmap_path = output_dir / "coco_labels.txt"
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(labelmap_path, "w") as f:
            f.write("\n".join(COCO_LABELS))
        logging.info(f"COCO label map saved to {labelmap_path}")
        return labelmap_path
    except IOError as e:
        logging.error(f"Failed to save label map to {labelmap_path}: {e}")
        return None


def update_env_file(model_path: Path, labelmap_path: Path):
    """Update .env file with YOLOv8 paths."""
    repo_root = get_repo_root()
    env_file = repo_root / ".env"
    logging.info(f"Updating environment variables in: {env_file}")

    # Make paths relative to the repo root for portability
    try:
        relative_model_path = str(
            model_path.relative_to(repo_root)).replace(
            "\\", "/")
        relative_label_path = str(
            labelmap_path.relative_to(repo_root)).replace(
            "\\", "/")
    except ValueError:
        logging.warning(
            f"Model/Label paths ({model_path}, {labelmap_path}) are outside "
            f"the repo root ({repo_root}). Using absolute paths in .env."
        )
        relative_model_path = str(model_path).replace("\\", "/")
        relative_label_path = str(labelmap_path).replace("\\", "/")

    env_content = []
    updated = {"model": False, "label": False, "flag": False}
    section_exists = False

    # Read existing .env file if it exists
    if env_file.exists():
        with open(env_file, "r") as f:
            for line in f:
                line_strip = line.strip()

                if line_strip == "# YOLOv8 configuration":
                    section_exists = True
                    env_content.append(line)
                elif line_strip.startswith("YOLO_MODEL_PATH="):
                    env_content.append(
                        f"YOLO_MODEL_PATH={relative_model_path}\n")
                    updated["model"] = True
                elif line_strip.startswith("YOLO_LABEL_PATH="):
                    env_content.append(
                        f"YOLO_LABEL_PATH={relative_label_path}\n")
                    updated["label"] = True
                elif line_strip.startswith("USE_YOLOV8="):
                    env_content.append("USE_YOLOV8=True\n")
                    updated["flag"] = True
                else:
                    env_content.append(line)

    # Add missing entries
    if not section_exists:
        env_content.append("\n# YOLOv8 configuration\n")
    if not updated["model"]:
        env_content.append(f"YOLO_MODEL_PATH={relative_model_path}\n")
    if not updated["label"]:
        env_content.append(f"YOLO_LABEL_PATH={relative_label_path}\n")
    if not updated["flag"]:
        env_content.append("USE_YOLOV8=True\n")

    # Write updated .env file
    try:
        with open(env_file, "w") as f:
            f.writelines(env_content)
        logging.info(f"Successfully updated {env_file}")
    except IOError as e:
        logging.error(f"Failed to write updated {env_file}: {e}")


def main():
    """Main entry point."""
    args = parse_args()

    logging.info(
        f"--- Starting YOLOv8 {args.model} TFLite Download Process ---")

    # Determine output directory
    repo_root = get_repo_root()
    default_output = repo_root / "src" / "mower" / "obstacle_detection" / "models"
    output_dir = args.output if args.output else default_output

    logging.info(f"Repository root detected: {repo_root}")
    logging.info(f"Output directory set to: {output_dir}")

    # Download model
    model_path = download_model(args.model, output_dir)
    if not model_path:
        logging.error("Model download failed.")
        sys.exit(1)

    # Save label map
    labelmap_path = save_label_map(output_dir)
    if not labelmap_path:
        logging.error("Failed to save label map.")
        sys.exit(1)

    # Update environment file
    update_env_file(model_path, labelmap_path)

    logging.info("--- YOLOv8 Download Process Complete ---")
    logging.info(f"Model downloaded to: {model_path}")
    logging.info(f"Label map saved to: {labelmap_path}")
    logging.info(f"Environment file updated: {repo_root / '.env'}")
    logging.info(
        "\nSetup complete! You can now use YOLOv8 in your autonomous mower.")


if __name__ == "__main__":
    main()
