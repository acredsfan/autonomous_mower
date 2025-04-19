"""
State definitions for the autonomous mower.

This module defines the states and state categories for the autonomous mower.
It provides a unified state enum that can be used across all components.
"""

from enum import Enum, auto
from typing import Dict, List, Set


class StateCategory(Enum):
    """Categories of mower states."""
    OPERATIONAL = auto()  # Normal operational states
    ERROR = auto()        # Error states
    SPECIAL = auto()      # Special states like initialization, shutdown


class MowerState(Enum):
    """
    Unified state enum for the autonomous mower.
    
    This enum combines all possible states from different components into
    a single, consistent enum that can be used throughout the codebase.
    """
    # Operational states
    IDLE = "idle"                 # Mower is idle, waiting for commands
    MOWING = "mowing"             # Mower is actively mowing
    DOCKING = "docking"           # Mower is returning to dock
    MANUAL = "manual"             # Mower is under manual control
    AVOIDING = "avoiding"         # Mower is avoiding an obstacle
    RETURNING_HOME = "returning_home"  # Mower is returning to home location
    DOCKED = "docked"             # Mower is docked at charging station
    
    # Error states
    ERROR = "error"               # Generic error state
    EMERGENCY_STOP = "emergency_stop"  # Emergency stop activated
    STUCK = "stuck"               # Mower is stuck and needs assistance
    LOW_BATTERY = "low_battery"   # Battery is critically low
    
    # Special states
    INITIALIZING = "initializing"  # Mower is initializing
    SHUTTING_DOWN = "shutting_down"  # Mower is shutting down
    PAUSED = "paused"             # Mower operation is paused
    
    @property
    def category(self) -> StateCategory:
        """Get the category of this state."""
        if self in _STATE_CATEGORIES[StateCategory.OPERATIONAL]:
            return StateCategory.OPERATIONAL
        elif self in _STATE_CATEGORIES[StateCategory.ERROR]:
            return StateCategory.ERROR
        else:
            return StateCategory.SPECIAL
    
    @property
    def display_name(self) -> str:
        """Get a human-readable display name for this state."""
        return _STATE_DISPLAY_NAMES.get(self, self.value.replace('_', ' ').title())
    
    @property
    def description(self) -> str:
        """Get a description of this state."""
        return _STATE_DESCRIPTIONS.get(self, "")
    
    @property
    def allowed_transitions(self) -> Set["MowerState"]:
        """Get the set of states that this state can transition to."""
        return _STATE_TRANSITIONS.get(self, set())


# Define state categories
_STATE_CATEGORIES: Dict[StateCategory, Set[MowerState]] = {
    StateCategory.OPERATIONAL: {
        MowerState.IDLE,
        MowerState.MOWING,
        MowerState.DOCKING,
        MowerState.MANUAL,
        MowerState.AVOIDING,
        MowerState.RETURNING_HOME,
        MowerState.DOCKED,
    },
    StateCategory.ERROR: {
        MowerState.ERROR,
        MowerState.EMERGENCY_STOP,
        MowerState.STUCK,
        MowerState.LOW_BATTERY,
    },
    StateCategory.SPECIAL: {
        MowerState.INITIALIZING,
        MowerState.SHUTTING_DOWN,
        MowerState.PAUSED,
    },
}

# Define display names for states
_STATE_DISPLAY_NAMES: Dict[MowerState, str] = {
    MowerState.IDLE: "Idle",
    MowerState.MOWING: "Mowing",
    MowerState.DOCKING: "Docking",
    MowerState.MANUAL: "Manual Control",
    MowerState.AVOIDING: "Avoiding Obstacle",
    MowerState.RETURNING_HOME: "Returning Home",
    MowerState.DOCKED: "Docked",
    MowerState.ERROR: "Error",
    MowerState.EMERGENCY_STOP: "Emergency Stop",
    MowerState.STUCK: "Stuck",
    MowerState.LOW_BATTERY: "Low Battery",
    MowerState.INITIALIZING: "Initializing",
    MowerState.SHUTTING_DOWN: "Shutting Down",
    MowerState.PAUSED: "Paused",
}

