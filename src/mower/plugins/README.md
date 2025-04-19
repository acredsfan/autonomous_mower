# Plugin System for Autonomous Mower

This package provides a plugin architecture for sensors and detection algorithms in the autonomous mower project. It allows for easy extension of the system with new sensors and detection algorithms without modifying the core codebase.

## Overview

The plugin system consists of the following components:

- **Plugin Base Classes**: Define the interfaces that plugins must implement
- **Plugin Manager**: Handles plugin registration, discovery, and loading
- **Example Plugins**: Demonstrate how to create and use plugins

## Plugin Types

The system supports the following types of plugins:

1. **Sensor Plugins**: Provide data from physical or virtual sensors
2. **Detection Plugins**: Detect obstacles, objects, or other features in the environment
3. **Avoidance Plugins**: Generate paths to avoid obstacles

## Using Plugins

### Getting Plugin Managers

The system provides singleton instances of plugin managers for each plugin type:

```python
from mower.plugins.plugin_manager import (
    get_sensor_plugin_manager,
    get_detection_plugin_manager,
    get_avoidance_plugin_manager
)

# Get the sensor plugin manager
sensor_manager = get_sensor_plugin_manager()

# Get the detection plugin manager
detection_manager = get_detection_plugin_manager()

# Get the avoidance plugin manager
avoidance_manager = get_avoidance_plugin_manager()
```

### Discovering Plugins

To discover plugins in a directory:

```python
# Add a directory to search for plugins
sensor_manager.add_plugin_directory("/path/to/plugins")

# Discover plugins in the registered directories
num_plugins = sensor_manager.discover_plugins()
print(f"Discovered {num_plugins} sensor plugins")
```

### Getting Plugin Instances

To get a plugin instance by ID:

```python
# Get a plugin instance by ID
temperature_sensor = sensor_manager.get_plugin("temperature_sensor")

# Get a plugin instance by name
obstacle_detector = detection_manager.get_plugin_by_name("Simple Obstacle Detector")

# Get all plugin instances
all_avoidance_plugins = avoidance_manager.get_all_plugins()
```

### Using Plugin Instances

Once you have a plugin instance, you can use it according to its type:

```python
# Using a sensor plugin
if temperature_sensor:
    data = temperature_sensor.get_data()
    print(f"Temperature: {data.get('temperature_c')}°C")

# Using a detection plugin
if obstacle_detector:
    obstacles = obstacle_detector.detect(sensor_data)
    print(f"Detected {len(obstacles)} obstacles")

# Using an avoidance plugin
if avoidance_plugin:
    new_path = avoidance_plugin.avoid(obstacles, current_path)
    print(f"Generated a new path with {len(new_path)} points")
```

### Cleaning Up

When you're done with the plugins, clean them up:

```python
# Clean up a specific plugin
temperature_sensor.cleanup()

# Clean up all plugins managed by a manager
sensor_manager.cleanup()
```

## Creating Plugins

To create a new plugin, you need to:

1. Create a new class that inherits from one of the plugin base classes
2. Implement the required methods and properties
3. Place the plugin in a directory that will be searched by the plugin manager

### Example Sensor Plugin

```python
from mower.plugins.plugin_base import SensorPlugin

class MySensorPlugin(SensorPlugin):
    @property
    def plugin_id(self) -> str:
        return "my_sensor"
    
    @property
    def plugin_name(self) -> str:
        return "My Sensor"
    
    @property
    def plugin_version(self) -> str:
        return "1.0.0"
    
    @property
    def plugin_description(self) -> str:
        return "My custom sensor plugin"
    
    @property
    def sensor_type(self) -> str:
        return "temperature"
    
    def initialize(self) -> bool:
        # Initialize the sensor
        return True
    
    def get_data(self) -> Dict[str, Any]:
        # Get data from the sensor
        return {"temperature": 25.0}
    
    def get_status(self) -> Dict[str, Any]:
        # Get the status of the sensor
        return {"status": "ok"}
    
    def cleanup(self) -> None:
        # Clean up resources
        pass
```

### Example Detection Plugin

```python
from mower.plugins.plugin_base import DetectionPlugin

class MyDetectionPlugin(DetectionPlugin):
    @property
    def plugin_id(self) -> str:
        return "my_detector"
    
    @property
    def plugin_name(self) -> str:
        return "My Detector"
    
    @property
    def plugin_version(self) -> str:
        return "1.0.0"
    
    @property
    def plugin_description(self) -> str:
        return "My custom detection plugin"
    
    @property
    def detection_type(self) -> str:
        return "obstacle"
    
    @property
    def required_data_keys(self) -> List[str]:
        return ["image"]
    
    def initialize(self) -> bool:
        # Initialize the detector
        return True
    
    def detect(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Detect objects in the data
        return [{"type": "obstacle", "position": "front"}]
    
    def cleanup(self) -> None:
        # Clean up resources
        pass
```

### Example Avoidance Plugin

```python
from mower.plugins.plugin_base import AvoidancePlugin

class MyAvoidancePlugin(AvoidancePlugin):
    @property
    def plugin_id(self) -> str:
        return "my_avoidance"
    
    @property
    def plugin_name(self) -> str:
        return "My Avoidance"
    
    @property
    def plugin_version(self) -> str:
        return "1.0.0"
    
    @property
    def plugin_description(self) -> str:
        return "My custom avoidance plugin"
    
    @property
    def avoidance_type(self) -> str:
        return "obstacle"
    
    def initialize(self) -> bool:
        # Initialize the avoidance algorithm
        return True
    
    def avoid(self, obstacles: List[Dict[str, Any]], current_path: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # Generate a new path to avoid obstacles
        return current_path
    
    def cleanup(self) -> None:
        # Clean up resources
        pass
```

## Example Plugins

The `examples` directory contains example plugins that demonstrate how to create and use plugins:

- `temperature_sensor_plugin.py`: Example sensor plugin
- `simple_obstacle_detector_plugin.py`: Example detection plugin
- `basic_avoidance_plugin.py`: Example avoidance plugin

These examples can be used as templates for creating your own plugins.