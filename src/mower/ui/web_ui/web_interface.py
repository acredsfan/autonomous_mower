"""Web interface for the autonomous mower."""

from typing import TYPE_CHECKING

from mower.utilities import LoggerConfigInfo

if TYPE_CHECKING:
    from mower.mower import Mower


class WebInterface:
    """Web interface for controlling the mower."""

    def __init__(self, mower: 'Mower'):
        """Initialize the web interface.

        Args:
            mower: The mower instance to control.
        """
        self.logger = LoggerConfigInfo.get_logger(__name__)
        self.mower = mower

    def start(self) -> None:
        """Start the web interface."""
        self.logger.info("Starting web interface...")
        # TODO: Implement web interface startup

    def stop(self) -> None:
        """Stop the web interface."""
        self.logger.info("Stopping web interface...")
        # TODO: Implement web interface shutdown 