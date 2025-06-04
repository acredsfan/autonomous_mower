# State Management System

This module provides a unified state management system for the autonomous mower project. It includes a state enum, state manager, and utilities for state transitions and validation.

## Features

- Unified state enum for consistent state representation across components
- Thread-safe state transitions with validation
- State categories for grouping related states
- State transition history tracking
- Callback system for state transitions, entry, and exit
- Error condition handling
- Comprehensive state information

## Components

### MowerState Enum

The `MowerState` enum defines all possible states for the mower:

- **Operational States**: IDLE, MOWING, DOCKING, MANUAL, AVOIDING, RETURNING_HOME, DOCKED
- **Error States**: ERROR, EMERGENCY_STOP, STUCK, LOW_BATTERY
- **Special States**: INITIALIZING, SHUTTING_DOWN, PAUSED

Each state has:
- A display name for UI presentation
- A description of the state
- A category (OPERATIONAL, ERROR, SPECIAL)
- A set of allowed transitions to other states

### StateManager Class

The `StateManager` class manages the state of the mower, including:

- Current and previous state tracking
- Validation of state transitions
- Error condition management
- State transition history
- Callback registration and execution

### StateTransitionError Exception

The `StateTransitionError` exception is raised when an invalid state transition is attempted.

## Usage

### Basic State Management

```python
from mower.state_management import MowerState, StateManager

# Create a state manager with the default initial state (INITIALIZING)
state_manager = StateManager()

# Get the current state
current_state = state_manager.current_state
print(f"Current state: {current_state.name}")

# Transition to IDLE state
state_manager.transition_to(MowerState.IDLE)

# Check if a transition is valid
if state_manager.can_transition_to(MowerState.MOWING):
    state_manager.transition_to(MowerState.MOWING)
```

### Using Callbacks

```python
# Define callback functions
def on_enter_mowing(state, context):
    print(f"Entered MOWING state with context: {context}")
    # Start the blade motor
    
def on_exit_mowing(state, context):
    print(f"Exited MOWING state with context: {context}")
    # Stop the blade motor

# Register callbacks
state_manager.register_state_entry_callback(MowerState.MOWING, on_enter_mowing)
state_manager.register_state_exit_callback(MowerState.MOWING, on_exit_mowing)

# Transition to MOWING state
state_manager.transition_to(
    MowerState.MOWING,
    context={"reason": "User requested mowing"}
)
```

### Error Handling

```python
try:
    # Some operation that might fail
    raise RuntimeError("Obstacle detection system failure")
except Exception as e:
    # Set the error condition
    state_manager.set_error_condition(str(e))
    
    # The state manager will automatically transition to ERROR state
    print(f"Current state: {state_manager.current_state.name}")
    print(f"Error condition: {state_manager.error_condition}")

# Attempt to recover
state_manager.transition_to(MowerState.IDLE)
state_manager.clear_error_condition()
```

### Emergency Stop

```python
# Emergency stop can be triggered from any state
state_manager.transition_to(
    MowerState.EMERGENCY_STOP,
    context={"reason": "Emergency stop button pressed"}
)
```

### State History

```python
# Get the transition history
history = state_manager.transition_history

print("State transition history:")
for timestamp, from_state, to_state in history:
    print(f"  {time.ctime(timestamp)}: {from_state.name} -> {to_state.name}")
```

## Integration with Components

To integrate the state management system with existing components:

1. Replace existing state enums with `MowerState`
2. Create a `StateManager` instance in the component
3. Use `transition_to()` instead of direct state assignment
4. Register callbacks for state-dependent actions
5. Use `set_error_condition()` for error handling

## Thread Safety

The state manager is thread-safe and can be used in multi-threaded environments. All state transitions and queries are protected by a lock to ensure consistency.

## Examples

See the `examples.py` file for complete examples of using the state management system.
