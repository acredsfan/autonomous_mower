"""
Event bus for the autonomous mower.

This module provides an event bus implementation for the autonomous mower
project. The event bus allows components to publish events and subscribe
to events without direct dependencies on each other.
"""

import logging
import queue
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from mower.events.event import Event, EventPriority, EventType
from mower.utilities.logger_config import LoggerConfigInfo

# Initialize logger
logger = LoggerConfigInfo.get_logger(__name__)


class EventBus:
    """
    Event bus for inter-component communication.

    The event bus allows components to publish events and subscribe to events
    without direct dependencies on each other. It supports filtering events
    by type and priority, and can process events synchronously or asynchronously.

    Attributes:
        subscribers: Dictionary mapping event types to subscriber callbacks
        event_queue: Queue of events for asynchronous processing
        processing_thread: Thread for asynchronous event processing
        running: Flag indicating if the event bus is running
    """

    def __init__(self):
        """Initialize the event bus."""
        self._subscribers: Dict[EventType, List[Callable[[Event], None]]] = {}
        self._wildcard_subscribers: List[Callable[[Event], None]] = []
        self._event_queue: queue.Queue = queue.Queue()
        self._processing_thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.RLock()
        self._event_history: List[Event] = []
        self._max_history_size = 100

    def start(self):
        """Start the event bus."""
        with self._lock:
            if self._running:
                logger.warning("Event bus is already running")
                return

            self._running = True
            self._processing_thread = threading.Thread(target=self._process_events, daemon=True)
            self._processing_thread.start()
            logger.info("Event bus started")

    def stop(self):
        """Stop the event bus."""
        with self._lock:
            if not self._running:
                logger.warning("Event bus is not running")
                return

            self._running = False

            # Wait for the processing thread to complete
            if self._processing_thread and self._processing_thread.is_alive():
                self._processing_thread.join(timeout=5.0)
                if self._processing_thread.is_alive():
                    logger.warning("Event processing thread did not terminate")

            self._processing_thread = None
            logger.info("Event bus stopped")

    def subscribe(
        self,
        callback: Callable[[Event], None],
        event_type: Optional[EventType] = None,
    ):
        """
        Subscribe to events.

        Args:
            callback: Function to call when an event is received
            event_type: Type of events to subscribe to, or None for all events
        """
        with self._lock:
            if event_type is None:
                # Subscribe to all events
                self._wildcard_subscribers.append(callback)
                logger.debug(f"Added wildcard subscriber: {callback.__name__}")
            else:
                # Subscribe to specific event type
                if event_type not in self._subscribers:
                    self._subscribers[event_type] = []

                self._subscribers[event_type].append(callback)
                logger.debug(f"Added subscriber for {event_type.name}: {callback.__name__}")

    def unsubscribe(
        self,
        callback: Callable[[Event], None],
        event_type: Optional[EventType] = None,
    ):
        """
        Unsubscribe from events.

        Args:
            callback: Function to unsubscribe
            event_type: Type of events to unsubscribe from, or None for all events
        """
        with self._lock:
            if event_type is None:
                # Unsubscribe from all events
                if callback in self._wildcard_subscribers:
                    self._wildcard_subscribers.remove(callback)
                    logger.debug(f"Removed wildcard subscriber: {callback.__name__}")

                # Also remove from specific event types
                for event_type in self._subscribers:
                    if callback in self._subscribers[event_type]:
                        self._subscribers[event_type].remove(callback)
                        logger.debug(f"Removed subscriber for {event_type.name}: " f"{callback.__name__}")
            else:
                # Unsubscribe from specific event type
                if event_type in self._subscribers and callback in self._subscribers[event_type]:
                    self._subscribers[event_type].remove(callback)
                    logger.debug(f"Removed subscriber for {event_type.name}: " f"{callback.__name__}")

    def publish(self, event: Event, synchronous: bool = False):
        """
        Publish an event.

        Args:
            event: Event to publish
            synchronous: If True, process the event synchronously
        """
        # Add to event history
        with self._lock:
            self._event_history.append(event)
            if len(self._event_history) > self._max_history_size:
                self._event_history = self._event_history[-self._max_history_size :]

        if synchronous:
            # Process the event synchronously
            self._dispatch_event(event)
        else:
            # Add to queue for asynchronous processing
            self._event_queue.put(event)

    def _process_events(self):
        """Process events from the queue."""
        while self._running:
            try:
                # Get an event from the queue with timeout
                try:
                    event = self._event_queue.get(timeout=0.1)
                except queue.Empty:
                    continue

                # Dispatch the event
                self._dispatch_event(event)

                # Mark the task as done
                self._event_queue.task_done()

            except Exception as e:
                logger.error(f"Error processing event: {e}")

    def _dispatch_event(self, event: Event):
        """
        Dispatch an event to subscribers.

        Args:
            event: Event to dispatch
        """
        try:
            # Get subscribers for this event type
            event_subscribers = []
            with self._lock:
                # Add specific subscribers
                if event.event_type in self._subscribers:
                    event_subscribers.extend(self._subscribers[event.event_type])

                # Add wildcard subscribers
                event_subscribers.extend(self._wildcard_subscribers)

            # Call subscribers
            for subscriber in event_subscribers:
                try:
                    subscriber(event)
                except Exception as e:
                    logger.error(f"Error in subscriber {subscriber.__name__}: {e}")

        except Exception as e:
            logger.error(f"Error dispatching event: {e}")

    def get_event_history(self) -> List[Event]:
        """
        Get the event history.

        Returns:
            List[Event]: List of recent events
        """
        with self._lock:
            return list(self._event_history)

    def clear_event_history(self):
        """Clear the event history."""
        with self._lock:
            self._event_history = []


# Singleton instance of EventBus
_event_bus: Optional[EventBus] = None
_event_bus_lock = threading.RLock()


def get_event_bus() -> EventBus:
    """
    Get the singleton instance of EventBus.

    Returns:
        EventBus: The singleton instance
    """
    global _event_bus

    with _event_bus_lock:
        if _event_bus is None:
            _event_bus = EventBus()
            _event_bus.start()

    return _event_bus


# Initialize the event bus
get_event_bus()
