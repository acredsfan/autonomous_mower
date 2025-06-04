"""
Download and convert a TensorFlow model to TFLite format with robust error handling,
retries, checksum verification, dry-run mode, and actionable logging.

Author: Autonomous Mower Team
"""

import argparse
import logging
import os
from typing import Optional

import tensorflow as tf

from mower.utilities.model_downloader import download_file

try:
    import kagglehub
except ImportError:
    kagglehub = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("tf_model_downloads")


def download_model(
    url: Optional[str] = None,
    dest_path: Optional[str] = None,
    checksum: Optional[str] = None,
    dry_run: bool = False,
    max_retries: int = 3,
):
    """
    Download a model file using a direct URL or kagglehub.

    Args:
        url: Direct download URL (preferred)
        dest_path: Where to save the downloaded file
        checksum: Optional SHA256 checksum for verification
        dry_run: If True, only check URL and disk space
        max_retries: Number of download attempts

    Returns:
        Path to the downloaded model directory, or None on failure
    """
    if url:
        if not dest_path:
            logger.error("Destination path must be specified for direct URL download.")
            return None
        logger.info(f"Downloading model from URL: {url}")
        ok = download_file(
            url,
            dest_path,
            expected_sha256=checksum,
            max_retries=max_retries,
            dry_run=dry_run,
        )
        if not ok:
            logger.error("Model download failed.")
            return None
        logger.info(f"Model downloaded to {dest_path}")
        return dest_path
    else:
        if not kagglehub:
            logger.error("kagglehub is not installed. Cannot download model.")
            return None
        logger.info("Downloading the model using kagglehub...")
        try:
            model_path = kagglehub.model_download("google/mobilenet-v2/tensorFlow2/100-224-classification")
            logger.info(f"Model downloaded to {model_path}")
            return model_path
        except Exception as e:
            logger.error(f"kagglehub download failed: {e}")
            return None


def convert_model(saved_model_dir, tflite_model_path):
    """
    Convert a TensorFlow SavedModel to TFLite format.

    Args:
        saved_model_dir: Path to the SavedModel directory
        tflite_model_path: Output path for the TFLite model
    """
    logger.info("Converting the model to TFLite format...")
    try:
        converter = tf.lite.TFLiteConverter.from_saved_model(saved_model_dir)
        # Set optimizations only if attribute exists and is correct type
        if hasattr(converter, "optimizations"):
            try:
                converter.optimizations = [tf.lite.Optimize.DEFAULT]  # type: ignore
            except Exception as e:
                logger.warning(f"Could not set optimizations: {e}")
        tflite_model = converter.convert()
        if not isinstance(tflite_model, bytes):
            logger.error("TFLite model conversion did not return bytes. Aborting write.")
            return
        with open(tflite_model_path, "wb") as f:
            f.write(tflite_model)
        logger.info(f"TFLite model saved to {tflite_model_path}")
    except Exception as e:
        logger.error(f"Model conversion failed: {e}")


def main():
    parser = argparse.ArgumentParser(description="Download and convert model to TFLite with robust error handling.")
    parser.add_argument(
        "--output_path",
        type=str,
        required=True,
        help="The output path for the converted TFLite model.",
    )
    parser.add_argument(
        "--url",
        type=str,
        default=None,
        help="Direct download URL for the model (preferred).",
    )
    parser.add_argument(
        "--dest_path",
        type=str,
        default=None,
        help="Destination path for the downloaded model file (if using --url).",
    )
    parser.add_argument(
        "--checksum",
        type=str,
        default=None,
        help="Optional SHA256 checksum for the model file.",
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

    # Download the model
    model_path = download_model(
        url=args.url,
        dest_path=args.dest_path,
        checksum=args.checksum,
        dry_run=args.dry_run,
        max_retries=args.max_retries,
    )

    if args.dry_run:
        logger.info("Dry-run complete. Exiting.")
        return

    if not model_path:
        logger.error("Model download failed. Exiting.")
        return

    # If the model is a directory (SavedModel), use it directly; if it's a
    # file, check if it's a zip/tar
    if os.path.isdir(model_path):
        saved_model_dir = model_path
    else:
        saved_model_dir = model_path  # For now, assume it's a directory or compatible

    # Convert and save the model
    convert_model(saved_model_dir, args.output_path)


if __name__ == "__main__":
    main()
