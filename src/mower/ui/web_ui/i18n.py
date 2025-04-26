"""Internationalization module for the web interface.

This module provides functions for translating the web interface
into different languages using Flask-Babel.
"""

import os
from flask import Flask, request, session
from flask_babel import Babel

# Initialize Babel
babel = Babel()


def init_babel(app: Flask) -> None:
    """Initialize Babel for the Flask application.

    Args:
        app: The Flask application instance.
    """
    # Configure Babel
    app.config["BABEL_DEFAULT_LOCALE"] = "en"
    app.config["BABEL_DEFAULT_TIMEZONE"] = "UTC"
    app.config["BABEL_TRANSLATION_DIRECTORIES"] = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "translations"
    )

    # Locale selector function
    def get_locale():
        if "language" in session:
            return session["language"]
        codes = [lang["code"] for lang in get_supported_languages()]
        return request.accept_languages.best_match(codes)

    # Initialize Babel with custom locale selector
    babel.init_app(app, locale_selector=get_locale)


def get_supported_languages():
    """Get a list of supported languages.

    Returns:
        A list of dictionaries with language code and name.
    """
    return [
        {"code": "en", "name": "English"},
        {"code": "es", "name": "Español"},
        {"code": "fr", "name": "Français"},
        {"code": "de", "name": "Deutsch"},
        {"code": "zh", "name": "中文"},
    ]
