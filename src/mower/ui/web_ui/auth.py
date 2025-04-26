"""Authentication module for the web interface.

This module provides functions for authenticating users and protecting routes
in the web interface.
"""

import functools
import hashlib
import os
from typing import Callable, Optional, TypeVar, cast

from flask import (
    Flask,
    Response,
    current_app,
    flash,
    redirect,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from mower.utilities.logger_config import LoggerConfigInfo
from mower.utilities.audit_log import get_audit_logger, AuditEventType

# Initialize logger
logger = LoggerConfigInfo.get_logger(__name__)

# Get audit logger
audit_logger = get_audit_logger()

# Type variable for route functions
F = TypeVar("F", bound=Callable[..., Response])


def init_auth(app: Flask, config: dict) -> None:
    """Initialize authentication for the Flask application.

    Args:
        app: The Flask application instance.
        config: Configuration dictionary containing auth settings.
    """
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(24).hex())

    # Add authentication middleware if required
    if config.get("auth_required", True):
        logger.info("Authentication is enabled for the web interface")

        # Register the before_request handler to check authentication
        @app.before_request
        def check_auth() -> Optional[Response]:
            """Check if the user is authenticated before processing requests."""
            # Skip authentication for login page and static files
            if request.endpoint == "login" or request.path.startswith(
                "/static/"
            ):
                return None

            if not session.get("authenticated"):
                return redirect(url_for("login"))

            return None

        # Add login route
        @app.route("/login", methods=["GET", "POST"])
        def login() -> Response:
            """Handle user login."""
            error = None

            if request.method == "POST":
                username = request.form.get("username", "")
                password = request.form.get("password", "")

                if authenticate(username, password, config):
                    session["authenticated"] = True
                    session["username"] = username

                    # Get client IP address
                    ip_address = request.remote_addr

                    # Log successful login
                    logger.info(
                        f"User '{username}' logged in successfully from {ip_address}"
                    )

                    # Audit log for successful login
                    audit_logger.log_login(username, ip_address, success=True)

                    # Redirect to the page the user was trying to access
                    next_page = request.args.get("next", "/")
                    return redirect(next_page)
                else:
                    error = "Invalid username or password"

                    # Get client IP address
                    ip_address = request.remote_addr

                    # Log failed login attempt
                    logger.warning(
                        f"Failed login attempt for user '{username}' from {ip_address}"
                    )

                    # Audit log for failed login
                    audit_logger.log_login(
                        username, ip_address, success=False
                    )

            return current_app.send_static_file("login.html")

        # Add logout route
        @app.route("/logout")
        def logout() -> Response:
            """Handle user logout."""
            if session.get("authenticated"):
                username = session.get("username", "Unknown")

                # Get client IP address
                ip_address = request.remote_addr

                # Log logout
                logger.info(f"User '{username}' logged out from {ip_address}")

                # Audit log for logout
                audit_logger.log_logout(username, ip_address)

            session.clear()
            return redirect(url_for("login"))

    else:
        logger.info("Authentication is disabled for the web interface")


def authenticate(username: str, password: str, config: dict) -> bool:
    """Authenticate a user with the provided credentials.

    Args:
        username: The username to authenticate.
        password: The password to authenticate.
        config: Configuration dictionary containing auth settings.

    Returns:
        True if authentication is successful, False otherwise.
    """
    if not config.get("auth_required", True):
        return True

    expected_username = config.get("auth_username", "admin")
    expected_password = config.get("auth_password", "")

    # If no password is set, authentication fails
    if not expected_password:
        logger.warning(
            "Authentication failed: No password set in configuration"
        )
        return False

    # Check if username and password match
    if username == expected_username and password == expected_password:
        return True

    return False


def require_auth(func: F) -> F:
    """Decorator to require authentication for a route.

    This decorator can be used to protect specific routes when the global
    authentication is disabled.

    Args:
        func: The route function to protect.

    Returns:
        The wrapped function that checks authentication.
    """

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        if not session.get("authenticated"):
            return redirect(url_for("login", next=request.path))
        return func(*args, **kwargs)

    return cast(F, wrapped)
