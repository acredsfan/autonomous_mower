"""
Robust model downloader utility for the autonomous mower project.

Features:
- Download with retries and exponential backoff
- SHA256 checksum verification
- Dry-run mode (checks URL reachability and disk space)
- Actionable logging
- Usable from scripts and shell

Author: Autonomous Mower Team
"""

import os
import logging
import hashlib
import requests
import shutil
import time

# from pathlib import Path
from typing import Optional

logger = logging.getLogger("model_downloader")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s")


def get_free_space_bytes(directory: str) -> int:
    """Return free disk space in bytes for the given directory."""
    try:
        total, used, free = shutil.disk_usage(directory)
        return free
    except Exception as e:
        logger.error(f"Failed to check disk space for {directory}: {e}")
        return 0


def verify_checksum(file_path: str, expected_sha256: str) -> bool:
    """Verify SHA256 checksum of a file."""
    sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        file_hash = sha256.hexdigest()
        if file_hash.lower() == expected_sha256.lower():
            logger.info(f"Checksum verified for {file_path}")
            return True
        else:
            logger.error(
                "Checksum mismatch for %s: expected %s, got %s",
                file_path, expected_sha256, file_hash
            )
            return False
    except Exception as e:
        logger.error(f"Failed to verify checksum for {file_path}: {e}")
        return False


def url_reachable(url: str, timeout: int = 10) -> bool:
    """Check if a URL is reachable (HEAD request)."""
    try:
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        if response.status_code == 200:
            logger.info(f"URL reachable: {url}")
            return True
        else:
            logger.error(
                f"URL not reachable (status {response.status_code}): {url}"
            )
            return False
    except Exception as e:
        logger.error(f"URL not reachable: {url} ({e})")
        return False


def download_file(
    url: str,
    dest_path: str,
    expected_sha256: Optional[str] = None,
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    dry_run: bool = False,
    min_free_space_bytes: int = 100 * 1024 * 1024,  # 100MB default
) -> bool:
    """
    Download a file with retries, checksum verification, and dry-run support.

    Args:
        url: Download URL
        dest_path: Destination file path
        expected_sha256: Optional SHA256 checksum for verification
        max_retries: Number of download attempts
        backoff_factor: Exponential backoff factor
        dry_run: If True, only check URL and disk space, do not download
        min_free_space_bytes: Minimum free space required

    Returns:
        True if download (or dry-run) succeeded, False otherwise
    """
    dest_path = str(dest_path)
    dest_dir = os.path.dirname(dest_path) or "."
    logger.info(f"Preparing to download: {url} -> {dest_path}")

    # Dry-run: check URL and disk space
    if dry_run:
        logger.info("Dry-run mode enabled.")
        url_ok = url_reachable(url)
        free_space = get_free_space_bytes(dest_dir)
        if not url_ok:
            logger.error("Dry-run failed: URL not reachable.")
            return False
        if free_space < min_free_space_bytes:
            logger.error(
                "Dry-run failed: Not enough disk space in %s "
                "(required: %d, available: %d)",
                dest_dir,
                min_free_space_bytes,
                free_space
            )
            return False
        logger.info("Dry-run passed: URL reachable and sufficient disk space.")
        return True

    # Download with retries
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Download attempt {attempt} of {max_retries}...")
            with requests.get(url, stream=True, timeout=30) as r:
                r.raise_for_status()
                os.makedirs(dest_dir, exist_ok=True)
                with open(dest_path, "wb") as f:
                    shutil.copyfileobj(r.raw, f)
            logger.info(f"Downloaded file to {dest_path}")

            # Check disk space after download
            free_space = get_free_space_bytes(dest_dir)
            if free_space < min_free_space_bytes:
                logger.error(
                    "Low disk space after download in %s (required: %d, available: %d)",
                    dest_dir,
                    min_free_space_bytes,
                    free_space)
                return False

            # Checksum verification
            if expected_sha256:
                if not verify_checksum(dest_path, expected_sha256):
                    logger.error(
                        "Checksum verification failed. Retrying download...")
                    os.remove(dest_path)
                    raise ValueError("Checksum mismatch")
            return True
        except Exception as e:
            logger.error(f"Download failed (attempt {attempt}): {e}")
            if attempt < max_retries:
                sleep_time = backoff_factor ** (attempt - 1)
                logger.info(f"Retrying in {sleep_time:.1f} seconds...")
                time.sleep(sleep_time)
            else:
                logger.error("Max retries reached. Download failed.")
                return False
    return False
