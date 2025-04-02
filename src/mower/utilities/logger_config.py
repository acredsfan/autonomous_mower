"""
Logger configuration module.

This module provides a centralized configuration for logging across the application.
"""

import os
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime

class LoggerConfigInfo:
    """
    Logger configuration class that provides consistent logging setup.
    
    This class configures logging with:
    - Console output for all levels
    - File output with rotation
    - Consistent formatting across handlers
    """
    
    _configured = False
    _logger = None
    
    @classmethod
    def configure_logging(cls):
        """Configure logging with console and file handlers."""
        if cls._configured:
            return
            
        # Create logs directory if it doesn't exist
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Set up main log file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"mower_{timestamp}.log"
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        
        # Create formatters
        console_formatter = logging.Formatter(
            '%(levelname)s: %(message)s'
        )
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # File handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=1024*1024,  # 1MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
        
        cls._configured = True
        cls._logger = root_logger
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Get a logger instance with the specified name.
        
        Args:
            name: The name for the logger
            
        Returns:
            logging.Logger: Configured logger instance
        """
        if not cls._configured:
            cls.configure_logging()
        return logging.getLogger(name)
