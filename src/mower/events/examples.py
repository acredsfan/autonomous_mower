"""
Examples of using the event system.

This module provides examples of how to use the event system in the autonomous
mower project. These examples can be used as templates for implementing
event-based communication in your components.
"""

import time
from typing import Dict, Any

from mower.events.event import Event, EventType, EventPriority
from mower.events.event_bus import EventBus, get_event_bus
from mower.events.handlers import EventHandler, handle_event, subscribe, publish


# Example 1: Basic event publishing and subscribing
def example_basic_usage():
    """Example of basic event publishing and subscribing."""
    print("\nExample 1: Basic event publishing and subscribing")
    
    # Define a callback function
    def on_sensor_data(event: Event):
        print(f"Received sensor data: {event.data}")
    
    # Get the event bus
    event_bus = get_event_bus()
    
    # Subscribe to events
    event_bus.subscribe(on_sensor_data, EventType.HARDWARE_SENSOR_DATA)
    
    # Publish an event
    event = Event(
        event_type=EventType.HARDWARE_SENSOR_DATA,
        data={"temperature": 25.0, "humidity": 60.0},
        source="example_basic_usage"
    )
    event_bus.publish(event, synchronous=True)
    
    # Unsubscribe when done
    event_bus.unsubscribe(on_sensor_data, EventType.HARDWARE_SENSOR_DATA)


# Example 2: Using the subscribe decorator
@subscribe(EventType.HARDWARE_BATTERY_STATUS)
def handle_battery_status(event: Event):
    """Handle battery status events."""
    battery_level = event.data.get("level", 0)
    print(f"Battery level: {battery_level}%")
    
    if battery_level < 20:
        print("Warning: Battery level low!")


def example_decorator_usage():
    """Example of using the subscribe decorator."""
    print("\nExample 2: Using the subscribe decorator")
    
    # Publish a battery status event
    publish(
        EventType.HARDWARE_BATTERY_STATUS,
        data={"level": 15, "voltage": 11.2},
        source="example_decorator_usage"
    )


# Example 3: Creating an event handler class
class SensorHandler(EventHandler):
    """Example event handler for sensor events."""
    
    def __init__(self):
        """Initialize the sensor handler."""
        super().__init__()
        self.temperature_readings = []
        self.humidity_readings = []
    
    @handle_event(EventType.HARDWARE_SENSOR_DATA)
    def handle_sensor_data(self, event: Event):
        """Handle sensor data events."""
        if "temperature" in event.data:
            self.temperature_readings.append(event.data["temperature"])
            print(f"Temperature: {event.data['temperature']}°C")
        
        if "humidity" in event.data:
            self.humidity_readings.append(event.data["humidity"])
            print(f"Humidity: {event.data['humidity']}%")
    
    @handle_event(EventType.HARDWARE_IMU_DATA)
    def handle_imu_data(self, event: Event):
        """Handle IMU data events."""
        print(f"IMU data: {event.data}")
    
    def get_average_temperature(self) -> float:
        """Get the average temperature reading."""
        if not self.temperature_readings:
            return 0.0
        return sum(self.temperature_readings) / len(self.temperature_readings)


def example_event_handler_class():
    """Example of using an event handler class."""
    print("\nExample 3: Using an event handler class")
    
    # Create a sensor handler
    sensor_handler = SensorHandler()
    
    # Subscribe to events
    sensor_handler.subscribe_all()
    
    # Publish some events
    publish(
        EventType.HARDWARE_SENSOR_DATA,
        data={"temperature": 22.5, "humidity": 55.0},
        source="example_event_handler_class"
    )
    
    publish(
        EventType.HARDWARE_SENSOR_DATA,
        data={"temperature": 23.0, "humidity": 56.0},
        source="example_event_handler_class"
    )
    
    publish(
        EventType.HARDWARE_IMU_DATA,
        data={"acceleration": [0.1, 0.2, 9.8], "gyro": [0.01, 0.02, 0.03]},
        source="example_event_handler_class"
    )
    
    # Get the average temperature
    avg_temp = sensor_handler.get_average_temperature()
    print(f"Average temperature: {avg_temp}°C")
    
    # Unsubscribe when done
    sensor_handler.unsubscribe_all()


