"""
Network diagnostics utility for the autonomous mower project.

Provides functions to check internet connectivity and access to required endpoints
(model repositories, update servers, etc.),
with clear logging and actionable error messages.

Author: Autonomous Mower Team
"""

import logging
import requests

# Use the project logger if available, else fallback
try:
    from mower.utilities.logger_config import LoggerConfigInfo as LoggerConfig
    logger = LoggerConfig.get_logger(__name__)
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("network_diagnostics")

REQUIRED_ENDPOINTS = [
    # Coral model URLs
    # Coral model URLs
    "https://github.com/google-coral/test_data/raw/master/"
    "ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite",
    "https://github.com/google-coral/test_data/raw/master/"
    "ssd_mobilenet_v2_coco_quant_postprocess.tflite",
    "https://raw.githubusercontent.com/google-coral/test_data/master/"
    "coco_labels.txt",
    # Update server (replace with actual repo URL if different)
    "https://github.com/yourusername/autonomous_mower.git",
    # Add more endpoints as needed (e.g., YOLOv8, DuckDNS, etc.)
]


def check_internet_connectivity(timeout: int = 5) -> bool:
    """
    Check if the mower has general internet connectivity.

    Returns:
        True if internet is reachable, False otherwise.
    """
    test_url = "https://www.google.com"
    try:
        logger.info(f"Checking internet connectivity via {test_url} ...")
        response = requests.get(test_url, timeout=timeout)
        if response.status_code == 200:
            logger.info("Internet connectivity: OK")
            return True
        else:
            logger.error(
                f"Internet connectivity check failed (status {
                    response.status_code})")
            return False
    except Exception as e:
        logger.error(f"Internet connectivity check failed: {e}")
        return False


def check_required_endpoints(timeout: int = 10) -> bool:
    """
    Check if all required endpoints are reachable.

    Returns:
        True if all endpoints are reachable, False otherwise.
    """
    all_ok = True
    for url in REQUIRED_ENDPOINTS:
        try:
            logger.info(f"Checking endpoint: {url}")
            # For git repo, just check if the domain is reachable via HEAD/GET
            if url.endswith(".git"):
                # Try to access the repo page
                repo_url = url.replace(".git", "")
                response = requests.head(
                    repo_url, timeout=timeout, allow_redirects=True)
            else:
                response = requests.head(
                    url, timeout=timeout, allow_redirects=True)
            if response.status_code == 200:
                logger.info(f"Endpoint reachable: {url}")
            else:
                logger.error(
                    f"Endpoint not reachable (status {
                        response.status_code}): {url}")
                all_ok = False
        except Exception as e:
            logger.error(f"Endpoint not reachable: {url} ({e})")
            all_ok = False
    return all_ok


def run_preflight_check() -> bool:
    """
    Run a pre-flight network check for setup or before downloads.

    Returns:
        True if all checks pass, False otherwise.
    """
    logger.info("Running network pre-flight check...")
    internet_ok = check_internet_connectivity()
    endpoints_ok = check_required_endpoints()
    if internet_ok and endpoints_ok:
        logger.info("Network pre-flight check PASSED.")
        return True
    else:
        logger.error(
            "Network pre-flight check FAILED. "
            "Please resolve network issues before proceeding."
        )
        return False


if __name__ == "__main__":
    # Allow running as a standalone script
    import sys
    result = run_preflight_check()
    sys.exit(0 if result else 1)
