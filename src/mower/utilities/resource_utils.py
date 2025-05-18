"""
Resource management utilities for the autonomous mower.

This module provides utilities for resource management, configuration loading/saving,
and initialization/cleanup. It centralizes common functionality used across
different components of the autonomous mower project.
"""

from mower.utilities.config_schema import validate_config, ValidationError
import threading
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Union, Type

from mower.config_management import (
    get_config_manager,
    get_config,
    set_config,
    CONFIG_DIR,
)
from mower.utilities.logger_config import LoggerConfigInfo

# Initialize logger
logger = LoggerConfigInfo.get_logger(__name__)

# Import config schema validator


def load_config(filename: str) -> Optional[Dict[str, Any]]:
    """
    Load a configuration file using the configuration manager.

    Args:
        filename: Name or path of the configuration file to load

    Returns:
        dict: Configuration data, or None if the file doesn't exist or there was an error
    """
    try:
        # Get the configuration manager
        config_manager = get_config_manager()

        # Get the full path to the configuration file
        if isinstance(filename, str) and not Path(filename).is_absolute():
            config_path = CONFIG_DIR / filename
        else:
            config_path = Path(filename)

        # Check if the file exists
        if not config_path.exists():
            logger.warning(f"Configuration file {filename} not found")
            return None

        # Load the configuration file
        config = config_manager.load(str(config_path))
        logger.info(f"Loaded configuration from {filename}")

        # Validate configuration schema
        try:
            validated = validate_config(config)
            return validated.model_dump()  # Return as dict for backward compatibility
        except ValidationError as ve:
            logger.error(
                f"Configuration validation failed for {filename}: {ve}")
            return None

    except Exception as e:
        logger.error(f"Error loading config file {filename}: {e}")
        return None


def save_config(filename: str, data: Dict[str, Any]) -> bool:
    """
    Save configuration data to a file using the configuration manager.

    Args:
        filename: Name or path of the configuration file to save
        data: Configuration data to save

    Returns:
        bool: True if the configuration was saved successfully, False otherwise
    """
    try:
        # Get the configuration manager
        config_manager = get_config_manager()

        # Get the full path to the configuration file
        if isinstance(filename, str) and not Path(filename).is_absolute():
            config_path = CONFIG_DIR / filename
        else:
            config_path = Path(filename)

        # Save the configuration file
        config_manager.save(str(config_path), data)
        logger.info(f"Saved configuration to {filename}")
        return True
    except Exception as e:
        logger.error(f"Error saving config file {filename}: {e}")
        return False


def cleanup_resources(
    resources: Dict[str, Any], initialized: bool, lock: threading.Lock
) -> bool:
    """
    Clean up all resources.

    Args:
        resources: Dictionary of resources to clean up
        initialized: Flag indicating if resources are initialized
        lock: Lock for thread-safe access to resources

    Returns:
        bool: True if cleanup was successful, False otherwise
    """
    with lock:
        if not initialized:
            return True

        try:
            # Clean up hardware in reverse order
            for name, resource in reversed(list(resources.items())):
                try:
                    if hasattr(resource, "cleanup"):
                        resource.cleanup()
                    elif hasattr(resource, "shutdown"):
                        resource.shutdown()
                except Exception as e:
                    logger.error(f"Error cleaning up {name}: {e}")

            resources.clear()
            logger.info("All resources cleaned up successfully")
            return True
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return False
