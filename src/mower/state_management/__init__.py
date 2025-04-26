"""
State management package for the autonomous mower.

This package provides a unified state management system for the autonomous mower
project. It includes a state enum, state manager, and utilities for state
transitions and validation.

Usage:
    from mower.state_management import MowerState, StateManager
    
    # Create a state manager
    state_manager = StateManager()
    
    # Get the current state
    current_state = state_manager.current_state
    
    # Transition to a new state
    state_manager.transition_to(MowerState.MOWING)
    
    # Check if a transition is valid
    if state_manager.can_transition_to(MowerState.DOCKING):
        state_manager.transition_to(MowerState.DOCKING)
"""

from mower.state_management.states import MowerState, StateCategory
from mower.state_management.state_manager import (
    StateManager,
    StateTransitionError,
)

__all__ = [
    "MowerState",
    "StateCategory",
    "StateManager",
    "StateTransitionError",
]
