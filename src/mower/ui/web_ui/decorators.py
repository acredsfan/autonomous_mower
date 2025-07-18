"""
Decorators for web UI functionality.
"""

from functools import wraps
from flask import jsonify
from mower.utilities.logger_config import LoggerConfigInfo

logger = LoggerConfigInfo.get_logger(__name__)


def api_error_handler(func):
    """
    Decorator to handle API errors consistently.
    
    This decorator wraps API endpoints to provide consistent error handling
    and logging. It catches exceptions and returns a standardized JSON error
    response.
    
    Args:
        func: The API endpoint function to wrap
        
    Returns:
        The wrapped function with error handling
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"API error in {func.__name__}: {e}", exc_info=True)
            return jsonify({"success": False, "error": str(e)}), 500
    return wrapper


def validate_json_request(required_fields=None):
    """
    Decorator to validate JSON request data.
    
    Args:
        required_fields: List of required field names in the JSON payload
        
    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from flask import request
            
            if not request.is_json:
                return jsonify({"success": False, "error": "Request must be JSON"}), 400
                
            data = request.get_json()
            if not data:
                return jsonify({"success": False, "error": "No JSON data provided"}), 400
                
            if required_fields:
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    return jsonify({
                        "success": False, 
                        "error": f"Missing required fields: {', '.join(missing_fields)}"
                    }), 400
                    
            return func(*args, **kwargs)
        return wrapper
    return decorator