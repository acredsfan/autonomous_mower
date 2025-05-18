"""
Configuration schema and validation for the autonomous mower.

Defines a Pydantic model for validating configuration files.
Allows extra fields for backward compatibility.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ValidationError, Extra


class RemoteAccessConfig(BaseModel):
    REMOTE_ACCESS_TYPE: str = Field(
        default="port_forward",
        description="Type of remote access")
    WEB_UI_PORT: Optional[int] = Field(default=8080, description="Web UI port")
    DDNS_PROVIDER: Optional[str] = None
    DDNS_DOMAIN: Optional[str] = None
    DDNS_TOKEN: Optional[str] = None
    CLOUDFLARE_TOKEN: Optional[str] = None
    CLOUDFLARE_ZONE_ID: Optional[str] = None
    CLOUDFLARE_TUNNEL_NAME: Optional[str] = "mower-tunnel"
    CUSTOM_DOMAIN: Optional[str] = None
    SSL_EMAIL: Optional[str] = None
    NGROK_AUTH_TOKEN: Optional[str] = None

    class Config:
        extra = Extra.allow  # Allow extra fields for backward compatibility


class AuthConfig(BaseModel):
    auth_username: str = Field(default="admin", description="Admin username")

    class Config:
        extra = Extra.allow


class PowerSettingsConfig(BaseModel):
    power_settings: Optional[Dict[str, Any]] = None

    class Config:
        extra = Extra.allow


class MowerConfig(BaseModel):
    # Top-level config model that includes all known sections
    REMOTE_ACCESS_TYPE: Optional[str] = None
    WEB_UI_PORT: Optional[int] = None
    DDNS_PROVIDER: Optional[str] = None
    DDNS_DOMAIN: Optional[str] = None
    DDNS_TOKEN: Optional[str] = None
    CLOUDFLARE_TOKEN: Optional[str] = None
    CLOUDFLARE_ZONE_ID: Optional[str] = None
    CLOUDFLARE_TUNNEL_NAME: Optional[str] = None
    CUSTOM_DOMAIN: Optional[str] = None
    SSL_EMAIL: Optional[str] = None
    NGROK_AUTH_TOKEN: Optional[str] = None
    auth_username: Optional[str] = None
    power_settings: Optional[Dict[str, Any]] = None

    class Config:
        extra = Extra.allow  # Allow extra fields for backward compatibility


def validate_config(config: dict) -> MowerConfig:
    """
    Validate a configuration dictionary using the MowerConfig schema.

    Args:
        config: The configuration dictionary to validate.

    Returns:
        MowerConfig: The validated config object.

    Raises:
        ValidationError: If the config does not match the schema.
    """
    try:
        return MowerConfig(**config)
    except ValidationError as e:
        # Raise with a clear error message
        raise ValidationError(f"Configuration validation failed: {e}") from e
