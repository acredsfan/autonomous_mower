# System Architecture

This document describes the overall architecture of the Autonomous Mower system and how the different components interact with each other.

## Overview

The Autonomous Mower system is designed with a modular architecture that separates concerns and allows for easy extension and maintenance. The system is composed of several key components that work together to provide the mower's functionality.

## High-Level Architecture

The system follows a layered architecture with the following main layers:

1. **User Interface Layer**: Provides interfaces for user interaction (web UI, mobile app)
2. **Application Layer**: Contains the business logic and coordinates between components
3. **Hardware Abstraction Layer**: Provides abstractions for hardware components
4. **Hardware Layer**: Interfaces directly with the physical hardware

## Component Diagram

```
+---------------------+     +---------------------+
|    User Interface   |     |   Remote Access     |
| (Web UI, Mobile App)|     | (DDNS, Cloudflare)  |
+----------+----------+     +---------+-----------+
           |                          |
           v                          v
+---------------------------------------------+
|               Main Controller               |
+---------------------------------------------+
           |                |
           v                v
+---------------------+     +---------------------+
|     Navigation      |     | Obstacle Detection  |
| (Path Planning, GPS)|     | (Camera, Sensors)   |
+----------+----------+     +---------+-----------+
           |                          |
           v                          v
+---------------------------------------------+
|         Hardware Abstraction Layer          |
+---------------------------------------------+
           |                |
           v                v
+---------------------+     +---------------------+
|  Motor Controllers  |     |       Sensors       |
| (Wheels, Blades)    |     | (GPS, IMU, Camera)  |
+---------------------+     +---------------------+
```

## Key Components

### Main Controller

The Main Controller is the central component of the system. It:
- Coordinates between all other components
- Manages the overall state of the mower
- Handles resource initialization and cleanup
- Processes user commands
- Manages the event system

**Key Classes**:
- `MainController`: Main entry point and coordinator
- `ResourceManager`: Manages hardware and software resources
- `StateManager`: Manages the mower's state

### Navigation

The Navigation component is responsible for planning and executing the mower's movement. It:
- Generates mowing paths based on boundaries and obstacles
- Controls the mower's movement
- Tracks the mower's position using GPS and other sensors
- Implements different mowing patterns

**Key Classes**:
- `PathPlanner`: Generates mowing paths
- `NavigationController`: Controls the mower's movement
- `GPSManager`: Manages GPS data and position tracking
- `BoundaryManager`: Manages mowing boundaries and no-go zones

### Obstacle Detection

The Obstacle Detection component is responsible for detecting and avoiding obstacles. It:
- Processes camera images to detect obstacles
- Reads distance sensors to detect nearby objects
- Implements obstacle avoidance algorithms
- Provides real-time obstacle information to the Navigation component

**Key Classes**:
- `ObstacleDetector`: Detects obstacles using camera and sensors
- `AvoidanceAlgorithm`: Implements obstacle avoidance strategies
- `SensorFusion`: Combines data from multiple sensors

### Hardware Abstraction Layer

The Hardware Abstraction Layer provides abstractions for hardware components. It:
- Provides a consistent interface for hardware components
- Handles hardware-specific details
- Allows for easy switching between real hardware and simulation
- Manages hardware resources

**Key Classes**:
- `HardwareManager`: Manages hardware components
- `MotorController`: Controls motors (wheels, blades)
- `SensorInterface`: Provides a consistent interface for sensors
- `CameraInterface`: Provides a consistent interface for cameras

### User Interface

The User Interface component provides interfaces for user interaction. It:
- Provides a web interface for control and monitoring
- Provides a mobile app for remote control
- Displays the mower's status and position
- Allows for configuration and scheduling

**Key Classes**:
- `WebServer`: Serves the web interface
- `APIController`: Provides API endpoints for the mobile app
- `DashboardController`: Manages the dashboard display
- `ConfigurationController`: Manages configuration settings

## Component Interactions

### Startup Sequence

1. The `MainController` initializes the `ResourceManager`
2. The `ResourceManager` initializes hardware components
3. The `StateManager` sets the initial state
4. The `WebServer` starts and serves the web interface
5. The `NavigationController` initializes the GPS and other sensors
6. The `ObstacleDetector` initializes the camera and distance sensors
7. The `MainController` enters the ready state

### Mowing Sequence

1. The user initiates mowing through the UI
2. The `MainController` changes the state to "mowing"
3. The `PathPlanner` generates a mowing path
4. The `NavigationController` starts following the path
5. The `ObstacleDetector` continuously monitors for obstacles
6. If an obstacle is detected, the `AvoidanceAlgorithm` calculates an avoidance path
7. The `NavigationController` follows the avoidance path
8. Once the obstacle is avoided, the `NavigationController` returns to the original path
9. When the battery is low, the `MainController` initiates a return to the charging station
10. The `NavigationController` navigates to the charging station

### Event System

The system uses an event-driven architecture for communication between components:

1. Components can publish events to the event bus
2. Components can subscribe to events they are interested in
3. When an event is published, all subscribers are notified
4. Events include:
   - `ObstacleDetectedEvent`: Published when an obstacle is detected
   - `LowBatteryEvent`: Published when the battery is low
   - `PathCompletedEvent`: Published when a path is completed
   - `ErrorEvent`: Published when an error occurs

## Plugin Architecture

The system supports plugins for extending functionality:

1. Plugins implement specific interfaces defined in the `interfaces` package
2. The `PluginManager` discovers and loads plugins at runtime
3. Plugins can provide:
   - Additional sensor support
   - Custom obstacle detection algorithms
   - Custom path planning algorithms
   - Custom UI components

## Configuration Management

The system uses a centralized configuration management approach:

1. Configuration settings are stored in a central repository
2. Components access configuration through the `ConfigManager`
3. Configuration can be changed through the UI
4. Configuration changes trigger events that components can respond to

## Error Handling

The system uses a unified error handling approach:

1. Errors are represented by the `Error` class hierarchy
2. Components can throw errors or publish error events
3. The `ErrorHandler` processes errors and determines the appropriate response
4. Errors are logged and, if appropriate, displayed to the user
5. Critical errors trigger a safe shutdown sequence

## Simulation Capabilities

The system supports simulation for testing without hardware:

1. The `SimulationManager` coordinates the simulation
2. Virtual hardware components implement the same interfaces as real hardware
3. The `VirtualWorld` simulates the environment
4. The system can be switched between real hardware and simulation through configuration

## Conclusion

The Autonomous Mower system's modular architecture allows for easy extension and maintenance. The separation of concerns between components, the use of interfaces, and the event-driven communication model provide a flexible and robust foundation for the system's functionality.