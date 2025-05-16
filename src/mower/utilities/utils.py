"""
Utilities module for the autonomous mower project.

This module contains utility functions for various tasks
like mapping values between ranges and other general helpers.
"""


class Utils:
    """
    Utility class containing static helper methods.

    This class provides various utility functions used throughout the project.
    """

    @staticmethod
    def map_range(x, x_min, x_max, y_min, y_max):
        """
        Linear mapping between two ranges of values.

        Args:
            x: Input value to be mapped
            x_min: Minimum value of input range
            x_max: Maximum value of input range
            y_min: Minimum value of output range
            y_max: Maximum value of output range

        Returns:
            int: Mapped value in the output range as an integer
        """
        x_range = x_max - x_min
        y_range = y_max - y_min
        xy_ratio = x_range / y_range

        y = ((x - x_min) / xy_ratio + y_min) // 1

        return int(y)

    @staticmethod
    def map_range_float(x, x_min, x_max, y_min, y_max):
        """
        Linear mapping between two ranges of values with float results.

        Args:
            x: Input value to be mapped
            x_min: Minimum value of input range
            x_max: Maximum value of input range
            y_min: Minimum value of output range
            y_max: Maximum value of output range

        Returns:
            float: Mapped value in the output range (rounded to 2 decimal places)
        """
        x_range = x_max - x_min
        y_range = y_max - y_min
        xy_ratio = x_range / y_range

        y = (x - x_min) / xy_ratio + y_min

        return round(y, 2)
