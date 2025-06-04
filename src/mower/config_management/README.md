# Configuration Management System

This package provides a standardized configuration management system for the autonomous mower project. It includes interfaces and implementations for loading, saving, and accessing configuration from various sources, such as environment variables, configuration files, and command-line arguments.

## Overview

The configuration management system consists of the following components:

- **ConfigurationInterface**: Defines the interface for configuration management
- **ConfigurationSource**: Defines the interface for configuration sources
- **ConfigurationManager**: Implements the ConfigurationInterface and provides a centralized configuration manager
- **EnvironmentConfigurationSource**: Configuration source that uses environment variables
- **FileConfigurationSource**: Configuration source that uses files
- **DictConfigurationSource**: Configuration source that uses dictionaries

## Features

- **Hierarchical Configuration**: Support for hierarchical configuration keys (e.g., `section.key`)
- **Multiple Sources**: Support for multiple configuration sources with different priorities
- **Type Conversion**: Automatic conversion of configuration values to various types
- **Thread Safety**: Thread-safe implementation for concurrent access
- **Singleton Instance**: Singleton instance of ConfigurationManager for easy access
- **Convenience Functions**: Convenience functions for common operations

## Usage

### Basic Usage

```python
from mower.config_management import get_config_manager

# Get the configuration manager
config_manager = get_config_manager()

# Get a configuration value
value = config_manager.get('key', 'default_value')

# Set a configuration value
config_manager.set('key', 'value')

# Check if a configuration key exists
if config_manager.has('key'):
    print('Key exists')

# Delete a configuration value
config_manager.delete('key')

# Get a configuration section
section = config_manager.get_section('section')

# Get all configuration values
all_values = config_manager.get_all()

# Load configuration from a file
config_manager.load('config.json')

# Save configuration to a file
config_manager.save('config.json')

# Reset the configuration to its default state
config_manager.reset()
```

### Type-Specific Getters

```python
# Get a configuration value as an integer
value = config_manager.get_int('key', 0)

# Get a configuration value as a float
value = config_manager.get_float('key', 0.0)

# Get a configuration value as a boolean
value = config_manager.get_bool('key', False)

# Get a configuration value as a string
value = config_manager.get_str('key', '')

# Get a configuration value as a list
value = config_manager.get_list('key', [])

# Get a configuration value as a dictionary
value = config_manager.get_dict('key', {})
```

### Hierarchical Configuration

```python
# Set a hierarchical configuration value
config_manager.set('section.key', 'value')

# Get a hierarchical configuration value
value = config_manager.get('section.key', 'default_value')

# Get a configuration section
section = config_manager.get_section('section')
```

### Multiple Sources

```python
from mower.config_management import (
    get_config_manager,
    EnvironmentConfigurationSource,
    FileConfigurationSource,
    DictConfigurationSource
)

# Get the configuration manager
config_manager = get_config_manager()

# Add a configuration source
config_manager.add_source(FileConfigurationSource('config.json'))

# Add a configuration source with higher priority
config_manager.add_source(EnvironmentConfigurationSource(), 0)

# Add a configuration source with default values
config_manager.add_source(DictConfigurationSource({'key': 'value'}))

# Remove a configuration source
config_manager.remove_source(source)

# Get all configuration sources
sources = config_manager.get_sources()
```

### Convenience Functions

```python
from mower.config_management import get_config, set_config, initialize_config_manager

# Initialize the configuration manager
initialize_config_manager(
    defaults={'key': 'value'},
    config_file='config.json',
    env_file='.env'
)

# Get a configuration value
value = get_config('key', 'default_value')

# Set a configuration value
set_config('key', 'value')
```

## Implementation Details

### ConfigurationInterface

The `ConfigurationInterface` defines the interface for configuration management. It includes methods for getting, setting, checking, and deleting configuration values, as well as loading and saving configuration.

### ConfigurationSource

The `ConfigurationSource` interface defines the contract that all configuration sources must adhere to. It includes methods for getting, setting, checking, and deleting configuration values, as well as loading and saving configuration.

### ConfigurationManager

The `ConfigurationManager` class implements the `ConfigurationInterface` and provides a centralized configuration manager. It supports multiple configuration sources with different priorities, hierarchical configuration keys, and type conversion.

### EnvironmentConfigurationSource

The `EnvironmentConfigurationSource` class is a configuration source that uses environment variables. It supports loading from a .env file and accessing environment variables directly.

### FileConfigurationSource

The `FileConfigurationSource` class is a configuration source that uses files. It supports loading and saving configuration from/to JSON files.

### DictConfigurationSource

The `DictConfigurationSource` class is a configuration source that uses dictionaries. It is useful for testing and for providing default values.

## Best Practices

1. **Use the Singleton Instance**: Use the `get_config_manager()` function to get the singleton instance of `ConfigurationManager`.
2. **Use Type-Specific Getters**: Use the type-specific getters (`get_int()`, `get_float()`, etc.) to ensure type safety.
3. **Use Hierarchical Keys**: Use hierarchical keys (e.g., `section.key`) to organize configuration values.
4. **Set Defaults**: Set default values for all configuration keys to ensure that the application works even if the configuration is missing.
5. **Use Multiple Sources**: Use multiple configuration sources with different priorities to allow for flexible configuration.
6. **Validate Configuration**: Validate configuration values to ensure that they are valid and meet the application's requirements.
7. **Document Configuration**: Document all configuration keys, their purpose, and their default values.
