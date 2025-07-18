"""
Health monitoring interfaces and base classes for system components.

This module provides interfaces and base classes for monitoring the health
of system components, tracking metrics, and providing diagnostic information.
"""

import abc
import enum
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger(__name__)


class HealthStatus(enum.Enum):
    """Health status of a component."""
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    STARTING = "starting"
    STOPPING = "stopping"
    MAINTENANCE = "maintenance"


@dataclass
class HealthIssue:
    """Represents a health issue with a component."""
    
    id: str
    description: str
    severity: str  # "info", "warning", "error", "critical"
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict[str, Any] = field(default_factory=dict)
    related_component: Optional[str] = None
    resolution_steps: List[str] = field(default_factory=list)
    
    def is_critical(self) -> bool:
        """Check if issue is critical."""
        return self.severity == "critical"
    
    def is_error(self) -> bool:
        """Check if issue is an error."""
        return self.severity in ("error", "critical")
    
    def is_warning(self) -> bool:
        """Check if issue is a warning."""
        return self.severity == "warning"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "description": self.description,
            "severity": self.severity,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
            "related_component": self.related_component,
            "resolution_steps": self.resolution_steps
        }


@dataclass
class ComponentHealth:
    """
    Health status and metrics for a component.
    
    This class tracks the health status, metrics, and issues for a component,
    providing a comprehensive view of its current state.
    """
    
    component_name: str
    status: HealthStatus = HealthStatus.UNKNOWN
    last_check: datetime = field(default_factory=datetime.now)
    start_time: datetime = field(default_factory=datetime.now)
    metrics: Dict[str, Any] = field(default_factory=dict)
    issues: List[HealthIssue] = field(default_factory=list)
    dependencies: Set[str] = field(default_factory=set)
    
    def update_status(self, status: HealthStatus) -> None:
        """Update health status."""
        self.status = status
        self.last_check = datetime.now()
    
    def add_issue(self, issue: HealthIssue) -> None:
        """Add a health issue."""
        self.issues.append(issue)
        
        # Update status based on issue severity
        if issue.severity == "critical":
            self.status = HealthStatus.FAILED
        elif issue.severity == "error" and self.status != HealthStatus.FAILED:
            self.status = HealthStatus.DEGRADED
        elif issue.severity == "warning" and self.status == HealthStatus.HEALTHY:
            self.status = HealthStatus.DEGRADED
    
    def clear_issues(self) -> None:
        """Clear all health issues."""
        self.issues = []
    
    def update_metric(self, name: str, value: Any) -> None:
        """Update a metric value."""
        self.metrics[name] = value
        self.last_check = datetime.now()
    
    def get_uptime(self) -> timedelta:
        """Get component uptime."""
        return datetime.now() - self.start_time
    
    def is_healthy(self) -> bool:
        """Check if component is healthy."""
        return self.status == HealthStatus.HEALTHY
    
    def is_degraded(self) -> bool:
        """Check if component is degraded."""
        return self.status == HealthStatus.DEGRADED
    
    def is_failed(self) -> bool:
        """Check if component has failed."""
        return self.status == HealthStatus.FAILED
    
    def has_critical_issues(self) -> bool:
        """Check if component has critical issues."""
        return any(issue.is_critical() for issue in self.issues)
    
    def get_issues_by_severity(self, severity: str) -> List[HealthIssue]:
        """Get issues filtered by severity."""
        return [issue for issue in self.issues if issue.severity == severity]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "component_name": self.component_name,
            "status": self.status.value,
            "last_check": self.last_check.isoformat(),
            "start_time": self.start_time.isoformat(),
            "uptime_seconds": self.get_uptime().total_seconds(),
            "metrics": self.metrics,
            "issues": [issue.to_dict() for issue in self.issues],
            "dependencies": list(self.dependencies)
        }


