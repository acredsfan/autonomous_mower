"""
Services module for the autonomous mower.

This module provides centralized services that can be shared across
different components of the mower system.
"""

from .gps_service import GpsService

__all__ = ["GpsService"]
