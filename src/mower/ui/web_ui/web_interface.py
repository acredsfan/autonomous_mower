"""Web interface for the autonomous mower."""

import os
import threading
from typing import TYPE_CHECKING, Optional

from flask import Flask
from flask_socketio import SocketIO

from mower.ui.web_ui.app import create_app
from mower.utilities import LoggerConfigInfo

if TYPE_CHECKING:
    from mower.mower import Mower


class WebInterface:
    """Web interface for controlling the mower."""

    def __init__(self, mower: "Mower"): # mower is actually ResourceManager instance
        """Initialize the web interface.

        Args:
            mower: The mower instance (actually ResourceManager) to control.
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
        print("DEBUG: WebInterface.start() - Entered method") # ADDED
        self.logger.info("WebInterface.start() called.")

        if self._is_running:
            self.logger.warning("Web interface is already running")
            print("DEBUG: WebInterface.start() - Already running, returning.") # ADDED
            return

        try:
            # Create Flask app and SocketIO instance
            print(f"DEBUG: WebInterface.start() - self.mower type: {type(self.mower)}") # ADDED
            self.logger.info(f"WebInterface: self.mower type is {type(self.mower)}")

            # Pass self.mower (which is ResourceManager) to create_app
            print("DEBUG: WebInterface.start() - Calling create_app...") # ADDED
            app_instance, socketio_instance = create_app(self.mower)
            self.app = app_instance
            self.socketio = socketio_instance
            print("DEBUG: WebInterface.start() - create_app returned") # ADDED
            self.logger.info("WebInterface: create_app returned successfully.")

            # Start the web server in a separate thread
            self._thread = threading.Thread(target=self._run_server, daemon=True)
            self._thread.start()
            print(f"DEBUG: WebInterface.start() - Thread started: {self._thread.ident}") # ADDED
            self.logger.info(f"WebInterface: Server thread {self._thread.ident} started.")

            self._is_running = True
            self.logger.info("Web interface started successfully")
            print("DEBUG: WebInterface.start() - Exiting method normally.") # ADDED
        except Exception as e:
            print(f"DEBUG: WebInterface.start() - Exception caught: {e}") # ADDED
            self.logger.error(f"Failed to start web interface: {e}", exc_info=True)
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
        if not self._is_running:
            self.logger.warning("Web interface is not running")
            return

        try:
            self.logger.info("Attempting to stop web interface...")
            # Signal the server to stop
            if self.socketio:
                self.logger.info("Requesting SocketIO server to stop...")
                try:
                    # This is a common way to ask Flask-SocketIO to shutdown
                    # It might not be available in all versions or configurations
                    # If this doesn't work, the thread join timeout is the fallback
                    self.socketio.server.shutdown()
                    self.logger.info("SocketIO server shutdown requested.")
                except Exception as e:
                    self.logger.warning(f"Could not explicitly call socketio.server.shutdown(): {e}. Relying on thread join.")

            self._stop_event.set() # Ensure our internal stop event is also set

            # Wait for the server thread to complete
            if self._thread and self._thread.is_alive():
                self.logger.info(f"Waiting for web server thread (id: {self._thread.ident}) to join...")
                self._thread.join(timeout=10.0) # Increased timeout
                if self._thread.is_alive():
                    self.logger.warning(f"Web server thread (id: {self._thread.ident}) did not join in time.")
                else:
                    self.logger.info(f"Web server thread (id: {self._thread.ident}) joined successfully.")


            # Clean up resources - socketio.stop() might be redundant if shutdown worked
            # but it's good for cleanup.
            if self.socketio:
                try:
                    self.logger.info("Calling socketio.stop() for final cleanup...")
                    self.socketio.stop() # Ensure this is called for cleanup
                    self.logger.info("Socketio.stop() called.")
                except Exception as e:
                    self.logger.error(f"Error during socketio.stop(): {e}")


            self._is_running = False
            self.logger.info("Web interface stopped successfully")
        except Exception as e:
            self.logger.error(f"Error stopping web interface: {e}", exc_info=True)
            # Do not re-raise here if we want the main cleanup to continue
            # raise

    def _run_server(self) -> None:
        """Run the web server.

        This method runs in a separate thread and handles the actual
        web server operation.
        """
        print(f"DEBUG: WebInterface._run_server() - Entered method in thread {threading.get_ident()}") # ADDED
        try:
            if self.socketio and self.app:
                print("DEBUG: WebInterface._run_server() - socketio and app exist. Calling socketio.run()") # ADDED
                self.logger.info("Attempting to start Flask-SocketIO server on 0.0.0.0:5000...")
                self.socketio.run(
                    self.app,
                    host="0.0.0.0",
                    port=int(os.environ.get("MOWER_WEB_PORT", 5000)),
                    debug=False, # Keep debug False for production/stability
                    use_reloader=False, # Reloader should be False for threads
                    allow_unsafe_werkzeug=True, # Necessary for some SocketIO setups
                    # log_output=True # Consider adding if Flask/SocketIO logs are not appearing
                )
                self.logger.info("Flask-SocketIO server has stopped.")
                print("DEBUG: WebInterface._run_server() - socketio.run() returned.") # ADDED
            else:
                self.logger.error("SocketIO or Flask app not initialized. Cannot start server.")
                print("DEBUG: WebInterface._run_server() - socketio or app is None.") # ADDED
        except Exception as e:
            print(f"DEBUG: WebInterface._run_server() - Exception caught: {e}") # ADDED
            self.logger.error(f"Error in web server thread during socketio.run: {e}", exc_info=True)
            self._is_running = False # Ensure state reflects failure
        finally:
            self.logger.info(f"Web server thread (id: {threading.get_ident()}) is exiting.")
            print(f"DEBUG: WebInterface._run_server() - Exiting method in thread {threading.get_ident()}") # ADDED
            self._is_running = False # Ensure this is set if server stops for any reason

    @property
    def is_running(self) -> bool:
        """Check if the web interface is running.

        Returns:
            bool: True if the web interface is running, False otherwise.
        """
        return self._is_running
