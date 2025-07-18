"""
Configuration utilities for the web UI.
"""

import os
from typing import List


class WebUIConfig:
    """Configuration class for web UI settings."""
    
    def __init__(self):
        self.streaming_fps = int(os.getenv("STREAMING_FPS", 30))
        self.jpeg_quality = int(os.getenv("JPEG_QUALITY", 95))
        self.web_ui_port = int(os.getenv("WEB_UI_PORT", 5000))
        self.use_simulation = os.environ.get("USE_SIMULATION", "").lower() in ("true", "1", "yes")
        self.google_maps_api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
        
    @property
    def allowed_origins(self) -> List[str]:
        """Get allowed CORS origins from environment."""
        origins_str = os.environ.get("ALLOWED_ORIGINS", "")
        if not origins_str:
            # Default to localhost patterns for development
            return [
                "http://localhost:*",
                "http://127.0.0.1:*",
                "https://localhost:*",
                "https://127.0.0.1:*"
            ]
        return [origin.strip() for origin in origins_str.split(",") if origin.strip()]
    
    @property
    def cors_config(self) -> dict:
        """Get CORS configuration dictionary."""
        return {
            "resources": {r"/*": {"origins": self.allowed_origins}},
            "supports_credentials": True,
            "allow_headers": [
                "Content-Type", 
                "Authorization", 
                "Access-Control-Allow-Credentials", 
                "CF-Access-Client-Id", 
                "CF-Access-Client-Secret"
            ]
        }
    
    @property
    def socketio_config(self) -> dict:
        """Get SocketIO configuration dictionary."""
        return {
            "cors_allowed_origins": self.allowed_origins,
            "cors_credentials": True,
            "ping_timeout": 20,
            "ping_interval": 25,
            "logger": True,
            "engineio_logger": True,
            "transports": ['polling', 'websocket']
        }
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of warnings."""
        warnings = []
        
        if not self.google_maps_api_key:
            warnings.append("GOOGLE_MAPS_API_KEY not set - map functionality will be limited")
            
        if "*" in str(self.allowed_origins):
            warnings.append("CORS origins contain wildcards - this may be a security risk in production")
            
        if self.streaming_fps > 60:
            warnings.append(f"High streaming FPS ({self.streaming_fps}) may impact performance")
            
        return warnings