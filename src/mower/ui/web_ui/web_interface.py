"""Web interface for the autonomous mower."""

import os
import threading
from typing import TYPE_CHECKING, Optional

from flask import Flask
from flask_socketio import SocketIO

from mower.ui.web_ui.app import create_app
from mower.utilities import LoggerConfigInfo

if TYPE_CHECKING:
    from mower.main_controller import ResourceManager


class WebInterface:
    """Web interface for controlling the mower."""

    def __init__(self, mower: "ResourceManager"):
        """Initialize the web interface.

        Args:
            mower: The ResourceManager instance to control.
        """
        self.logger = LoggerConfigInfo.get_logger(__name__)
        self.mower = mower
        self.app: Optional[Flask] = None
        self.socketio: Optional[SocketIO] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._is_running = False
        self._lock = threading.Lock()  # Add thread safety

    def start(self) -> None:
        """Start the web interface.

        This method:
        1. Creates the Flask application
        2. Starts the web server in a separate thread
        3. Sets up WebSocket communication
        """
        with self._lock:
            self.logger.info("WebInterface.start() called.")

            if self._is_running:
                self.logger.warning("Web interface is already running")
                return

            try:
                # Create Flask app and SocketIO instance
                self.logger.info(f"WebInterface: self.mower type is {type(self.mower)}")

                # Pass self.mower (which is ResourceManager) to create_app
                app_instance, socketio_instance = create_app(self.mower)
                self.app = app_instance
                self.socketio = socketio_instance
                self.logger.info("WebInterface: create_app returned successfully.")

                # Start the web server in a separate thread
                self._thread = threading.Thread(target=self._run_server, daemon=True)
                self._thread.start()
                self.logger.info(f"WebInterface: Server thread {self._thread.ident} started.")

                self._is_running = True
                self.logger.info("Web interface started successfully")
            except Exception as e:
                self.logger.error(f"Failed to start web interface: {e}", exc_info=True)
                self._is_running = False  # Ensure state is consistent on failure
                raise

    def run(self) -> None:
        """Run the web interface (calls start)."""
        self.logger.info("WebInterface.run() called, redirecting to start()")
        self.start()

    def stop(self) -> None:
        """Stop the web interface.

        This method:
        1. Signals the server to shut down
        2. Waits for the server thread to complete
        3. Cleans up resources
        """
        with self._lock:
            if not self._is_running:
                self.logger.warning("Web interface is not running")
                return

            try:
                self.logger.info("Attempting to stop web interface...")
                self._stop_event.set()  # Signal stop first
                
                # Clean up SocketIO server
                if self.socketio:
                    self.logger.info("Requesting SocketIO server to stop...")
                    try:
                        self.socketio.server.shutdown()
                        self.logger.info("SocketIO server shutdown requested.")
                    except Exception as e:
                        self.logger.warning(f"Could not explicitly call socketio.server.shutdown(): {e}")

                # Wait for the server thread to complete
                if self._thread and self._thread.is_alive():
                    self.logger.info(f"Waiting for web server thread (id: {self._thread.ident}) to join...")
                    self._thread.join(timeout=10.0)
                    if self._thread.is_alive():
                        self.logger.warning(f"Web server thread (id: {self._thread.ident}) did not join in time.")
                    else:
                        self.logger.info(f"Web server thread (id: {self._thread.ident}) joined successfully.")

                # Final cleanup
                if self.socketio:
                    try:
                        self.socketio.stop()
                        self.logger.info("SocketIO cleanup completed.")
                    except Exception as e:
                        self.logger.error(f"Error during socketio.stop(): {e}")

                self._is_running = False
                self.logger.info("Web interface stopped successfully")
                
            except Exception as e:
                self.logger.error(f"Error stopping web interface: {e}", exc_info=True)
                self._is_running = False  # Ensure state is consistent even on error

    def _run_server(self) -> None:
        """Run the web server.

        This method runs in a separate thread and handles the actual
        web server operation.
        """
        try:
            if self.socketio and self.app:
                self.logger.info("Attempting to start Flask-SocketIO server on 0.0.0.0:5000 (IPv4 all interfaces)...")
                try:
                    self.socketio.run(
                        self.app,
                        host="0.0.0.0",
                        port=int(os.environ.get("WEB_UI_PORT", 5000)),
                        debug=False, # Keep debug False for production/stability
                        use_reloader=False, # Reloader should be False for threads
                        allow_unsafe_werkzeug=True, # Necessary for some SocketIO setups
                        # log_output=True # Consider adding if Flask/SocketIO logs are not appearing
                    )
                    self.logger.info("Flask-SocketIO server has stopped.")
                except Exception as run_exc:
                    self.logger.error(f"Exception during socketio.run: {run_exc}", exc_info=True)
            else:
                self.logger.error("SocketIO or Flask app not initialized. Cannot start server.")
        except Exception as e:
            self.logger.error(f"Error in web server thread during socketio.run: {e}", exc_info=True)
            self._is_running = False # Ensure state reflects failure
        finally:
            self.logger.info(f"Web server thread (id: {threading.get_ident()}) is exiting.")
            self._is_running = False # Ensure this is set if server stops for any reason

    @property
    def is_running(self) -> bool:
        """Check if the web interface is running.

        Returns:
            bool: True if the web interface is running, False otherwise.
        """
        return self._is_running
