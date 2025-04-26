"""
State manager for the autonomous mower.

This module provides a state manager class that handles state transitions
and validation for the autonomous mower.
"""

import threading
import time
from typing import Callable, Dict, List, Optional, Set, Tuple, Any

from mower.state_management.states import MowerState, is_valid_transition
from mower.utilities.logger_config import LoggerConfigInfo


# Initialize logger
logger = LoggerConfigInfo.get_logger(__name__)


class StateTransitionError(Exception):
    """Exception raised when an invalid state transition is attempted."""

    pass


class StateManager:
    """
    State manager for the autonomous mower.

    This class manages the state of the mower, including state transitions,
    validation, and event handling.

    Attributes:
        current_state: The current state of the mower
        previous_state: The previous state of the mower
        error_condition: Description of the current error condition (if any)
        transition_history: List of state transitions with timestamps
    """

    def __init__(self, initial_state: MowerState = MowerState.INITIALIZING):
        """
        Initialize the state manager.

        Args:
            initial_state: The initial state of the mower
        """
        self._current_state = initial_state
        self._previous_state = None
        self._error_condition = None
        self._transition_history: List[
            Tuple[float, MowerState, MowerState]
        ] = []
        self._state_entry_time = time.time()
        self._lock = threading.RLock()
        self._transition_callbacks: Dict[
            Tuple[MowerState, MowerState], List[Callable]
        ] = {}
        self._state_entry_callbacks: Dict[MowerState, List[Callable]] = {}
        self._state_exit_callbacks: Dict[MowerState, List[Callable]] = {}

        logger.info(
            f"State manager initialized with state: {initial_state.name}"
        )

    @property
    def current_state(self) -> MowerState:
        """Get the current state of the mower."""
        with self._lock:
            return self._current_state

    @property
    def previous_state(self) -> Optional[MowerState]:
        """Get the previous state of the mower."""
        with self._lock:
            return self._previous_state

    @property
    def error_condition(self) -> Optional[str]:
        """Get the current error condition."""
        with self._lock:
            return self._error_condition

    @property
    def time_in_current_state(self) -> float:
        """Get the time (in seconds) spent in the current state."""
        with self._lock:
            return time.time() - self._state_entry_time

    @property
    def transition_history(
        self,
    ) -> List[Tuple[float, MowerState, MowerState]]:
        """Get the history of state transitions."""
        with self._lock:
            return list(self._transition_history)

    def can_transition_to(self, target_state: MowerState) -> bool:
        """
        Check if a transition to the target state is valid.

        Args:
            target_state: The state to transition to

        Returns:
            bool: True if the transition is valid, False otherwise
        """
        with self._lock:
            return is_valid_transition(self._current_state, target_state)

    def transition_to(
        self,
        target_state: MowerState,
        error_condition: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Transition to a new state.

        Args:
            target_state: The state to transition to
            error_condition: Optional error condition (for error states)
            context: Optional context information for the transition

        Returns:
            bool: True if the transition was successful, False otherwise

        Raises:
            StateTransitionError: If the transition is invalid
        """
        if not context:
            context = {}

        with self._lock:
            # Check if the transition is valid
            if not self.can_transition_to(target_state):
                error_msg = (
                    f"Invalid state transition: {self._current_state.name} -> "
                    f"{target_state.name}"
                )
                logger.error(error_msg)
                raise StateTransitionError(error_msg)

            # Save the previous state
            previous_state = self._current_state

            # Update the error condition if provided
            if error_condition is not None:
                self._error_condition = error_condition
            elif target_state != MowerState.ERROR:
                # Clear error condition if transitioning to a non-error state
                self._error_condition = None

            # Call exit callbacks for the current state
            self._call_state_exit_callbacks(previous_state, context)

            # Update the state
            self._previous_state = previous_state
            self._current_state = target_state
            self._state_entry_time = time.time()

            # Record the transition
            transition = (time.time(), previous_state, target_state)
            self._transition_history.append(transition)

            # Trim history if it gets too long
            if len(self._transition_history) > 100:
                self._transition_history = self._transition_history[-100:]

            # Call transition callbacks
            self._call_transition_callbacks(
                previous_state, target_state, context
            )

            # Call entry callbacks for the new state
            self._call_state_entry_callbacks(target_state, context)

            logger.info(
                f"State transition: {previous_state.name} -> {target_state.name}"
            )

            return True

    def set_error_condition(self, error_condition: str) -> None:
        """
        Set the current error condition.

        Args:
            error_condition: Description of the error condition
        """
        with self._lock:
            self._error_condition = error_condition

            # If not already in an error state, transition to ERROR
            if (
                self._current_state != MowerState.ERROR
                and self._current_state != MowerState.EMERGENCY_STOP
            ):
                try:
                    self.transition_to(
                        MowerState.ERROR, error_condition=error_condition
                    )
                except StateTransitionError:
                    logger.error(
                        f"Failed to transition to ERROR state from "
                        f"{self._current_state.name}"
                    )

    def clear_error_condition(self) -> None:
        """Clear the current error condition."""
        with self._lock:
            self._error_condition = None

    def register_transition_callback(
        self,
        from_state: MowerState,
        to_state: MowerState,
        callback: Callable[[MowerState, MowerState, Dict[str, Any]], None],
    ) -> None:
        """
        Register a callback for a specific state transition.

        Args:
            from_state: The state to transition from
            to_state: The state to transition to
            callback: The callback function to call when the transition occurs
        """
        with self._lock:
            transition = (from_state, to_state)
            if transition not in self._transition_callbacks:
                self._transition_callbacks[transition] = []
            self._transition_callbacks[transition].append(callback)

    def register_state_entry_callback(
        self,
        state: MowerState,
        callback: Callable[[MowerState, Dict[str, Any]], None],
    ) -> None:
        """
        Register a callback for when a state is entered.

        Args:
            state: The state to register the callback for
            callback: The callback function to call when the state is entered
        """
        with self._lock:
            if state not in self._state_entry_callbacks:
                self._state_entry_callbacks[state] = []
            self._state_entry_callbacks[state].append(callback)

    def register_state_exit_callback(
        self,
        state: MowerState,
        callback: Callable[[MowerState, Dict[str, Any]], None],
    ) -> None:
        """
        Register a callback for when a state is exited.

        Args:
            state: The state to register the callback for
            callback: The callback function to call when the state is exited
        """
        with self._lock:
            if state not in self._state_exit_callbacks:
                self._state_exit_callbacks[state] = []
            self._state_exit_callbacks[state].append(callback)

    def _call_transition_callbacks(
        self,
        from_state: MowerState,
        to_state: MowerState,
        context: Dict[str, Any],
    ) -> None:
        """
        Call all registered callbacks for a state transition.

        Args:
            from_state: The state being transitioned from
            to_state: The state being transitioned to
            context: Context information for the transition
        """
        transition = (from_state, to_state)
        callbacks = self._transition_callbacks.get(transition, [])

        for callback in callbacks:
            try:
                callback(from_state, to_state, context)
            except Exception as e:
                logger.error(
                    f"Error in transition callback {callback.__name__}: {e}"
                )

    def _call_state_entry_callbacks(
        self, state: MowerState, context: Dict[str, Any]
    ) -> None:
        """
        Call all registered callbacks for entering a state.

        Args:
            state: The state being entered
            context: Context information for the transition
        """
        callbacks = self._state_entry_callbacks.get(state, [])

        for callback in callbacks:
            try:
                callback(state, context)
            except Exception as e:
                logger.error(
                    f"Error in state entry callback {callback.__name__}: {e}"
                )

    def _call_state_exit_callbacks(
        self, state: MowerState, context: Dict[str, Any]
    ) -> None:
        """
        Call all registered callbacks for exiting a state.

        Args:
            state: The state being exited
            context: Context information for the transition
        """
        callbacks = self._state_exit_callbacks.get(state, [])

        for callback in callbacks:
            try:
                callback(state, context)
            except Exception as e:
                logger.error(
                    f"Error in state exit callback {callback.__name__}: {e}"
                )

    def get_state_info(self) -> Dict[str, Any]:
        """
        Get information about the current state.

        Returns:
            Dict[str, Any]: Dictionary with state information
        """
        with self._lock:
            return {
                "current_state": self._current_state,
                "current_state_name": self._current_state.name,
                "current_state_display_name": self._current_state.display_name,
                "current_state_description": self._current_state.description,
                "current_state_category": self._current_state.category.name,
                "previous_state": (
                    self._previous_state.name
                    if self._previous_state
                    else None
                ),
                "error_condition": self._error_condition,
                "time_in_current_state": self.time_in_current_state,
                "allowed_transitions": [
                    state.name
                    for state in self._current_state.allowed_transitions
                ],
            }
