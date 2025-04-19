"""
Tests for the configuration management system.

This module tests the functionality of the configuration manager, including:
1. Initialization with default values
2. Getting and setting configuration values
3. Loading and saving configuration files
4. Type conversion
5. Hierarchical configuration keys
6. Error handling
"""

import os
import json
import pytest
from pathlib import Path

from mower.config_management import (
    get_config_manager, get_config, set_config,
    CONFIG_DIR, initialize_config_manager
)


class TestConfigManager:
    """Tests for the ConfigurationManager class."""

    def test_initialization(self, config_manager):
        """Test initialization with default values."""
        # Verify that the configuration manager was initialized with the test values
        assert config_manager is not None
        assert get_config("test.string_value") == "test_string"
        assert get_config("test.int_value") == 42
        assert get_config("test.float_value") == 3.14
        assert get_config("test.bool_value") is True
        assert get_config("test.list_value") == [1, 2, 3]
        assert get_config("test.dict_value") == {"key": "value"}

    def test_get_config(self, config_manager):
        """Test getting configuration values."""
        # Test getting existing values
        assert get_config("test.string_value") == "test_string"
        assert get_config("test.int_value") == 42
        
        # Test getting non-existent values with default
        assert get_config("non_existent_key", "default") == "default"
        assert get_config("test.non_existent_key", 100) == 100
        
        # Test getting non-existent values without default
        assert get_config("non_existent_key") is None

    def test_set_config(self, config_manager):
        """Test setting configuration values."""
        # Test setting new values
        set_config("test.new_value", "new_value")
        assert get_config("test.new_value") == "new_value"
        
        # Test overwriting existing values
        set_config("test.string_value", "updated_string")
        assert get_config("test.string_value") == "updated_string"
        
        # Test setting nested values
        set_config("test.nested.value", "nested_value")
        assert get_config("test.nested.value") == "nested_value"

    def test_type_conversion(self, config_manager):
        """Test type conversion for configuration values."""
        # Set values of different types
        set_config("test.int_value", "42")
        set_config("test.float_value", "3.14")
        set_config("test.bool_value", "true")
        set_config("test.list_value", "[1, 2, 3]")
        set_config("test.dict_value", '{"key": "value"}')
        
        # Test type-specific getters
        assert config_manager.get_int("test.int_value", 0) == 42
        assert config_manager.get_float("test.float_value", 0.0) == 3.14
        assert config_manager.get_bool("test.bool_value", False) is True
        assert config_manager.get_list("test.list_value", []) == [1, 2, 3]
        assert config_manager.get_dict("test.dict_value", {}) == {"key": "value"}
        
        # Test type conversion with invalid values
        set_config("test.invalid_int", "not_an_int")
        assert config_manager.get_int("test.invalid_int", 0) == 0
        
        set_config("test.invalid_float", "not_a_float")
        assert config_manager.get_float("test.invalid_float", 0.0) == 0.0
        
        set_config("test.invalid_bool", "not_a_bool")
        assert config_manager.get_bool("test.invalid_bool", False) is False
        
        set_config("test.invalid_list", "not_a_list")
        assert config_manager.get_list("test.invalid_list", []) == []
        
        set_config("test.invalid_dict", "not_a_dict")
        assert config_manager.get_dict("test.invalid_dict", {}) == {}

    def test_hierarchical_keys(self, config_manager):
        """Test hierarchical configuration keys."""
        # Set hierarchical values
        set_config("section.subsection.key", "value")
        
        # Test getting hierarchical values
        assert get_config("section.subsection.key") == "value"
        
        # Test getting sections
        section = config_manager.get_section("section")
        assert section is not None
        assert section.get("subsection.key") == "value"
        
        subsection = config_manager.get_section("section.subsection")
        assert subsection is not None
        assert subsection.get("key") == "value"

    def test_save_load(self, temp_config_dir):
        """Test saving and loading configuration files."""
        # Initialize configuration manager with test values
        test_config = {
            "test": {
                "string_value": "test_string",
                "int_value": 42
            }
        }
        initialize_config_manager(defaults=test_config)
        config_manager = get_config_manager()
        
        # Set a new value
        set_config("test.new_value", "new_value")
        
        # Save configuration to file
        test_config_path = Path(temp_config_dir) / "test_config.json"
        config_manager.save(str(test_config_path))
        
        # Verify file was created
        assert test_config_path.exists()
        
        # Load configuration from file
        loaded_config = config_manager.load(str(test_config_path))
        
        # Verify loaded configuration
        assert loaded_config["test"]["string_value"] == "test_string"
        assert loaded_config["test"]["int_value"] == 42
        assert loaded_config["test"]["new_value"] == "new_value"

    def test_error_handling(self, config_manager):
        """Test error handling in the configuration manager."""
        # Test loading non-existent file
        result = config_manager.load("non_existent_file.json")
        assert result is None
        
        # Test saving to invalid path
        with pytest.raises(Exception):
            config_manager.save("/invalid/path/config.json")
        
        # Test getting section that doesn't exist
        section = config_manager.get_section("non_existent_section")
        assert section is None