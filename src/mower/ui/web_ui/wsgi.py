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
import threading
from typing import Optional

from mower.main_controller import ResourceManager
from mower.ui.web_ui.web_interface import WebInterface
from mower.utilities.logger_config import LoggerConfigInfo

# Initialize logger
logging = LoggerConfigInfo.get_logger(__name__)

# Add project root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class WSGIManager:
    """Thread-safe WSGI application manager."""
    
    def __init__(self):
        self._web_interface: Optional[WebInterface] = None
        self._lock = threading.Lock()
    
    def get_application(self):
        """Get the WSGI application instance with thread safety."""
        with self._lock:
            if not self._web_interface or not self._web_interface.is_running:
                self._start_web_interface()
            return self._web_interface.app
    
    def _start_web_interface(self) -> None:
        """Start the web interface with proper error handling."""
        try:
            if self._web_interface and self._web_interface.is_running:
                logging.warning("Web interface is already running")
                return

            mower = ResourceManager()
            self._web_interface = WebInterface(mower)
            self._web_interface.start()
            logging.info("Web interface started successfully")
        except Exception as e:
            logging.error(f"Failed to start web interface: {e}")
            raise RuntimeError(f"Web interface startup failed: {e}")
    
    def stop_web_interface(self) -> None:
        """Stop the web interface if it's running."""
        with self._lock:
            try:
                if self._web_interface and self._web_interface.is_running:
                    self._web_interface.stop()
                    logging.info("Web interface stopped successfully")
            except Exception as e:
                logging.error(f"Error stopping web interface: {e}")


# Global WSGI manager instance
_wsgi_manager = WSGIManager()


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
    _wsgi_manager._start_web_interface()


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
    _wsgi_manager.stop_web_interface()


def get_application():
    """
    Get the WSGI application instance.

    This function is used by WSGI servers to get the application instance.
    It ensures the web interface is started before returning the app.

    Returns:
        flask.Flask: The Flask application instance
    """
    return _wsgi_manager.get_application()


# WSGI application entry point
application = get_application


if __name__ == "__main__":
    try:
        start_web_interface()
    except Exception as e:
        logging.error(f"Failed to start web interface from __main__: {e}")
        sys.exit(1)
