"""
YOLOv8 model download and conversion utility for autonomous mower.

This script downloads YOLOv8 models and converts them to TFLite format
for use with the obstacle detection system on Raspberry Pi.
"""

import os
import sys
import logging
import argparse
import requests  # type: ignore

# from pathlib import Path

from tqdm import tqdm  # type: ignore

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# YOLOv8 model URLs - These are TFLite versions of YOLOv8 models
MODEL_URLS = {
    "yolov8n": (
        "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.tflite"
    ),
    "yolov8s": (
        "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8s.tflite"
    ),
    "yolov8m": (
        "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8m.tflite"
    ),
}

# COCO dataset label map
LABELMAP_URL = (
    "https://raw.githubusercontent.com/ultralytics/ultralytics/main/"
    "ultralytics/datasets/coco.yaml"
)


def download_file(url, output_path):
    """
    Download a file with progress bar.

    Args:
        url: URL to download from
        output_path: Path to save the file to

    Returns:
        The path to the downloaded file
    """
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()

        total_size = int(response.headers.get("content-length", 0))
        block_size = 1024  # 1 Kibibyte

        logger.info(f"Downloading {url} to {output_path}")

        with (
            open(output_path, "wb") as file,
            tqdm(
                desc=os.path.basename(output_path),
                total=total_size,
                unit="iB",
                unit_scale=True,
                unit_divisor=1024,
            ) as bar,
        ):
            for data in response.iter_content(block_size):
                size = file.write(data)
                bar.update(size)

        return output_path

    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        if os.path.exists(output_path):
            os.remove(output_path)
        return None


def download_and_parse_labels(output_dir):
    """
    Download and parse COCO labels from YOLOv8 YAML file.

    Args:
        output_dir: Directory to save the labels file

    Returns:
        Path to the created labels file
    """
    try:
        # Download the YAML file
        response = requests.get(LABELMAP_URL)
        response.raise_for_status()

        yaml_content = response.text

        # Parse the YAML to extract class names
        names_section = None
        for line in yaml_content.split("\n"):
            if line.startswith("names:"):
                names_section = True
                continue

            if names_section and line.strip():
                if not line.startswith(" "):
                    break

        # Extract the names dictionary (this is a simplified approach)
        labels = []
        in_names_section = False
        for line in yaml_content.split("\n"):
            if "names:" in line:
                in_names_section = True
                continue

            if in_names_section:
                if not line.strip() or not line.startswith(" "):
                    # End of names section
                    if not line.strip():
                        continue
                    else:
                        break

                # Parse the class name
                if ":" in line:
                    parts = line.strip().split(":")
                    if len(parts) >= 2:
                        class_name = parts[1].strip().strip("'").strip('"')
                        labels.append(class_name)

        # Write labels to file
        output_path = os.path.join(output_dir, "labelmap.txt")
        with open(output_path, "w") as f:
            for label in labels:
                f.write(f"{label}\n")

        logger.info(f"Created label map at {output_path} with {len(labels)} classes")
        return output_path

    except Exception as e:
        logger.error(f"Error downloading/parsing labels: {e}")
        return None


def download_yolov8_model(model_size="yolov8n", output_dir="models"):
    """
    Download a YOLOv8 TFLite model.

    Args:
        model_size: Size of YOLOv8 model ('yolov8n', 'yolov8s', or 'yolov8m')
        output_dir: Directory to save the model to

    Returns:
        Tuple of (model_path, labelmap_path)
    """
    # Ensure model size is valid
    if model_size not in MODEL_URLS:
        valid_models = list(MODEL_URLS.keys())
        logger.error(f"Invalid model size. Choose from: {valid_models}")
        return None, None

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Download the model
    model_url = MODEL_URLS[model_size]
    model_path = os.path.join(output_dir, f"{model_size}.tflite")
    success = download_file(model_url, model_path)

    if not success:
        return None, None

    # Download and parse labels
    labelmap_path = download_and_parse_labels(output_dir)

    return model_path, labelmap_path


def main():
    """Main function to handle CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Download YOLOv8 model in TFLite format"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="yolov8n",
        choices=["yolov8n", "yolov8s", "yolov8m"],
        help="YOLOv8 model size (default: yolov8n)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="models",
        help="Output directory (default: models/)",
    )

    args = parser.parse_args()

    # Download the model
    model_path, labelmap_path = download_yolov8_model(args.model, args.output)

    if model_path and labelmap_path:
        logger.info(f"Successfully downloaded YOLOv8 model to {model_path}")
        logger.info(f"Label map saved to {labelmap_path}")
        return 0
    else:
        logger.error("Failed to download YOLOv8 model")
        return 1


if __name__ == "__main__":
    sys.exit(main())
