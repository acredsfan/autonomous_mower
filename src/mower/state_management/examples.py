"""
Examples of using the state management system.

This module provides examples of how to use the state management system
in various scenarios. These examples can be used as templates for
implementing consistent state management patterns throughout the codebase.
"""

import time
from typing import Any, Dict

from mower.state_management import MowerState, StateManager, StateTransitionError


def basic_state_management_example():
    """Example of basic state management."""
    # Create a state manager with the default initial state (INITIALIZING)
    state_manager = StateManager()

    # Get the current state
    current_state = state_manager.current_state
    print(f"Current state: {current_state.name}")

    # Transition to IDLE state
    try:
        state_manager.transition_to(MowerState.IDLE)
        print(f"Transitioned to: {state_manager.current_state.name}")
    except StateTransitionError as e:
        print(f"Error: {e}")

    # Check if a transition is valid
    can_transition = state_manager.can_transition_to(MowerState.MOWING)
    print(f"Can transition to MOWING: {can_transition}")

    # Transition to MOWING state
    if can_transition:
        state_manager.transition_to(MowerState.MOWING)
        print(f"Transitioned to: {state_manager.current_state.name}")

    # Try an invalid transition
    try:
        state_manager.transition_to(MowerState.DOCKED)
        print(f"Transitioned to: {state_manager.current_state.name}")
    except StateTransitionError as e:
        print(f"Error: {e}")

    # Get state information
    state_info = state_manager.get_state_info()
    print("\nState information:")
    for key, value in state_info.items():
        print(f"  {key}: {value}")


def state_callbacks_example():
    """Example of using state callbacks."""
    # Create a state manager
    state_manager = StateManager(initial_state=MowerState.IDLE)

    # Define callback functions
    def on_enter_mowing(state: MowerState, context: Dict[str, Any]):
        print(f"Entered MOWING state with context: {context}")
        # Start the blade motor
        print("Starting blade motor...")

    def on_exit_mowing(state: MowerState, context: Dict[str, Any]):
        print(f"Exited MOWING state with context: {context}")
        # Stop the blade motor
        print("Stopping blade motor...")

    def on_transition_to_error(from_state: MowerState, to_state: MowerState, context: Dict[str, Any]):
        print(f"Transitioning from {from_state.name} to {to_state.name}")
        print(f"Error condition: {context.get('error_message', 'Unknown error')}")

    # Register callbacks
    state_manager.register_state_entry_callback(MowerState.MOWING, on_enter_mowing)
    state_manager.register_state_exit_callback(MowerState.MOWING, on_exit_mowing)
    state_manager.register_transition_callback(MowerState.MOWING, MowerState.ERROR, on_transition_to_error)

    # Transition to MOWING state
    state_manager.transition_to(MowerState.MOWING, context={"reason": "User requested mowing"})

    # Simulate an error
    state_manager.transition_to(
        MowerState.ERROR,
        error_condition="Blade motor overheated",
        context={
            "error_message": "Blade motor overheated",
            "temperature": 85,
        },
    )


def error_handling_example():
    """Example of error handling with state management."""
    # Create a state manager
    state_manager = StateManager(initial_state=MowerState.IDLE)

    # Transition to MOWING state
    state_manager.transition_to(MowerState.MOWING)

    # Simulate detecting an error
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
    try:
        # Try to transition back to IDLE
        state_manager.transition_to(MowerState.IDLE)

        # Clear the error condition
        state_manager.clear_error_condition()

        print(f"Recovered to state: {state_manager.current_state.name}")
        print(f"Error condition: {state_manager.error_condition}")
    except StateTransitionError as e:
        print(f"Could not recover: {e}")


def emergency_stop_example():
    """Example of emergency stop handling."""
    # Create a state manager
    state_manager = StateManager(initial_state=MowerState.MOWING)

    # Define emergency stop callback
    def on_emergency_stop(state: MowerState, context: Dict[str, Any]):
        print("EMERGENCY STOP ACTIVATED!")
        print("Stopping all motors immediately...")
        print(f"Reason: {context.get('reason', 'Unknown')}")

    # Register callback
    state_manager.register_state_entry_callback(MowerState.EMERGENCY_STOP, on_emergency_stop)

    # Simulate emergency stop button press
    state_manager.transition_to(
        MowerState.EMERGENCY_STOP,
        context={
            "reason": "Emergency stop button pressed",
            "user_initiated": True,
        },
    )

    # Check state after emergency stop
    print(f"Current state: {state_manager.current_state.name}")
    print(f"Previous state: {state_manager.previous_state.name}")

    # Attempt to resume normal operation
    try:
        # Can only transition to IDLE from EMERGENCY_STOP
        state_manager.transition_to(MowerState.IDLE)
        print(f"Resumed operation in state: {state_manager.current_state.name}")
    except StateTransitionError as e:
        print(f"Could not resume: {e}")


def state_history_example():
    """Example of using state transition history."""
    # Create a state manager
    state_manager = StateManager(initial_state=MowerState.INITIALIZING)

    # Perform several transitions
    state_manager.transition_to(MowerState.IDLE)
    time.sleep(0.1)  # Small delay to make timestamps different

    state_manager.transition_to(MowerState.MOWING)
    time.sleep(0.1)

    state_manager.transition_to(MowerState.AVOIDING)
    time.sleep(0.1)

    state_manager.transition_to(MowerState.MOWING)
    time.sleep(0.1)

    state_manager.transition_to(MowerState.RETURNING_HOME)
    time.sleep(0.1)

    state_manager.transition_to(MowerState.DOCKED)

    # Get the transition history
    history = state_manager.transition_history

    print("State transition history:")
    for timestamp, from_state, to_state in history:
        print(f"  {time.ctime(timestamp)}: {from_state.name} -> {to_state.name}")


if __name__ == "__main__":
    print("\n=== Basic State Management Example ===")
    basic_state_management_example()

    print("\n=== State Callbacks Example ===")
    state_callbacks_example()

    print("\n=== Error Handling Example ===")
    error_handling_example()

    print("\n=== Emergency Stop Example ===")
    emergency_stop_example()

    print("\n=== State History Example ===")
    state_history_example()
