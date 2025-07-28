# Code Consolidation Guide

This guide explains how to migrate from duplicate code patterns to the new consolidated utilities.

## Overview

Our code duplication analysis identified several areas with significant duplication:

1. Interface implementations
2. Configuration handling
3. Error handling
4. Logging patterns

To address these issues, we've created standardized utility modules that provide consistent implementations for these common patterns.

## Interface Base Classes

### Before Consolidation

```python
class SensorA:
    def __init__(self):
        self._initialized = False
        self._running = False
        
    def initialize(self):
        if self._initialized:
            return
        # Custom initialization
        self._initialized = True
        
    def cleanup(self):
        if not self._initialized:
            return
        # Custom cleanup
        self._initialized = False
        self._running = False
        
    def start(self):
        if not self._initialized:
            self.initialize()
        if self._running:
            return
        # Custom start
        self._running = True
        
    def stop(self):
        if not self._running:
            return
        # Custom stop
        self._running = False
```

### After Consolidation

```python
from mower.utilities.interface_base import InterfaceBase

class SensorA(InterfaceBase):
    def _initialize(self):
        # Custom initialization only
        pass
        
    def _cleanup(self):
        # Custom cleanup only
        pass
        
    def _start(self):
        # Custom start only
        pass
        
    def _stop(self):
        # Custom stop only
        pass
```

## Error Handling

### Before Consolidation

```python
def fetch_data():
    retry_count = 0
    max_retries = 3
    delay = 1.0
    
    while retry_count < max_retries:
        try:
            # Attempt to fetch data
            return data
        except Exception as e:
            retry_count += 1
            if retry_count == max_retries:
                logger.error(f"Failed to fetch data after {max_retries} attempts: {e}")
                raise
            logger.warning(f"Retry {retry_count}/{max_retries} after error: {e}")
            time.sleep(delay)
            delay *= 2
```

### After Consolidation

```python
from mower.utilities.error_handling import retry

@retry(max_attempts=3, delay=1.0, backoff_factor=2.0)
def fetch_data():
    # Attempt to fetch data
    return data
```

## Configuration Management

### Before Consolidation

```python
def get_config_value(key, default=None):
    # Check environment variables
    env_key = f"MOWER_{key.upper()}"
    if env_key in os.environ:
        return os.environ[env_key]
    
    # Check config file
    try:
        with open("config/main_config.json", "r") as f:
            config = json.load(f)
            if key in config:
                return config[key]
    except Exception as e:
        logger.error(f"Error loading config file: {e}")
    
    # Return default
    return default

def get_int_config(key, default=0):
    value = get_config_value(key, default)
    try:
        return int(value)
    except (ValueError, TypeError):
        logger.warning(f"Failed to convert '{key}' to int, using default")
        return default
```

### After Consolidation

```python
from mower.utilities.config_manager import config_manager

# Setup (once at application startup)
config_manager.add_environment_source(prefix="MOWER_")
config_manager.add_file_source("config/main_config.json")
config_manager.set_defaults({"log_level": "INFO"})

# Usage throughout the application
value = config_manager.get("key", default)
int_value = config_manager.get_int("key", default=0)
```

## Logging

### Before Consolidation

```python
def process_request(request_id, user):
    logger.info(f"Processing request {request_id} for user {user}")
    try:
        # Process request
        logger.info(f"Request {request_id} processed successfully")
    except Exception as e:
        logger.error(f"Error processing request {request_id}: {e}")
        raise
```

### After Consolidation

```python
from mower.utilities.logging_utils import get_logger, LogContext

logger = get_logger(__name__, with_context=True)

def process_request(request_id, user):
    with LogContext(logger, request_id=request_id, user=user):
        logger.info("Processing request")
        # Process request
        logger.info("Request processed successfully")
        # Any exceptions will be logged with context automatically
```

## Migration Steps

1. **Identify Duplicate Patterns**:
   - Use the code duplication analysis report to identify areas to consolidate
   - Focus on the most duplicated patterns first

2. **Interface Classes**:
   - Replace custom interface implementations with extensions of the base classes
   - Override only the specific methods needed for custom behavior
   - Test thoroughly to ensure behavior is preserved

3. **Error Handling**:
   - Replace custom try/except blocks with `ErrorContext`
   - Replace custom retry logic with the `retry` decorator
   - Replace resource cleanup patterns with `ResourceGuard`

4. **Configuration**:
   - Replace direct file loading with `config_manager`
   - Replace environment variable access with `config_manager`
   - Replace custom validation with `config_manager` validators

5. **Logging**:
   - Replace direct logger calls with context-aware logging
   - Replace custom log formatting with standardized formatters
   - Use decorators for consistent function call logging

## Testing After Migration

After migrating to the consolidated utilities, ensure:

1. All tests pass with the new implementations
2. Behavior is preserved for all components
3. Error handling works as expected
4. Configuration is loaded correctly
5. Logs contain the same information as before

## Example Migration: Sensor Interface

### Original Code

```python
class TOFSensor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._initialized = False
        self._running = False
        self._last_reading = None
        
    def initialize(self):
        if self._initialized:
            self.logger.debug("TOFSensor already initialized")
            return
        
        try:
            self.logger.debug("Initializing TOFSensor")
            # Custom initialization
            self._initialized = True
            self.logger.debug("TOFSensor initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize TOFSensor: {e}")
            raise
    
    def cleanup(self):
        if not self._initialized:
            return
        
        try:
            # Custom cleanup
            self._initialized = False
            self._running = False
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    def read(self):
        if not self._initialized:
            self.initialize()
        
        try:
            # Read sensor data
            self._last_reading = data
            return data
        except Exception as e:
            self.logger.error(f"Error reading sensor: {e}")
            if self._last_reading is not None:
                return self._last_reading
            raise
```

### Migrated Code

```python
from mower.utilities.interface_base import SensorInterfaceBase

class TOFSensor(SensorInterfaceBase):
    def __init__(self):
        super().__init__("TOFSensor")
    
    def _initialize(self):
        # Custom initialization only
        pass
    
    def _cleanup(self):
        # Custom cleanup only
        pass
    
    def _read_sensor(self):
        # Read sensor data
        return data
```

## Benefits of Consolidation

1. **Reduced Code Size**: Eliminates hundreds of lines of duplicate code
2. **Improved Consistency**: Standardized patterns across the codebase
3. **Better Error Handling**: Comprehensive and consistent error handling
4. **Easier Maintenance**: Changes to common patterns only need to be made once
5. **Improved Readability**: Focus on business logic rather than boilerplate
6. **Better Testing**: Consolidated utilities can be thoroughly tested once