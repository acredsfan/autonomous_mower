"""Web interface for the autonomous mower."""

import os
import threading
from typing import TYPE_CHECKING, Optional
from flask import Flask  # type:ignore
from flask_socketio import SocketIO  # type:ignore

from mower.utilities import LoggerConfigInfo
from mower.ui.web_ui.app import create_app
from mower.config_management import get_config_manager

if TYPE_CHECKING:
    from mower.mower import Mower


class WebInterface:
    """Web interface for controlling the mower."""

    def __init__(self, mower: 'Mower'):
        """Initialize the web interface.

        Args:
            mower: The mower instance to control.
        """
        self.logger = LoggerConfigInfo.get_logger(__name__)
        self.mower = mower
        self.app: Optional[Flask] = None
        self.socketio: Optional[SocketIO] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._is_running = False

    def start(self) -> None:
        """Start the web interface.

        This method:
        1. Creates the Flask application
        2. Starts the web server in a separate thread
        3. Sets up WebSocket communication
        """
        if self._is_running:
            self.logger.warning("Web interface is already running")
            return

        try:
            # Create Flask app and SocketIO instance
            self.app, self.socketio = create_app(self.mower)

            # Start the web server in a separate thread
            self._thread = threading.Thread(
                target=self._run_server,
                daemon=True
                )
            self._thread.start()

            self._is_running = True
            self.logger.info("Web interface started successfully")
        except Exception as e:
            self.logger.error(f"Failed to start web interface: {e}")
            raise

    def stop(self) -> None:
        """Stop the web interface.

        This method:
        1. Signals the server to shut down
        2. Waits for the server thread to complete
        3. Cleans up resources
        """
        if not self._is_running:
            self.logger.warning("Web interface is not running")
            return

        try:
            # Signal the server to stop
            self._stop_event.set()

            # Wait for the server thread to complete
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=5.0)

            # Clean up resources
            if self.socketio:
                self.socketio.stop()

            self._is_running = False
            self.logger.info("Web interface stopped successfully")
        except Exception as e:
            self.logger.error(f"Error stopping web interface: {e}")
            raise

    def _run_server(self) -> None:
        """Run the web server.

        This method runs in a separate thread and handles the actual
        web server operation. If SSL is enabled in the configuration,
        the server will use HTTPS.
        """
        try:
            if self.socketio and self.app:
                # Get configuration from mower's config manager
                config_manager = get_config_manager()
                web_ui_config = config_manager.get_config_section('web_ui')

                # Get web UI port from config or environment
                port = int(web_ui_config.get('port', 5000))

                # Check if SSL is enabled
                ssl_enabled = web_ui_config.get('enable_ssl', False)
                ssl_context = None

                if ssl_enabled:
                    ssl_cert = web_ui_config.get('ssl_cert_path', '')
                    ssl_key = web_ui_config.get('ssl_key_path', '')

                    if ssl_cert and ssl_key and os.path.exists(ssl_cert) and os.path.exists(ssl_key):
                        self.logger.info(f"Starting web server with SSL on port {port}")
                        ssl_context = (ssl_cert, ssl_key)
                    else:
                        self.logger.warning(
                            "SSL is enabled but certificate or key file not found. "
                            "Falling back to HTTP."
                        )

                # Start the server
                self.socketio.run(
                    self.app,
                    host='0.0.0.0',
                    port=port,
                    debug=False,
                    use_reloader=False,
                    ssl_context=ssl_context
                )
        except Exception as e:
            self.logger.error(f"Error in web server thread: {e}")
            self._is_running = False
            raise

    @property
    def is_running(self) -> bool:
        """Check if the web interface is running.

        Returns:
            bool: True if the web interface is running, False otherwise.
        """
        return self._is_running

    def cleanup(self):
        """Clean up resources used by the web interface."""
        try:
            # Add any specific cleanup logic here
            self.logger.info("Web interface cleaned up successfully.")
        except Exception as e:
            self.logger.error(f"Error cleaning up web interface: {e}")