# Define descriptions for states
_STATE_DESCRIPTIONS: Dict[MowerState, str] = {
    MowerState.IDLE: "The mower is idle and waiting for commands.",
    MowerState.MOWING: "The mower is actively mowing the lawn.",
    MowerState.DOCKING: "The mower is returning to the docking station.",
    MowerState.MANUAL: "The mower is under manual control.",
    MowerState.AVOIDING: "The mower is avoiding an obstacle.",
    MowerState.RETURNING_HOME: "The mower is returning to the home location.",
    MowerState.DOCKED: "The mower is docked at the charging station.",
    MowerState.ERROR: "The mower has encountered an error.",
    MowerState.EMERGENCY_STOP: "The mower has been emergency stopped.",
    MowerState.STUCK: "The mower is stuck and needs assistance.",
    MowerState.LOW_BATTERY: "The mower's battery is critically low.",
    MowerState.INITIALIZING: "The mower is initializing its systems.",
    MowerState.SHUTTING_DOWN: "The mower is shutting down.",
    MowerState.PAUSED: "The mower operation is paused.",
}

# Define allowed state transitions
_STATE_TRANSITIONS: Dict[MowerState, Set[MowerState]] = {
    MowerState.INITIALIZING: {
        MowerState.IDLE,
        MowerState.ERROR,
        MowerState.EMERGENCY_STOP,
    },
    MowerState.IDLE: {
        MowerState.MOWING,
        MowerState.MANUAL,
        MowerState.DOCKING,
        MowerState.SHUTTING_DOWN,
        MowerState.ERROR,
        MowerState.EMERGENCY_STOP,
    },
    MowerState.MOWING: {
        MowerState.IDLE,
        MowerState.PAUSED,
        MowerState.AVOIDING,
        MowerState.RETURNING_HOME,
        MowerState.DOCKING,
        MowerState.ERROR,
        MowerState.EMERGENCY_STOP,
        MowerState.STUCK,
        MowerState.LOW_BATTERY,
    },
    MowerState.AVOIDING: {
        MowerState.MOWING,
        MowerState.IDLE,
        MowerState.RETURNING_HOME,
        MowerState.ERROR,
        MowerState.EMERGENCY_STOP,
        MowerState.STUCK,
    },
    MowerState.RETURNING_HOME: {
        MowerState.IDLE,
        MowerState.DOCKED,
        MowerState.AVOIDING,
        MowerState.ERROR,
        MowerState.EMERGENCY_STOP,
        MowerState.STUCK,
        MowerState.LOW_BATTERY,
    },
    MowerState.DOCKING: {
        MowerState.IDLE,
        MowerState.DOCKED,
        MowerState.AVOIDING,
        MowerState.ERROR,
        MowerState.EMERGENCY_STOP,
        MowerState.STUCK,
    },
    MowerState.DOCKED: {
        MowerState.IDLE,
        MowerState.SHUTTING_DOWN,
        MowerState.ERROR,
        MowerState.EMERGENCY_STOP,
    },
    MowerState.MANUAL: {
        MowerState.IDLE,
        MowerState.ERROR,
        MowerState.EMERGENCY_STOP,
    },
    MowerState.PAUSED: {
        MowerState.MOWING,
        MowerState.IDLE,
        MowerState.RETURNING_HOME,
        MowerState.ERROR,
        MowerState.EMERGENCY_STOP,
    },
    MowerState.ERROR: {
        MowerState.IDLE,
        MowerState.EMERGENCY_STOP,
        MowerState.SHUTTING_DOWN,
    },
    MowerState.EMERGENCY_STOP: {
        MowerState.IDLE,
        MowerState.SHUTTING_DOWN,
    },
    MowerState.STUCK: {
        MowerState.IDLE,
        MowerState.MOWING,
        MowerState.RETURNING_HOME,
        MowerState.ERROR,
        MowerState.EMERGENCY_STOP,
    },
    MowerState.LOW_BATTERY: {
        MowerState.IDLE,
        MowerState.DOCKING,
        MowerState.RETURNING_HOME,
        MowerState.ERROR,
        MowerState.EMERGENCY_STOP,
    },
    MowerState.SHUTTING_DOWN: {
        # No transitions from shutting down
    },
}


def get_all_states() -> List[MowerState]:
    """Get a list of all mower states."""
    return list(MowerState)


def get_states_by_category(category: StateCategory) -> List[MowerState]:
    """
    Get a list of states in the specified category.
    
    Args:
        category: The category to get states for
        
    Returns:
        List[MowerState]: List of states in the category
    """
    return list(_STATE_CATEGORIES.get(category, set()))


def is_valid_transition(from_state: MowerState, to_state: MowerState) -> bool:
    """
    Check if a transition from one state to another is valid.
    
    Args:
        from_state: The state to transition from
        to_state: The state to transition to
        
    Returns:
        bool: True if the transition is valid, False otherwise
    """
    # Emergency stop can be triggered from any state
    if to_state == MowerState.EMERGENCY_STOP:
        return True
    
    # Check if the transition is allowed
    allowed = _STATE_TRANSITIONS.get(from_state, set())
    return to_state in allowed