class HealthCheckInterface(abc.ABC):
    """
    Interface for components that support health checks.
    
    This interface defines the standard methods that components should implement
    to support health monitoring and diagnostics.
    """
    
    @abc.abstractmethod
    def check_health(self) -> ComponentHealth:
        """
        Check component health and return status.
        
        Returns:
            ComponentHealth: Current health status and metrics
        """
        pass
    
    @abc.abstractmethod
    def get_health_metrics(self) -> Dict[str, Any]:
        """
        Get component health metrics.
        
        Returns:
            Dict[str, Any]: Current metrics
        """
        pass
    
    def register_health_callback(self, callback: Callable[[ComponentHealth], None]) -> None:
        """
        Register callback for health status changes.
        
        Args:
            callback: Function to call when health status changes
        """
        pass


class HealthMonitor:
    """
    Monitor health of system components.
    
    This class provides centralized health monitoring for system components,
    tracking their status, metrics, and issues.
    """
    
    def __init__(self):
        """Initialize health monitor."""
        self._components: Dict[str, ComponentHealth] = {}
        self._callbacks: Dict[str, List[Callable[[ComponentHealth], None]]] = {}
        self._global_callbacks: List[Callable[[str, ComponentHealth], None]] = []
        self._check_interval: float = 60.0  # seconds
        self._last_check: Dict[str, float] = {}
    
    def register_component(
        self,
        component_name: str,
        initial_status: HealthStatus = HealthStatus.UNKNOWN,
        dependencies: Optional[List[str]] = None
    ) -> ComponentHealth:
        """
        Register a component for health monitoring.
        
        Args:
            component_name: Name of the component
            initial_status: Initial health status
            dependencies: List of component dependencies
            
        Returns:
            ComponentHealth: Component health object
        """
        if component_name in self._components:
            return self._components[component_name]
        
        health = ComponentHealth(
            component_name=component_name,
            status=initial_status,
            dependencies=set(dependencies or [])
        )
        
        self._components[component_name] = health
        self._callbacks[component_name] = []
        self._last_check[component_name] = time.time()
        
        logger.info(f"Registered component '{component_name}' for health monitoring")
        return health
    
    def update_health(
        self,
        component_name: str,
        status: Optional[HealthStatus] = None,
        metrics: Optional[Dict[str, Any]] = None,
        issues: Optional[List[HealthIssue]] = None
    ) -> None:
        """
        Update component health.
        
        Args:
            component_name: Name of the component
            status: New health status (if None, status is not updated)
            metrics: Metrics to update (if None, metrics are not updated)
            issues: Issues to add (if None, no issues are added)
        """
        if component_name not in self._components:
            health = self.register_component(component_name)
        else:
            health = self._components[component_name]
        
        if status is not None:
            old_status = health.status
            health.update_status(status)
            
            # Notify callbacks if status changed
            if old_status != status:
                self._notify_callbacks(component_name, health)
        
        if metrics is not None:
            for name, value in metrics.items():
                health.update_metric(name, value)
        
        if issues is not None:
            for issue in issues:
                health.add_issue(issue)
                
                # Notify callbacks if critical issue
                if issue.is_critical():
                    self._notify_callbacks(component_name, health)
        
        self._last_check[component_name] = time.time()
    
    def get_component_health(self, component_name: str) -> Optional[ComponentHealth]:
        """
        Get health status for a component.
        
        Args:
            component_name: Name of the component
            
        Returns:
            ComponentHealth or None if component not found
        """
        return self._components.get(component_name)
    
    def get_all_health(self) -> Dict[str, ComponentHealth]:
        """
        Get health status for all components.
        
        Returns:
            Dict[str, ComponentHealth]: Health status by component name
        """
        return self._components.copy()
    
    def register_callback(
        self,
        component_name: str,
        callback: Callable[[ComponentHealth], None]
    ) -> None:
        """
        Register callback for component health changes.
        
        Args:
            component_name: Name of the component
            callback: Function to call when health status changes
        """
        if component_name not in self._callbacks:
            self._callbacks[component_name] = []
        
        self._callbacks[component_name].append(callback)
    
    def register_global_callback(
        self,
        callback: Callable[[str, ComponentHealth], None]
    ) -> None:
        """
        Register global callback for any component health changes.
        
        Args:
            callback: Function to call when any component's health changes
        """
        self._global_callbacks.append(callback)
    
    def _notify_callbacks(self, component_name: str, health: ComponentHealth) -> None:
        """
        Notify callbacks of health status change.
        
        Args:
            component_name: Name of the component
            health: Current health status
        """
        # Component-specific callbacks
        for callback in self._callbacks.get(component_name, []):
            try:
                callback(health)
            except Exception as e:
                logger.error(f"Error in health callback for '{component_name}': {e}")
        
        # Global callbacks
        for callback in self._global_callbacks:
            try:
                callback(component_name, health)
            except Exception as e:
                logger.error(f"Error in global health callback for '{component_name}': {e}")
    
    def check_component(self, component_name: str, component: HealthCheckInterface) -> ComponentHealth:
        """
        Check health of a component.
        
        Args:
            component_name: Name of the component
            component: Component to check
            
        Returns:
            ComponentHealth: Updated health status
        """
        try:
            health = component.check_health()
            self.update_health(
                component_name,
                status=health.status,
                metrics=health.metrics,
                issues=health.issues
            )
            return health
        except Exception as e:
            logger.error(f"Error checking health of '{component_name}': {e}")
            
            # Create failure health status
            issue = HealthIssue(
                id=f"{component_name}_check_failed",
                description=f"Health check failed: {e}",
                severity="error",
                details={"exception": str(e), "traceback": traceback.format_exc()}
            )
            
            self.update_health(
                component_name,
                status=HealthStatus.DEGRADED,
                issues=[issue]
            )
            
            return self._components[component_name]
    
    def check_all_components(self, components: Dict[str, HealthCheckInterface]) -> Dict[str, ComponentHealth]:
        """
        Check health of all components.
        
        Args:
            components: Dictionary of component name to component
            
        Returns:
            Dict[str, ComponentHealth]: Updated health status by component name
        """
        results = {}
        for name, component in components.items():
            results[name] = self.check_component(name, component)
        return results
    
    def get_system_health(self) -> Tuple[HealthStatus, List[HealthIssue]]:
        """
        Get overall system health status.
        
        Returns:
            Tuple[HealthStatus, List[HealthIssue]]: Overall status and issues
        """
        if not self._components:
            return HealthStatus.UNKNOWN, []
        
        # Collect all issues
        all_issues = []
        for health in self._components.values():
            all_issues.extend(health.issues)
        
        # Determine overall status
        if any(health.status == HealthStatus.FAILED for health in self._components.values()):
            return HealthStatus.FAILED, all_issues
        
        if any(health.status == HealthStatus.DEGRADED for health in self._components.values()):
            return HealthStatus.DEGRADED, all_issues
        
        if all(health.status == HealthStatus.HEALTHY for health in self._components.values()):
            return HealthStatus.HEALTHY, all_issues
        
        # Some components are unknown, starting, or stopping
        return HealthStatus.DEGRADED, all_issues
    
    def get_health_summary(self) -> Dict[str, Any]:
        """
        Get summary of system health.
        
        Returns:
            Dict[str, Any]: Health summary
        """
        overall_status, issues = self.get_system_health()
        
        # Count components by status
        status_counts = {status.value: 0 for status in HealthStatus}
        for health in self._components.values():
            status_counts[health.status.value] += 1
        
        # Count issues by severity
        severity_counts = {"info": 0, "warning": 0, "error": 0, "critical": 0}
        for issue in issues:
            severity_counts[issue.severity] += 1
        
        return {
            "overall_status": overall_status.value,
            "component_count": len(self._components),
            "status_counts": status_counts,
            "issue_counts": severity_counts,
            "critical_issues": [issue.to_dict() for issue in issues if issue.severity == "critical"],
            "error_issues": [issue.to_dict() for issue in issues if issue.severity == "error"],
            "timestamp": datetime.now().isoformat()
        }


