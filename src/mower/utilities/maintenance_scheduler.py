#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Maintenance scheduler for the autonomous mower.

This module provides functionality to track maintenance tasks, schedule them
based on usage or time intervals, and provide reminders when maintenance is due.
It helps users keep their mowers in good condition and prevent failures due to
lack of maintenance.

Key features:
- Define maintenance tasks with intervals
- Track usage metrics (runtime, distance, etc.)
- Schedule maintenance based on usage or time
- Generate maintenance reminders
- Log maintenance history
- Export maintenance schedule

Example usage:
    # Initialize the maintenance scheduler
    scheduler = MaintenanceScheduler()

    # Define maintenance tasks
    scheduler.add_task("blade_replacement", "Replace cutting blade",
                      interval_hours=100, interval_distance=500)

    # Update usage metrics
    scheduler.update_metrics(runtime_hours=2.5, distance_km=1.2)

    # Check for due maintenance
    due_tasks = scheduler.get_due_tasks()

    # Mark task as completed
    scheduler.complete_task("blade_replacement")
"""

import json
import os
import time
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union, Any

from mower.utilities.logger_config import LoggerConfigInfo as LoggerConfig

# Configure logging
logger = LoggerConfig.get_logger(__name__)


class MaintenanceInterval:
    """Maintenance interval based on time, usage, or both."""

    def __init__(
        self,
        hours: Optional[float] = None,
        days: Optional[int] = None,
        distance_km: Optional[float] = None,
        mowing_cycles: Optional[int] = None,
    ):
        """
        Initialize maintenance interval.

        Args:
            hours: Interval in operating hours.
            days: Interval in calendar days.
            distance_km: Interval in kilometers traveled.
            mowing_cycles: Interval in mowing cycles.
        """
        self.hours = hours
        self.days = days
        self.distance_km = distance_km
        self.mowing_cycles = mowing_cycles

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "hours": self.hours,
            "days": self.days,
            "distance_km": self.distance_km,
            "mowing_cycles": self.mowing_cycles,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MaintenanceInterval":
        """Create from dictionary after deserialization."""
        return cls(
            hours=data.get("hours"),
            days=data.get("days"),
            distance_km=data.get("distance_km"),
            mowing_cycles=data.get("mowing_cycles"),
        )


class MaintenanceTask:
    """Maintenance task with description, interval, and history."""

    def __init__(
        self,
        task_id: str,
        description: str,
        interval: MaintenanceInterval,
        priority: int = 1,
        requires_parts: bool = False,
        estimated_duration_minutes: int = 30,
        instructions: Optional[str] = None,
    ):
        """
        Initialize maintenance task.

        Args:
            task_id: Unique identifier for the task.
            description: Description of the task.
            interval: Maintenance interval.
            priority: Priority level (1-5, where 1 is highest).
            requires_parts: Whether the task requires replacement parts.
            estimated_duration_minutes: Estimated time to complete the task.
            instructions: Detailed instructions for performing the task.
        """
        self.task_id = task_id
        self.description = description
        self.interval = interval
        self.priority = priority
        self.requires_parts = requires_parts
        self.estimated_duration_minutes = estimated_duration_minutes
        self.instructions = instructions

        # Maintenance history
        self.last_completed: Optional[datetime] = None
        self.last_completed_metrics: Dict[str, float] = {
            "hours": 0.0,
            "distance_km": 0.0,
            "mowing_cycles": 0,
        }
        self.completion_history: List[Dict[str, Any]] = []

    def is_due(
            self, current_metrics: Dict[str, float],
            current_time: datetime) -> bool:
        """
        Check if the task is due for maintenance.

        Args:
            current_metrics: Current usage metrics.
            current_time: Current time.

        Returns:
            bool: True if the task is due, False otherwise.
        """
        # If never completed, it's due
        if self.last_completed is None:
            return True

        # Check time-based intervals
        if self.interval.hours is not None:
            hours_since_last = (
                current_metrics["hours"] - self.last_completed_metrics["hours"]
            )
            if hours_since_last >= self.interval.hours:
                return True

        if self.interval.days is not None:
            days_since_last = (current_time - self.last_completed).total_seconds() / (
                24 * 3600
            )
            if days_since_last >= self.interval.days:
                return True

        # Check usage-based intervals
        if self.interval.distance_km is not None:
            distance_since_last = (
                current_metrics["distance_km"]
                - self.last_completed_metrics["distance_km"]
            )
            if distance_since_last >= self.interval.distance_km:
                return True

        if self.interval.mowing_cycles is not None:
            cycles_since_last = (
                current_metrics["mowing_cycles"]
                - self.last_completed_metrics["mowing_cycles"]
            )
            if cycles_since_last >= self.interval.mowing_cycles:
                return True

        return False

    def complete(
        self,
        current_metrics: Dict[str, float],
        current_time: datetime,
        notes: Optional[str] = None,
    ) -> None:
        """
        Mark the task as completed.

        Args:
            current_metrics: Current usage metrics.
            current_time: Current time.
            notes: Optional notes about the maintenance.
        """
        # Record completion
        completion = {
            "timestamp": current_time.isoformat(),
            "metrics": current_metrics.copy(),
            "notes": notes,
        }

        self.completion_history.append(completion)
        self.last_completed = current_time
        self.last_completed_metrics = current_metrics.copy()

        logger.info(f"Maintenance task '{self.task_id}' completed")

    def get_next_due(
        self, current_metrics: Dict[str, float], current_time: datetime
    ) -> Dict[str, Any]:
        """
        Get information about when the task will next be due.

        Args:
            current_metrics: Current usage metrics.
            current_time: Current time.

        Returns:
            Dict[str, Any]: Information about when the task will next be due.
        """
        if self.last_completed is None:
            return {
                "due_now": True,
                "reason": "Never completed",
            }

        result = {
            "due_now": False,
            "remaining": {},
        }

        # Check time-based intervals
        if self.interval.hours is not None:
            hours_since_last = (
                current_metrics["hours"] - self.last_completed_metrics["hours"]
            )
            hours_remaining = max(0, self.interval.hours - hours_since_last)
            result["remaining"]["hours"] = hours_remaining
            if hours_remaining <= 0:
                result["due_now"] = True
                result[
                    "reason"
 (
     f"Operating hours exceeded ({hours_since_last:.1f} > {self.interval"
     f".hours:.1f})"
 )

        if self.interval.days is not None:
            days_since_last = (current_time - self.last_completed).total_seconds() / (
                24 * 3600
            )
            days_remaining = max(0, self.interval.days - days_since_last)
            result["remaining"]["days"] = days_remaining
            if days_remaining <= 0 and not result["due_now"]:
                result["due_now"] = True
                result[
                    "reason"
                ] = f"Days exceeded ({days_since_last:.1f} > {self.interval.days})"

        # Check usage-based intervals
        if self.interval.distance_km is not None:
            distance_since_last = (
                current_metrics["distance_km"]
                - self.last_completed_metrics["distance_km"]
            )
            distance_remaining = max(0, self.interval.distance_km - distance_since_last)
            result["remaining"]["distance_km"] = distance_remaining
            if distance_remaining <= 0 and not result["due_now"]:
                result["due_now"] = True
                result[
                    "reason"
 (
     f"Distance exceeded ({distance_since_last:.1f} > {self.interval"
     f".distance_km:.1f})"
 )

        if self.interval.mowing_cycles is not None:
            cycles_since_last = (
                current_metrics["mowing_cycles"]
                - self.last_completed_metrics["mowing_cycles"]
            )
            cycles_remaining = max(0, self.interval.mowing_cycles - cycles_since_last)
            result["remaining"]["mowing_cycles"] = cycles_remaining
            if cycles_remaining <= 0 and not result["due_now"]:
                result["due_now"] = True
                result[
                    "reason"
 (
     f"Mowing cycles exceeded ({cycles_since_last} > {self.interval"
     f".mowing_cycles})"
 )

        return result

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "task_id": self.task_id,
            "description": self.description,
            "interval": self.interval.to_dict(),
            "priority": self.priority,
            "requires_parts": self.requires_parts,
            "estimated_duration_minutes": self.estimated_duration_minutes,
            "instructions": self.instructions,
            "last_completed": (
                self.last_completed.isoformat() if self.last_completed else None
            ),
            "last_completed_metrics": self.last_completed_metrics,
            "completion_history": self.completion_history,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MaintenanceTask":
        """Create from dictionary after deserialization."""
        task = cls(
            task_id=data["task_id"],
            description=data["description"],
            interval=MaintenanceInterval.from_dict(data["interval"]),
            priority=data.get("priority", 1),
            requires_parts=data.get("requires_parts", False),
            estimated_duration_minutes=data.get("estimated_duration_minutes", 30),
            instructions=data.get("instructions"),
        )

        # Restore history
        if data.get("last_completed"):
            task.last_completed = datetime.fromisoformat(data["last_completed"])
        task.last_completed_metrics = data.get(
            "last_completed_metrics",
            {
                "hours": 0.0,
                "distance_km": 0.0,
                "mowing_cycles": 0,
            },
        )
        task.completion_history = data.get("completion_history", [])

        return task


class MaintenanceScheduler:
    """
    Maintenance scheduler for the autonomous mower.

    This class provides methods to track maintenance tasks, schedule them
    based on usage or time intervals, and provide reminders when maintenance
    is due.
    """

    def __init__(self, data_file: Optional[str] = None):
        """
        Initialize the maintenance scheduler.

        Args:
            data_file: Path to the data file for storing maintenance data.
                If None, a default path will be used.
        """
        self.data_file = data_file or os.path.expanduser("~/.mower/maintenance.json")
        self.tasks: Dict[str, MaintenanceTask] = {}
        self.current_metrics = {
            "hours": 0.0,
            "distance_km": 0.0,
            "mowing_cycles": 0,
        }
        self.last_save_time = 0

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)

        # Load existing data if available
        self.load()

        # Add default tasks if none exist
        if not self.tasks:
            self._add_default_tasks()

    def _add_default_tasks(self) -> None:
        """Add default maintenance tasks."""
        # Blade replacement (every 50 hours or 250 km)
        self.add_task(
            task_id="blade_replacement",
            description="Replace cutting blade",
            interval=MaintenanceInterval(hours=50, distance_km=250),
            priority=1,
            requires_parts=True,
            estimated_duration_minutes=15,
            instructions="1. Turn off the mower and disconnect the battery\n"
            "2. Flip the mower over carefully\n"
            "3. Remove the old blade using a wrench\n"
            "4. Install the new blade and tighten securely\n"
            "5. Reconnect the battery and test",
        )

        # Blade sharpening (every 25 hours or 125 km)
        self.add_task(
            task_id="blade_sharpening",
            description="Sharpen cutting blade",
            interval=MaintenanceInterval(hours=25, distance_km=125),
            priority=2,
            requires_parts=False,
            estimated_duration_minutes=20,
            instructions="1. Turn off the mower and disconnect the battery\n"
            "2. Remove the blade\n"
            "3. Sharpen the blade using a file or grinder\n"
            "4. Balance the blade\n"
            "5. Reinstall the blade and tighten securely",
        )

        # Battery check (every 100 hours or 30 days)
        self.add_task(
            task_id="battery_check",
            description="Check battery health and connections",
            interval=MaintenanceInterval(hours=100, days=30),
            priority=2,
            requires_parts=False,
            estimated_duration_minutes=10,
            instructions="1. Turn off the mower\n"
            "2. Check battery terminals for corrosion\n"
            "3. Clean terminals if necessary\n"
            "4. Check battery voltage under load\n"
            "5. Ensure all connections are secure",
        )

        # General cleaning (every 20 hours or 14 days)
        self.add_task(
            task_id="general_cleaning",
            description="Clean mower deck, wheels, and sensors",
            interval=MaintenanceInterval(hours=20, days=14),
            priority=3,
            requires_parts=False,
            estimated_duration_minutes=30,
            instructions="1. Turn off the mower and disconnect the battery\n"
            "2. Remove debris from the mower deck\n"
            "3. Clean the wheels and remove any tangled grass\n"
            "4. Clean all sensors with a soft cloth\n"
            "5. Check for any loose parts or damage",
        )

        # Wheel check (every 100 hours or 500 km)
        self.add_task(
            task_id="wheel_check",
            description="Check wheel condition and alignment",
            interval=MaintenanceInterval(hours=100, distance_km=500),
            priority=3,
            requires_parts=False,
            estimated_duration_minutes=15,
            instructions="1. Turn off the mower\n"
            "2. Check wheels for wear and damage\n"
            "3. Check wheel alignment\n"
            "4. Tighten wheel bolts if necessary\n"
            "5. Lubricate wheel bearings if needed",
        )

        # Software update (every 30 days)
        self.add_task(
            task_id="software_update",
            description="Check for and install software updates",
            interval=MaintenanceInterval(days=30),
            priority=2,
            requires_parts=False,
            estimated_duration_minutes=20,
            instructions="1. Connect the mower to Wi-Fi\n"
            "2. Check for available updates\n"
            "3. Install updates if available\n"
            "4. Restart the mower\n"
            "5. Verify that all systems are functioning correctly",
        )

        # Full inspection (every 200 hours or 90 days)
        self.add_task(
            task_id="full_inspection",
            description="Complete inspection of all mower systems",
            interval=MaintenanceInterval(hours=200, days=90),
            priority=1,
            requires_parts=False,
            estimated_duration_minutes=60,
            instructions="1. Turn off the mower and disconnect the battery\n"
            "2. Check all mechanical components for wear\n"
            "3. Inspect all electrical connections\n"
            "4. Test all sensors and motors\n"
            "5. Update firmware if needed\n"
            "6. Clean all components thoroughly",
        )

    def add_task(
        self,
        task_id: str,
        description: str,
        interval: MaintenanceInterval,
        priority: int = 1,
        requires_parts: bool = False,
        estimated_duration_minutes: int = 30,
        instructions: Optional[str] = None,
    ) -> None:
        """
        Add a maintenance task.

        Args:
            task_id: Unique identifier for the task.
            description: Description of the task.
            interval: Maintenance interval.
            priority: Priority level (1-5, where 1 is highest).
            requires_parts: Whether the task requires replacement parts.
            estimated_duration_minutes: Estimated time to complete the task.
            instructions: Detailed instructions for performing the task.
        """
        self.tasks[task_id] = MaintenanceTask(
            task_id=task_id,
            description=description,
            interval=interval,
            priority=priority,
            requires_parts=requires_parts,
            estimated_duration_minutes=estimated_duration_minutes,
            instructions=instructions,
        )
        logger.info(f"Added maintenance task '{task_id}'")
        self.save()

    def remove_task(self, task_id: str) -> bool:
        """
        Remove a maintenance task.

        Args:
            task_id: Unique identifier for the task.

        Returns:
            bool: True if the task was removed, False if it didn't exist.
        """
        if task_id in self.tasks:
            del self.tasks[task_id]
            logger.info(f"Removed maintenance task '{task_id}'")
            self.save()
            return True
        return False

    def update_metrics(
        self,
        runtime_hours: Optional[float] = None,
        distance_km: Optional[float] = None,
        mowing_cycles: Optional[int] = None,
    ) -> None:
        """
        Update usage metrics.

        Args:
            runtime_hours: Additional runtime hours.
            distance_km: Additional distance in kilometers.
            mowing_cycles: Additional mowing cycles.
        """
        if runtime_hours is not None:
            self.current_metrics["hours"] += runtime_hours

        if distance_km is not None:
            self.current_metrics["distance_km"] += distance_km

        if mowing_cycles is not None:
            self.current_metrics["mowing_cycles"] += mowing_cycles

        # Save metrics periodically (not on every update to reduce I/O)
        current_time = time.time()
        if current_time - self.last_save_time > 300:  # 5 minutes
            self.save()
            self.last_save_time = current_time

    def set_metrics(
        self,
        runtime_hours: Optional[float] = None,
        distance_km: Optional[float] = None,
        mowing_cycles: Optional[int] = None,
    ) -> None:
        """
        Set absolute usage metrics.

        Args:
            runtime_hours: Total runtime hours.
            distance_km: Total distance in kilometers.
            mowing_cycles: Total mowing cycles.
        """
        if runtime_hours is not None:
            self.current_metrics["hours"] = runtime_hours

        if distance_km is not None:
            self.current_metrics["distance_km"] = distance_km

        if mowing_cycles is not None:
            self.current_metrics["mowing_cycles"] = mowing_cycles

        self.save()

    def get_due_tasks(self) -> List[Dict[str, Any]]:
        """
        Get tasks that are due for maintenance.

        Returns:
            List[Dict[str, Any]]: List of due tasks with details.
        """
        current_time = datetime.now()
        due_tasks = []

        for task_id, task in self.tasks.items():
            if task.is_due(self.current_metrics, current_time):
                next_due = task.get_next_due(self.current_metrics, current_time)
                due_tasks.append(
                    {
                        "task_id": task_id,
                        "description": task.description,
                        "priority": task.priority,
                        "requires_parts": task.requires_parts,
                        "estimated_duration_minutes": task.estimated_duration_minutes,
                        "instructions": task.instructions,
                        "reason": next_due.get("reason", "Maintenance due"),
                    }
                )

        # Sort by priority (lowest number first)
        due_tasks.sort(key=lambda x: x["priority"])

        return due_tasks

    def get_upcoming_tasks(self, days_ahead: int = 30) -> List[Dict[str, Any]]:
        """
        Get tasks that will be due in the near future.

        Args:
            days_ahead: Number of days to look ahead.

        Returns:
            List[Dict[str, Any]]: List of upcoming tasks with details.
        """
        current_time = datetime.now()
        future_time = current_time + timedelta(days=days_ahead)

        # Estimate future metrics based on average daily usage
        days_of_history = 30  # Use up to 30 days of history for estimation

        # Calculate daily averages
        daily_hours = 0.0
        daily_distance = 0.0
        daily_cycles = 0.0

        # Use simple estimation for now
        # In a real implementation, you would use actual usage history
        daily_hours = 2.0  # Assume 2 hours per day
        daily_distance = 1.0  # Assume 1 km per day
        daily_cycles = 0.2  # Assume 1 cycle every 5 days

        # Estimate future metrics
        future_metrics = {
            "hours": self.current_metrics["hours"] + (daily_hours * days_ahead),
            "distance_km": self.current_metrics["distance_km"]
            + (daily_distance * days_ahead),
            "mowing_cycles": self.current_metrics["mowing_cycles"]
            + int(daily_cycles * days_ahead),
        }

        upcoming_tasks = []

        for task_id, task in self.tasks.items():
            # Skip tasks that are already due
            if task.is_due(self.current_metrics, current_time):
                continue

            # Check if the task will be due in the future
            if task.is_due(future_metrics, future_time):
                next_due = task.get_next_due(self.current_metrics, current_time)

                # Estimate days until due
                days_until_due = None

                if "days" in next_due.get("remaining", {}):
                    days_until_due = next_due["remaining"]["days"]
                elif "hours" in next_due.get("remaining", {}):
                    days_until_due = (
                        next_due["remaining"]["hours"] / daily_hours
                        if daily_hours > 0
                        else None
                    )
                elif "distance_km" in next_due.get("remaining", {}):
                    days_until_due = (
                        next_due["remaining"]["distance_km"] / daily_distance
                        if daily_distance > 0
                        else None
                    )
                elif "mowing_cycles" in next_due.get("remaining", {}):
                    days_until_due = (
                        next_due["remaining"]["mowing_cycles"] / daily_cycles
                        if daily_cycles > 0
                        else None
                    )

                upcoming_tasks.append(
                    {
                        "task_id": task_id,
                        "description": task.description,
                        "priority": task.priority,
                        "requires_parts": task.requires_parts,
                        "estimated_duration_minutes": task.estimated_duration_minutes,
                        "days_until_due": days_until_due,
                        "remaining": next_due.get("remaining", {}),
                    }
                )

        # Sort by days until due
        upcoming_tasks.sort(
            key=lambda x: x.get("days_until_due", float("inf")) or float("inf")
        )

        return upcoming_tasks

    def complete_task(self, task_id: str, notes: Optional[str] = None) -> bool:
        """
        Mark a task as completed.

        Args:
            task_id: Unique identifier for the task.
            notes: Optional notes about the maintenance.

        Returns:
            bool: True if the task was completed, False if it doesn't exist.
        """
        if task_id in self.tasks:
            self.tasks[task_id].complete(self.current_metrics, datetime.now(), notes)
            self.save()
            return True
        return False

    def get_task_history(self, task_id: str) -> List[Dict[str, Any]]:
        """
        Get the maintenance history for a task.

        Args:
            task_id: Unique identifier for the task.

        Returns:
            List[Dict[str, Any]]: List of maintenance records.

        Raises:
            KeyError: If the task doesn't exist.
        """
        if task_id not in self.tasks:
            raise KeyError(f"Task '{task_id}' not found")

        return self.tasks[task_id].completion_history

    def get_all_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all tasks.

        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of task information.
        """
        current_time = datetime.now()
        result = {}

        for task_id, task in self.tasks.items():
            next_due = task.get_next_due(self.current_metrics, current_time)
            result[task_id] = {
                "description": task.description,
                "priority": task.priority,
                "requires_parts": task.requires_parts,
                "estimated_duration_minutes": task.estimated_duration_minutes,
                "instructions": task.instructions,
                "last_completed": (
                    task.last_completed.isoformat() if task.last_completed else None
                ),
                "is_due": next_due.get("due_now", False),
                "next_due": next_due,
            }

        return result

    def save(self) -> None:
        """Save maintenance data to file."""
        data = {
            "metrics": self.current_metrics,
            "tasks": {task_id: task.to_dict() for task_id, task in self.tasks.items()},
        }

        try:
            with open(self.data_file, "w") as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved maintenance data to {self.data_file}")
        except Exception as e:
            logger.error(f"Error saving maintenance data: {e}")

    def load(self) -> bool:
        """
        Load maintenance data from file.

        Returns:
            bool: True if data was loaded successfully, False otherwise.
        """
        if not os.path.exists(self.data_file):
            logger.info(f"Maintenance data file {self.data_file} not found")
            return False

        try:
            with open(self.data_file, "r") as f:
                data = json.load(f)

            # Load metrics
            self.current_metrics = data.get(
                "metrics",
                {
                    "hours": 0.0,
                    "distance_km": 0.0,
                    "mowing_cycles": 0,
                },
            )

            # Load tasks
            self.tasks = {}
            for task_id, task_data in data.get("tasks", {}).items():
                self.tasks[task_id] = MaintenanceTask.from_dict(task_data)

            logger.info(f"Loaded maintenance data from {self.data_file}")
            return True
        except Exception as e:
            logger.error(f"Error loading maintenance data: {e}")
            return False

    def export_schedule(self, format_type: str = "text") -> str:
        """
        Export the maintenance schedule.

        Args:
            format_type: Format type ("text", "html", or "json").

        Returns:
            str: Formatted maintenance schedule.
        """
        current_time = datetime.now()
        due_tasks = self.get_due_tasks()
        upcoming_tasks = self.get_upcoming_tasks()

        if format_type == "json":
            return json.dumps(
                {
                    "current_metrics": self.current_metrics,
                    "due_tasks": due_tasks,
                    "upcoming_tasks": upcoming_tasks,
                    "all_tasks": self.get_all_tasks(),
                },
                indent=2,
            )

        elif format_type == "html":
            html = "<html><head><title>Maintenance Schedule</title></head><body>"
            html += f"<h1>Maintenance Schedule</h1>"
            html += f"<p>Generated on {current_time.strftime('%Y-%m-%d %H:%M')}</p>"

            html += "<h2>Current Metrics</h2>"
            html += "<ul>"
            html += f"<li>Runtime: {self.current_metrics['hours']:.1f} hours</li>"
            html += f"<li>Distance: {self.current_metrics['distance_km']:.1f} km</li>"
            html += f"<li>Mowing Cycles: {self.current_metrics['mowing_cycles']}</li>"
            html += "</ul>"

            if due_tasks:
                html += "<h2>Due Tasks</h2>"
                html += "<table border='1'>"
                html += (
                    "<tr><th>Priority</th><th>Task</th><th>Reason</th>"
                    "<th>Est. Time</th><th>Parts Required</th></tr>"
                )
                for task in due_tasks:
                    html += f"<tr>"
                    html += f"<td>{task['priority']}</td>"
                    html += f"<td>{task['description']}</td>"
                    html += f"<td>{task['reason']}</td>"
                    html += f"<td>{task['estimated_duration_minutes']} min</td>"
                    html += f"<td>{'Yes' if task['requires_parts'] else 'No'}</td>"
                    html += f"</tr>"
                html += "</table>"
            else:
                html += "<h2>Due Tasks</h2>"
                html += "<p>No tasks currently due.</p>"

            if upcoming_tasks:
                html += "<h2>Upcoming Tasks</h2>"
                html += "<table border='1'>"
                html += "<tr><th>Priority</th><th>Task</th><th>Days Until Due</th><th>Est. Time</th><th>Parts Required</th></tr>"
                for task in upcoming_tasks:
                    days = task.get("days_until_due")
                    days_str = f"{days:.1f}" if days is not None else "Unknown"
                    html += f"<tr>"
                    html += f"<td>{task['priority']}</td>"
                    html += f"<td>{task['description']}</td>"
                    html += f"<td>{days_str}</td>"
                    html += f"<td>{task['estimated_duration_minutes']} min</td>"
                    html += f"<td>{'Yes' if task['requires_parts'] else 'No'}</td>"
                    html += f"</tr>"
                html += "</table>"
            else:
                html += "<h2>Upcoming Tasks</h2>"
                html += "<p>No upcoming tasks within the next 30 days.</p>"

            html += "</body></html>"
            return html

        else:  # text format
            text = "MAINTENANCE SCHEDULE\n"
            text += "=" * 80 + "\n"
            text += f"Generated on {current_time.strftime('%Y-%m-%d %H:%M')}\n\n"

            text += "CURRENT METRICS\n"
            text += "-" * 80 + "\n"
            text += f"Runtime: {self.current_metrics['hours']:.1f} hours\n"
            text += f"Distance: {self.current_metrics['distance_km']:.1f} km\n"
            text += f"Mowing Cycles: {self.current_metrics['mowing_cycles']}\n\n"

            text += "DUE TASKS\n"
            text += "-" * 80 + "\n"
            if due_tasks:
                for task in due_tasks:
                    text += f"Priority {task['priority']}: {task['description']}\n"
                    text += f"  Reason: {task['reason']}\n"
 (f"  Estimated Time: {task['estimated_duration_minutes']} minutes\n
  f"
 (f"  Parts Required: {'Yes' if task['requires_parts'] else 'No'}\n
  f"
                    if task.get("instructions"):
                        text += (
                            f"  Instructions:\n    "
                            + task["instructions"].replace("\n", "\n    ")
                            + "\n"
                        )
                    text += "\n"
            else:
                text += "No tasks currently due.\n\n"

            text += "UPCOMING TASKS\n"
            text += "-" * 80 + "\n"
            if upcoming_tasks:
                for task in upcoming_tasks:
                    days = task.get("days_until_due")
                    days_str = f"{days:.1f}" if days is not None else "Unknown"
                    text += f"Priority {task['priority']}: {task['description']}\n"
                    text += f"  Days Until Due: {days_str}\n"
 (f"  Estimated Time: {task['estimated_duration_minutes']} minutes\n
  f"
 (f"  Parts Required: {'Yes' if task['requires_parts'] else 'No'}\n\n
  f"
            else:
                text += "No upcoming tasks within the next 30 days.\n\n"

            return text
