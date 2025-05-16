"""
Event handling utilities for the autonomous mower.

This module provides utilities for handling events in the autonomous mower
project, including decorators for subscribing to events and convenience
functions for publishing events.
"""

import functools
import inspect
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    cast,
)

from mower.events.event import Event, EventType, EventPriority
from mower.events.event_bus import get_event_bus

# Type variable for event handler functions
F = TypeVar("F", bound=Callable[..., Any])


class EventHandler:
    """
    Base class for event handlers.

    Event handlers are objects that can subscribe to and handle events.
    This class provides a common interface for event handlers and utilities
    for subscribing to events.
    """

    def __init__(self):
        """Initialize the event handler."""
        self._subscriptions: List[Tuple[EventType, Callable]] = []

    def subscribe(self, event_type: EventType):
        """
        Subscribe to events of the specified type.

        Args:
            event_type: Type of events to subscribe to
        """
        event_bus = get_event_bus()

        # Find methods in this class that are decorated with @handle_event
        for name, method in inspect.getmembers(self, inspect.ismethod):
            if (
                hasattr(method, "_event_types")
                and event_type in method._event_types
            ):
                event_bus.subscribe(method, event_type)
                self._subscriptions.append((event_type, method))

    def subscribe_all(self):
        """Subscribe to all events that this handler can handle."""
        # Find methods in this class that are decorated with @handle_event
        for name, method in inspect.getmembers(self, inspect.ismethod):
            if hasattr(method, "_event_types"):
                for event_type in method._event_types:
                    self.subscribe(event_type)

    def unsubscribe_all(self):
        """Unsubscribe from all events."""
        event_bus = get_event_bus()

        for event_type, method in self._subscriptions:
            event_bus.unsubscribe(method, event_type)

        self._subscriptions = []

    def publish(
        self,
        event_type: EventType,
        data: Optional[Dict[str, Any]] = None,
        priority: EventPriority = EventPriority.NORMAL,
        synchronous: bool = False,
    ):
        """
        Publish an event.

        Args:
            event_type: Type of the event
            data: Data to include in the event
            priority: Priority of the event
            synchronous: If True, process the event synchronously
        """
        event = Event(
            event_type=event_type,
            data=data,
            priority=priority,
            source=self.__class__.__name__,
        )

        event_bus = get_event_bus()
        event_bus.publish(event, synchronous=synchronous)


def handle_event(*event_types: EventType):
    """
    Decorator for methods that handle events.

    Args:
        *event_types: Types of events that this method can handle

    Returns:
        Callable: Decorated method
    """

    def decorator(func: F) -> F:
        # Store the event types in the function object
        func._event_types = event_types  # type: ignore

        @functools.wraps(func)
        def wrapper(self, event: Event, *args, **kwargs):
            return func(self, event, *args, **kwargs)

        return cast(F, wrapper)

    return decorator


def subscribe(event_type: EventType):
    """
    Decorator for functions that subscribe to events.

    Args:
        event_type: Type of events to subscribe to

    Returns:
        Callable: Decorated function
    """

    def decorator(func: F) -> F:
        # Subscribe the function to the event type
        event_bus = get_event_bus()
        event_bus.subscribe(func, event_type)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return cast(F, wrapper)

    return decorator


def publish(
    event_type: EventType,
    data: Optional[Dict[str, Any]] = None,
    priority: EventPriority = EventPriority.NORMAL,
    source: Optional[str] = None,
    synchronous: bool = False,
):
    """
    Publish an event.

    Args:
        event_type: Type of the event
        data: Data to include in the event
        priority: Priority of the event
        source: Source of the event
        synchronous: If True, process the event synchronously
    """
    event = Event(
        event_type=event_type, data=data, priority=priority, source=source
    )

    event_bus = get_event_bus()
    event_bus.publish(event, synchronous=synchronous)
