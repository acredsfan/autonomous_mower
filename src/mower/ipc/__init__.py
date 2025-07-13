"""
Inter-process communication utilities for the autonomous mower.

This module provides command queue functionality to enable communication
between the web UI process and the main controller process.
"""

from .command_queue import CommandQueue, CommandProcessor, get_command_queue, get_command_processor

__all__ = ['CommandQueue', 'CommandProcessor', 'get_command_queue', 'get_command_processor']
