"""
User interface interfaces for the autonomous mower.

This module defines interfaces for user interface components used in the
autonomous mower project, such as web interfaces and mobile app interfaces.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class WebInterfaceInterface(ABC):
    """
    Interface for web interface implementations.

    This interface defines the contract that all web interface
    implementations must adhere to.
    """

    @abstractmethod
    def start(self) -> None:
        """
        Start the web interface.

        This method should:
        1. Create the web application
        2. Start the web server
        3. Set up any required communication channels
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """
        Stop the web interface.

        This method should:
        1. Signal the server to shut down
        2. Wait for server threads to complete
        3. Clean up resources
        """
        pass

    @property
    @abstractmethod
    def is_running(self) -> bool:
        """
        Check if the web interface is running.

        Returns:
            bool: True if the web interface is running, False otherwise
        """
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources used by the web interface."""
        pass


class MobileAppInterfaceInterface(ABC):
    """
    Interface for mobile app interface implementations.

    This interface defines the contract that all mobile app interface
    implementations must adhere to.
    """

    @abstractmethod
    def start(self) -> None:
        """
        Start the mobile app interface.

        This method should:
        1. Initialize the communication channel
        2. Start listening for connections
        3. Set up authentication if required
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """
        Stop the mobile app interface.

        This method should:
        1. Close all active connections
        2. Stop listening for new connections
        3. Clean up resources
        """
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """
        Check if any mobile app is connected.

        Returns:
            bool: True if at least one mobile app is connected, False otherwise
        """
        pass

    @abstractmethod
    def send_status_update(self, status: Dict[str, Any]) -> bool:
        """
        Send a status update to connected mobile apps.

        Args:
            status: Status information to send

        Returns:
            bool: True if the update was sent successfully, False otherwise
        """
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources used by the mobile app interface."""
        pass
