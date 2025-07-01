"""
Logger configuration module.

This module provides a centralized configuration for logging across the
autonomous mower application.
"""

import logging
import logging.handlers
import os
from pathlib import Path
import time


class LoggerConfigInfo:
    """
    Logger configuration class that provides consistent logging setup.
    """

    _instance = None
    _initialized = False
    _log_dir = os.getenv("MOWER_LOG_DIR", str(Path(__file__).resolve().parent.parent.parent / "logs"))

    @classmethod
    def configure_logging(cls) -> None:
        """Configure the logging system."""
        if cls._initialized:
            return

        try:
            # Ensure the log directory exists
            log_dir_path = Path(cls._log_dir)
            if not log_dir_path.exists():
                try:
                    log_dir_path.mkdir(parents=True, exist_ok=True)
                    # Basic print for this specific case, as logger might not be fully set up
                    print(f"Log directory {log_dir_path} created.")
                except (OSError, PermissionError) as e:
                    # Fallback to /tmp for logging if primary location fails
                    fallback_log_dir = Path("/tmp/autonomous_mower_logs")
                    print(f"Error creating log directory {log_dir_path}: {e}")
                    print(f"Falling back to {fallback_log_dir}")
                    try:
                        fallback_log_dir.mkdir(parents=True, exist_ok=True)
                        cls._log_dir = str(fallback_log_dir)
                        log_dir_path = fallback_log_dir
                        print(f"Fallback log directory {fallback_log_dir} created.")
                    except (OSError, PermissionError) as e2:
                        print(f"Failed to create fallback log directory {fallback_log_dir}: {e2}")
                        print("Logging to console only.")
                        log_dir_path = None

            # Set up root logger
            root_logger = logging.getLogger()
            root_logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

            # Remove any existing handlers to avoid duplicates
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)

            # Create formatters
            detailed_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

            # Set up console handler first
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(detailed_formatter)
            root_logger.addHandler(console_handler)

            # Set up rotating file handler for main log if directory exists or was created
            if log_dir_path and log_dir_path.is_dir(): # Check again after attempting creation
                main_log = log_dir_path / "mower.log"
                file_handler = logging.handlers.RotatingFileHandler(
                    main_log, maxBytes=1024 * 1024, backupCount=5  # 1MB
                )
                file_handler.setFormatter(detailed_formatter)
                root_logger.addHandler(file_handler)
            else:
                root_logger.warning(f"Log directory not available. Logging to console only.")

            cls._initialized = True
            root_logger.info("Logging system initialized successfully")

        except Exception as e:
            # Use basic print for critical errors during logging setup
            print(f"Critical error during logging configuration: {e}")
            # Fallback to basic console logging if setup fails
            logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            logging.error("Logging system failed to initialize properly. Using basicConfig.")

        cls._initialized = True # Mark as initialized even if only console logging is active

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
        # Remove log files older than the specified number of days

        log_directory = Path(cls._log_dir)  # Corrected line

        # Ensure logging is configured before trying to log, or use basic print as fallback
        # It's better to get a logger instance if possible.
        logger_instance = cls.get_logger(__name__)

        if not log_directory.is_dir():
            logger_instance.warning(f"Log directory {log_directory} not found for cleanup.")
            return

        cutoff = time.time() - (days * 86400)
        try:
            for filename in os.listdir(log_directory):
                file_path = log_directory / filename
                if file_path.is_file():  # Ensure it's a file
                    try:
                        if file_path.stat().st_mtime < cutoff:
                            file_path.unlink()
                            logger_instance.info(f"Deleted old log file: {file_path}")
                    except OSError as e:
                        logger_instance.error(f"Error deleting log file {file_path}: {e}")
        except OSError as e:
            logger_instance.error(f"Error listing log directory {log_directory} for cleanup: {e}")
