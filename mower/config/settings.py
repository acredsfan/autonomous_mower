"""
Unified configuration management system.

This module provides a single source of truth for all system configuration
with validation, environment overrides, and safe defaults.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from pydantic import BaseModel, Field, validator


class HardwareConfig(BaseModel):
    """Hardware configuration settings."""
    
    # RoboHAT configuration
    robohat_port: str = Field(default="/dev/ttyACM1", description="RoboHAT serial port")
    robohat_baudrate: int = Field(default=115200, description="RoboHAT baud rate")
    robohat_timeout: float = Field(default=1.0, description="RoboHAT command timeout")
    
    # Motor limits and safety
    steering_range: tuple[int, int] = Field(default=(-100, 100), description="Steering PWM range")
    throttle_range: tuple[int, int] = Field(default=(-100, 100), description="Throttle PWM range")
    blade_range: tuple[int, int] = Field(default=(0, 100), description="Blade PWM range")
    max_speed: int = Field(default=50, description="Maximum allowed speed")
    
    # Sensor configuration
    gps_port: str = Field(default="/dev/ttyUSB0", description="GPS serial port")
    gps_baudrate: int = Field(default=9600, description="GPS baud rate")
    i2c_bus: int = Field(default=1, description="I2C bus number")
    
    # GPIO pins
    emergency_stop_pin: int = Field(default=21, description="Emergency stop button GPIO pin")
    status_led_pin: int = Field(default=18, description="Status LED GPIO pin")
    
    @validator('steering_range', 'throttle_range', 'blade_range')
    def validate_ranges(cls, v):
        if len(v) != 2 or v[0] >= v[1]:
            raise ValueError("Range must be tuple of (min, max) with min < max")
        return v


class SafetyConfig(BaseModel):
    """Safety system configuration."""
    
    command_timeout: float = Field(default=5.0, description="Command timeout in seconds")
    emergency_stop_debounce: float = Field(default=0.1, description="Emergency stop debounce time")
    boundary_buffer: float = Field(default=1.0, description="Safety buffer around boundaries")
    max_tilt_angle: float = Field(default=30.0, description="Maximum allowed tilt angle")
    low_battery_threshold: float = Field(default=11.5, description="Low battery voltage threshold")
    
    # Watchdog timers
    motor_watchdog: float = Field(default=2.0, description="Motor command watchdog timeout")
    sensor_watchdog: float = Field(default=5.0, description="Sensor data watchdog timeout")
    vision_watchdog: float = Field(default=10.0, description="Vision system watchdog timeout")


class ServicesConfig(BaseModel):
    """Services configuration."""
    
    redis_url: str = Field(default="redis://localhost:6379", description="Redis connection URL")
    redis_db: int = Field(default=0, description="Redis database number")
    log_level: str = Field(default="INFO", description="Logging level")
    
    # Web interface
    web_host: str = Field(default="0.0.0.0", description="Web server host")
    web_port: int = Field(default=8080, description="Web server port")
    web_debug: bool = Field(default=False, description="Web server debug mode")
    google_maps_api_key: str = Field(default="", description="Google Maps API key for mapping features")
    
    # Service health check intervals
    health_check_interval: float = Field(default=1.0, description="Health check interval")
    service_startup_timeout: float = Field(default=30.0, description="Service startup timeout")


class SystemConfig(BaseModel):
    """Complete system configuration."""
    
    hardware: HardwareConfig = Field(default_factory=HardwareConfig)
    safety: SafetyConfig = Field(default_factory=SafetyConfig)
    services: ServicesConfig = Field(default_factory=ServicesConfig)
    
    # Environment and deployment
    environment: str = Field(default="production", description="Environment (dev/test/production)")
    simulation_mode: bool = Field(default=False, description="Enable hardware simulation")
    data_directory: str = Field(default="/home/pi/mower_data", description="Data storage directory")


class ConfigManager:
    """Manages system configuration with validation and environment overrides."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize configuration manager.
        
        Args:
            config_path: Path to configuration file. If None, uses default locations.
        """
        self.config_path = config_path or self._find_config_file()
        self._config: Optional[SystemConfig] = None
    
    def _find_config_file(self) -> Path:
        """Find configuration file in standard locations."""
        search_paths = [
            Path("/home/pi/autonomous_mower/mower/config/config.yaml"),
            Path("/etc/mower/config.yaml"),
            Path.cwd() / "config.yaml",
            Path(__file__).parent / "config.yaml"
        ]
        
        for path in search_paths:
            if path.exists():
                return path
        
        # Return default path if none found
        return search_paths[0]
    
    def load_config(self) -> SystemConfig:
        """Load and validate configuration."""
        if self._config is not None:
            return self._config
        
        config_data = {}
        
        # Load base configuration file if it exists
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                config_data = yaml.safe_load(f) or {}
        
        # Apply environment-specific overrides
        env_config = self._load_environment_overrides()
        config_data = self._merge_configs(config_data, env_config)
        
        # Apply environment variable overrides
        env_vars = self._load_environment_variables()
        config_data = self._merge_configs(config_data, env_vars)
        
        # Validate and create configuration object
        self._config = SystemConfig(**config_data)
        
        return self._config
    
    def _load_environment_overrides(self) -> Dict[str, Any]:
        """Load environment-specific configuration overrides."""
        environment = os.getenv("MOWER_ENV", "production")
        env_file = self.config_path.parent / f"config.{environment}.yaml"
        
        if env_file.exists():
            with open(env_file, 'r') as f:
                return yaml.safe_load(f) or {}
        
        return {}
    
    def _load_environment_variables(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        env_config = {}
        
        # Map environment variables to config keys
        env_mappings = {
            "MOWER_REDIS_URL": ["services", "redis_url"],
            "MOWER_WEB_PORT": ["services", "web_port"],
            "MOWER_LOG_LEVEL": ["services", "log_level"],
            "MOWER_SIMULATION": ["simulation_mode"],
            "MOWER_ROBOHAT_PORT": ["hardware", "robohat_port"],
            "MOWER_GPS_PORT": ["hardware", "gps_port"],
        }
        
        for env_var, config_path in env_mappings.items():
            if env_var in os.environ:
                value = os.environ[env_var]
                
                # Convert value types
                if env_var.endswith("_PORT") and value.isdigit():
                    value = int(value)
                elif env_var == "MOWER_SIMULATION":
                    value = value.lower() in ("true", "1", "yes")
                
                # Set nested configuration value
                current = env_config
                for key in config_path[:-1]:
                    current = current.setdefault(key, {})
                current[config_path[-1]] = value
        
        return env_config
    
    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge configuration dictionaries."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def save_config(self, config: SystemConfig) -> None:
        """Save configuration to file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.config_path, 'w') as f:
            yaml.dump(config.dict(), f, default_flow_style=False)
        
        self._config = config
    
    def reload_config(self) -> SystemConfig:
        """Reload configuration from file."""
        self._config = None
        return self.load_config()


# Global configuration instance
_config_manager = ConfigManager()

def get_config() -> SystemConfig:
    """Get current system configuration."""
    return _config_manager.load_config()

def reload_config() -> SystemConfig:
    """Reload configuration from file."""
    return _config_manager.reload_config()
