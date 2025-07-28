# API Documentation

This document provides comprehensive API documentation for the autonomous mower system, including recent improvements and error handling mechanisms.

## Table of Contents

1. [System Overview](#system-overview)
2. [Core APIs](#core-apis)
3. [Hardware APIs](#hardware-apis)
4. [Error Handling](#error-handling)
5. [Configuration APIs](#configuration-apis)
6. [Validation APIs](#validation-apis)
7. [Usage Examples](#usage-examples)

## System Overview

The autonomous mower system provides a comprehensive API for hardware control, sensor data collection, navigation, and system management. All APIs include robust error handling and graceful degradation mechanisms.

### Key Features

- **Graceful Degradation**: APIs continue to function with fallback data when hardware fails
- **Timeout Protection**: All hardware operations include timeout mechanisms
- **Error Recovery**: Automatic retry and recovery mechanisms for transient failures
- **Performance Monitoring**: Built-in performance metrics and resource monitoring
- **Comprehensive Validation**: End-to-end testing and validation capabilities

## Core APIs

### MainController

The main system controller coordinates all subsystems and provides the primary interface for system control.

```python
from mower.main_controller import MainController

# Initialize the main controller
controller = MainController()

# Initialize all subsystems
success = controller.initialize()

# Start system operations
controller.start()

# Get system status
status = controller.get_status()

# Execute commands
result = controller.execute_command("emergency_stop")

# Stop and cleanup
controller.stop()
```

#### Methods

- `initialize() -> bool`: Initialize all system components
- `start() -> None`: Start system operations
- `stop() -> None`: Stop system and cleanup resources
- `get_status() -> Dict[str, Any]`: Get current system status
- `execute_command(command: str, params: Dict[str, Any] = None) -> Dict[str, Any]`: Execute system commands

#### Status Response Format

```json
{
  "status": "running|stopped|error",
  "state": "idle|mowing|docking|error|emergency_stop",
  "initialized": true,
  "uptime": 3600,
  "memory_usage": 512.5,
  "cpu_usage": 15.2
}
```

### ResourceManager

Manages all system resources including hardware components and software modules.

```python
from mower.main_controller import ResourceManager

# Initialize resource manager
resource_manager = ResourceManager()
resource_manager.initialize()

# Get sensor data
sensor_data = resource_manager.get_sensor_data()

# Get GPS location
gps_location = resource_manager.get_gps_location()

# Get system resource status
system_status = resource_manager.get_system_resource_status()

# Execute commands
result = resource_manager.execute_command("manual_drive", {"forward": 0.5, "turn": 0.2})
```

#### Key Methods

- `get_sensor_data() -> Dict[str, Any]`: Get comprehensive sensor data with fallback handling
- `get_gps_location() -> Optional[Dict[str, Any]]`: Get GPS location data
- `get_safety_critical_sensor_data() -> Dict[str, Any]`: Get safety-critical sensor data with highest priority
- `get_system_resource_status() -> Dict[str, Any]`: Get system resource usage and status
- `execute_command(command: str, params: Dict[str, Any] = None) -> Dict[str, Any]`: Execute system commands

## Hardware APIs

### Sensor Interface

The sensor interface provides unified access to all sensor data with comprehensive error handling.

```python
from mower.hardware.async_sensor_manager import AsyncSensorInterface

# Initialize sensor interface
sensor_interface = AsyncSensorInterface(simulate=False)
sensor_interface.start()

# Get sensor data
sensor_data = sensor_interface.get_sensor_data()

# Stop sensor interface
sensor_interface.stop()
```

#### Sensor Data Format

```json
{
  "environment": {
    "temperature": 25.5,
    "humidity": 60.2,
    "pressure": 1013.25
  },
  "imu": {
    "heading": 45.0,
    "roll": 2.1,
    "pitch": -1.5,
    "acceleration": {"x": 0.1, "y": 0.0, "z": 9.8},
    "gyroscope": {"x": 0.0, "y": 0.0, "z": 0.1},
    "magnetometer": {"x": 25.0, "y": -10.0, "z": 45.0},
    "calibration": "good",
    "safety_status": {"is_safe": true, "status": "operational"}
  },
  "power": {
    "voltage": 12.6,
    "current": 2.5,
    "power": 31.5,
    "percentage": 85,
    "solar_voltage": 18.2,
    "solar_current": 1.2,
    "solar_power": 21.8
  },
  "tof": {
    "left": 150.5,
    "right": 200.3,
    "working": true
  },
  "timestamp": 1642781234.567,
  "status": "operational"
}
```

### Hardware Registry

The hardware registry manages all hardware components with automatic initialization and error handling.

```python
from mower.hardware.hardware_registry import get_hardware_registry

# Get hardware registry instance
hardware_registry = get_hardware_registry()

# Initialize all hardware
success = hardware_registry.initialize()

# Get specific hardware components
camera = hardware_registry.get_camera()
gps = hardware_registry.get_serial_port()
robohat = hardware_registry.get_robohat()

# Cleanup hardware
hardware_registry.cleanup()
```

### Individual Sensor APIs

#### IMU Sensor

```python
from mower.hardware.imu import IMU

# Initialize IMU
imu = IMU(port="/dev/ttyAMA4", baudrate=3000000)

# Get IMU data
imu_data = imu.get_data()

# Check if IMU is available
is_available = imu.is_available()
```

#### ToF Sensors

```python
from mower.hardware.tof import TOFSensor

# Initialize ToF sensors
tof = TOFSensor()

# Get distance measurements
distances = tof.get_distances()
# Returns: {"left": 150.5, "right": 200.3, "working": True}
```

#### Environmental Sensor (BME280)

```python
from mower.hardware.bme280 import BME280

# Initialize BME280
bme280 = BME280()

# Get environmental data
env_data = bme280.get_data()
# Returns: {"temperature": 25.5, "humidity": 60.2, "pressure": 1013.25}
```

## Error Handling

The system includes comprehensive error handling mechanisms that ensure graceful degradation and automatic recovery.

### Error Handling Decorators

```python
from mower.error_handling import (
    safe_hardware_operation,
    sensor_data_operation,
    critical_system_operation,
    with_comprehensive_error_handling
)

@safe_hardware_operation("sensor_read", "imu")
def read_imu_data():
    # Hardware operation with automatic error handling
    return imu.get_data()

@sensor_data_operation("sensor_collection", fallback_value={})
def collect_sensor_data():
    # Sensor operation with fallback data
    return sensor_interface.get_sensor_data()

@critical_system_operation("system_init")
def initialize_system():
    # Critical operation with enhanced error handling
    return system.initialize()
```

### Error Response Format

```json
{
  "success": false,
  "error": "Sensor communication timeout",
  "error_code": "SENSOR_TIMEOUT",
  "component": "imu",
  "operation": "read_data",
  "timestamp": 1642781234.567,
  "fallback_used": true,
  "retry_count": 3
}
```

### Circuit Breaker Pattern

```python
from mower.error_handling.circuit_breaker import CircuitBreaker

# Create circuit breaker for hardware component
circuit_breaker = CircuitBreaker(
    failure_threshold=3,
    recovery_timeout=30,
    expected_exception=RuntimeError
)

@circuit_breaker
def hardware_operation():
    # Hardware operation protected by circuit breaker
    return hardware.read_data()
```

## Configuration APIs

### Configuration Manager

```python
from mower.config_management import get_config_manager, get_config

# Get configuration manager
config_manager = get_config_manager()

# Get configuration values
log_level = get_config("mower.log_level", "INFO")
use_simulation = get_config("hardware.use_simulation", False)
watchdog_timeout = get_config("safety.watchdog_timeout", 15)

# Update configuration
config_manager.set("mower.log_level", "DEBUG")
config_manager.save()
```

### Environment Configuration

```python
import os
from mower.config_management.environment_config import EnvironmentConfigurationSource

# Load environment variables
env_config = EnvironmentConfigurationSource()
env_config.load()

# Get environment values with defaults
gps_port = os.environ.get("GPS_SERIAL_PORT", "/dev/ttyACM0")
log_level = os.environ.get("LOG_LEVEL", "INFO")
use_simulation = os.environ.get("USE_SIMULATION", "false").lower() == "true"
```

## Validation APIs

### System Validation

```python
from tests.system_validation.test_comprehensive_system import SystemValidationSuite

# Create validation suite
validator = SystemValidationSuite()

# Run comprehensive validation
results = validator.run_comprehensive_validation()

# Check results
if results["overall_success"]:
    print(f"Validation passed with {results['summary']['success_rate']:.1%} success rate")
else:
    print("Validation failed - check detailed results")
    for suite_name, suite_result in results['suite_results'].items():
        if not suite_result['success']:
            print(f"Failed suite: {suite_name}")
            for error in suite_result['errors']:
                print(f"  Error: {error}")
```

### Hardware Testing

```python
from tools.test_sensors import test_all_sensors, test_specific_sensor

# Test all sensors
results = test_all_sensors()

# Test specific sensor
imu_result = test_specific_sensor("imu")
tof_result = test_specific_sensor("tof")
bme280_result = test_specific_sensor("bme280")
```

## Usage Examples

### Basic System Startup

```python
from mower.main_controller import MainController
import time

# Initialize and start the system
controller = MainController()

try:
    # Initialize all components
    if controller.initialize():
        print("System initialized successfully")
        
        # Start operations
        controller.start()
        print("System started")
        
        # Monitor system status
        while True:
            status = controller.get_status()
            print(f"Status: {status['status']}, State: {status['state']}")
            time.sleep(5)
            
    else:
        print("System initialization failed")
        
except KeyboardInterrupt:
    print("Shutting down...")
    
finally:
    controller.stop()
    print("System stopped")
```

### Sensor Data Collection

```python
from mower.main_controller import ResourceManager
import json

# Initialize resource manager
resource_manager = ResourceManager()
resource_manager.initialize()

try:
    # Collect sensor data
    sensor_data = resource_manager.get_sensor_data()
    
    # Print formatted sensor data
    print(json.dumps(sensor_data, indent=2))
    
    # Get safety-critical data
    safety_data = resource_manager.get_safety_critical_sensor_data()
    print(f"Safety status: {safety_data['imu']['safety_status']}")
    
    # Get GPS location
    gps_location = resource_manager.get_gps_location()
    if gps_location:
        print(f"GPS: {gps_location['latitude']}, {gps_location['longitude']}")
    else:
        print("GPS not available")
        
finally:
    resource_manager.cleanup_all_resources()
```

### Manual Control

```python
from mower.main_controller import ResourceManager

# Initialize system
resource_manager = ResourceManager()
resource_manager.initialize()

try:
    # Enable manual control
    resource_manager.start_manual_control()
    
    # Drive forward
    result = resource_manager.execute_command("manual_drive", {
        "forward": 0.5,  # 50% forward speed
        "turn": 0.0      # No turning
    })
    print(f"Drive command result: {result}")
    
    # Turn right
    result = resource_manager.execute_command("manual_drive", {
        "forward": 0.0,  # No forward movement
        "turn": 0.3      # 30% right turn
    })
    print(f"Turn command result: {result}")
    
    # Emergency stop
    result = resource_manager.execute_command("emergency_stop")
    print(f"Emergency stop result: {result}")
    
finally:
    resource_manager.cleanup_all_resources()
```

### Error Handling Example

```python
from mower.main_controller import ResourceManager
from mower.error_handling import comprehensive_error_context

# Initialize system with error handling
resource_manager = ResourceManager()

try:
    with comprehensive_error_context(
        operation="system_startup",
        component="main",
        critical=True
    ):
        # Initialize with comprehensive error handling
        success = resource_manager.initialize()
        
        if success:
            print("System initialized successfully")
            
            # Collect sensor data with error handling
            try:
                sensor_data = resource_manager.get_sensor_data()
                print(f"Collected {len(sensor_data)} sensor data types")
            except Exception as e:
                print(f"Sensor collection failed: {e}")
                # System continues with fallback data
                
        else:
            print("System initialization failed - check logs")
            
except Exception as e:
    print(f"Critical system error: {e}")
    
finally:
    try:
        resource_manager.cleanup_all_resources()
    except Exception as e:
        print(f"Cleanup error: {e}")
```

## Performance Considerations

### Sensor Collection Optimization

- Sensor data collection is optimized for <2 second response times
- Timeout protection prevents system hanging on failed sensors
- Parallel sensor reading where possible
- Automatic fallback to cached data when sensors are slow

### Memory Management

- System typically uses <600MB of memory
- Automatic garbage collection and resource cleanup
- Memory monitoring and leak detection
- Graceful degradation under memory pressure

### Error Recovery

- Automatic retry with exponential backoff for transient failures
- Circuit breaker pattern prevents cascading failures
- Graceful degradation maintains core functionality
- Comprehensive logging for debugging and monitoring

## Best Practices

1. **Always use error handling**: Wrap hardware operations in appropriate error handling decorators
2. **Check return values**: Verify operation success before proceeding
3. **Use timeouts**: Set appropriate timeouts for all blocking operations
4. **Monitor resources**: Regularly check system resource usage
5. **Validate inputs**: Always validate configuration and input parameters
6. **Test thoroughly**: Use the comprehensive validation suite before deployment
7. **Handle failures gracefully**: Design for graceful degradation when components fail
8. **Log appropriately**: Use structured logging for debugging and monitoring