"""Central logging utilities for the autonomous mower project."""

from __future__ import annotations

import logging

from mower.utilities.logger_config import LoggerConfigInfo


def configure_logging() -> None:
    """Initialize the global logging configuration."""
    LoggerConfigInfo.configure_logging()


def get_logger(name: str) -> logging.Logger:
    """Return a logger configured with the global settings."""
    return LoggerConfigInfo.get_logger(name)
