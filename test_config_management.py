"""
Test script for configuration management functionality.

This script tests the standardized configuration management system
to ensure that configuration values can be loaded, saved, and accessed
consistently across components.
"""

import os
import json
from pathlib import Path

# Import configuration management
from mower.config_management import (
    get_config_manager, get_config, set_config,
    CONFIG_DIR, initialize_config_manager
)

def test_config_management():
    """Test configuration management functionality."""
    print("Testing configuration management...")
    
    # Initialize configuration manager with test values
    test_config = {
        "test": {
            "string_value": "test_string",
            "int_value": 42,
            "float_value": 3.14,
            "bool_value": True,
            "list_value": [1, 2, 3],
            "dict_value": {"key": "value"}
        }
    }
    
    # Initialize configuration manager
    initialize_config_manager(defaults=test_config)
    
    # Get configuration manager
    config_manager = get_config_manager()
    
    # Test get_config function
    assert get_config("test.string_value") == "test_string"
    assert get_config("test.int_value") == 42
    assert get_config("test.float_value") == 3.14
    assert get_config("test.bool_value") is True
    assert get_config("test.list_value") == [1, 2, 3]
    assert get_config("test.dict_value") == {"key": "value"}
    
    # Test default values
    assert get_config("non_existent_key", "default") == "default"
    
    # Test set_config function
    set_config("test.new_value", "new_value")
    assert get_config("test.new_value") == "new_value"
    
    # Test saving configuration to file
    test_config_path = CONFIG_DIR / "test_config.json"
    config_manager.save(str(test_config_path))
    
    # Verify file was created
    assert test_config_path.exists()
    
    # Load configuration from file
    loaded_config = config_manager.load(str(test_config_path))
    
    # Verify loaded configuration
    assert loaded_config["test"]["string_value"] == "test_string"
    assert loaded_config["test"]["int_value"] == 42
    assert loaded_config["test"]["new_value"] == "new_value"
    
    # Clean up test file
    if test_config_path.exists():
        os.remove(test_config_path)
    
    print("All configuration management tests passed!")

if __name__ == "__main__":
    # Ensure config directory exists
    os.makedirs(CONFIG_DIR, exist_ok=True)
    
    # Run tests
    test_config_management()