# Event System

This package provides a unified event system for inter-component communication in the autonomous mower project. It allows components to communicate without direct dependencies, improving modularity and testability.

## Features

- Event-based communication between components
- Asynchronous event processing
- Event priorities
- Event history tracking
- Thread-safe operations
- Flexible subscription model
- Decorator-based event handling

## Architecture

The event system consists of the following components:

### Event

The `Event` class represents an event in the system. Events have:
- A type (from the `EventType` enum)
- Data (a dictionary of key-value pairs)
- Priority (from the `EventPriority` enum)
- Metadata (timestamp, source, event ID)

### EventBus

The `EventBus` class is the central component of the event system. It:
- Manages subscriptions to events
- Dispatches events to subscribers
- Processes events asynchronously
- Tracks event history

### EventHandler

The `EventHandler` class is a base class for components that handle events. It provides:
- Methods for subscribing to events
- Methods for publishing events
- Automatic event handling based on decorated methods

## Usage

### Basic Usage

```python
from mower.events import Event, EventType, EventPriority, get_event_bus

# Get the event bus
event_bus = get_event_bus()

# Define a callback function
def on_sensor_data(event):
    print(f"Received sensor data: {event.data}")

# Subscribe to events
event_bus.subscribe(on_sensor_data, EventType.HARDWARE_SENSOR_DATA)

# Publish an event
event = Event(
    event_type=EventType.HARDWARE_SENSOR_DATA,
    data={"temperature": 25.0, "humidity": 60.0},
    source="example"
)
event_bus.publish(event)

# Unsubscribe when done
event_bus.unsubscribe(on_sensor_data, EventType.HARDWARE_SENSOR_DATA)
```

### Using Decorators

```python
from mower.events import EventType, subscribe, publish

@subscribe(EventType.HARDWARE_BATTERY_STATUS)
def handle_battery_status(event):
    battery_level = event.data.get("level", 0)
    print(f"Battery level: {battery_level}%")
    
    if battery_level < 20:
        print("Warning: Battery level low!")

# Publish a battery status event
publish(
    EventType.HARDWARE_BATTERY_STATUS,
    data={"level": 15, "voltage": 11.2},
    source="example"
)
```

### Creating Event Handlers

```python
from mower.events import EventHandler, EventType, handle_event

class SensorHandler(EventHandler):
    def __init__(self):
        super().__init__()
        self.temperature_readings = []
    
    @handle_event(EventType.HARDWARE_SENSOR_DATA)
    def handle_sensor_data(self, event):
        if "temperature" in event.data:
            self.temperature_readings.append(event.data["temperature"])
            print(f"Temperature: {event.data['temperature']}°C")
    
    def get_average_temperature(self):
        if not self.temperature_readings:
            return 0.0
        return sum(self.temperature_readings) / len(self.temperature_readings)

# Create a sensor handler
sensor_handler = SensorHandler()

# Subscribe to events
sensor_handler.subscribe_all()

# Unsubscribe when done
sensor_handler.unsubscribe_all()
```

## Event Types

The `EventType` enum defines all the event types in the system:

- Hardware events: `HARDWARE_SENSOR_DATA`, `HARDWARE_MOTOR_STATUS`, etc.
- Navigation events: `NAVIGATION_POSITION_UPDATED`, `NAVIGATION_PATH_UPDATED`, etc.
- Obstacle detection events: `OBSTACLE_DETECTED`, `OBSTACLE_CLEARED`, etc.
- State events: `STATE_CHANGED`, `ERROR_OCCURRED`, etc.
- User interface events: `UI_COMMAND_RECEIVED`, `UI_STATUS_UPDATED`, etc.
- System events: `SYSTEM_STARTUP`, `SYSTEM_SHUTDOWN`, etc.

## Event Priorities

The `EventPriority` enum defines the priority levels for events:

- `LOW`: Low priority events
- `NORMAL`: Normal priority events (default)
- `HIGH`: High priority events
- `CRITICAL`: Critical priority events

## Examples

See the `examples.py` file for more detailed examples of using the event system.