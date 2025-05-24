"""
Download Coral EdgeTPU and TFLite models with robust error handling, retries,
checksum verification, dry-run mode, and actionable logging.

Intended to replace fragile shell logic in setup_coral.sh.

Usage:
    python3 download_coral_model.py --model detect_edgetpu.tflite \\
        --url https://github.com/google-coral/test_data/raw/master/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite \\ \        --checksum <sha256> --output_dir src/mower/obstacle_detection/models

    python3 download_coral_model.py --model detect.tflite \\
        --url https://github.com/google-coral/test_data/raw/master/ssd_mobilenet_v2_coco_quant_postprocess.tflite \\ \        --checksum <sha256> --output_dir src/mower/obstacle_detection/models

    python3 download_coral_model.py --model labelmap.txt \\
        --url https://raw.githubusercontent.com/google-coral/test_data/master/coco_labels.txt \\ \        --output_dir src/mower/obstacle_detection/models

Author: Autonomous Mower Team
"""

import argparse
import logging
import os

from mower.utilities.model_downloader import download_file

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("download_coral_model")


def main():
    parser = argparse.ArgumentParser(
        description="Download Coral EdgeTPU/TFLite models with robust error handling."
    )
    parser.add_argument(
        "--model",
        type=str,
        required=True,
        help=(
            "Filename for the model (e.g., detect_edgetpu.tflite, "
            "detect.tflite, labelmap.txt)"
        ),
    )
    parser.add_argument(
        "--url",
        type=str,
        required=True,
        help="Direct download URL for the model.",
    )
    parser.add_argument(
        "--checksum",
        type=str,
        default=None,
        help="Optional SHA256 checksum for the model file.",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="src/mower/obstacle_detection/models",
        help="Directory to save the downloaded model.",
    )
    parser.add_argument(
        "--dry_run",
        action="store_true",
        help="Perform a dry-run (check URL and disk space only).",
    )
    parser.add_argument(
        "--max_retries",
        type=int,
        default=3,
        help="Maximum number of download retries.",
    )
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    dest_path = os.path.join(args.output_dir, args.model)

    ok = download_file(
        url=args.url,
        dest_path=dest_path,
        expected_sha256=args.checksum,
        max_retries=args.max_retries,
        dry_run=args.dry_run,
    )

    if args.dry_run:
        if ok:
            logger.info("Dry-run successful: URL and disk space OK.")
        else:
            logger.error("Dry-run failed.")
        return

    if ok:
        logger.info(f"Model downloaded successfully to {dest_path}")
    else:
        logger.error("Model download failed.")


if __name__ == "__main__":
    main()
