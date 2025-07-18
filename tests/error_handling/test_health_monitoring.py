"""
Unit tests for health monitoring interfaces.
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from mower.error_handling.health_monitoring import (
    ComponentHealth,
    HealthCheckInterface,
    HealthCheckMixin,
    HealthIssue,
    HealthMonitor,
    HealthStatus,
    create_health_issue,
    get_health_monitor,
)


class TestHealthIssue:
    """Test cases for HealthIssue class."""
    
    def test_init_default_values(self):
        """Test health issue initialization with default values."""
        issue = HealthIssue(
            id="test_issue",
            description="Test issue",
            severity="warning"
        )
        
        assert issue.id == "test_issue"
        assert issue.description == "Test issue"
        assert issue.severity == "warning"
        assert isinstance(issue.timestamp, datetime)
        assert issue.details == {}
        assert issue.related_component is None
        assert issue.resolution_steps == []
    
    def test_init_custom_values(self):
        """Test health issue initialization with custom values."""
        timestamp = datetime.now()
        details = {"key": "value"}
        resolution_steps = ["Step 1", "Step 2"]
        
        issue = HealthIssue(
            id="test_issue",
            description="Test issue",
            severity="error",
            timestamp=timestamp,
            details=details,
            related_component="test_component",
            resolution_steps=resolution_steps
        )
        
        assert issue.id == "test_issue"
        assert issue.description == "Test issue"
        assert issue.severity == "error"
        assert issue.timestamp == timestamp
        assert issue.details == details
        assert issue.related_component == "test_component"
        assert issue.resolution_steps == resolution_steps
    
    def test_severity_checks(self):
        """Test severity check methods."""
        critical_issue = HealthIssue(id="critical", description="Critical issue", severity="critical")
        error_issue = HealthIssue(id="error", description="Error issue", severity="error")
        warning_issue = HealthIssue(id="warning", description="Warning issue", severity="warning")
        info_issue = HealthIssue(id="info", description="Info issue", severity="info")
        
        assert critical_issue.is_critical() is True
        assert critical_issue.is_error() is True
        assert critical_issue.is_warning() is False
        
        assert error_issue.is_critical() is False
        assert error_issue.is_error() is True
        assert error_issue.is_warning() is False
        
        assert warning_issue.is_critical() is False
        assert warning_issue.is_error() is False
        assert warning_issue.is_warning() is True
        
        assert info_issue.is_critical() is False
        assert info_issue.is_error() is False
        assert info_issue.is_warning() is False
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        timestamp = datetime.now()
        issue = HealthIssue(
            id="test_issue",
            description="Test issue",
            severity="warning",
            timestamp=timestamp,
            details={"key": "value"},
            related_component="test_component",
            resolution_steps=["Step 1", "Step 2"]
        )
        
        result = issue.to_dict()
        
        assert result["id"] == "test_issue"
        assert result["description"] == "Test issue"
        assert result["severity"] == "warning"
        assert result["timestamp"] == timestamp.isoformat()
        assert result["details"] == {"key": "value"}
        assert result["related_component"] == "test_component"
        assert result["resolution_steps"] == ["Step 1", "Step 2"]


class TestComponentHealth:
    """Test cases for ComponentHealth class."""
    
    def test_init_default_values(self):
        """Test component health initialization with default values."""
        health = ComponentHealth(component_name="test_component")
        
        assert health.component_name == "test_component"
        assert health.status == HealthStatus.UNKNOWN
        assert isinstance(health.last_check, datetime)
        assert isinstance(health.start_time, datetime)
        assert health.metrics == {}
        assert health.issues == []
        assert health.dependencies == set()
    
    def test_init_custom_values(self):
        """Test component health initialization with custom values."""
        last_check = datetime.now()
        start_time = datetime.now() - timedelta(hours=1)
        metrics = {"metric1": 10, "metric2": "value"}
        issues = [HealthIssue(id="issue1", description="Issue 1", severity="warning")]
        dependencies = {"dep1", "dep2"}
        
        health = ComponentHealth(
            component_name="test_component",
            status=HealthStatus.HEALTHY,
            last_check=last_check,
            start_time=start_time,
            metrics=metrics,
            issues=issues,
            dependencies=dependencies
        )
        
        assert health.component_name == "test_component"
        assert health.status == HealthStatus.HEALTHY
        assert health.last_check == last_check
        assert health.start_time == start_time
        assert health.metrics == metrics
        assert health.issues == issues
        assert health.dependencies == dependencies
    
    def test_update_status(self):
        """Test updating health status."""
        health = ComponentHealth(component_name="test_component")
        
        # Initial status
        assert health.status == HealthStatus.UNKNOWN
        
        # Update status
        health.update_status(HealthStatus.HEALTHY)
        assert health.status == HealthStatus.HEALTHY
        
        # Check that last_check was updated
        assert (datetime.now() - health.last_check).total_seconds() < 1.0
    
    def test_add_issue(self):
        """Test adding health issues."""
        health = ComponentHealth(component_name="test_component", status=HealthStatus.HEALTHY)
        
        # Add warning issue
        warning_issue = HealthIssue(id="warning", description="Warning issue", severity="warning")
        health.add_issue(warning_issue)
        
        assert len(health.issues) == 1
        assert health.issues[0] == warning_issue
        assert health.status == HealthStatus.DEGRADED  # Status should change to DEGRADED
        
        # Add error issue
        error_issue = HealthIssue(id="error", description="Error issue", severity="error")
        health.add_issue(error_issue)
        
        assert len(health.issues) == 2
        assert health.issues[1] == error_issue
        assert health.status == HealthStatus.DEGRADED  # Status should remain DEGRADED
        
        # Add critical issue
        critical_issue = HealthIssue(id="critical", description="Critical issue", severity="critical")
        health.add_issue(critical_issue)
        
        assert len(health.issues) == 3
        assert health.issues[2] == critical_issue
        assert health.status == HealthStatus.FAILED  # Status should change to FAILED
    
    def test_clear_issues(self):
        """Test clearing health issues."""
        health = ComponentHealth(component_name="test_component")
        
        # Add issues
        health.add_issue(HealthIssue(id="issue1", description="Issue 1", severity="warning"))
        health.add_issue(HealthIssue(id="issue2", description="Issue 2", severity="error"))
        
        assert len(health.issues) == 2
        
        # Clear issues
        health.clear_issues()
        
        assert len(health.issues) == 0
    
    def test_update_metric(self):
        """Test updating metrics."""
        health = ComponentHealth(component_name="test_component")
        
        # Update metric
        health.update_metric("metric1", 10)
        
        assert health.metrics == {"metric1": 10}
        
        # Update existing metric
        health.update_metric("metric1", 20)
        
        assert health.metrics == {"metric1": 20}
        
        # Add another metric
        health.update_metric("metric2", "value")
        
        assert health.metrics == {"metric1": 20, "metric2": "value"}
    
    def test_get_uptime(self):
        """Test getting uptime."""
        # Create component with start time in the past
        start_time = datetime.now() - timedelta(hours=1)
        health = ComponentHealth(component_name="test_component", start_time=start_time)
        
        uptime = health.get_uptime()
        
        # Uptime should be close to 1 hour
        assert 3500 < uptime.total_seconds() < 3700  # Allow some margin for test execution time
    
    def test_status_checks(self):
        """Test status check methods."""
        health = ComponentHealth(component_name="test_component")
        
        # Test HEALTHY status
        health.update_status(HealthStatus.HEALTHY)
        assert health.is_healthy() is True
        assert health.is_degraded() is False
        assert health.is_failed() is False
        
        # Test DEGRADED status
        health.update_status(HealthStatus.DEGRADED)
        assert health.is_healthy() is False
        assert health.is_degraded() is True
        assert health.is_failed() is False
        
        # Test FAILED status
        health.update_status(HealthStatus.FAILED)
        assert health.is_healthy() is False
        assert health.is_degraded() is False
        assert health.is_failed() is True
    
    def test_has_critical_issues(self):
        """Test checking for critical issues."""
        health = ComponentHealth(component_name="test_component")
        
        # No issues
        assert health.has_critical_issues() is False
        
        # Add non-critical issue
        health.add_issue(HealthIssue(id="warning", description="Warning issue", severity="warning"))
        assert health.has_critical_issues() is False
        
        # Add critical issue
        health.add_issue(HealthIssue(id="critical", description="Critical issue", severity="critical"))
        assert health.has_critical_issues() is True
    
    def test_get_issues_by_severity(self):
        """Test getting issues by severity."""
        health = ComponentHealth(component_name="test_component")
        
        # Add issues with different severities
        health.add_issue(HealthIssue(id="info", description="Info issue", severity="info"))
        health.add_issue(HealthIssue(id="warning1", description="Warning issue 1", severity="warning"))
        health.add_issue(HealthIssue(id="warning2", description="Warning issue 2", severity="warning"))
        health.add_issue(HealthIssue(id="error", description="Error issue", severity="error"))
        health.add_issue(HealthIssue(id="critical", description="Critical issue", severity="critical"))
        
        # Get issues by severity
        info_issues = health.get_issues_by_severity("info")
        warning_issues = health.get_issues_by_severity("warning")
        error_issues = health.get_issues_by_severity("error")
        critical_issues = health.get_issues_by_severity("critical")
        
        assert len(info_issues) == 1
        assert info_issues[0].id == "info"
        
        assert len(warning_issues) == 2
        assert {issue.id for issue in warning_issues} == {"warning1", "warning2"}
        
        assert len(error_issues) == 1
        assert error_issues[0].id == "error"
        
        assert len(critical_issues) == 1
        assert critical_issues[0].id == "critical"
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        health = ComponentHealth(
            component_name="test_component",
            status=HealthStatus.HEALTHY,
            metrics={"metric1": 10, "metric2": "value"},
            dependencies={"dep1", "dep2"}
        )
        
        # Add an issue
        health.add_issue(HealthIssue(id="issue1", description="Issue 1", severity="warning"))
        
        result = health.to_dict()
        
        assert result["component_name"] == "test_component"
        assert result["status"] == "healthy"
        assert "last_check" in result
        assert "start_time" in result
        assert "uptime_seconds" in result
        assert result["metrics"] == {"metric1": 10, "metric2": "value"}
        assert len(result["issues"]) == 1
        assert result["issues"][0]["id"] == "issue1"
        assert sorted(result["dependencies"]) == ["dep1", "dep2"]


class MockHealthCheckComponent(HealthCheckInterface):
    """Mock component implementing HealthCheckInterface for testing."""
    
    def __init__(self, component_name: str):
        self.component_name = component_name
        self._health = ComponentHealth(component_name=component_name)
        self._callbacks = []
    
    def check_health(self) -> ComponentHealth:
        self._health.update_metric("check_count", self._health.metrics.get("check_count", 0) + 1)
        return self._health
    
    def get_health_metrics(self) -> dict:
        return self._health.metrics
    
    def register_health_callback(self, callback):
        self._callbacks.append(callback)
    
    def update_status(self, status: HealthStatus):
        self._health.update_status(status)
        for callback in self._callbacks:
            callback(self._health)


class TestHealthMonitor:
    """Test cases for HealthMonitor class."""
    
    def test_register_component(self):
        """Test registering a component."""
        monitor = HealthMonitor()
        
        health = monitor.register_component("test_component")
        
        assert health.component_name == "test_component"
        assert monitor.get_component_health("test_component") == health
    
    def test_register_component_with_dependencies(self):
        """Test registering a component with dependencies."""
        monitor = HealthMonitor()
        
        health = monitor.register_component(
            "test_component",
            initial_status=HealthStatus.HEALTHY,
            dependencies=["dep1", "dep2"]
        )
        
        assert health.status == HealthStatus.HEALTHY
        assert health.dependencies == {"dep1", "dep2"}
    
    def test_update_health(self):
        """Test updating component health."""
        monitor = HealthMonitor()
        
        # Register component
        monitor.register_component("test_component")
        
        # Update health
        monitor.update_health(
            "test_component",
            status=HealthStatus.HEALTHY,
            metrics={"metric1": 10},
            issues=[HealthIssue(id="issue1", description="Issue 1", severity="warning")]
        )
        
        health = monitor.get_component_health("test_component")
        assert health.status == HealthStatus.HEALTHY
        assert health.metrics == {"metric1": 10}
        assert len(health.issues) == 1
        assert health.issues[0].id == "issue1"
    
    def test_update_health_unregistered_component(self):
        """Test updating health for unregistered component."""
        monitor = HealthMonitor()
        
        # Update health for unregistered component
        monitor.update_health(
            "new_component",
            status=HealthStatus.HEALTHY
        )
        
        # Component should be automatically registered
        health = monitor.get_component_health("new_component")
        assert health is not None
        assert health.component_name == "new_component"
        assert health.status == HealthStatus.HEALTHY
    
    def test_get_all_health(self):
        """Test getting health for all components."""
        monitor = HealthMonitor()
        
        # Register components
        monitor.register_component("component1", initial_status=HealthStatus.HEALTHY)
        monitor.register_component("component2", initial_status=HealthStatus.DEGRADED)
        
        # Get all health
        all_health = monitor.get_all_health()
        
        assert len(all_health) == 2
        assert all_health["component1"].status == HealthStatus.HEALTHY
        assert all_health["component2"].status == HealthStatus.DEGRADED
    
    def test_register_callback(self):
        """Test registering callback for component health changes."""
        monitor = HealthMonitor()
        callback = Mock()
        
        # Register component and callback
        monitor.register_component("test_component")
        monitor.register_callback("test_component", callback)
        
        # Update health to trigger callback
        monitor.update_health("test_component", status=HealthStatus.DEGRADED)
        
        # Check that callback was called
        callback.assert_called_once()
        health = callback.call_args[0][0]
        assert health.component_name == "test_component"
        assert health.status == HealthStatus.DEGRADED
    
    def test_register_global_callback(self):
        """Test registering global callback for any component health changes."""
        monitor = HealthMonitor()
        callback = Mock()
        
        # Register components and global callback
        monitor.register_component("component1")
        monitor.register_component("component2")
        monitor.register_global_callback(callback)
        
        # Update health to trigger callback
        monitor.update_health("component1", status=HealthStatus.DEGRADED)
        
        # Check that callback was called
        callback.assert_called_once()
        component_name, health = callback.call_args[0]
        assert component_name == "component1"
        assert health.status == HealthStatus.DEGRADED
        
        # Reset mock and update another component
        callback.reset_mock()
        monitor.update_health("component2", status=HealthStatus.FAILED)
        
        # Check that callback was called again
        callback.assert_called_once()
        component_name, health = callback.call_args[0]
        assert component_name == "component2"
        assert health.status == HealthStatus.FAILED
    
    def test_check_component(self):
        """Test checking health of a component."""
        monitor = HealthMonitor()
        component = MockHealthCheckComponent("test_component")
        
        # Check component health
        health = monitor.check_component("test_component", component)
        
        assert health.component_name == "test_component"
        assert health.metrics.get("check_count") == 1
        
        # Check component health again
        health = monitor.check_component("test_component", component)
        
        assert health.metrics.get("check_count") == 2
    
    def test_check_all_components(self):
        """Test checking health of all components."""
        monitor = HealthMonitor()
        component1 = MockHealthCheckComponent("component1")
        component2 = MockHealthCheckComponent("component2")
        
        # Check all components
        results = monitor.check_all_components({
            "component1": component1,
            "component2": component2
        })
        
        assert len(results) == 2
        assert results["component1"].component_name == "component1"
        assert results["component2"].component_name == "component2"
        assert results["component1"].metrics.get("check_count") == 1
        assert results["component2"].metrics.get("check_count") == 1
    
    def test_get_system_health_empty(self):
        """Test getting system health with no components."""
        monitor = HealthMonitor()
        
        status, issues = monitor.get_system_health()
        
        assert status == HealthStatus.UNKNOWN
        assert issues == []
    
    def test_get_system_health(self):
        """Test getting system health."""
        monitor = HealthMonitor()
        
        # Register components with different statuses
        monitor.register_component("component1", initial_status=HealthStatus.HEALTHY)
        monitor.register_component("component2", initial_status=HealthStatus.DEGRADED)
        
        # Add issues
        monitor.update_health(
            "component2",
            issues=[HealthIssue(id="issue1", description="Issue 1", severity="warning")]
        )
        
        # Get system health
        status, issues = monitor.get_system_health()
        
        assert status == HealthStatus.DEGRADED
        assert len(issues) == 1
        assert issues[0].id == "issue1"
        
        # Update component to FAILED
        monitor.update_health(
            "component2",
            status=HealthStatus.FAILED,
            issues=[HealthIssue(id="issue2", description="Issue 2", severity="critical")]
        )
        
        # Get system health again
        status, issues = monitor.get_system_health()
        
        assert status == HealthStatus.FAILED
        assert len(issues) == 2
        assert {issue.id for issue in issues} == {"issue1", "issue2"}
    
    def test_get_health_summary(self):
        """Test getting health summary."""
        monitor = HealthMonitor()
        
        # Register components with different statuses
        monitor.register_component("component1", initial_status=HealthStatus.HEALTHY)
        monitor.register_component("component2", initial_status=HealthStatus.DEGRADED)
        monitor.register_component("component3", initial_status=HealthStatus.FAILED)
        
        # Add issues with different severities
        monitor.update_health(
            "component2",
            issues=[
                HealthIssue(id="warning", description="Warning issue", severity="warning"),
                HealthIssue(id="error", description="Error issue", severity="error")
            ]
        )
        
        monitor.update_health(
            "component3",
            issues=[HealthIssue(id="critical", description="Critical issue", severity="critical")]
        )
        
        # Get health summary
        summary = monitor.get_health_summary()
        
        assert summary["overall_status"] == "failed"
        assert summary["component_count"] == 3
        assert summary["status_counts"]["healthy"] == 1
        assert summary["status_counts"]["degraded"] == 1
        assert summary["status_counts"]["failed"] == 1
        assert summary["issue_counts"]["warning"] == 1
        assert summary["issue_counts"]["error"] == 1
        assert summary["issue_counts"]["critical"] == 1
        assert len(summary["critical_issues"]) == 1
        assert summary["critical_issues"][0]["id"] == "critical"
        assert len(summary["error_issues"]) == 1
        assert summary["error_issues"][0]["id"] == "error"


class TestHealthCheckMixin:
    """Test cases for HealthCheckMixin class."""
    
    class TestComponent(HealthCheckMixin):
        """Test component using HealthCheckMixin."""
        
        def __init__(self, component_name):
            super().__init__(component_name=component_name)
            self.value = 0
        
        def _collect_health_metrics(self):
            super()._collect_health_metrics()
            self.update_health_metric("value", self.value)
    
    def test_init(self):
        """Test initialization."""
        component = self.TestComponent("test_component")
        
        assert component._component_name == "test_component"
        assert component._health.component_name == "test_component"
        assert component._health_callbacks == []
    
    def test_check_health(self):
        """Test check_health method."""
        component = self.TestComponent("test_component")
        component.value = 42
        
        health = component.check_health()
        
        assert health.component_name == "test_component"
        assert health.metrics["value"] == 42
        assert "uptime_seconds" in health.metrics
    
    def test_get_health_metrics(self):
        """Test get_health_metrics method."""
        component = self.TestComponent("test_component")
        component.value = 42
        
        # Check health to collect metrics
        component.check_health()
        
        metrics = component.get_health_metrics()
        
        assert metrics["value"] == 42
        assert "uptime_seconds" in metrics
    
    def test_update_health_status(self):
        """Test update_health_status method."""
        component = self.TestComponent("test_component")
        callback = Mock()
        
        # Register callback
        component.register_health_callback(callback)
        
        # Update status
        component.update_health_status(HealthStatus.DEGRADED)
        
        assert component._health.status == HealthStatus.DEGRADED
        
        # Check that callback was called
        callback.assert_called_once()
        health = callback.call_args[0][0]
        assert health.status == HealthStatus.DEGRADED
        
        # Check that global health monitor was updated
        monitor = get_health_monitor()
        health = monitor.get_component_health("test_component")
        assert health is not None
        assert health.status == HealthStatus.DEGRADED
    
    def test_add_health_issue(self):
        """Test add_health_issue method."""
        component = self.TestComponent("test_component")
        callback = Mock()
        
        # Register callback
        component.register_health_callback(callback)
        
        # Add issue
        issue = HealthIssue(id="issue1", description="Issue 1", severity="warning")
        component.add_health_issue(issue)
        
        assert len(component._health.issues) == 1
        assert component._health.issues[0] == issue
        
        # Non-critical issue should not trigger callback
        callback.assert_not_called()
        
        # Add critical issue
        critical_issue = HealthIssue(id="critical", description="Critical issue", severity="critical")
        component.add_health_issue(critical_issue)
        
        # Critical issue should trigger callback
        callback.assert_called_once()
        
        # Check that global health monitor was updated
        monitor = get_health_monitor()
        health = monitor.get_component_health("test_component")
        assert health is not None
        assert len(health.issues) == 2
    
    def test_update_health_metric(self):
        """Test update_health_metric method."""
        component = self.TestComponent("test_component")
        
        # Update metric
        component.update_health_metric("test_metric", 42)
        
        assert component._health.metrics["test_metric"] == 42
        
        # Check that global health monitor was updated
        monitor = get_health_monitor()
        health = monitor.get_component_health("test_component")
        assert health is not None
        assert health.metrics["test_metric"] == 42


def test_create_health_issue():
    """Test create_health_issue function."""
    # Reset health monitor
    monitor = get_health_monitor()
    
    # Create health issue
    issue = create_health_issue(
        component_name="test_component",
        issue_id="test_issue",
        description="Test issue",
        severity="warning",
        details={"key": "value"},
        resolution_steps=["Step 1", "Step 2"]
    )
    
    assert issue.id == "test_issue"
    assert issue.description == "Test issue"
    assert issue.severity == "warning"
    assert issue.details == {"key": "value"}
    assert issue.related_component == "test_component"
    assert issue.resolution_steps == ["Step 1", "Step 2"]
    
    # Check that issue was registered with health monitor
    health = monitor.get_component_health("test_component")
    assert health is not None
    assert len(health.issues) == 1
    assert health.issues[0].id == "test_issue"


def test_get_health_monitor():
    """Test get_health_monitor function."""
    monitor1 = get_health_monitor()
    monitor2 = get_health_monitor()
    
    assert monitor1 is monitor2  # Should be singleton