"""
Event system for the autonomous mower.

This package provides a unified event system for inter-component communication
in the autonomous mower project. It includes event classes, an event bus for
publishing and subscribing to events, and utilities for event handling.

Usage:
    from mower.events import Event, EventBus, subscribe, publish

    # Create an event
    event = Event("sensor_data", {"temperature": 25.0})

    # Publish an event
    publish(event)

    # Subscribe to events
    @subscribe("sensor_data")
    def handle_sensor_data(event):
        print(f"Received sensor data: {event.data}")
"""

from mower.events.event import Event, EventPriority, EventType
from mower.events.event_bus import EventBus, get_event_bus
from mower.events.handlers import EventHandler, publish, subscribe

__all__ = [
    "Event",
    "EventType",
    "EventPriority",
    "EventBus",
    "get_event_bus",
    "EventHandler",
    "subscribe",
    "publish",
]
