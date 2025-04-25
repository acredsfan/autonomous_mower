"""
Integration tests for configuration management and component initialization.

This module tests the interaction between the configuration management system and
component initialization, ensuring that components are initialized correctly using
configuration values from the configuration management system.
"""

import pytest
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from mower.config_management import (
    get_config_manager, get_config, set_config,
    CONFIG_DIR, initialize_config_manager
)
from mower.navigation.path_planner import (
    PathPlanner, PatternConfig, LearningConfig, PatternType
)
from mower.mower import ResourceManager, Mower


class TestConfigComponentInitialization:
    """Integration tests for configuration management and component initialization."""

    @pytest.fixture
    def setup_config_environment(self, tmpdir):
        """Set up a test configuration environment."""
        # Create a temporary directory for configuration files
        config_dir = tmpdir.mkdir("config")

        # Create test configuration files
        home_location_file = config_dir.join("home_location.json")
        home_location_file.write('{"location": [0.0, 0.0]}')

        boundary_file = config_dir.join("boundary.json")
        boundary_file.write(
            '{"boundary": [[0, 0], [10, 0], [10, 10], [0, 10]]}')

        no_go_zones_file = config_dir.join("no_go_zones.json")
        no_go_zones_file.write('{"zones": [[[2, 2], [4, 2], [4, 4], [2, 4]]]}')

        schedule_file = config_dir.join("schedule.json")
        schedule_file.write(
            '{"schedule": [{"day": "Monday", "start": "09:00", "end": "12:00"}]}')

        # Patch the CONFIG_DIR constant
        with patch("mower.config_management.CONFIG_DIR", Path(config_dir)):
            with patch("mower.mower.CONFIG_DIR", Path(config_dir)):
                # Initialize the configuration manager with test values
                test_config = {
                    "path_planning": {
                        "pattern_type": "PARALLEL",
                        "spacing": 0.5,
                        "angle": 45.0,
                        "overlap": 0.2,
                        "start_point": [0.0, 0.0],
                        "boundary_points": [[0, 0], [10, 0], [10, 10], [0, 10]],
                        "learning": {
                            "learning_rate": 0.2,
                            "discount_factor": 0.8,
                            "exploration_rate": 0.3,
                            "memory_size": 500,
                            "batch_size": 16,
                            "update_frequency": 50,
                            "model_path": str(config_dir / "model.h5")
                        }
                    },
                    "hardware": {
                        "blade_speed": 0.8,
                        "motor_speed": 0.6,
                        "sensor_update_frequency": 10
                    },
                    "safety": {
                        "min_battery_voltage": 11.5,
                        "max_slope_angle": 20.0,
                        "min_obstacle_distance": 30.0
                    }
                }

                # Initialize configuration manager
                initialize_config_manager(defaults=test_config)

                yield {
                    "config_dir": config_dir,
                    "config_manager": get_config_manager()
                }

    def test_path_planner_initialization_from_config(self, setup_config_environment):
        """Test that the PathPlanner is initialized correctly from configuration."""
        # Get the configuration manager
        config_manager = setup_config_environment["config_manager"]

        # Create a PathPlanner instance
        with patch("mower.navigation.path_planner.get_config") as mock_get_config:
            # Configure the mock to return values from the actual config manager
            mock_get_config.side_effect = lambda key, default=None: config_manager.get(
                key, default)

            # Create pattern and learning configurations using values from config
            pattern_config = PatternConfig(
                pattern_type=PatternType[get_config(
                    'path_planning.pattern_type', 'PARALLEL')],
                spacing=get_config('path_planning.spacing', 0.3),
                angle=get_config('path_planning.angle', 0.0),
                overlap=get_config('path_planning.overlap', 0.1),
                start_point=get_config(
                    'path_planning.start_point', (0.0, 0.0)),
                boundary_points=get_config('path_planning.boundary_points', [])
            )

            learning_config = LearningConfig(
                learning_rate=get_config(
                    'path_planning.learning.learning_rate', 0.1),
                discount_factor=get_config(
                    'path_planning.learning.discount_factor', 0.9),
                exploration_rate=get_config(
                    'path_planning.learning.exploration_rate', 0.2),
                memory_size=get_config(
                    'path_planning.learning.memory_size', 1000),
                batch_size=get_config('path_planning.learning.batch_size', 32),
                update_frequency=get_config(
                    'path_planning.learning.update_frequency', 100),
                model_path=get_config(
                    'path_planning.learning.model_path', "model.h5")
            )

            # Create a PathPlanner instance
            path_planner = PathPlanner(pattern_config, learning_config)

            # Verify that the PathPlanner was initialized with the correct values
            assert path_planner.pattern_config.pattern_type == PatternType.PARALLEL
            assert path_planner.pattern_config.spacing == 0.5
            assert path_planner.pattern_config.angle == 45.0
            assert path_planner.pattern_config.overlap == 0.2
            assert path_planner.pattern_config.start_point == [0.0, 0.0]
            assert path_planner.pattern_config.boundary_points == [
                [0, 0], [10, 0], [10, 10], [0, 10]]

            assert path_planner.learning_config.learning_rate == 0.2
            assert path_planner.learning_config.discount_factor == 0.8
            assert path_planner.learning_config.exploration_rate == 0.3
            assert path_planner.learning_config.memory_size == 500
            assert path_planner.learning_config.batch_size == 16
            assert path_planner.learning_config.update_frequency == 50
            assert path_planner.learning_config.model_path == str(
                setup_config_environment["config_dir"] / "model.h5")

    def test_resource_manager_initialization_from_config(self, setup_config_environment):
        """Test that the ResourceManager is initialized correctly from configuration."""
        # Get the configuration manager
        config_manager = setup_config_environment["config_manager"]

        # Mock the hardware initialization
        with patch("mower.mower.ResourceManager._initialize_hardware") as mock_init_hardware:
            with patch("mower.mower.ResourceManager._initialize_software") as mock_init_software:
                with patch("mower.mower.get_config") as mock_get_config:
                    # Configure the mock to return values from the actual config manager
                    mock_get_config.side_effect = lambda key, default=None: config_manager.get(
                        key, default)

                    # Create a ResourceManager instance
                    resource_manager = ResourceManager()

                    # Initialize the resource manager
                    resource_manager.initialize()

                    # Verify that the hardware and software initialization methods were called
                    mock_init_hardware.assert_called_once()
                    mock_init_software.assert_called_once()

    def test_mower_initialization_from_config(self, setup_config_environment):
        """Test that the Mower is initialized correctly from configuration."""
        # Get the configuration manager
        config_manager = setup_config_environment["config_manager"]

        # Mock the ResourceManager
        with patch("mower.mower.ResourceManager") as MockResourceManager:
            # Configure the mock to return a mock resource manager
            mock_resource_manager = MagicMock()
            MockResourceManager.return_value = mock_resource_manager

            # Mock the load_config method to return test configuration
            mock_resource_manager._load_config.return_value = {
                "location": [0.0, 0.0]}

            # Create a Mower instance
            mower = Mower()

            # Verify that the ResourceManager was initialized
            MockResourceManager.assert_called_once()

            # Verify that the home location was loaded from configuration
            assert mower.home_location == [0.0, 0.0]
            mock_resource_manager._load_config.assert_called_with(
                "home_location.json")

    def test_config_changes_affect_components(self, setup_config_environment):
        """Test that changes to configuration affect component behavior."""
        # Get the configuration manager
        config_manager = setup_config_environment["config_manager"]

        # Create a PathPlanner instance
        with patch("mower.navigation.path_planner.get_config") as mock_get_config:
            # Configure the mock to return values from the actual config manager
            mock_get_config.side_effect = lambda key, default=None: config_manager.get(
                key, default)

            # Create pattern and learning configurations using values from config
            pattern_config = PatternConfig(
                pattern_type=PatternType[get_config(
                    'path_planning.pattern_type', 'PARALLEL')],
                spacing=get_config('path_planning.spacing', 0.3),
                angle=get_config('path_planning.angle', 0.0),
                overlap=get_config('path_planning.overlap', 0.1),
                start_point=get_config(
                    'path_planning.start_point', (0.0, 0.0)),
                boundary_points=get_config('path_planning.boundary_points', [])
            )

            learning_config = LearningConfig(
                learning_rate=get_config(
                    'path_planning.learning.learning_rate', 0.1),
                discount_factor=get_config(
                    'path_planning.learning.discount_factor', 0.9),
                exploration_rate=get_config(
                    'path_planning.learning.exploration_rate', 0.2),
                memory_size=get_config(
                    'path_planning.learning.memory_size', 1000),
                batch_size=get_config('path_planning.learning.batch_size', 32),
                update_frequency=get_config(
                    'path_planning.learning.update_frequency', 100),
                model_path=get_config(
                    'path_planning.learning.model_path', "model.h5")
            )

            # Create a PathPlanner instance
            path_planner = PathPlanner(pattern_config, learning_config)

            # Verify initial values
            assert path_planner.pattern_config.spacing == 0.5

            # Change the configuration
            set_config('path_planning.spacing', 0.7)

            # Create a new PathPlanner instance with the updated configuration
            pattern_config = PatternConfig(
                pattern_type=PatternType[get_config(
                    'path_planning.pattern_type', 'PARALLEL')],
                spacing=get_config('path_planning.spacing', 0.3),
                angle=get_config('path_planning.angle', 0.0),
                overlap=get_config('path_planning.overlap', 0.1),
                start_point=get_config(
                    'path_planning.start_point', (0.0, 0.0)),
                boundary_points=get_config('path_planning.boundary_points', [])
            )

            new_path_planner = PathPlanner(pattern_config, learning_config)

            # Verify that the new PathPlanner has the updated value
            assert new_path_planner.pattern_config.spacing == 0.7

    def test_config_file_loading(self, setup_config_environment):
        """Test that configuration files are loaded correctly."""
        # Get the configuration directory
        config_dir = setup_config_environment["config_dir"]

        # Create a Mower instance with mocked ResourceManager
        with patch("mower.mower.ResourceManager") as MockResourceManager:
            # Configure the mock to return a mock resource manager
            mock_resource_manager = MagicMock()
            MockResourceManager.return_value = mock_resource_manager

            # Configure the mock to return test configuration
            mock_resource_manager._load_config.side_effect = lambda filename: {
                "home_location.json": {"location": [1.0, 1.0]},
                "boundary.json": {"boundary": [[0, 0], [10, 0], [10, 10], [0, 10]]},
                "no_go_zones.json": {"zones": [[[2, 2], [4, 2], [4, 4], [2, 4]]]},
                "schedule.json": {"schedule": [{"day": "Monday", "start": "09:00", "end": "12:00"}]}
            }.get(filename)

            # Create a Mower instance
            mower = Mower()

            # Load configuration files
            mower.set_home_location([1.0, 1.0])
            mower.save_boundary([[0, 0], [10, 0], [10, 10], [0, 10]])
            mower.save_no_go_zones([[[2, 2], [4, 2], [4, 4], [2, 4]]])
            mower.set_mowing_schedule(
                [{"day": "Monday", "start": "09:00", "end": "12:00"}])

            # Verify that the configuration files were saved
            mock_resource_manager._save_config.assert_any_call(
                "home_location.json", {"location": [1.0, 1.0]})
            mock_resource_manager._save_config.assert_any_call(
                "boundary.json", {"boundary": [[0, 0], [10, 0], [10, 10], [0, 10]]})
            mock_resource_manager._save_config.assert_any_call(
                "no_go_zones.json", {"zones": [[[2, 2], [4, 2], [4, 4], [2, 4]]]})
            mock_resource_manager._save_config.assert_any_call(
                "schedule.json", {"schedule": [{"day": "Monday", "start": "09:00", "end": "12:00"}]})
