"""
Test module for test_config_manager.py.
"""

from pathlib import Path

import pytest

# Assuming these are the correct imports, adjust if necessary
from mower.config_management import ConfigManager, get_config, get_config_manager, initialize_config_manager, set_config


class TestConfigManager:
    @pytest.fixture
    def config_manager(self, tmp_path):
        # Create a temporary config directory for testing
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        # Initialize with a default config or an empty one
        initialize_config_manager(
            config_dir=str(config_dir),
            defaults={
                "test": {
                    "string_value": "test_string",
                    "int_value": 42,
                    "float_value": 3.14,
                    "bool_value": True,
                    "list_value": [1, 2, 3],
                    "dict_value": {"key": "value"},
                }
            },
        )
        return get_config_manager()

    def test_initialization(self, config_manager: ConfigManager):
        # Test getting existing values
        assert get_config("test.string_value") == "test_string"
        assert get_config("test.int_value") == 42

        # Test getting non-existent values with default
        assert get_config("non_existent_key", "default") == "default"
        assert get_config("test.non_existent_key", 100) == 100

        # Test getting non-existent values without default
        assert get_config("non_existent_key") is None

    def test_set_config(self, config_manager: ConfigManager):
        # Set values of different types
        set_config("test.int_value_str", "42")
        set_config("test.float_value_str", "3.14")
        set_config("test.bool_value_str", "true")
        set_config("test.list_value_str", "[1, 2, 3]")
        set_config("test.dict_value_str", '{"key": "value_str"}')

        # Test type-specific getters
        assert config_manager.get_int("test.int_value_str", 0) == 42
        assert config_manager.get_float("test.float_value_str", 0.0) == 3.14
        assert config_manager.get_bool("test.bool_value_str", False) is True
        assert config_manager.get_list("test.list_value_str", []) == [1, 2, 3]
        assert config_manager.get_dict("test.dict_value_str", {}) == {"key": "value_str"}

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

    def test_hierarchical_keys(self, config_manager: ConfigManager, tmp_path):
        # Initialize configuration manager with test values
        # This is now handled by the fixture for consistency
        # test_config = {
        #     "test": {"string_value": "test_string", "int_value": 42}
        # }
        # initialize_config_manager(defaults=test_config, config_dir=str(tmp_path))
        # config_manager = get_config_manager()

        # Set a new value
        set_config("test.new_value", "new_value")

        # Save configuration to file
        # Use the config_dir from the config_manager instance
        # Assuming user_config.json is the save target
        test_config_path = Path(config_manager.config_dir) / "user_config.json"
        # save method might not take a path, or save to its pre-configured path
        config_manager.save()

        # Verify file was created
        assert test_config_path.exists()

        # Load configuration from file
        # Re-initialize or use a new manager to truly test loading from file
        new_manager = ConfigManager(config_dir=str(Path(config_manager.config_dir)))
        # Assuming get_all() or similar loads and returns all
        loaded_config = new_manager.get_all()

        # Verify loaded configuration
        assert loaded_config["test"]["string_value"] == "test_string"
        assert loaded_config["test"]["int_value"] == 42
        assert loaded_config["test"]["new_value"] == "new_value"

    def test_error_handling(self, config_manager: ConfigManager):
        pass
