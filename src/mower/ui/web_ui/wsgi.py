"""
WSGI entry point for the autonomous mower web interface.

This module provides the WSGI application entry point for running the web
    interface in a production environment. It handles:
- Web interface initialization
- Path configuration
- Logging setup
- Error handling
"""

import os
import sys
from typing import Optional

from mower.ui.web_ui.web_interface import WebInterface
from mower.utilities.logger_config import LoggerConfigInfo

# Initialize logger
logging = LoggerConfigInfo.get_logger(__name__)

# Add project root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Global instance
_web_interface: Optional[WebInterface] = None


def start_web_interface() -> None:
    """
    Start the web interface if it's not already running.

    This function:
    1. Checks if the interface is already running
    2. Initializes a new interface if needed
    3. Handles any startup errors

    Returns:
        None

    Raises:
        RuntimeError: If the web interface fails to start
    """
    global _web_interface

    try:
        # Check if already running
        if _web_interface and _web_interface.is_running:
            logging.warning("Web interface is already running")
            return

        # Create and start new instance
        from mower.mower import Mower

        mower = Mower()
        _web_interface = WebInterface(mower)
        _web_interface.start()

        logging.info("Web interface started successfully")
    except Exception as e:
        logging.error(f"Failed to start web interface: {e}")
        raise RuntimeError(f"Web interface startup failed: {e}")


def stop_web_interface() -> None:
    """
    Stop the web interface if it's running.

    This function:
    1. Checks if the interface exists and is running
    2. Stops the interface gracefully
    3. Handles any shutdown errors

    Returns:
        None
    """
    global _web_interface

    try:
        if _web_interface and _web_interface.is_running:
            _web_interface.stop()
            logging.info("Web interface stopped successfully")
    except Exception as e:
        logging.error(f"Error stopping web interface: {e}")


def get_application():
    """
    Get the WSGI application instance.

    This function is used by WSGI servers to get the application instance.
    It ensures the web interface is started before returning the app.

    Returns:
        flask.Flask: The Flask application instance
    """
    if not _web_interface or not _web_interface.is_running:
        start_web_interface()
    return _web_interface.app


if __name__ == "__main__":
    try:
        start_web_interface()
    except Exception as e:
        logging.error(f"Failed to start web interface from __main__: {e}")
        sys.exit(1)
