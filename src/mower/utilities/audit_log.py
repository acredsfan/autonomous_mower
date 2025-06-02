"""Audit logging for security-relevant operations.

This module provides functions for logging security-relevant operations
in a format suitable for security auditing and compliance.
"""

import json
import logging
import os
import socket
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Union

from mower.utilities.logger_config import LoggerConfigInfo


class AuditEventType(Enum):
    """Types of audit events."""

    # Authentication events
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILURE = "LOGIN_FAILURE"
    LOGOUT = "LOGOUT"
    PASSWORD_CHANGE = "PASSWORD_CHANGE"

    # Authorization events
    PERMISSION_CHANGE = "PERMISSION_CHANGE"
    ACCESS_DENIED = "ACCESS_DENIED"

    # Configuration events
    CONFIG_CHANGE = "CONFIG_CHANGE"
    SECURITY_SETTING_CHANGE = "SECURITY_SETTING_CHANGE"

    # System events
    SYSTEM_START = "SYSTEM_START"
    SYSTEM_STOP = "SYSTEM_STOP"

    # Mower operation events
    MOWER_START = "MOWER_START"
    MOWER_STOP = "MOWER_STOP"
    EMERGENCY_STOP = "EMERGENCY_STOP"

    # Boundary events
    BOUNDARY_CHANGE = "BOUNDARY_CHANGE"
    NO_GO_ZONE_CHANGE = "NO_GO_ZONE_CHANGE"

    # Remote access events
    REMOTE_ACCESS = "REMOTE_ACCESS"

    # Other security events
    SUSPICIOUS_ACTIVITY = "SUSPICIOUS_ACTIVITY"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"


