"""Web interface for the autonomous mower."""

import threading
from typing import TYPE_CHECKING, Optional
from flask import Flask
from flask_socketio import SocketIO

from mower.utilities import LoggerConfigInfo
from mower.ui.web_ui.app import create_app

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
        web server operation.
        """
        try:
            if self.socketio and self.app:
                self.socketio.run(
                    self.app,
                    host='0.0.0.0',
                    port=5000,
                    debug=False,
                    use_reloader=False
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