# Global health monitor instance
_health_monitor = HealthMonitor()


def get_health_monitor() -> HealthMonitor:
    """Get the global health monitor instance."""
    return _health_monitor


class HealthCheckMixin:
    """
    Mixin for adding health check capabilities to a class.
    
    This mixin provides a default implementation of the HealthCheckInterface
    that can be easily added to existing classes.
    """
    
    def __init__(self, component_name: str, *args, **kwargs):
        """
        Initialize health check mixin.
        
        Args:
            component_name: Name of the component
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments
        """
        super().__init__(*args, **kwargs)
        self._component_name = component_name
        self._health = ComponentHealth(component_name=component_name)
        self._health_callbacks: List[Callable[[ComponentHealth], None]] = []
        
        # Register with global health monitor
        get_health_monitor().register_component(component_name)
    
    def check_health(self) -> ComponentHealth:
        """
        Check component health and return status.
        
        Returns:
            ComponentHealth: Current health status and metrics
        """
        # Update last check time
        self._health.last_check = datetime.now()
        
        # Collect metrics (override in subclass for specific metrics)
        self._collect_health_metrics()
        
        return self._health
    
    def _collect_health_metrics(self) -> None:
        """
        Collect health metrics.
        
        This method should be overridden by subclasses to collect
        component-specific metrics.
        """
        # Default implementation just updates uptime
        self._health.update_metric("uptime_seconds", self._health.get_uptime().total_seconds())
    
    def get_health_metrics(self) -> Dict[str, Any]:
        """
        Get component health metrics.
        
        Returns:
            Dict[str, Any]: Current metrics
        """
        return self._health.metrics
    
    def update_health_status(self, status: HealthStatus) -> None:
        """
        Update component health status.
        
        Args:
            status: New health status
        """
        old_status = self._health.status
        self._health.update_status(status)
        
        # Notify callbacks if status changed
        if old_status != status:
            self._notify_health_callbacks()
            
            # Update global health monitor
            get_health_monitor().update_health(
                self._component_name,
                status=status
            )
    
    def add_health_issue(self, issue: HealthIssue) -> None:
        """
        Add a health issue.
        
        Args:
            issue: Health issue to add
        """
        self._health.add_issue(issue)
        
        # Notify callbacks if critical issue
        if issue.is_critical():
            self._notify_health_callbacks()
        
        # Update global health monitor
        get_health_monitor().update_health(
            self._component_name,
            issues=[issue]
        )
    
    def update_health_metric(self, name: str, value: Any) -> None:
        """
        Update a health metric.
        
        Args:
            name: Metric name
            value: Metric value
        """
        self._health.update_metric(name, value)
        
        # Update global health monitor
        get_health_monitor().update_health(
            self._component_name,
            metrics={name: value}
        )
    
    def register_health_callback(self, callback: Callable[[ComponentHealth], None]) -> None:
        """
        Register callback for health status changes.
        
        Args:
            callback: Function to call when health status changes
        """
        self._health_callbacks.append(callback)
    
    def _notify_health_callbacks(self) -> None:
        """Notify all registered health callbacks."""
        for callback in self._health_callbacks:
            try:
                callback(self._health)
            except Exception as e:
                logger.error(f"Error in health callback for '{self._component_name}': {e}")


def create_health_issue(
    component_name: str,
    issue_id: str,
    description: str,
    severity: str = "error",
    details: Optional[Dict[str, Any]] = None,
    resolution_steps: Optional[List[str]] = None
) -> HealthIssue:
    """
    Create a health issue and register it with the health monitor.
    
    Args:
        component_name: Name of the component
        issue_id: Unique identifier for the issue
        description: Description of the issue
        severity: Issue severity ("info", "warning", "error", "critical")
        details: Additional details about the issue
        resolution_steps: Steps to resolve the issue
        
    Returns:
        HealthIssue: Created health issue
    """
    issue = HealthIssue(
        id=issue_id,
        description=description,
        severity=severity,
        details=details or {},
        related_component=component_name,
        resolution_steps=resolution_steps or []
    )
    
    # Register with health monitor
    get_health_monitor().update_health(
        component_name,
        issues=[issue]
    )
    
    return issue


import traceback  # Import at the top of the file