class AuditLogger:
    """Logger for security audit events.

    This class provides methods for logging security-relevant operations
    in a format suitable for security auditing and compliance.
    """

    def __init__(self, log_dir: Optional[Union[str, Path]] = None):
        """Initialize the audit logger.

        Args:
            log_dir: Directory where audit logs will be stored.
                If not provided, logs will be stored in /var/log/autonomous-mower/audit.
        """
        if log_dir is None:
            # Default log directory
            log_dir = Path("/var/log/autonomous-mower/audit")
        else:
            log_dir = Path(log_dir)

        # Create log directory if it doesn't exist
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            # Use the standard logger to report this critical setup error
            # Initialize a temporary logger if self.error_logger is not yet available
            temp_error_logger = LoggerConfigInfo.get_logger(__name__ + ".init_error")
            temp_error_logger.error(f"Failed to create audit log directory {log_dir}: {e}")
            # Depending on policy, you might re-raise or exit
            # For now, we'll let it continue, but logging will likely fail.
            # Consider a fallback mechanism or a more robust error handling strategy.

        # Set up the audit logger
        self.logger = logging.getLogger("audit")
        self.logger.setLevel(logging.INFO)

        # Remove existing handlers to avoid duplicates
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        # Create a file handler for the audit log
        log_file = log_dir / "audit.log"
        try:
            handler = logging.FileHandler(log_file)

            # Create a formatter for the audit log
            formatter = logging.Formatter(
                "%(asctime)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            handler.setFormatter(formatter)

            # Add the handler to the logger
            self.logger.addHandler(handler)
        except OSError as e:
            temp_error_logger = LoggerConfigInfo.get_logger(__name__ + ".handler_error")
            temp_error_logger.error(f"Failed to create audit log file handler for {log_file}: {e}")
            # Audit logging will not function if this fails.

        # Get hostname for audit records
        try:
            self.hostname = socket.gethostname()
        except socket.gaierror:
            self.hostname = "unknown_host"
            temp_error_logger = LoggerConfigInfo.get_logger(__name__ + ".hostname_error")
            temp_error_logger.warning("Failed to get hostname for audit logs.")

        # Get standard logger for internal errors
        self.error_logger = LoggerConfigInfo.get_logger(__name__)

    def log_event(
        self,
        event_type: AuditEventType,
        user: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
    ) -> None:
        """Log a security audit event.

        Args:
            event_type: Type of audit event.
            user: Username of the user who performed the action.
            ip_address: IP address of the client.
            details: Additional details about the event.
            success: Whether the operation was successful.
        """
        try:
            # Create the audit record
            audit_record: Dict[str, Any] = {
                "timestamp": datetime.now().isoformat(),
                "event_type": event_type.value,
                "hostname": self.hostname,
                "process_id": os.getpid(),
                "success": success,
            }

            # Add optional fields if provided
            if user:
                audit_record["user"] = user
            if ip_address:
                audit_record["ip_address"] = ip_address
            if details:
                audit_record["details"] = details

            # Log the audit record
            self.logger.info(json.dumps(audit_record))
        except AttributeError as e:  # Catch if self.logger or self.hostname is not set due to init errors
            # This might happen if __init__ failed to set up the logger or hostname
            # Log to a fallback or print if absolutely necessary and no other logger is available
            # For now, using the error_logger if available, or a temp one.
            fallback_logger = getattr(self, 'error_logger',
                                      LoggerConfigInfo.get_logger(__name__ + ".log_event_error"))
            fallback_logger.error(
                f"AuditLogger not properly initialized. Failed to log audit event: {e}",
                exc_info=True
            )
        except Exception as e:
            # Use self.error_logger if available, otherwise a temporary one
            current_error_logger = getattr(self, 'error_logger',
                                           LoggerConfigInfo.get_logger(__name__ + ".log_event_error"))
            current_error_logger.error(f"Failed to log audit event: {e}", exc_info=True)

    def log_login(self, user: str, ip_address: str, success: bool) -> None:
        """Log a login event.

        Args:
            user: Username of the user who attempted to log in.
            ip_address: IP address of the client.
            success: Whether the login was successful.
        """
        event_type = (
            AuditEventType.LOGIN_SUCCESS
            if success
            else AuditEventType.LOGIN_FAILURE
        )
        self.log_event(event_type, user, ip_address, success=success)

    def log_logout(self, user: str, ip_address: str) -> None:
        """Log a logout event.

        Args:
            user: Username of the user who logged out.
            ip_address: IP address of the client.
        """
        self.log_event(AuditEventType.LOGOUT, user, ip_address)

    def log_config_change(
        self,
        user: str,
        ip_address: str,
        config_section: str,
        old_value: Any,
        new_value: Any,
        success: bool = True,
    ) -> None:
        """Log a configuration change event.

        Args:
            user: Username of the user who changed the configuration.
            ip_address: IP address of the client.
            config_section: Section of the configuration that was changed.
            old_value: Previous value of the configuration.
            new_value: New value of the configuration.
            success: Whether the configuration change was successful.
        """
        details = {
            "config_section": config_section,
            "old_value": old_value,
            "new_value": new_value,
        }
        self.log_event(
            AuditEventType.CONFIG_CHANGE, user, ip_address, details, success
        )

    def log_security_setting_change(
        self,
        user: str,
        ip_address: str,
        setting_name: str,
        old_value: Any,
        new_value: Any,
        success: bool = True,
    ) -> None:
        """Log a security setting change event.

        Args:
            user: Username of the user who changed the security setting.
            ip_address: IP address of the client.
            setting_name: Name of the security setting that was changed.
            old_value: Previous value of the security setting.
            new_value: New value of the security setting.
            success: Whether the security setting change was successful.
        """
        details = {
            "setting_name": setting_name,
            "old_value": old_value,
            "new_value": new_value,
        }
        self.log_event(
            AuditEventType.SECURITY_SETTING_CHANGE,
            user,
            ip_address,
            details,
            success,
        )

    def log_access_denied(
        self, user: str, ip_address: str, resource: str, reason: str
    ) -> None:
        """Log an access denied event.

        Args:
            user: Username of the user who was denied access.
            ip_address: IP address of the client.
            resource: Resource that the user attempted to access.
            reason: Reason why access was denied.
        """
        details = {"resource": resource, "reason": reason}
        self.log_event(
            AuditEventType.ACCESS_DENIED,
            user,
            ip_address,
            details,
            success=False,
        )

    def log_suspicious_activity(
        self, ip_address: str, activity: str, details: Optional[Dict[str, Any]] = None  # Added Optional
    ) -> None:
        """Log a suspicious activity event.

        Args:
            ip_address: IP address of the client.
            activity: Description of the suspicious activity.
            details: Additional details about the suspicious activity.
        """
        current_details = details if details is not None else {}  # Create new dict if None
        current_details["activity"] = activity  # Add activity to the new or existing dict
        self.log_event(
            AuditEventType.SUSPICIOUS_ACTIVITY,
            ip_address=ip_address,
            details=current_details,  # Use the modified dict
            success=False,
        )

    def log_rate_limit_exceeded(
        self, ip_address: str, endpoint: str, limit: str
    ) -> None:
        """Log a rate limit exceeded event.

        Args:
            ip_address: IP address of the client.
            endpoint: API endpoint that was rate limited.
            limit: Rate limit that was exceeded.
        """
        details = {"endpoint": endpoint, "limit": limit}
        self.log_event(
            AuditEventType.RATE_LIMIT_EXCEEDED,
            ip_address=ip_address,
            details=details,
            success=False,
        )


# Singleton instance
_audit_logger_instance = None


def get_audit_logger(
    log_dir: Optional[Union[str, Path]] = None
) -> AuditLogger:
    """Get the audit logger instance.

    Args:
        log_dir: Directory where audit logs will be stored.
            If not provided, logs will be stored in /var/log/autonomous-mower/audit.

    Returns:
        The audit logger instance.
    """
    global _audit_logger_instance

    if _audit_logger_instance is None:
        _audit_logger_instance = AuditLogger(log_dir)

    return _audit_logger_instance
