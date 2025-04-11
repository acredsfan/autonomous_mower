"""
Logger configuration module.

This module provides a centralized configuration for logging across the
autonomous mower application.

Note: Deprecate other logging setups in favor of LoggerConfigInfo.
"""

import os
import logging
import logging.handlers


class LoggerConfigInfo:
    """
    Logger configuration class that provides consistent logging setup.
    """
    _instance = None
    _initialized = False
    _log_dir = os.getenv('MOWER_LOG_DIR', '/var/log/autonomous-mower')

    @classmethod
    def configure_logging(cls) -> None:
        """Configure the logging system."""
        if cls._initialized:
            return

        try:
            # Set up root logger
            root_logger = logging.getLogger()
            root_logger.setLevel(os.getenv('LOG_LEVEL', 'INFO'))

            # Remove any existing handlers to avoid duplicates
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)

            # Create formatters
            detailed_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )

            # Set up console handler first
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(detailed_formatter)
            root_logger.addHandler(console_handler)

            # Set up rotating file handler for main log if directory exists
            if os.path.isdir(cls._log_dir):
                main_log = os.path.join(cls._log_dir, 'mower.log')
                file_handler = logging.handlers.RotatingFileHandler(
                    main_log,
                    maxBytes=1024 * 1024,  # 1MB
                    backupCount=5
                )
                file_handler.setFormatter(detailed_formatter)
                root_logger.addHandler(file_handler)
            else:
                root_logger.warning(
                    f"Log directory {cls._log_dir} does not exist. "
                    "Logging to console only."
                )

            cls._initialized = True
            root_logger.info("Logging system initialized successfully")

        except Exception as e:
            # Use print as a fallback since logging might not be working
            print(f"Failed to configure logging: {e}")
            raise

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Get a logger instance with the specified name.

        Args:
            name: The name for the logger

        Returns:
            logging.Logger: Configured logger instance
        """
        if not cls._initialized:
            cls.configure_logging()
        return logging.getLogger(name)

    @classmethod
    def cleanup_old_logs(cls, days: int = 7) -> None:
        """
        Clean up log files older than specified days.

        Args:
            days: Number of days to keep logs for
        """
        # Implementation of log cleanup
        pass  # TODO: Implement log cleanup
