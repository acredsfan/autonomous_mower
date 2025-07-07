"""
Safety module for autonomous mower.

This module provides safety checks and validation to prevent
unsafe autonomous operation of the mower.
"""

from .autonomous_safety import SafetyChecker, requires_safety_validation

__all__ = ["SafetyChecker", "requires_safety_validation"]
