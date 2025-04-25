"""Permission management for the web interface.

This module provides functions for managing user roles and permissions
in the web interface.
"""

import functools
from enum import Enum, auto
from typing import Callable, Dict, List, Optional, Set, TypeVar, Union, cast

from flask import Flask, Response, abort, request, session

from mower.utilities.logger_config import LoggerConfigInfo
from mower.utilities.audit_log import get_audit_logger, AuditEventType

# Initialize logger
logger = LoggerConfigInfo.get_logger(__name__)

# Get audit logger
audit_logger = get_audit_logger()

# Type variable for route functions
F = TypeVar('F', bound=Callable[..., Response])


class Permission(Enum):
    """Permission types for the web interface."""

    # View permissions
    VIEW_DASHBOARD = auto()
    VIEW_MAP = auto()
    VIEW_DIAGNOSTICS = auto()
    VIEW_SETTINGS = auto()

    # Control permissions
    CONTROL_MOWER = auto()
    EMERGENCY_STOP = auto()

    # Configuration permissions
    EDIT_SETTINGS = auto()
    EDIT_BOUNDARY = auto()
    EDIT_SCHEDULE = auto()

    # System permissions
    MANAGE_USERS = auto()
    SYSTEM_MAINTENANCE = auto()
    VIEW_LOGS = auto()

    # Security permissions
    EDIT_SECURITY_SETTINGS = auto()


class Role(Enum):
    """User roles for the web interface."""

    VIEWER = "viewer"
    OPERATOR = "operator"
    ADMIN = "admin"


# Default permissions for each role
DEFAULT_ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.VIEWER: {
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_MAP,
        Permission.VIEW_DIAGNOSTICS,
        Permission.EMERGENCY_STOP,
    },
    Role.OPERATOR: {
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_MAP,
        Permission.VIEW_DIAGNOSTICS,
        Permission.VIEW_SETTINGS,
        Permission.CONTROL_MOWER,
        Permission.EMERGENCY_STOP,
        Permission.EDIT_BOUNDARY,
        Permission.EDIT_SCHEDULE,
    },
    Role.ADMIN: {
        # Admins have all permissions
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_MAP,
        Permission.VIEW_DIAGNOSTICS,
        Permission.VIEW_SETTINGS,
        Permission.CONTROL_MOWER,
        Permission.EMERGENCY_STOP,
        Permission.EDIT_SETTINGS,
        Permission.EDIT_BOUNDARY,
        Permission.EDIT_SCHEDULE,
        Permission.MANAGE_USERS,
        Permission.SYSTEM_MAINTENANCE,
        Permission.VIEW_LOGS,
        Permission.EDIT_SECURITY_SETTINGS,
    }
}


class PermissionManager:
    """Manager for user roles and permissions."""

    def __init__(self):
        """Initialize the permission manager."""
        self.role_permissions = DEFAULT_ROLE_PERMISSIONS.copy()
        self.user_roles: Dict[str, Role] = {}

    def get_user_role(self, username: str) -> Role:
        """Get the role for a user.

        Args:
            username: The username to get the role for.

        Returns:
            The user's role, or Role.VIEWER if the user has no role.
        """
        return self.user_roles.get(username, Role.VIEWER)

    def set_user_role(self, username: str, role: Role) -> None:
        """Set the role for a user.

        Args:
            username: The username to set the role for.
            role: The role to assign to the user.
        """
        self.user_roles[username] = role

    def has_permission(self, username: str, permission: Permission) -> bool:
        """Check if a user has a specific permission.

        Args:
            username: The username to check permissions for.
            permission: The permission to check.

        Returns:
            True if the user has the permission, False otherwise.
        """
        role = self.get_user_role(username)
        return permission in self.role_permissions[role]

    def get_user_permissions(self, username: str) -> Set[Permission]:
        """Get all permissions for a user.

        Args:
            username: The username to get permissions for.

        Returns:
            A set of permissions that the user has.
        """
        role = self.get_user_role(username)
        return self.role_permissions[role].copy()


# Singleton instance
_permission_manager_instance = None


def get_permission_manager() -> PermissionManager:
    """Get the permission manager instance.

    Returns:
        The permission manager instance.
    """
    global _permission_manager_instance

    if _permission_manager_instance is None:
        _permission_manager_instance = PermissionManager()

    return _permission_manager_instance


def require_permission(permission: Permission) -> Callable[[F], F]:
    """Decorator to require a specific permission for a route.

    Args:
        permission: The permission required to access the route.

    Returns:
        A decorator that checks if the user has the required permission.
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            # Check if the user is authenticated
            if not session.get('authenticated'):
                return abort(401)  # Unauthorized

            username = session.get('username', '')

            # Check if the user has the required permission
            permission_manager = get_permission_manager()
            if not permission_manager.has_permission(username, permission):
                # Get client IP address
                ip_address = request.remote_addr

                # Log access denied
                logger.warning(
                    f"Access denied: User '{username}' from {ip_address} "
                    f"attempted to access a resource requiring {permission.name}"
                )

                # Audit log for access denied
                audit_logger.log_access_denied(
                    username,
                    ip_address,
                    request.path,
                    f"Missing permission: {permission.name}"
                )

                return abort(403)  # Forbidden

            return func(*args, **kwargs)

        return cast(F, wrapped)

    return decorator


def init_permissions(app: Flask, config: dict) -> None:
    """Initialize permission management for the Flask application.

    Args:
        app: The Flask application instance.
        config: Configuration dictionary containing permission settings.
    """
    # Initialize the permission manager
    permission_manager = get_permission_manager()

    # Set up default admin user
    admin_username = config.get('auth_username', 'admin')
    permission_manager.set_user_role(admin_username, Role.ADMIN)

    # Add context processor to make permissions available in templates
    @app.context_processor
    def inject_permissions():
        """Inject permissions into templates."""
        if not session.get('authenticated'):
            return {'has_permission': lambda p: False}

        username = session.get('username', '')

        def has_permission(permission_name: str) -> bool:
            """Check if the current user has a specific permission.

            Args:
                permission_name: The name of the permission to check.

            Returns:
                True if the user has the permission, False otherwise.
            """
            try:
                permission = Permission[permission_name]
                return permission_manager.has_permission(username, permission)
            except KeyError:
                logger.error(f"Invalid permission name: {permission_name}")
                return False

        return {'has_permission': has_permission}
