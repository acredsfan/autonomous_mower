"""
Event classes for the autonomous mower.

This module defines the base Event class and related classes for the
event system. Events are used for inter-component communication in the
autonomous mower project.
"""

import time
import uuid
from enum import Enum, auto
from typing import Any, Dict, Optional


class EventType(Enum):
    """Types of events in the system."""

    # Hardware events
    HARDWARE_SENSOR_DATA = auto()
    HARDWARE_MOTOR_STATUS = auto()
    HARDWARE_BLADE_STATUS = auto()
    HARDWARE_BATTERY_STATUS = auto()
    HARDWARE_GPS_DATA = auto()
    HARDWARE_IMU_DATA = auto()
    HARDWARE_CAMERA_DATA = auto()

    # Navigation events
    NAVIGATION_POSITION_UPDATED = auto()
    NAVIGATION_PATH_UPDATED = auto()
    NAVIGATION_WAYPOINT_REACHED = auto()
    NAVIGATION_DESTINATION_REACHED = auto()

    # Obstacle detection events
    OBSTACLE_DETECTED = auto()
    OBSTACLE_CLEARED = auto()
    DROP_DETECTED = auto()

    # State events
    STATE_CHANGED = auto()
    ERROR_OCCURRED = auto()
    WARNING_OCCURRED = auto()

    # User interface events
    UI_COMMAND_RECEIVED = auto()
    UI_STATUS_UPDATED = auto()

    # System events
    SYSTEM_STARTUP = auto()
    SYSTEM_SHUTDOWN = auto()
    SYSTEM_HEARTBEAT = auto()

    # Custom event type for extensibility
    CUSTOM = auto()


class EventPriority(Enum):
    """Priority levels for events."""

    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class Event:
    """
    Base class for all events in the system.

    Events are used for inter-component communication in the autonomous mower.
    They contain a type, data, and metadata such as timestamp and source.

    Attributes:
        event_type: The type of the event
        data: The data associated with the event
        priority: The priority of the event
        timestamp: When the event was created
        source: The component that created the event
        event_id: Unique identifier for the event
    """

    def __init__(
        self,
        event_type: EventType,
        data: Optional[Dict[str, Any]] = None,
        priority: EventPriority = EventPriority.NORMAL,
        source: Optional[str] = None,
    ):
        """
        Initialize an event.

        Args:
            event_type: The type of the event
            data: The data associated with the event
            priority: The priority of the event
            source: The component that created the event
        """
        self.event_type = event_type
        self.data = data or {}
        self.priority = priority
        self.timestamp = time.time()
        self.source = source
        self.event_id = str(uuid.uuid4())

    def __str__(self) -> str:
        """Get a string representation of the event."""
        return (
            f"Event(type={self.event_type.name}, "
            f"priority={self.priority.name}, "
            f"source={self.source}, "
            f"data={self.data})"
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the event to a dictionary.

        Returns:
            Dict[str, Any]: Dictionary representation of the event
        """
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.name,
            "data": self.data,
            "priority": self.priority.name,
            "timestamp": self.timestamp,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, event_dict: Dict[str, Any]) -> "Event":
        """
        Create an event from a dictionary.

        Args:
            event_dict: Dictionary representation of the event

        Returns:
            Event: The created event
        """
        event = cls(
            event_type=EventType[event_dict["event_type"]],
            data=event_dict["data"],
            priority=EventPriority[event_dict["priority"]],
            source=event_dict["source"],
        )
        event.event_id = event_dict["event_id"]
        event.timestamp = event_dict["timestamp"]
        return event


# Convenience function to create events
def create_event(
    event_type: EventType,
    data: Optional[Dict[str, Any]] = None,
    priority: EventPriority = EventPriority.NORMAL,
    source: Optional[str] = None,
) -> Event:
    """
    Create an event.

    Args:
        event_type: The type of the event
        data: The data associated with the event
        priority: The priority of the event
        source: The component that created the event

    Returns:
        Event: The created event
    """
    return Event(event_type, data, priority, source)
