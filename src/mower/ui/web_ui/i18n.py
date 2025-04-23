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
    app.config['BABEL_DEFAULT_LOCALE'] = 'en'
    app.config['BABEL_DEFAULT_TIMEZONE'] = 'UTC'
    app.config['BABEL_TRANSLATION_DIRECTORIES'] = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'translations'
    )
    
    # Initialize Babel with the app
    babel.init_app(app)
    
    # Set up locale selector
    @babel.locale_selector
    def get_locale():
        # 1. Check if user has explicitly set a language in the session
        if 'language' in session:
            return session['language']
        
        # 2. Otherwise, try to detect the language from the browser
        return request.accept_languages.best_match(['en', 'es', 'fr', 'de', 'zh'])

def get_supported_languages():
    """Get a list of supported languages.
    
    Returns:
        A list of dictionaries with language code and name.
    """
    return [
        {'code': 'en', 'name': 'English'},
        {'code': 'es', 'name': 'Español'},
        {'code': 'fr', 'name': 'Français'},
        {'code': 'de', 'name': 'Deutsch'},
        {'code': 'zh', 'name': '中文'}
    ]