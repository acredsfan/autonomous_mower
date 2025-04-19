"""
Configuration management package for the autonomous mower.

This package provides a standardized configuration management system for the
autonomous mower project. It includes interfaces and implementations for
loading, saving, and accessing configuration from various sources, such as
environment variables, configuration files, and command-line arguments.

Usage:
    from mower.config_management import get_config_manager

    # Get the configuration manager
    config_manager = get_config_manager()

    # Get a configuration value
    value = config_manager.get('key', 'default_value')

    # Set a configuration value
    config_manager.set('key', 'value')

    # Save configuration to a file
    config_manager.save('config.json')
"""

from mower.config_management.config_interface import ConfigurationInterface
from mower.config_management.config_manager import (
    ConfigurationManager,
    get_config_manager,
    initialize_config_manager,
    get_config,
    set_config
)
from mower.config_management.config_source import (
    ConfigurationSource,
    EnvironmentConfigurationSource,
    FileConfigurationSource,
    DictConfigurationSource
)
from mower.config_management.constants import (
    BASE_DIR,
    CONFIG_DIR,
    USER_POLYGON_PATH,
    HOME_LOCATION_PATH,
    MOWING_SCHEDULE_PATH,
    PATTERN_PLANNER_PATH,
    DEFAULT_CONFIG,
    ENV_PREFIX,
    DEFAULT_CONFIG_FILE,
    DEFAULT_ENV_FILE
)

# Initialize the configuration manager with default values
def init_config():
    """
    Initialize the configuration manager with default values.

    This function initializes the configuration manager with the default values
    from constants.py, loads configuration from the default configuration file
    if it exists, and adds an environment variables source.

    Returns:
        ConfigurationManager: The initialized configuration manager
    """
    return initialize_config_manager(
        defaults=DEFAULT_CONFIG,
        config_file=DEFAULT_CONFIG_FILE,
        env_file=DEFAULT_ENV_FILE
    )

# Initialize the configuration manager
init_config()

__all__ = [
    'ConfigurationInterface',
    'ConfigurationManager',
    'get_config_manager',
    'initialize_config_manager',
    'get_config',
    'set_config',
    'init_config',
    'ConfigurationSource',
    'EnvironmentConfigurationSource',
    'FileConfigurationSource',
    'DictConfigurationSource',
    'BASE_DIR',
    'CONFIG_DIR',
    'USER_POLYGON_PATH',
    'HOME_LOCATION_PATH',
    'MOWING_SCHEDULE_PATH',
    'PATTERN_PLANNER_PATH',
    'DEFAULT_CONFIG',
    'ENV_PREFIX',
    'DEFAULT_CONFIG_FILE',
    'DEFAULT_ENV_FILE'
]