# Example 4: Event priorities and asynchronous processing
def example_priorities_and_async():
    """Example of event priorities and asynchronous processing."""
    print("\nExample 4: Event priorities and asynchronous processing")
    
    # Define callback functions
    def handle_normal_event(event: Event):
        print(f"Handling normal event: {event}")
    
    def handle_critical_event(event: Event):
        print(f"Handling CRITICAL event: {event}")
    
    # Get the event bus
    event_bus = get_event_bus()
    
    # Subscribe to events
    event_bus.subscribe(handle_normal_event, EventType.SYSTEM_HEARTBEAT)
    event_bus.subscribe(handle_critical_event, EventType.ERROR_OCCURRED)
    
    # Publish events with different priorities
    normal_event = Event(
        event_type=EventType.SYSTEM_HEARTBEAT,
        data={"timestamp": time.time()},
        priority=EventPriority.NORMAL,
        source="example_priorities_and_async"
    )
    
    critical_event = Event(
        event_type=EventType.ERROR_OCCURRED,
        data={"error": "Critical system error", "code": 500},
        priority=EventPriority.CRITICAL,
        source="example_priorities_and_async"
    )
    
    # Publish asynchronously
    print("Publishing events asynchronously...")
    event_bus.publish(normal_event)
    event_bus.publish(critical_event)
    
    # Wait for events to be processed
    time.sleep(0.5)
    
    # Unsubscribe when done
    event_bus.unsubscribe(handle_normal_event, EventType.SYSTEM_HEARTBEAT)
    event_bus.unsubscribe(handle_critical_event, EventType.ERROR_OCCURRED)


# Example 5: Integration with components
class TemperatureSensor:
    """Example temperature sensor component."""
    
    def __init__(self):
        """Initialize the temperature sensor."""
        self.temperature = 20.0
    
    def read_temperature(self) -> float:
        """Read the current temperature."""
        # Simulate temperature reading
        self.temperature += 0.1
        return self.temperature
    
    def publish_temperature(self):
        """Publish the current temperature as an event."""
        temperature = self.read_temperature()
        publish(
            EventType.HARDWARE_SENSOR_DATA,
            data={"temperature": temperature, "sensor_id": "temp_sensor_1"},
            source="TemperatureSensor"
        )


class TemperatureMonitor(EventHandler):
    """Example temperature monitor component."""
    
    def __init__(self):
        """Initialize the temperature monitor."""
        super().__init__()
        self.temperature_threshold = 25.0
        self.subscribe(EventType.HARDWARE_SENSOR_DATA)
    
    @handle_event(EventType.HARDWARE_SENSOR_DATA)
    def handle_temperature(self, event: Event):
        """Handle temperature sensor data."""
        if "temperature" in event.data:
            temperature = event.data["temperature"]
            print(f"Temperature monitor: {temperature}°C")
            
            if temperature > self.temperature_threshold:
                # Publish a warning event
                self.publish(
                    EventType.WARNING_OCCURRED,
                    data={
                        "message": f"Temperature above threshold: {temperature}°C",
                        "threshold": self.temperature_threshold
                    }
                )


def example_component_integration():
    """Example of integrating the event system with components."""
    print("\nExample 5: Integration with components")
    
    # Create components
    sensor = TemperatureSensor()
    monitor = TemperatureMonitor()
    
    # Define a callback for warnings
    @subscribe(EventType.WARNING_OCCURRED)
    def handle_warning(event: Event):
        print(f"WARNING: {event.data.get('message')}")
    
    # Simulate temperature readings
    for _ in range(10):
        sensor.publish_temperature()
        time.sleep(0.1)
    
    # Cleanup
    monitor.unsubscribe_all()


# Run all examples
if __name__ == "__main__":
    print("Running event system examples...")
    
    example_basic_usage()
    example_decorator_usage()
    example_event_handler_class()
    example_priorities_and_async()
    example_component_integration()
    
    print("\nAll examples completed.")