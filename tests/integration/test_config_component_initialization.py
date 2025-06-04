"""
Test module for test_config_component_initialization.py.
"""

from unittest.mock import MagicMock, patch

import pytest

from mower.mower import Mower
from mower.navigation.path_planner import LearningConfig, PathPlanner, PatternConfig, PatternType

# Assuming get_config is a helper or should be imported, e.g.,
# from a config manager. For now, we'll assume it's available in the
# scope or defined elsewhere. If it's part of config_manager,
# it should be config_manager.get_config(...)

# It seems this file intends to have test functions rather than a class.
# If these were meant to be methods of a class, the class definition is
# missing.


@pytest.fixture
def setup_config_environment(tmpdir):
    # This fixture *provides* a config_manager and config_dir.
    # It does not read them from an external dictionary of the same name.
    config_manager = MagicMock()
    config_dir = tmpdir

    # This dictionary maps config keys to their mock values with correct types
    mock_config_values = {
        "path_planning.pattern_type": "PARALLEL",  # str
        "path_planning.spacing": 0.5,  # float
        "path_planning.angle": 45.0,  # float
        "path_planning.overlap": 0.2,  # float
        # Adjusted to List[float] to match assertion expectations
        "path_planning.start_point": [0.0, 0.0],
        # Adjusted to List[List[float]] to match assertion expectations
        "path_planning.boundary_points": [[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0]],
        "path_planning.learning.learning_rate": 0.1,  # float
        "path_planning.learning.discount_factor": 0.9,  # float
        "path_planning.learning.exploration_rate": 0.2,  # float
        "path_planning.learning.memory_size": 1000,  # int
        "path_planning.learning.batch_size": 32,  # int
        "path_planning.learning.update_frequency": 100,  # int
        "path_planning.learning.model_path": "model.h5",  # str
    }

    def mock_get_side_effect(key, default=None):
        return mock_config_values.get(key, default)

    config_manager.get.side_effect = mock_get_side_effect

    # This helper will be patched into mower.navigation.path_planner
    def get_config_for_patch(key, default=None):
        return config_manager.get(key, default)

    with patch("mower.navigation.path_planner.get_config", new=get_config_for_patch):
        # Values for constructors are now fetched via the patched get_config,
        # which uses the specifically typed mock_config_values.
        # Default values in get_config calls below are fallbacks if key is missing,
        # but mock_config_values should cover all needed keys.
        pattern_config = PatternConfig(
            pattern_type=PatternType[
                get_config_for_patch("path_planning.pattern_type", "SPIRAL")
            ],  # Default "SPIRAL" is just a fallback
            spacing=get_config_for_patch("path_planning.spacing", 0.3),
            angle=get_config_for_patch("path_planning.angle", 0.0),
            overlap=get_config_for_patch("path_planning.overlap", 0.1),
            start_point=get_config_for_patch("path_planning.start_point", (0.0, 0.0)),
            boundary_points=get_config_for_patch("path_planning.boundary_points", []),
        )

        learning_config = LearningConfig(
            learning_rate=get_config_for_patch("path_planning.learning.learning_rate", 0.01),
            discount_factor=get_config_for_patch("path_planning.learning.discount_factor", 0.99),
            exploration_rate=get_config_for_patch("path_planning.learning.exploration_rate", 0.1),
            memory_size=get_config_for_patch("path_planning.learning.memory_size", 2000),
            batch_size=get_config_for_patch("path_planning.learning.batch_size", 64),
            update_frequency=get_config_for_patch("path_planning.learning.update_frequency", 200),
            model_path=get_config_for_patch("path_planning.learning.model_path", "default_model.h5"),
        )
        path_planner = PathPlanner(pattern_config, learning_config)

    return {
        "config_manager": config_manager,
        "config_dir": config_dir,
        "path_planner": path_planner,
        "get_config_mock_setup": get_config_for_patch,
    }


def test_path_planner_initialization_from_config(setup_config_environment_fixture_result):
    path_planner = setup_config_environment_fixture_result["path_planner"]
    config_dir = setup_config_environment_fixture_result["config_dir"]

    # Assertions should match the values defined in mock_config_values
    assert path_planner.pattern_config.pattern_type == PatternType.PARALLEL
    assert path_planner.pattern_config.spacing == 0.5
    assert path_planner.pattern_config.angle == 45.0
    assert path_planner.pattern_config.overlap == 0.2
    # Ensure assertion matches the (potentially list-based) type from mock
    assert path_planner.pattern_config.start_point == [0.0, 0.0]
    assert path_planner.pattern_config.boundary_points == [[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0]]

    # Assertions for learning_config should match mock_config_values
    assert path_planner.learning_config.learning_rate == 0.1
    assert path_planner.learning_config.discount_factor == 0.9
    assert path_planner.learning_config.exploration_rate == 0.2
    assert path_planner.learning_config.memory_size == 1000
    assert path_planner.learning_config.batch_size == 32
    assert path_planner.learning_config.update_frequency == 100
    assert path_planner.learning_config.model_path == str(
        config_dir / "model.h5"
    )  # model_path in mock_config_values is "model.h5"


def test_resource_manager_initialization_from_config(
    # Renamed to reflect it's the fixture's result
    setup_config_environment_fixture_result,
):
    # config_manager from fixture is not directly used here,
    # but its mock behavior is implicitly tested via Mower's interaction
    # with ResourceManager, which would use the config.

    # Mock the ResourceManager
    with patch("mower.mower.ResourceManager") as MockResourceManager:
        # Configure the mock to return a mock resource manager
        mock_resource_manager = MagicMock()
        MockResourceManager.return_value = mock_resource_manager

        # Mock the load_config method to return test configuration
        mock_resource_manager._load_config.return_value = {"location": [0.0, 0.0]}

        # Create a Mower instance
        mower = Mower()

        # Verify that the ResourceManager was initialized
        MockResourceManager.assert_called_once()

        # Verify that the home location was loaded from configuration
        assert mower.home_location == [0.0, 0.0]
        mock_resource_manager._load_config.assert_called_with("home_location.json")


# Renamed
def test_config_changes_affect_components(setup_config_environment_fixture_result):
    # config_dir from fixture is not directly used here.

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
            "schedule.json": {
                "schedule": [
                    {
                        "day": "Monday",
                        "start": "09:00",  # Corrected spacing
                        "end": "12:00",  # Corrected spacing
                    }
                ]
            },
        }.get(filename)

        # Create a Mower instance
        mower = Mower()

        # Load configuration files
        mower.set_home_location([1.0, 1.0])
        mower.save_boundary([[0, 0], [10, 0], [10, 10], [0, 10]])
        mower.save_no_go_zones([[[2, 2], [4, 2], [4, 4], [2, 4]]])
        mower.set_mowing_schedule(
            # Corrected spacing
            [{"day": "Monday", "start": "09:00", "end": "12:00"}]
        )

        # Verify that the configuration files were saved
        mock_resource_manager._save_config.assert_any_call("home_location.json", {"location": [1.0, 1.0]})
        mock_resource_manager._save_config.assert_any_call(
            "boundary.json",
            {"boundary": [[0, 0], [10, 0], [10, 10], [0, 10]]},
        )
        mock_resource_manager._save_config.assert_any_call(
            "no_go_zones.json",
            {"zones": [[[2, 2], [4, 2], [4, 4], [2, 4]]]},
        )
        mock_resource_manager._save_config.assert_any_call(
            "schedule.json",
            {"schedule": [{"day": "Monday", "start": "09:00", "end": "12:00"}]},  # Corrected spacing
        )
