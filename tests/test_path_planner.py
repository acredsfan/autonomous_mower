"""
Test module for test_path_planner.py.
"""

import unittest

from mower.navigation.path_planner import PathPlanner, PatternConfig, PatternType


class TestPathPlanner(unittest.TestCase):
    def setUp(self):
        self.pattern_config = PatternConfig(
            pattern_type=PatternType.PARALLEL,
            spacing=0.5,
            angle=0.0,
            overlap=0.1,
            start_point=(0.0, 0.0),
            boundary_points=[(0, 0), (10, 0), (10, 10), (0, 10)],
        )
        self.path_planner = PathPlanner(self.pattern_config)

    def test_initialization(self):
        """Test initialization of PathPlanner with pattern configuration."""
        self.assertEqual(self.path_planner.pattern_config.pattern_type, PatternType.PARALLEL)
        self.assertEqual(self.path_planner.pattern_config.spacing, 0.5)


if __name__ == "__main__":
    unittest.main()
